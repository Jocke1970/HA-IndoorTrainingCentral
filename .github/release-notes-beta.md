# HA-IndoorTrainingCentral 2026.11.0b4 (beta)

## Connection indicators

- Green status dot + **Ansluten** when the selected device's Home Assistant Bluetooth connection sensor is on.
- Grey status dot + **Frånkopplad** when it is off.
- Amber status dot + **Status okänd** when the sensor value is unavailable or unknown, avoiding false green positives.
- Show localized workout detail such as **Redo** beside the connected status.
- Apply the same connection indicator to the Wahoo HEADWIND accessory panel. Its **Av** fan state is not confused with Bluetooth disconnection.
- Include JavaScript smoke tests for the connection state mappings.

The internal `homefitnesscode` domain and existing dashboards remain compatible. No BLE command semantics, FIT export, or recording behavior is changed.

Strength-training artwork in the project icon is visual branding only; resistance-training device support is **not implemented** at this stage.
