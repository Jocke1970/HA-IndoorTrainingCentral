## 2026.11.0b16 — training archive and mobile display

- Official Garmin FIT SDK encoder/decoder; automatic and retrospective treadmill FIT export.
- Native and fēnix 7 Pro export identities (Garmin Connect training metrics not guaranteed).
- Estimated MET developer fields, recorded HR and RR intervals.
- Activity-based pause detection, pause decision popup, physical resume, active versus elapsed time.
- Configurable treadmill inactivity threshold; shared activity detector for cycling and rowing (full journals pending).
- Separate Training, History and Settings views, mobile display, optional fullscreen and screen wake lock.
- Persistent session names, FIT downloads and optional retention of raw JSONL. Default: keep raw data. Existing files are not retroactively pruned.
- No changes to Bluetooth transport or remote-start safety policy.

Automated tests: 61 passed on dev before release preparation. Practical Q5, mobile UI and Garmin Connect import tests remain pending. Keep raw retention enabled for initial testing.
