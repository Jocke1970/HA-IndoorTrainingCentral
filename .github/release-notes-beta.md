# HA-IndoorTrainingCentral 2026.11.0b9 (beta)

## Animated treadmill runner and correct live workout state

- Add a small animated running figure next to the treadmill heading and animate the treadmill navigation icon only while Q5 reports speed over 0.2 km/h.
- Use FTMS treadmill speed to update the backend **Workout status** entity: Ready -> Running -> Stopped. This fixes the Q5 displaying "Redo" during a walk because it does not transmit FTMS status on every start.
- Keep explicit FTMS safety-stop status authoritative and preserve status semantics for bikes, rowers, and HEADWIND.
- Include a defensive UI fallback for Q5 live speed, tests for connected/disconnected/idle/moving states, and reduced-motion accessibility.

**No changes to Bluetooth connection management, motor controls, raw session journaling, or saved workouts.**

Hardware check: verify runner moves and "Pass pågår" is shown when Q5 belt runs, then animation stops after speed returns to zero.
