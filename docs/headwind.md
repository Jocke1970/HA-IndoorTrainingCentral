# Wahoo HEADWIND companion module

## Verified sources and hardware notes

- HEADWIND has a proprietary BLE service, not FTMS (Bluetooth standard for fitness machines).
- Native HR and Speed fan control are already supported by legacy HEADWIND firmware. Owner currently uses HR strap with a directly paired fan.
- Firmware v2.0.43 (2026-03-17) added BLE sensor support, power/smart-trainer control, and adaptive multi-sensor cooling.
- Firmware v2.0.57 (2026-09-28) improves sensor connectivity.
- Official source: https://support.wahoofitness.com/hc/en-us/articles/360000760259-KICKR-HEADWIND-Firmware-Release-Notes
- Wahoo app can display whether an update is available: https://support.wahoofitness.com/hc/en-us/articles/360000788879-Update-Firmware-on-a-KICKR-HEADWIND

## HA implementation

- Separate Bluetooth connection from Tacx FLUX S; independently add HEADWIND as a device.
- HA `fan` entity offers Off / on (heart-rate mode), explicit percentage commands, and mode select.
- No writes on HA startup/reconnect. Do not change the user's paired HR sensor settings.
- `sensor.headwind_firmware` reports firmware revision from Device Information characteristic `0x2A26` **when available**; missing GATT information is shown as unknown and should not block the fan.
- Native fan modes Heart rate and Speed require sensors already paired to the physical fan.
- HA does **not** implement/advertise Wahoo’s newer native power/adaptive modes at this stage; configure those in Wahoo app if firmware supports them.

## Protocol

BLE service `a026ee0c-0a7d-4ab3-97fa-f1500f9feb8b`; control/notify characteristic `a026e038-0a7d-4ab3-97fa-f1500f9feb8b`.
Mode writes: 04 [01 off / 02 heart-rate / 03 speed / 04 manual] 00 00. Manual fan percentage: 02 [0-100] 00 00. These formats were cross-checked against publicly available reverse-engineered libraries; not tested on the owner’s hardware.

## First live test order

1. With HEADWIND using HR mode, check displayed firmware in Wahoo app without updating or re-pairing.
2. Disconnect the Wahoo app before HA BLE testing; confirm the fan continues HR control normally.
3. Add the fan to HomeFitnessCode using the HEADWIND BLE profile. Verify connected, mode and firmware fields before sending commands.
4. Deliberately test one manual percentage, then restore Heart rate explicitly.
5. Test with Tacx and HEADWIND independently, ensuring HA does not seize control of the trainer or fan automatically.

**Hardware not yet tested. Keep existing HR control as the fallback.**
