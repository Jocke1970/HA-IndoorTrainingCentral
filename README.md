# HomeFitnessCode / FTMS – Home Assistant

**Experimental development preview (dev), not a verified hardware release.**

Shared backend and responsive Lovelace custom card for treadmill, indoor cycling and indoor rowing.

## Machine profiles

| Machine | Transport | Current status |
| --- | --- | --- |
| HomeFitnessCode Q5 Pro / Y5 | FTMS / HomeFitnessCode FTMS profile | App APK contains FTMS, hardware not yet tested |
| Tacx FLUX S Smart T2900S | Standard FTMS or Tacx FE-C over Bluetooth | FE-C via pycycling, power/cadence/speed and ERG/simulated hill implemented but not hardware-verified |
| Top Sport / Christopeit WP5000 | FTMS first; read-only GATT discovery fallback | Owner confirmed direct Bluetooth pairing to MyWhoosh on phone without bridge; GATT/FTMS UUID not yet captured |

WP5000: The owner has confirmed **direct pairing of this rower to MyWhoosh on an Android phone, without QZ or any bridge**. MyWhoosh added generic FTMS rowing support in version 5.8.0 (June 2026), so FTMS is now our leading hypothesis. **This is still not a captured UUID or confirmed FTMS implementation**; some WP5000 console generations differ. First verify service `0x1826` and characteristic `0x2AD1` read-only. If FTMS is absent, select the read-only `christopeit_wp5000` diagnostic profile; it sends **no manufacturer commands**.

## Development installation

1. Copy custom_components/homefitnesscode to your Home Assistant configuration directory.
2. Restart Home Assistant and add HomeFitnessCode / FTMS under Devices & services.
3. Select Bluetooth equipment, protocol profile and conservative maximum target values.
4. Add dashboard JavaScript module resource: /homefitnesscode/homefitnesscode-card.js
5. Add Lovelace YAML card:

```yaml
type: custom:homefitnesscode-card
```

The card discovers any installed HomeFitnessCode entity group and adapts to screen width.

## Safety and limitations

- Remote control needs explicit manual arming. Disconnection clears arming, and no pending commands are replayed.
- The user must retain physical emergency stop/safety key access. This UI is **not** an emergency stop.
- FE-C Tacx transport and WP5000 discovery are experimental. Perform read-only testing before trying commands.
- Garmin FIT export/import and the user's existing FIT conversion utility are **not yet connected** to this repo.
- No beta/main changes until tests and hardware checks pass.

## Branch workflow

dev → beta → main

See docs/protocols.md for protocol details and the WP5000 discovery checklist.
