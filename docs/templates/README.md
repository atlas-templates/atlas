# Gedeelde templates

Deze map bevat templates voor gekoppelde data die Atlas-beheerders met elkaar delen. Een template is
één zip-bestand met precies vijf exportbestanden uit Atlas: `layers_*.json`, `authorizations_*.json`,
`tables_*.json`, `sources_*.json` en `categories_*.json`. Ze verschijnen op de pagina
**Templates** in de beheerdocumentatie, die de lijst live uit `index.json` op GitHub ophaalt.
Een nieuwe template is daardoor in elke Atlas-installatie zichtbaar zonder nieuwe release.

## Indienen

Gebruikers dienen een template in via het issue-formulier
[Template indienen](https://github.com/geo-commons/atlas/issues/new?template=template-indienen.yml).
Het issue krijgt automatisch het label `template-ingediend`.

## Goedkeuren (beheerders van de repository)

1. Controleer de inzending: open de zip en kijk of er geen geheimen, interne URL's of
   persoonsgegevens in staan.
2. Zet het label `template-goedgekeurd` op het issue.
3. De workflow `Templates` controleert of de zip precies de vijf exportbestanden bevat en of dat
   geldige JSON is. Daarna zet hij de zip in een eigen map, werkt `index.json` bij, reageert op het
   issue en sluit het. Klopt er iets niet, dan meldt de workflow de reden in het issue.

## Structuur

```
docs/templates/
├── index.json                 # wordt automatisch gegenereerd, niet met de hand aanpassen
└── <naam-van-template>/
    ├── template.json          # naam, beschrijving, Atlas-versie, auteur, datum, bestandsnaam, inhoud
    └── <bestand>.zip
```

Een template aanpassen of verwijderen kan gewoon met een commit of pull request in deze map. Na de
merge naar `main` bouwt de workflow `index.json` automatisch opnieuw op. Handmatig kan dat ook met:

```bash
python .github/scripts/templates.py build-index
```
