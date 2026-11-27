"""Read-only workout-state inference from live fitness-machine telemetry.

Some FTMS treadmills (including the tested Q5) do not emit FTMS status
notifications when the belt starts and stops. Speed is observed state,
not permission to issue motor commands.
"""
from __future__ import annotations

import math
from typing import Any

RUNNING_SPEED_KMH = 0.2


def observed_session_status(machine_type: str, previous: str,
                            values: dict[str, Any]) -> str:
    """Infer treadmill motion without overriding explicit FTMS safety events."""
    if "session_status" in values:
        return values["session_status"]
    if machine_type != "treadmill" or "speed_kmh" not in values:
        return previous
    try:
        speed = float(values["speed_kmh"])
    except (TypeError, ValueError):
        return previous
    if not math.isfinite(speed) or speed < 0:
        return previous
    if speed > RUNNING_SPEED_KMH:
        # A safety stop always takes precedence over movement telemetry.
        return previous if previous == "safety_stop" else "running"
    if previous == "running":
        return "stopped"
    return previous
