# HA-IndoorTrainingCentral – Home Assistant

**Experimental beta preview – not hardware-verified. Install the published pre-release using Home Assistant Marketplace.**

A shared Home Assistant training center for treadmill, Tacx FLUX S cycling, Top Sport WP5000 rowing, and Wahoo HEADWIND fan control.

## Machine profiles

| Machine | Transport | Current status |
| --- | --- | --- |
| HomeFitnessCode Q5 Pro / Y5 | FTMS / HomeFitnessCode FTMS profile | App APK contains FTMS, hardware not yet tested |
| Tacx FLUX S Smart T2900S | Standard FTMS or Tacx FE-C over Bluetooth | FE-C via pycycling, power/cadence/speed and ERG/simulated hill implemented but not hardware-verified |
| Top Sport / Christopeit WP5000 | FTMS first; read-only GATT discovery fallback | Owner confirmed direct Bluetooth pairing to MyWhoosh on phone without bridge; GATT/FTMS UUID not yet captured |

WP5000: The owner has confirmed **direct pairing of this rower to MyWhoosh on an Android phone, without QZ or any bridge**. MyWhoosh added generic FTMS rowing support in version 5.8.0 (June 2026), so FTMS is now our leading hypothesis. **This is still not a captured UUID or confirmed FTMS implementation**; some WP5000 console generations differ. First verify service `0x1826` and characteristic `0x2AD1` read-only. If FTMS is absent, select the read-only `christopeit_wp5000` diagnostic profile; it sends **no manufacturer commands**.

## Wahoo HEADWIND companion to Tacx FLUX S

A Wahoo KICKR HEADWIND can be added **as its own BLE device** to this integration with profile `wahoo_headwind`. It provides a native `fan` entity, a mode selector (Off / Heart rate / Speed / Manual), fan percentage and a read-only firmware version sensor (if firmware GATT value is readable). The Tacx bike card shows a companion fan control section when a HEADWIND is available.

**Owner's current setup:** HEADWIND is controlled autonomously from a paired heart-rate strap. We retain this as the default workflow. No Bluetooth control writes on HA startup or reconnect. A normal HA `fan.turn_on` selects Heart rate; fixed fan percentages or Manual are only set on explicit user actions. Wahoo's native sensor coupling continues without HA when disconnected.

**Firmware:** Wahoo firmware 2.0.43 (March 2026) adds trainer-power and multi-sensor adaptive cooling. 2.0.57 (September 2026) improves sensor connectivity. These newer modes are configured in the Wahoo app, not enabled by the current HA protocol. Older hardware may or may not offer an update: check the device's firmware in Wahoo app before changing anything. Wahoo warns an update may reset paired sensor settings; record the existing HR pairing first. [Headwind protocol notes](docs/headwind.md).

## Install via Home Assistant Marketplace (2026.11+)

This beta is distributed as a GitHub **pre-release**, not from the development branch and not as a manually copied archive.

1. In Home Assistant go to **Settings → Marketplace → Add from link**.
2. Add `https://github.com/Jocke1970/HA-IndoorTrainingCentral` as an **Integration**.
3. Open HA-IndoorTrainingCentral in Marketplace and enable **Pre-release**.
4. Install the newest `2026.11.0bN` pre-release (currently `2026.11.0b11`), not the `main` branch.
5. Open **Settings → Devices & services** and configure HA-IndoorTrainingCentral.
6. For new dashboards, register `/indoor-training-central/indoor-training-central-card.js` as a JavaScript module and add:

```yaml
type: custom:indoor-training-central-card
```

Already configured dashboards still work with `type: custom:homefitnesscode-card` and the old `/homefitnesscode/homefitnesscode-card.js` resource. Do not register both resources unless needed.

Marketplace manages downloaded files and replaces the integration directory during updates. If HomeFitnessCode was previously installed manually, do not install a second copy into the same domain; first reconcile the previous installation. Initial tests should be read-only.

The card discovers any installed HomeFitnessCode entity group and adapts to screen width.

