Via de beheerpagina kom je bij de verschillende onderdelen die ingesteld kunnen worden.

<img src="../images/beheerpagina.png" alt="Hoofdscherm Admin module" width="700"/>

###Importeren en Exporteren van configuratiegegevens.

<img src="../images/acties.png" alt="Importeren en Exporteren" width="300"/>

Binnen het configuratieonderdeel Kaarten, kunnen aangemaakte onderdelen worden geëxporteerd en geïmporteerd. Dit geldt voor Bronnen, Categorieën, Metadatasets, Kaarten, Kaartlagen en Viewers. Daarnaast zijn Autorisaties en Tabellen ook te exporteren en te importeren.
Let op dat bij Tabellen alleen de definitie van de tabellen wordt geëxporteerd, niet de inhoud. De gegevens van een export worden opgeslagen als JSON-bestand.

!!! warning "Eerst afhankelijkheden importeren"
Een kaartlaag met categorie X importeren terwijl categorie X niet bestaat in het doelsysteem, zal niet lukken. Importeer altijd eerst de categorie en de bron van een kaartlaag.

Exporteren en importeren van gegevens lukt alleen tussen twee Atlassystemen met dezelfde versie.

<!-- [Volgende](kaarten.md){ .md-button } -->
