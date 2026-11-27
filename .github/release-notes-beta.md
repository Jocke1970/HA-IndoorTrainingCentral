# HA-IndoorTrainingCentral 2026.11.0b8 (beta)

## Equipment selection via live-status tiles

- Replace the machine-selection dropdown with clear per-device buttons for treadmill, bike trainer and rower.
- Show a live colored dot and Bluetooth state text inside **each** tile, plus the session state when available.
- Highlight the selected machine, preserve existing entity IDs/card URLs, and update connection status on every HA state refresh without re-rendering the rest of the dashboard.
- Keep Wahoo HEADWIND in the bike's accessory panel. Standalone HEADWIND card views still work.
- Responsive tile grid for narrow Home Assistant dashboard columns.
- Add Node.js smoke tests for equipment classification, fan filtering, selection, and status text.

**No changes to Bluetooth connections, trainer control, Protocol Capture, treadmill raw-data journaling or session storage.**

Hardware/UI appearance still needs verification on the installed Home Assistant dashboard.
