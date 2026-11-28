# HA-IndoorTrainingCentral 2026.11.0b13

- Standard BLE Heart Rate Service discovery and read-only telemetry: pulse, optional RR and battery.
- Existing recognized heart rate entries migrate in place; generic entries can detect HRS by GATT.
- Shared card heart rate source selector; no dedicated training tab.
- Normalized HR fields prepare future ANT+ sources. ANT+ receiver, external HA source, journal and repeater integration are not implemented yet.
- Hardware testing required.