## Safety and limitations

- Remote control needs explicit manual arming. Disconnection clears arming, and no pending commands are replayed.
- The user must retain physical emergency stop/safety key access. This UI is **not** an emergency stop.
- FE-C Tacx transport and WP5000 discovery are experimental. Perform read-only testing before trying commands.
- Garmin FIT export/import and the user's existing FIT conversion utility are **not yet connected** to this repo.
- Beta is a supervised testing channel; the stable main branch is not a release yet.

## Branch workflow

dev → beta → main

See docs/protocols.md for protocol details and the WP5000 discovery checklist.

## Beta b2: machine-specific entities and HEADWIND

- Each equipment entry only registers applicable sensors and controls. Unknown/disconnected devices retain basic status until classified. Additional entities appear on successful BLE discovery.
- Legacy HEADWIND entries created by b1 with the `auto` profile are migrated **in place** by BLE device name; no re-pairing and no new config entry required.
- Irrelevant entities from b1 are pruned from the integration's **entity registry** after the machine type is identified. Relevant entity IDs are retained.
- Bike dashboard shows the linked HEADWIND fan, mode selector (Off / Heart rate / Speed / Manual), percent presets, and firmware version where readable. The fan also has a standalone selectable view.
- Pulsband/HEADWIND native pairing is preserved. No writes at startup or reconnect; manual fan percentage deliberately switches to Manual.
- This is a preliminary backend + UI code fix. Automated protocol tests and JS syntax validation are necessary, but not a substitute for real hardware confirmation.

## Name and compatibility (beta b3)

The GitHub repository was renamed to **Jocke1970/HA-IndoorTrainingCentral**. GitHub redirects the old repository URL, but new Marketplace additions should use the new URL.

The user-facing integration and card are called **HA-IndoorTrainingCentral**. For continuity with existing installations, the internal domain and Python package remain `homefitnesscode`. The entity unique IDs, config entries, device registry, and old Lovelace card name and resource URL remain valid.

Narrow desktop dashboard columns and phones are handled by a responsive tile/control layout. The interface lists only controls actually created for the connected equipment, includes Wahoo HEADWIND controls in the Tacx view, and handles offline status consistently.

Do **not** manually rename `/config/custom_components/homefitnesscode`: that is the original integration domain and is intentionally unchanged.

FIT session export remains planned, not implemented.

## Status indicators (beta b4)

Live Bluetooth status uses a colored dot **and** a text label:
- Green **Ansluten**: the equipment's `connected` binary sensor is `on`.
- Grey **Frånkopplad**: the sensor is `off`.
- Amber **Status okänd**: unavailable, unknown, or missing.

Workout details such as **Redo** are shown separately. The Wahoo HEADWIND section also distinguishes a physically switched-off fan from a disconnected Bluetooth connection. The barbell in the optional project artwork represents a future category, **not** a current strength-training device connection.

## Grafik (beta b5)

Vi behåller den detaljerade original-loggan med hanteln för större ytor. I Home Assistants integrationslista används en förenklad, tydlig **ITC-ikon** i mörkblått/turkos.

- Redigerbar ikonkälla: `assets/branding/itc-icon.svg`
- Native Home Assistant-branding: `custom_components/homefitnesscode/brand/icon.png` (256×256) och `icon@2x.png` (512×512)
- GitHub Actions genererar PNG-filerna från SVG på `dev` och committar dem. De ingår sedan i Marketplace-beta.
- HA visar bilden automatiskt från integrationens `brand/`-katalog (HA 2026.3+). Inga entitets-ID:n eller domännamn ändras.

Styrketräningsikonen i huvudloggan är visuell profilering och innebär inte att någon styrketräningsutrustning är uppkopplad.


## Protocol Capture – beta b6

Protocol Capture är en manuell felsökningsfunktion per registrerad träningsmaskin eller HEADWIND. Öppna **Protocol Capture** längst ned i Lovelace-kortet. Tryck **Starta inspelning**, använd träningsmaskinen, välj **Stoppa** och därefter **Exportera JSONL**. Inspelningen fungerar även när maskinen ännu inte är ansluten, och kan fånga efterföljande anslutningar.

