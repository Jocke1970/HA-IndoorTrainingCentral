# HA-IndoorTrainingCentral 2026.11.0b7 (beta)

## Persist treadmill workouts from raw FTMS notifications

- Automatically start a treadmill workout journal when actual belt speed exceeds 0.2 km/h; no HA machine-control commands.
- Store received raw FTMS payloads, timestamps, decoded fields and protocol information in append-only JSONL inside /config/homefitnesscode/sessions/<entry_id>/.
- Replay the raw file to derive a persisted per-session .summary.json; preserve peak elapsed time, distance and calories even when the treadmill resets them at stop.
- Close after approximately 15 seconds idle; allow explicit "Avsluta och spara pass" from the Lovelace card, independent of motor stop.
- Show a live session and recent saved sessions in a new "Träningspass" expander.
- Recover raw recordings after interrupted HA shutdown; classify interrupted/limited sessions separately.
- Bound single-session raw storage to 6 hours or 30 MB. No automated file deletion in this beta.
- Keep diagnostic Protocol Capture and direct Bluetooth control behavior unchanged.
- Add async journal/replay tests, including sensor reset, manual save, interruption recovery and phantom-session prevention.

**Scope:** FTMS treadmills only. Other machines, FIT export, multi-sensor session fusion and FTMS repeaters are not included. Hardware testing in HA is still required.
