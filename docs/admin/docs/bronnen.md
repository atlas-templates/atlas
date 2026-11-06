Binnen Bronnen worden de zogenaamde endpoints geconfigureerd. Een endpoint biedt toegang tot de gegevens die bijvoorbeeld op [Geoserver](https://geoserver.org/){target="\_blank"} opgeslagen zijn.
Om bijvoorbeeld WMS (Web Map Service) gegevens van Geoserver op te halen kan dit het endpoint zijn:

```
http://mijnserver.nl/geoserver/wms
```

Binnen Atlas kunnen meerdere endpoints geconfigureerd worden. Zo kan er een bron voor WMS lagen zijn, voor WFS (Web Feature Service) of bronnen voor externe kaartlagen. Bronnen kunnen toegevoegd, bewerkt of verwijderd worden.

Een bron kan ook het endpoint van een API zijn. Deze bronnen kunnen gebruikt worden voor gekoppelde data.

Klik op Nieuwe bron om een bron toe te voegen. Vul de Titel in, deze verschijnt in het hoofdmenu bronnen. Het veld Kort kenmerk moet een unieke waarde hebben en mag geen spaties bevatten. Vul bij de URL het endpoint in.

### Algemene gegevens

- **Titel**
  Dit is de titel zoals ingegeven bij het aanmaken van de bron.

- **URL**
  Dit is de URL zoals ingegeven bij het aanmaken van de bron.

- **Verstuur authenticatie-informatie naar bron**
  Deze optie kan aangevinkt worden wanneer extra beveiliging nodig is om de laag te kunnen bekijken. Wanneer deze optie aangevinkt is, kan de kaartlaag die deze bron gebruikt zo geconfigureerd worden dat deze maar door een beperkte groep gebruikers te zien is. Zie hiervoor het onderdeel [beveiliging](layer_security.md){target="\_blank"}.  
  Standaard waarde: _uit_

### Toegang

- **Vereis inlog voor deze bron**  
  Wanneer deze optie is aangevinkt kan de kaartlaag die deze bron gebruikt, alleen bekeken worden door ingelogde gebruikers.  
  Gebruik dit ook voor ['per layer security'](layer_security.md){target="\_blank"}.
- **Groepen**
  Wanneer er [gebruikersgroepen](groepen.md){target="\_blank"} zijn aangemaakt, kunnen hier deze gebruikersgroepen geselecteerd worden. De kaartlagen die deze bron gebruiken, kunnen dan alleen bekeken worden door de geselecteerde gebruikergroepen. Zie ook het onderdeel [beveiliging](layer_security.md){target="\_blank"}.
