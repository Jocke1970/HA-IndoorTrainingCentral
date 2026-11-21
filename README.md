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
4. Install the newest `2026.11.0bN` pre-release (currently `2026.11.0b4`), not the `main` branch.
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
