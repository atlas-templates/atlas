"""Manage shared linked-data templates in docs/templates/.

Usage:
    python .github/scripts/templates.py check-issue  # validate a submission and write a report for the submitter
    python .github/scripts/templates.py from-issue   # add the template from an approved issue
    python .github/scripts/templates.py build-index  # regenerate docs/templates/index.json

`check-issue` and `from-issue` read the issue data from environment variables (ISSUE_BODY,
ISSUE_NUMBER, ISSUE_AUTHOR and optionally GH_TOKEN) so user input never ends up in a shell command.
Messages shown to users are in Dutch, matching the rest of the documentation.
Only the standard library is used.
"""

import datetime
import io
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT_DIR / "docs" / "templates"
INDEX_FILE = TEMPLATES_DIR / "index.json"
METADATA_FILE_NAME = "template.json"

MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024  # 50 MB, guards against zip bombs
ATTACHMENT_URL_PATTERN = re.compile(r"https://github\.com/user-attachments/files/\d+/[^\s)\]\"'<>]+")

# Atlas components a template can contain. The submitter ticks which ones are in the zip;
# the zip must then contain exactly one export file for each ticked component and nothing else.
EXPORT_PREFIXES = ("layers", "authorizations", "tables", "sources", "categories")
EXPORT_FILE_PATTERN = re.compile(r"^(?P<prefix>[a-z]+)_.+\.json$", re.IGNORECASE)
CHECKED_OPTION_PATTERN = re.compile(r"^\s*[-*]\s*\[[xX]\]\s*(?P<label>.+)$")

# Marker that identifies the automatic check comment, so it can be updated instead of duplicated.
CHECK_COMMENT_MARKER = "<!-- template-check -->"

# Labels must match the ones in .github/ISSUE_TEMPLATE/template-indienen.yml
ISSUE_FORM_LABELS = {
    "name": "Naam van de template",
    "description": "Beschrijving",
    "atlas_version": "Atlas-versie",
    "included_files": "Bestanden in de zip",
    "attachment": "Zip-bestand",
}


class TemplateValidationError(Exception):
    """Error reported back to the submitter as a comment on the issue."""


def parse_issue_body(body: str) -> dict:
    """Read the fields of a GitHub issue form ('### Label' followed by its value)."""
    sections = {}
    current_label = None
    for line in body.replace("\r\n", "\n").split("\n"):
        heading = re.match(r"^###\s+(.+?)\s*$", line)
        if heading:
            current_label = heading.group(1)
            sections[current_label] = []
        elif current_label is not None:
            sections[current_label].append(line)

    fields = {}
    for key, label in ISSUE_FORM_LABELS.items():
        value = "\n".join(sections.get(label, [])).strip()
        fields[key] = "" if value == "_No response_" else value
    return fields


def parse_checked_export_prefixes(checkbox_text: str) -> list[str]:
    """Return the export prefixes whose checkbox is ticked, in the canonical order."""
    checked = set()
    for line in checkbox_text.split("\n"):
        match = CHECKED_OPTION_PATTERN.match(line)
        if not match:
            continue
        for prefix in EXPORT_PREFIXES:
            if re.search(rf"\b{prefix}_", match.group("label"), re.IGNORECASE):
                checked.add(prefix)
    return [prefix for prefix in EXPORT_PREFIXES if prefix in checked]


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:60].strip("-") or "template"


def zip_file_name_from_url(url: str) -> str:
    name = urllib.parse.unquote(url.rstrip("/").rsplit("/", 1)[-1])
    stem, dot, extension = name.rpartition(".")
    if not dot or extension.lower() != "zip":
        raise TemplateValidationError("Alleen een .zip-bestand is toegestaan.")
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", stem).strip("-.") or "template"
    return stem[:80] + ".zip"


def download_attachment(url: str, token: str | None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "atlas-templates-action"})
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(MAX_DOWNLOAD_BYTES + 1)
    except urllib.error.URLError:
        raise TemplateValidationError("Het zip-bestand kon niet worden gedownload. Upload het opnieuw.")
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise TemplateValidationError(f"Het bestand is groter dan {MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB.")
    if not data:
        raise TemplateValidationError("Het bestand is leeg.")
    return data


