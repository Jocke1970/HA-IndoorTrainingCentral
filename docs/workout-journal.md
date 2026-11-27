# Automatic FTMS treadmill workout journal – beta b7

## Syfte

HomeFitnessCode / HA-IndoorTrainingCentral lagrar varje mottaget FTMS-råpaket
under pågående löpbandspass i en egen katalog. Löpbandet kan nollställa
distans/tid/kalorier när det stoppas; historiken byggs därför från råfilen,
inte från sensorns sista värde.

## Filstruktur

Home Assistants konfigurationskatalog:

    /config/homefitnesscode/sessions/<entry_id>/
        20261127T183200Z-12ab34cd.jsonl
        20261127T183200Z-12ab34cd.summary.json

Det här är en data-/historikkatalog, INTE en mapp för installerad
integrationskod. Vid Marketplace-uppdatering ersätts integrationskod,
men inte datafilerna under /config/homefitnesscode/sessions.

Varje rad i JSONL kan innehålla "type", "timestamp", "direction",
"characteristic", "protocol", "hex", "decoded" eller "decode_error".
En startmarkör följs av samtliga råpaket från passet och en slutmarkör.
Slutsammanfattningen skrivs först efter att råfilen har flushats till disk.
JSONL är den auktoritativa källan; du kan återskapa sammanfattningen genom
att radera bara .summary.json och därefter ladda om integrationen.

## Automatiskt beteende

1. Börja gå på löpbandet med dess egna reglage. När FTMS-hastigheten är
   över 0,2 km/h startar inspelningen utan något HA-styrkommando.
2. HA skriver i bakgrunden i batchar. Hastighet, tid, distans, lutning
   och kalorier finns kvar i råfilen även om konsolen sedan nollställer dem.
3. Cirka 15 sekunder efter att hastighet och distans slutat öka stängs passet
   automatiskt. Du kan också välja "Avsluta och spara pass".
4. Passet visas i kortets "Träningspass"-expander. Rådata ligger lokalt
   på HA-servern; de laddas inte automatiskt upp någonstans.

Vid tappad anslutning avslutas passet som avbrutet. Om HA stängs av under
pågående pass finns redan flushad JSONL, som kan återställas när HA startar.

## Säkerhetsprinciper

- Inga Bluetooth-styrkommandon skickas av journalen.
- Passjournalen fungerar även om diagnostikfunktionen "Protocol Capture"
  inte är igång.
- Filnamn genereras av integrationen och config entry ID saneras för
  att förhindra sökvägsmanipulation.
- Maximalt 6 timmar / 30 MB per pass. Överskrids gränsen arkiveras det
  inspelade materialet som ofullständigt. Ingen automatisk radering i b7.
- Endast de datapaket HA själv får på sin anslutning lagras.
- Datamängden kan innehålla puls och personliga träningsuppgifter.
  Behåll filerna privat när du skickar dem vidare.

## Begränsningar och test

Det finns ännu ingen Garmin FIT-export, import till Garmin Connect
eller träningsanalys över längre tidsperioder. Beta b7 implementerar
tillförlitlig rådatainsamling och enkel passhistorik för löpbandet.
Prova först en kort promenad och kontrollera att både JSONL och
.summary.json skapats och att tids- och distansvärdena visas i kortet.
