# Protocol notes

## FTMS

Service 0x1826: treadmill data 0x2ACD, rower data 0x2AD1, indoor bike data 0x2AD2; features 0x2ACC, control 0x2AD9, status 0x2ADA.

HomeFitnessCode APK includes the standard FTMS identifiers; this does not prove the retail treadmill models implement them.

## Tacx FLUX S T2900S

Tacx FE-C over BLE service 6E40FEC1-B5A3-F393-E0A9-E50E24DCCA9E. Data notify UUID 6E40FEC2; command UUID 6E40FEC3.
Current command targets via pycycling: ERG power and simulated grade; status and hardware capability need real-device verification.

## Top Sport / Christopeit WP5000

Manufacturer documents Bluetooth/Kinomap and a 16-level magnetic brake. Some WP5000 console hardware revisions differ.

**Observed by owner:** The Top Sport WP5000 connected **directly to MyWhoosh on the phone**, with **no QZ, external adapter or bridge**. MyWhoosh introduced FTMS-compatible rowing support in v5.8.0 (2026-06-09): https://mywhoosh.com/mywhoosh-5-8-0-more-ways-to-row-more-ways-to-progress/. This makes an FTMS rower profile a strong hypothesis for this particular machine, but direct pairing alone does **not** confirm its advertised BLE UUIDs, rower console revision, or the command set. Older WP5000 owners reported no FTMS, so hardware revisions may matter. Do **not** infer remote magnetic resistance control from MyWhoosh compatibility.

**First test (read-only):** Wake WP5000, disconnect Kinomap/MyWhoosh, then select it in HA with profile `auto` and machine `rower`. Check whether FTMS service `0x1826` / rower data characteristic `0x2AD1` is present and whether live distance, stroke rate/count and split pace are published. Avoid control commands.

**Fallback:** If FTMS is absent, add the same BLE peripheral with profile `christopeit_wp5000` to expose a read-only GATT inventory. Capture the `GATT discovery` entity's `characteristics` attribute. Decoding private vendor notifications requires a further packet capture during rowing; do not invent commands.

Never transmit guessed write commands; keep proprietary profiles read-only until protocol verification.
