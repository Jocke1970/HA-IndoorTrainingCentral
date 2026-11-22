# Protocol Capture – test- och analysguide

Gäller **HA-IndoorTrainingCentral 2026.11.0b6** (Marketplace pre-release).

## Varför?

Normala HA-sensorer visar enbart de fält vi avkodar. Protocol Capture sparar tillfälligt notifieringar som HA faktiskt tar emot, **före avkodning**. Råa byte sparas som HEX, så att vi kan gå tillbaka och tolka okända fält senare.

## Användning

1. Uppdatera integrationen via **Home Assistant Marketplace**, välj **Pre-release 2026.11.0b6**, starta om HA och gör en hård omladdning av instrumentpanelen vid behov.
2. Öppna kortet `custom:indoor-training-central-card` (äldre `custom:homefitnesscode-card` fungerar också).
3. Välj WP5000, Tacx eller HEADWIND i maskinväljaren.
4. Expandera **Protocol Capture** och klicka **Starta inspelning**. Observera att en ny inspelning ersätter föregående buffert.
5. Kör ett kort träningspass (helst först 1–2 minuter utan annan styrande app) och stoppa inspelningen.
6. Klicka **Exportera JSONL**. Webbläsaren laddar ned `itc-protocol-<tid>.jsonl`. Den filen går att skicka in här för gemensam analys.

Du kan starta inspelningen innan enheten ansluter. UI visar antalet paket, minnesåtgång och ungefär återstående tid.

## JSONL-exempel

```jsonl
{"type":"capture_meta","schema":1,"device_name":"WP5000","protocol":"ftms","started_at":"2026-11-22T11:00:00.000+00:00","stopped_at":null,"stop_reason":null,"record_count":1,"bytes":180,"active_at_export":true,"capture_scope":"active_ha_ble_connection_only"}
{"type":"frame","timestamp":"2026-11-22T11:00:01.000+00:00","direction":"rx","characteristic":"00002ad1-0000-1000-8000-00805f9b34fb","protocol":"ftms","hex":"0000321400","decoded":{"stroke_rate_spm":25.0,"stroke_count":20}}
```

Exempelvärden ovan är illustrativa. HEX och avkodad data i din export kommer direkt från mottagna meddelanden.

## Täckning

| Källa | Råa meddelanden | Avkodning / diagnostik |
| --- | --- | --- |
| FTMS (löpband, cykel, rodd) | Ja, inkommande data/status/svar | Avkodade värden, även fel |
| Tacx BLE FE-C | Ja, notifieringar på Tacx FE-C TX | `pycycling==0.4.1` avkodar vidare till HA |
| Wahoo HEADWIND | Ja, notifieringar och utgående kommandoförsök | Avkodat fläktläge eller okänd ram |
| WP5000 diagnostikprofil | GATT-lista, inga okända notifikationer | Enbart read-only inventering |
| ANT+ radio / Garmin-klocka / extern Bluetooth-puls | Nej | Kräver framtida egna transportspecifika inspelare |
| MyWhoosh ↔ WP5000 direktanslutning | Nej | HA kan inte avlyssna en annan BLE-förbindelse |

## Säkerhet och begränsningar

- Manuell inspelning per enhet; ingen automatisk start vid HA-omstart, återanslutning eller när en session börjar.
- Ingen automatisk GATT-prenumeration på okända tjänster. Vi ändrar inte maskinens styrning bara för att logga.
- Max **600 sekunder**, **3 000 rader** eller **750 000 bytes** plus metadata. När en gräns nås stoppas inspelningen, och den tidigare datan finns kvar för export.
- Rådata hålls i HA:s arbetsminne tills en ny inspelning startas eller integrationen laddas om; ingen separat loggfil skapas på HA-servern. Efter export ligger filen i din webbläsares nedladdningsmapp.
- Endast administratörer med inloggad HA-session får tillgång till kommandot `homefitnesscode/protocol_capture`.
- HEX kan innehålla exempelvis puls- och hälsorelaterade mätvärden. Dela enbart fångster som du själv vill analysera.
- De inkommande paket som FE-C-biblioteket inte känner igen bevaras som rådata. Integrationens avkodare kan fortfarande behöva utökas för att visa nya värden som sensorer.

## Felsökning

Om UI visar **Okänt kommando** har du sannolikt uppdaterat JS-kortet men inte laddat om integrationen. Starta om Home Assistant och uppdatera instrumentpanelen med `Ctrl+F5`.

Om antalet paket förblir noll, kontrollera först att maskinen verkligen är ansluten till HA och sänder på de karakteristiker integrationen prenumererar på. Om WP5000 körs i ren GATT-diagnostikprofil är noll notifieringar **förväntat**; exportera ändå GATT-inventeringen som följer med vid start.
