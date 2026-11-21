# HomeFitnessCode 2026.11.0b1 (beta)

First experimental Home Assistant Marketplace beta. **No physical equipment has been verified yet.**

- Shared Bluetooth FTMS backend for treadmills, indoor cycles and rowing machines.
- HomeFitnessCode profile based on static Android APK analysis (Y5/Q5 Pro actual hardware not yet tested).
- Tacx FLUX S trainer transport using FE-C over BLE and `pycycling`.
- Top Sport / Christopeit WP5000: FTMS-first strategy with read-only GATT discovery fallback.
- Adaptive Home Assistant dashboard card for desktop/mobile.
- Explicit control arming; no automatic motor start or queued command replay after Bluetooth reconnection.

**For first tests:** Start WP5000 with read-only values. Keep remote commands disarmed and physical safety controls accessible.
**Known limitations:** Garmin/FIT converter not connected; proprietary WP5000 Bluetooth packets not decoded; unsupported devices may be shown as disconnected.
