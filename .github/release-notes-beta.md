# HA-IndoorTrainingCentral 2026.11.0b6 (beta)

## Protocol Capture – opt-in diagnostics

- Add a collapsible **Protocol Capture** section for each selected training device and standalone Wahoo HEADWIND.
- **Starta inspelning / Stoppa / Exportera JSONL** controls use Home Assistant's authenticated, administrator-only WebSocket API.
- Capture raw inbound FTMS characteristics (training telemetry, status, control acknowledgements), including malformed or unrecognized data as HEX with timestamps.
- Capture raw Tacx FE-C BLE notifications *before* the existing pinned pycycling 0.4.1 parser handles them.
- Capture incoming HEADWIND notifications and outgoing explicit command attempts; optional GATT inventory captured without new subscriptions.
- Bounded in-memory capture per config entry: 10 minutes, 3,000 records, 750 KB; recording off by default and not resumed on restart.
- Export JSONL to the browser for offline analysis; no persistent HA files and no payloads published in sensor state attributes.
- New pure Python tests and dashboard smoke checks.
- No FTMS repeater, active sniffing, ANT+ radio capture, Bluetooth-pulse-strap integration, FIT recording, or automatic exercise-machine control added.

**Beta validation:** CI checks syntax and capture bounds. Hardware capture and real HA WebSocket/browser export still need testing on physical Tacx, WP5000 and HEADWIND.