- **FTMS:** varje mottaget FTMS-datapaket, maskinstatus och kontrollsvar. Spara både originalbytes som HEX och avkodade värden eller avkodningsfel.
- **Tacx FE-C via BLE:** råa notifieringar från Tacx FE-C-kanalen. Vidarebefordras därefter till den befintliga `pycycling==0.4.1`-avkodaren.
- **Wahoo HEADWIND:** inkommande notifieringar och av HA initierade utgående kommandon. Capture ändrar inte fläktläge.
- **GATT:** inventering av anslutna tjänster/karakteristiker när sådan information finns. Den diagnostiska WP5000-profilen inventerar fortfarande GATT read-only, men prenumererar **inte** på okända tillverkarprotokoll.
- **Gränser:** högst 10 minuter, 3 000 händelser eller 750 kB i tillfälligt HA-minne per enhet. Inspelningen stoppas vid första gränsen.
- **Säkerhet:** avstängd vid start/omstart. Endast HA-administratörer får starta, stoppa eller exportera via autentiserat WebSocket API. Inga nya Bluetooth-styrkommandon görs.
- **Export:** UTF-8 JSONL, en JSON-post per rad, med metadata och råa HEX-data. **Exportera innan HA/integrationen startas om** – annars försvinner bufferten. Inspelningen lagras inte i Recorder och exponeras inte i sensorns attribut.

Capture kan bara observera **de notifieringar HA själv tar emot på sin aktiva BLE-anslutning**. Den kan inte passivt avlyssna Bluetooth-trafiken mellan en fysisk maskin och exempelvis MyWhoosh. ANT+ radiotrafik, fristående Bluetooth-pulsband och allmän snifferfunktion ingår inte i b6.

Dokumentation och ett testexempel finns i [docs/protocol-capture.md](docs/protocol-capture.md).


## Treadmill workout journaling (beta b7)

En ny automatisk **Träningspass**-expander i löpbandets kort sparar råa mottagna FTMS-meddelanden och härleder passinformation genom att läsa tillbaka råfilen. Det är **separat från Protocol Capture**: du behöver inte starta en diagnostikinspelning före varje promenad. Ingen styrning av löpbandet krävs.

- Lagring: `/config/homefitnesscode/sessions/<config_entry_id>/` på HA-servern (inte under `custom_components`, och inte i HA:s rotkatalog).
- `YYYYMMDDTHHMMSSZ-<id>.jsonl`: ett tidsstämplat FTMS-meddelande per rad (HEX + avkodade värden). Alla notifieringar som **HA faktiskt tar emot under passet** sparas, inklusive eventuella FTMS-statusmeddelanden.
- `YYYYMMDDTHHMMSSZ-<id>.summary.json`: passets beräknade slutvärden (tid, distans, högsta hastighet/lutning, kalorier, datapaket), **återskapade från JSONL-filen**.
- Inspelningen startar automatiskt när bandets rapporterade hastighet överstiger 0,2 km/h och stoppas efter ungefär 15 sekunders inaktivitet. Ett stopp eller en nollställning av löpbandets räknare raderar inte passets tidigare maxvärden.
- Du kan även välja **Avsluta och spara pass**, vilket enbart avslutar datainsamlingen. Det skickar **inga stopp- eller hastighetskommandon** till maskinen.
- Vid förlorad Bluetooth-anslutning eller omstart sparas tillgängliga rådata. En passfil utan avslutningspost återskapas vid nästa HA-start och märks som **avbruten**, så den inte misstas för ett fullständigt pass.
- Gränser: högst 6 timmar eller 30 MB rådata per pass. Filer raderas inte automatiskt i b7; följ därför lagringsutrymmet vid frekventa eller längre träningspass.
- Funktionen gäller **endast FTMS-löpband** i b7. Bike/rower och FIT-export kommer senare, efter verklig testning.
- Säkerhet: passhistorik och manuell passavslutning nås via inloggad administratörs-WebSocket i HA. Råfilerna stannar på din HA-server tills du själv hämtar eller raderar dem.

