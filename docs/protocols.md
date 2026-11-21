# Protocol notes

## FTMS

Service 0x1826: treadmill data 0x2ACD, rower data 0x2AD1, indoor bike data 0x2AD2; features 0x2ACC, control 0x2AD9, status 0x2ADA.

HomeFitnessCode APK includes the standard FTMS identifiers; this does not prove the retail treadmill models implement them.

## Tacx FLUX S T2900S

Tacx FE-C over BLE service 6E40FEC1-B5A3-F393-E0A9-E50E24DCCA9E. Data notify UUID 6E40FEC2; command UUID 6E40FEC3.
Current command targets via pycycling: ERG power and simulated grade; status and hardware capability need real-device verification.

## Top Sport / Christopeit WP5000

Manufacturer documents Bluetooth/Kinomap and a 16-level magnetic brake. Some WP5000 console hardware revisions differ.

**Evidence:** The owner has successfully used this WP5000 with MyWhoosh. MyWhoosh introduced support for FTMS-compatible rowers in v5.8.0 (2026-06-09): https://mywhoosh.com/mywhoosh-5-8-0-more-ways-to-row-more-ways-to-progress/. This raises the probability of FTMS if the WP5000 connected directly as a rower, but a bridge or different machine/console profile has not yet been ruled out. Other older WP5000 owner reports found no FTMS; console revisions likely matter. MyWhoosh connectivity alone does **not** demonstrate remote resistance control.

**First test (read-only):** Wake WP5000, disconnect Kinomap/MyWhoosh, then select it in HA with profile `auto` and machine `rower`. Check whether FTMS service `0x1826` / rower data characteristic `0x2AD1` is present and whether live distance, stroke rate/count and split pace are published. Avoid control commands.

**Fallback:** If FTMS is absent, add the same BLE peripheral with profile `christopeit_wp5000` to expose a read-only GATT inventory. Capture the `GATT discovery` entity's `characteristics` attribute. Decoding private vendor notifications requires a further packet capture during rowing; do not invent commands.

Never transmit guessed write commands; keep proprietary profiles read-only until protocol verification.
