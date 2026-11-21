# HomeFitnessCode / FTMS – Home Assistant

**Experimental beta preview – not hardware-verified. Install the published pre-release using Home Assistant Marketplace.**

Shared backend and responsive Lovelace custom card for treadmill, indoor cycling and indoor rowing.

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
2. Add `https://github.com/Jocke1970/HomeFitnessCode` as an **Integration**.
3. Open HomeFitnessCode in Marketplace and enable **Pre-release**.
4. Install the release labelled `2026.11.0b1` (not the default `main` branch).
5. Open **Settings → Devices & services** and configure the HomeFitnessCode / FTMS integration.
6. Register `/homefitnesscode/homefitnesscode-card.js` as a JavaScript module in dashboard resources, then add the card:

```yaml
type: custom:homefitnesscode-card
```

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