def is_ignorable_zip_entry(entry: zipfile.ZipInfo) -> bool:
    """Directories and metadata that operating systems add to zip files."""
    base_name = entry.filename.rsplit("/", 1)[-1]
    return entry.is_dir() or entry.filename.startswith("__MACOSX/") or base_name in {".DS_Store", "Thumbs.db"}


def validate_template_zip(data: bytes, expected_prefixes: list[str]) -> list[str]:
    """Check that the zip holds exactly one export file per expected prefix. Returns their names."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise TemplateValidationError("Het bestand is geen geldig zip-bestand.")

    with archive:
        entries = [entry for entry in archive.infolist() if not is_ignorable_zip_entry(entry)]
        if sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED_BYTES:
            raise TemplateValidationError("De inhoud van het zip-bestand is te groot.")

        files_by_prefix = {prefix: [] for prefix in expected_prefixes}
        unexpected_files = []
        for entry in entries:
            base_name = entry.filename.rsplit("/", 1)[-1]
            match = EXPORT_FILE_PATTERN.match(base_name)
            prefix = match.group("prefix").lower() if match else None
            if prefix in files_by_prefix:
                files_by_prefix[prefix].append(entry)
            else:
                unexpected_files.append(entry.filename)

        problems = []
        missing = [f"`{prefix}_datum.json`" for prefix, found in files_by_prefix.items() if not found]
        if missing:
            problems.append("Ontbrekende bestanden: " + ", ".join(missing) + ".")
        duplicates = [f"`{prefix}_*.json`" for prefix, found in files_by_prefix.items() if len(found) > 1]
        if duplicates:
            problems.append("Meer dan één bestand voor: " + ", ".join(duplicates) + ".")
        if unexpected_files:
            listed = ", ".join(f"`{name}`" for name in sorted(unexpected_files)[:10])
            problems.append(
                "Bestanden die niet zijn aangevinkt of geen exportbestand zijn: "
                + listed
                + ". Vink ze aan bij *Bestanden in de zip* of haal ze uit de zip."
            )
        if problems:
            raise TemplateValidationError("\n".join(f"- {problem}" for problem in problems))

        export_entries = [found[0] for found in files_by_prefix.values()]
        for entry in export_entries:
            try:
                json.loads(archive.read(entry).decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise TemplateValidationError(f"`{entry.filename}` is geen geldig JSON-bestand.")

    return sorted(entry.filename.rsplit("/", 1)[-1] for entry in export_entries)


def unique_template_dir(slug: str) -> Path:
    candidate = TEMPLATES_DIR / slug
    counter = 2
    while candidate.exists():
        candidate = TEMPLATES_DIR / f"{slug}-{counter}"
        counter += 1
    return candidate


def validate_submission(fields: dict) -> tuple[str, bytes, list[str]]:
    """Validate an issue submission. Returns the zip file name, its data and the export files it contains."""
    if not fields["name"]:
        raise TemplateValidationError("Het veld *Naam van de template* is leeg.")
    if not fields["description"]:
        raise TemplateValidationError("Het veld *Beschrijving* is leeg.")

    expected_prefixes = parse_checked_export_prefixes(fields["included_files"])
    if not expected_prefixes:
        raise TemplateValidationError("Vink bij *Bestanden in de zip* aan welke exportbestanden in de zip zitten.")

    urls = set(ATTACHMENT_URL_PATTERN.findall(fields["attachment"]))
    if not urls:
        raise TemplateValidationError(
            "Er is geen zip-bestand gevonden in het veld *Zip-bestand*. Sleep het bestand in dat veld."
        )
    if len(urls) > 1:
        raise TemplateValidationError("Er staan meerdere bestanden in het veld *Zip-bestand*. Upload er precies één.")

    url = urls.pop()
    zip_file_name = zip_file_name_from_url(url)
    data = download_attachment(url, os.environ.get("GH_TOKEN"))
    contents = validate_template_zip(data, expected_prefixes)
    return zip_file_name, data, contents


def add_template_from_issue() -> Path:
    fields = parse_issue_body(os.environ.get("ISSUE_BODY", ""))
    zip_file_name, data, contents = validate_submission(fields)

    target_dir = unique_template_dir(slugify(fields["name"]))
    target_dir.mkdir(parents=True)
    (target_dir / zip_file_name).write_bytes(data)

    metadata = {
        "name": fields["name"][:120],
        "description": fields["description"][:2000],
        "atlas_version": fields["atlas_version"][:40],
        "author": os.environ.get("ISSUE_AUTHOR", ""),
        "issue": int(os.environ["ISSUE_NUMBER"]) if os.environ.get("ISSUE_NUMBER") else None,
        "added": datetime.datetime.now(tz=datetime.UTC).date().isoformat(),
        "file": zip_file_name,
        "contents": contents,
    }
    (target_dir / METADATA_FILE_NAME).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target_dir


def build_index() -> list[dict]:
    templates = []
    for metadata_file in sorted(TEMPLATES_DIR.glob(f"*/{METADATA_FILE_NAME}")):
        template_dir = metadata_file.parent
        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            print(f"Skipped, invalid JSON in {metadata_file}: {error}", file=sys.stderr)
            continue
        file_path = template_dir / metadata.get("file", "")
        if not metadata.get("file") or not file_path.is_file():
            print(f"Skipped, file missing for {template_dir.name}", file=sys.stderr)
            continue
        templates.append({
            "id": template_dir.name,
            "name": metadata.get("name") or template_dir.name,
            "description": metadata.get("description", ""),
            "atlas_version": metadata.get("atlas_version", ""),
            "author": metadata.get("author", ""),
            "issue": metadata.get("issue"),
            "added": metadata.get("added", ""),
            "file": metadata["file"],
            "contents": metadata.get("contents", []),
            "path": f"{template_dir.name}/{metadata['file']}",
            "size": file_path.stat().st_size,
        })

    templates.sort(key=lambda template: (template["added"], template["name"]), reverse=True)
    INDEX_FILE.write_text(
        json.dumps({"templates": templates}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return templates


def check_issue() -> bool:
    """Validate a submission and write a Markdown comment for the submitter to CHECK_REPORT_FILE."""
    fields = parse_issue_body(os.environ.get("ISSUE_BODY", ""))
    try:
        _, _, contents = validate_submission(fields)
    except TemplateValidationError as error:
        passed = False
        report = (
            "❌ **Automatische controle mislukt**\n\n"
            f"{error}\n\n"
            "Pas je inzending aan via **···** → **Edit** rechtsboven in je issue: upload een nieuwe zip "
            "of pas de vinkjes aan. Na het opslaan wordt de controle automatisch opnieuw uitgevoerd."
        )
    else:
        passed = True
        listed = "\n".join(f"- `{name}`" for name in contents)
        report = (
            "✅ **Automatische controle geslaagd**\n\n"
            f"De zip bevat:\n{listed}\n\n"
            "Een beheerder bekijkt je inzending nog. Na goedkeuring verschijnt de template op de templatepagina."
        )

    print(report)
    if report_file := os.environ.get("CHECK_REPORT_FILE"):
        Path(report_file).write_text(f"{CHECK_COMMENT_MARKER}\n{report}\n", encoding="utf-8")
    return passed


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if command == "check-issue":
            return 0 if check_issue() else 1
        if command == "from-issue":
            target_dir = add_template_from_issue()
            print(f"Template added in {target_dir.relative_to(ROOT_DIR)}")
            build_index()
        elif command == "build-index":
            print(f"index.json updated with {len(build_index())} templates")
        else:
            print(__doc__)
            return 2
    except TemplateValidationError as error:
        message = str(error)
        print(message, file=sys.stderr)
        if error_file := os.environ.get("ERROR_FILE"):
            Path(error_file).write_text(message, encoding="utf-8")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
