# HA-IndoorTrainingCentral 2026.11.0b10 (beta)

## FTMS treadmill control test buttons

- Added dedicated treadmill UI: FTMS Start, Pause, Stop, ±0.5 km/h speed and ±1 percentage-point incline buttons.
- Speed and incline test buttons **stay locked until the treadmill is started and FTMS telemetry confirms the belt is moving** (>0.2 km/h). This is safe to try with an EMPTY treadmill and avoids starting the motor via a target-speed step.
- Start requires an explicit confirmation; Stop stays available once control is armed, independently of speed telemetry. Stop over BLE is not an emergency stop.
- Button commands reuse the established FTMS request-control, acknowledged write, range validation and HA number/button entities. No manufacturer-specific protocol or new Bluetooth connection is involved.
- Advanced exact numeric FTMS targets remain available while the belt is moving.
- Added JS smoke tests for stopped/moving, connection, arming, speed step and limits.

**Physical hardware validation remains required.** In particular, if Q5 accepts an FTMS Start command without actually spinning the motor, speed/incline buttons intentionally remain locked until movement is reported. Use physical safety key and keep belt clear.
