# HA-IndoorTrainingCentral 2026.11.0b11 (beta)

## Simplify confirmed Q5 FTMS remote controls

- Confirmed in real Q5 capture: Request Control, Start, target speed, target incline and Stop all return success. FTMS Start from HA is supported; starting on the treadmill console is **not** required.
- Prioritize large **−  [current speed]  +** / **−  [current incline]  +** controls, using 0.5 km/h and 1 percentage-point increments.
- Remove redundant speed confirmation when entering an exact value in Advanced. One-click +/− never prompts for individual adjustments; first motor Start still asks for confirmation.
- Show control-state text: disconnected, control not yet armed, motor stopped, or motor moving.
- Keep existing movement-based interlock, advertised FTMS min/max, HA entity availability and manual arm requirements. Stop remains available when armed; BLE stop is not a physical emergency stop.
- Does not alter BLE transport, FTMS opcodes, workout journal or other machine types.

Field verification remains required for UI display and repeated increment buttons.