Se [docs/workout-journal.md](docs/workout-journal.md) för testförfarande och filformat.


## Equipment tabs with live connection status (beta b8)

- Replaced the training-device dropdown with a responsive button per machine; each tile displays machine category, actual device name, and a live green/grey/amber Bluetooth dot plus text (**Ansluten · Redo**, **Frånkopplad**, or **Status okänd**).
- The active device is highlighted, including accessible `aria-pressed` state. Clicking a tile changes the selected view without starting or controlling any equipment.
- Fallback to the advertised equipment name when a disconnected machine still reports `machine_type=auto`, including Q5, Tacx FLUX and WP5000.
- HEADWIND remains available as a companion within the bike controls, not as a fourth training machine. A dedicated HEADWIND card configured with `entry_id` remains supported, and the fan is shown when it is the only equipment.
- Existing Protocol Capture and treadmill workout history remain accessible from the selected machine.
- Responsive layout: 2 columns on narrow screens and 1 on exceptionally narrow ones.


## Q5 observed running status and animated runner (beta b9)

- Infer treadmill workout state directly from valid FTMS speed samples: over 0.2 km/h shows **Pass pågår**; when speed returns to zero after running, status becomes **Stoppad**. Initial idle connection remains **Redo**.
- The inference updates the real `Workout status` sensor, not just the Lovelace card. Explicit safety-stop events are preserved.
- Animate the running-person icon in the treadmill header and device tile **only while speed is positive and the treadmill is connected**. The animation stops when the belt stops or HA loses connection.
- Respect the browser's reduced-motion preference. Bike/rower/HEADWIND and machine-control behavior are unchanged.


## Q5 FTMS supervised control test (beta b10)

- New treadmill panel: manually activate FTMS control, then **Start**, **Paus**, **Stopp**, **Hastighet −/+ 0,5 km/h**, and **Lutning −/+ 1 procentenhet**. Exact target fields remain under Advanced.
- Quick-step controls and exact targets unlock only when live treadmill speed exceeds 0.2 km/h (motor running); the operator need not be standing on the belt during these initial tests. If the device acknowledges Start but does not move, keep controls locked and inspect the hardware behavior.
- Start requires explicit confirmation. Speed steps are small and do not require repeated confirmations once the belt is moving. Both quick controls require an armed, connected FTMS device and advertised supported targets; they disable at speed/incline boundaries.
- Stopp remains available whenever the device is connected and control is armed, regardless of displayed treadmill speed; it is **not** an emergency stop. Always keep the physical safety key available.
- HA disconnection disarms the controller as before. No automatic rearming and no Bluetooth connection changes.
- No changes to saved workout JSONL data or HEARTWIND/Tacx/rower operation.


## Q5 FTMS controls polish (beta b11)

- Tested against the user's raw Q5 JSONL command trace: Request Control `00`, Start `07`, Set Speed `02` (1.0–2.0 km/h), Set Incline `03` (0–3%), Stop `0801`, all positively acknowledged by FTMS Control Point.
- Clarify that FTMS Start is supported from HA: there is **no requirement to press Start on the physical Q5 console**. Motor start retains an explicit confirmation; command receipt does not count as confirmed belt movement.
- Promote speed ±0.5 km/h and incline ±1 percentage-point to primary three-column stepper controls with observed current values in the middle.
- Remove repetitive speed-change confirmation for the optional exact numeric target under Advanced. The existing one-click ± steppers remain confirmation-free.
- Speed and incline changes remain locked until the motor is observed moving (FTMS speed >0.2 km/h), with armed connection and machine-advertised limits mandatory. Control is always disabled on disconnection; no auto-arm/auto-start.
- Provide a live explanation of why controls are locked or available; keep Stop visible when armed. Stop over BLE is not a safety stop.
