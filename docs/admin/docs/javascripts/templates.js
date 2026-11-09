/*
 * Templates page: loads docs/templates/index.json live from GitHub and renders a
 * searchable list with download buttons. The URLs are configured as data attributes
 * on #atlas-templates in templates.md. Text shown to users is in Dutch.
 */
(function () {
  "use strict";

  function createElement(tag, className, text) {
    var element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined && text !== null) element.textContent = text;
    return element;
  }

  function formatFileSize(bytes) {
    if (!bytes && bytes !== 0) return "";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + " kB";
    return (bytes / (1024 * 1024)).toFixed(1).replace(".", ",") + " MB";
  }

  function formatDate(isoDate) {
    if (!isoDate) return "";
    var date = new Date(isoDate + "T00:00:00");
    if (isNaN(date)) return isoDate;
    return date.toLocaleDateString("nl-NL", { day: "numeric", month: "long", year: "numeric" });
  }

  function encodePath(path) {
    return path.split("/").map(encodeURIComponent).join("/");
  }

  function downloadFile(url, fileName, button) {
    // The download attribute is ignored for cross-origin links, so fetch the file as a blob first.
    var originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = "Downloaden…";
    fetch(url)
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.blob();
      })
      .then(function (blob) {
        var objectUrl = URL.createObjectURL(blob);
        var link = document.createElement("a");
        link.href = objectUrl;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(function () { URL.revokeObjectURL(objectUrl); }, 1000);
      })
      .catch(function () {
        // Fall back to opening the file directly, e.g. when the fetch is blocked.
        window.open(url, "_blank", "noopener");
      })
      .finally(function () {
        button.disabled = false;
        button.textContent = originalLabel;
      });
  }

  var URL_PATTERN = /https?:\/\/[^\s<>"']+/g;

  // Builds the description from text nodes and links only, so submitted HTML is never interpreted.
  function createDescription(description) {
    var paragraph = createElement("p", "tpl-card__description");
    var text = description.replace(/<img\b[^>]*>/gi, "").replace(/^\s+/, "");
    var lastIndex = 0;
    text.replace(URL_PATTERN, function (match, offset) {
      var url = match.replace(/[.,;:!?)]+$/, "");
      paragraph.appendChild(document.createTextNode(text.slice(lastIndex, offset)));
      paragraph.appendChild(createExternalLink(null, url, url));
      lastIndex = offset + url.length;
      return match;
    });
    paragraph.appendChild(document.createTextNode(text.slice(lastIndex)));
    return paragraph;
  }

  function createImages(template, config) {
    var gallery = createElement("div", "tpl-card__images");
    template.images.forEach(function (image) {
      var imageUrl = config.filesUrl + encodePath(image.path);
      var link = createExternalLink("tpl-card__image-link", null, imageUrl);
      var img = createElement("img", "tpl-card__image");
      img.src = imageUrl;
      img.alt = image.alt || template.name;
      img.loading = "lazy";
      link.appendChild(img);
      gallery.appendChild(link);
    });
    return gallery;
  }

  function createExternalLink(className, text, href) {
    var link = createElement("a", className, text);
    link.href = href;
    link.target = "_blank";
    link.rel = "noopener";
    return link;
  }

  function renderTemplateCard(template, config) {
    var card = createElement("article", "tpl-card");
    card.appendChild(createElement("h3", "tpl-card__title", template.name));

    if (template.description) {
      card.appendChild(createDescription(template.description));
    }

    if (Array.isArray(template.images) && template.images.length) {
      card.appendChild(createImages(template, config));
    }

    var metaParts = [];
    if (template.author) metaParts.push("door " + template.author);
    if (template.added) metaParts.push(formatDate(template.added));
    if (template.atlas_version) metaParts.push("Atlas " + template.atlas_version);
    metaParts.push(template.file + (template.size ? " (" + formatFileSize(template.size) + ")" : ""));
    card.appendChild(createElement("p", "tpl-card__meta", metaParts.join(" · ")));

    if (Array.isArray(template.contents) && template.contents.length) {
      card.appendChild(createElement("p", "tpl-card__contents", "Bevat: " + template.contents.join(", ")));
    }

    var actions = createElement("div", "tpl-card__actions");
    var downloadButton = createElement("button", "md-button md-button--primary tpl-card__download", "Downloaden");
    downloadButton.type = "button";
    var fileUrl = config.filesUrl + encodePath(template.path);
    downloadButton.addEventListener("click", function () {
      downloadFile(fileUrl, template.file, downloadButton);
    });
    actions.appendChild(downloadButton);
    actions.appendChild(
      createExternalLink("md-button tpl-card__link", "Bekijken op GitHub", config.browseUrl + encodePath(template.id))
    );
    if (template.issue && config.issueUrl) {
      actions.appendChild(
        createExternalLink("tpl-card__issue", "Inzending #" + template.issue, config.issueUrl + template.issue)
      );
    }
    card.appendChild(actions);
    return card;
  }

  function renderTemplateList(container, templates, config) {
    container.textContent = "";

    if (!templates.length) {
      container.appendChild(createElement("p", "tpl-status", "Er zijn nog geen templates gedeeld. Wees de eerste!"));
      return;
    }

    var searchInput = createElement("input", "tpl-search");
    searchInput.type = "search";
    searchInput.placeholder = "Zoek op naam, beschrijving, auteur of Atlas-versie";
    searchInput.setAttribute("aria-label", "Templates zoeken");
    container.appendChild(searchInput);

    var resultCount = createElement("p", "tpl-count");
    container.appendChild(resultCount);
    var list = createElement("div", "tpl-list");
    container.appendChild(list);

    var cards = templates.map(function (template) {
      return {
        element: renderTemplateCard(template, config),
        searchText: [template.name, template.description, template.author, template.atlas_version, template.file]
          .join(" ")
          .toLowerCase(),
      };
    });

    function applySearch() {
      var searchTerms = searchInput.value.toLowerCase().split(/\s+/).filter(Boolean);
      var shownCount = 0;
      list.textContent = "";
      cards.forEach(function (card) {
        var matches = searchTerms.every(function (term) { return card.searchText.indexOf(term) !== -1; });
        if (!matches) return;
        list.appendChild(card.element);
        shownCount++;
      });
      resultCount.textContent = shownCount === templates.length
        ? templates.length + (templates.length === 1 ? " template" : " templates")
        : shownCount + " van " + templates.length + " templates";
      if (!shownCount) {
        list.appendChild(createElement("p", "tpl-status", "Geen templates gevonden met deze zoekopdracht."));
      }
    }

    searchInput.addEventListener("input", applySearch);
    applySearch();
  }

  function renderLoadError(container, config) {
    container.textContent = "";
    var message = createElement(
      "p",
      "tpl-status tpl-status--error",
      "De lijst met templates kon niet worden geladen. Mogelijk blokkeert je netwerk GitHub. "
    );
    message.appendChild(createExternalLink(null, "Bekijk de templates direct op GitHub.", config.browseUrl));
    container.appendChild(message);
  }

  function initTemplatesPage() {
    var container = document.getElementById("atlas-templates");
    if (!container || container.dataset.loaded) return;
    container.dataset.loaded = "true";

    var config = {
      indexUrl: container.dataset.indexUrl,
      filesUrl: container.dataset.filesUrl,
      browseUrl: container.dataset.browseUrl,
      issueUrl: container.dataset.issueUrl,
    };

    fetch(config.indexUrl, { cache: "no-cache" })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        renderTemplateList(container, Array.isArray(data.templates) ? data.templates : [], config);
      })
      .catch(function () {
        renderLoadError(container, config);
      });
  }

  // With Material's 'navigation.instant' pages load without a full reload; document$ covers that case.
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(initTemplatesPage);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initTemplatesPage);
  } else {
    initTemplatesPage();
  }
})();
