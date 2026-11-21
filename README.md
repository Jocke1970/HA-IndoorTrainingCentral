# HomeFitnessCode / FTMS – Home Assistant

**Experimental development preview (dev), not a verified hardware release.**

Shared backend and responsive Lovelace custom card for treadmill, indoor cycling and indoor rowing.

## Machine profiles

| Machine | Transport | Current status |
| --- | --- | --- |
| HomeFitnessCode Q5 Pro / Y5 | FTMS / HomeFitnessCode FTMS profile | App APK contains FTMS, hardware not yet tested |
| Tacx FLUX S Smart T2900S | Standard FTMS or Tacx FE-C over Bluetooth | FE-C via pycycling, power/cadence/speed and ERG/simulated hill implemented but not hardware-verified |
| Top Sport / Christopeit WP5000 | FTMS first; read-only GATT discovery fallback | Owner reports successful MyWhoosh connection; protocol and console variant still to be confirmed |

WP5000: A working MyWhoosh connection has been reported on the target machine. MyWhoosh added generic FTMS rowing support in version 5.8.0 (June 2026). This makes FTMS worth trying first, **but does not prove** whether this specific connection used FTMS, a bridge, or another supported profile. Some WP5000 console generations differ. If standard FTMS is absent, choose the read-only `christopeit_wp5000` diagnostic profile to inspect GATT characteristics; it sends **no manufacturer commands**.

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
