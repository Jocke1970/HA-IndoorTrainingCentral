# HA-IndoorTrainingCentral 2026.11.0b3 (beta)

- Public rebranding: GitHub repo, Marketplace display name, HA integration and dashboard.
- Preserves existing integration domain `homefitnesscode`, config entries, entity IDs, and old dashboard card type/resource.
- Introduces card `custom:indoor-training-central-card` and new optional resource URL.
- Responsive layout for narrow dashboard columns, mobile and desktop.
- Device-dependent controls, cleaner connection status, and improved names.
- Wahoo HEADWIND remains integrated with Tacx cycling view and in its own view.
- Rename 'Arm remote control' to 'Aktivera styrning' (the FTMS Request Control function).
- No automatic motor or fan mode changes on reconnect.
- No FIT generation yet; it remains a separate upcoming workstream.

Offline tests and UI smoke checks run in CI; verify all physical controls in HA before enabling remote writes.
