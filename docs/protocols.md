# Protocol notes

## FTMS

Service 0x1826: treadmill data 0x2ACD, rower data 0x2AD1, indoor bike data 0x2AD2; features 0x2ACC, control 0x2AD9, status 0x2ADA.

HomeFitnessCode APK includes the standard FTMS identifiers; this does not prove the retail treadmill models implement them.

## Tacx FLUX S T2900S

Tacx FE-C over BLE service 6E40FEC1-B5A3-F393-E0A9-E50E24DCCA9E. Data notify UUID 6E40FEC2; command UUID 6E40FEC3.
Current command targets via pycycling: ERG power and simulated grade; status and hardware capability need real-device verification.

## Top Sport / Christopeit WP5000

Manufacturer documents Bluetooth/Kinomap and a 16-level magnetic brake. Some WP5000 console hardware revisions differ.
App compatibility **does not imply FTMS or remote resistance control**.

To investigate: wake machine, disconnect Kinomap, add a HomeFitnessCode entry selecting its BLE advertisement and christopeit_wp5000 profile. Find the GATT discovery sensor, copy the characteristics attribute. A separate notification capture during a rowing workout will be needed before implementing a proprietary decoder.

Never transmit guessed write commands; keep proprietary profiles read-only until protocol verification.
