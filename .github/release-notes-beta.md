# HA-IndoorTrainingCentral 2026.11.0b5 (beta)

## Native Home Assistant icon

- Add an optimized **ITC** emblem for compact UI surfaces, matching the blue and turquoise color palette of the existing four-sport main logo.
- Ship `custom_components/homefitnesscode/brand/icon.png` (256 px) and `brand/icon@2x.png` (512 px), locally served by Home Assistant 2026.3+.
- Keep editable `assets/branding/itc-icon.svg` in the repository.
- No behavioral changes to Bluetooth, training targets, HEADWIND or FIT exports.
- Preserve legacy `homefitnesscode` integration domain and existing entities.

Keep b5 in beta until the icon is confirmed visible in a real HA dashboard/integration view.
