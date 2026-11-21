# HomeFitnessCode 2026.11.0b2 (beta)

## Entity cleanup and Wahoo HEADWIND

- Machine-specific sensor, number and button registration for treadmill, indoor bike trainer and rower. The initial generic 32-entity set is no longer created for every device.
- Dynamically add appropriate entities when an unknown device is identified by FTMS or Tacx BLE.
- Automatically migrate existing b1 HEADWIND config entries (whose name begins HEADWIND) from the previous auto profile, preserving the configuration entry and BLE address.
- Remove obsolete beta-1 entity registry entries after the machine is classified, without deleting matching entity IDs.
- Native HEADWIND BLE controls: fan entity, mode selector, percentage presets and firmware metadata. Show fan controls beside trainer and optionally standalone.
- Preserve existing pulse-strap pairing and fan's heart-rate mode. No control writes on reconnection or startup.

**Tests:** offline protocol tests and UI syntax checked by CI; physical hardware tests remain pending. Do not use HA fan or FTMS UI as an emergency stop.
