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


DEFAULT_IDLE_SECONDS = {"treadmill": 15, "indoor_bike": 15, "rower": 20}
MAX_SAMPLE_GAP = 10


class ActivityMonitor:
    """Infer activity from fresh machine-specific observations, not flywheel speed."""

    def __init__(self, machine_type="treadmill", idle_seconds=None):
        self.machine_type = machine_type
        self.idle_seconds = DEFAULT_IDLE_SECONDS[machine_type] if idle_seconds is None else idle_seconds
        if not 5 <= self.idle_seconds <= 300:
            raise ValueError("Invalid inactivity threshold")
        self.last_sample = None
        self.idle_since = None
        self.idle_timestamp = None
        self.stroke_count = None

    def observe(self, now, timestamp, values):
        """Return True/False for activity, None when no reliable observation exists."""
        key = {"treadmill": "speed_kmh", "indoor_bike": "cadence_rpm",
               "rower": "stroke_count"}[self.machine_type]
        value = values.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            return None
        if self.last_sample is not None and now - self.last_sample > MAX_SAMPLE_GAP:
            self.idle_since = self.idle_timestamp = None
            self.stroke_count = None
        self.last_sample = now
        if self.machine_type == "rower":
            previous = self.stroke_count
            self.stroke_count = value
            if previous is None or value < previous:
                self.idle_since = self.idle_timestamp = None
                return None
            moving = value > previous
        else:
            moving = value > (RUNNING_SPEED_KMH if self.machine_type == "treadmill" else 0)
        if moving:
            self.idle_since = self.idle_timestamp = None
        elif self.idle_since is None:
            self.idle_since, self.idle_timestamp = now, timestamp
        return moving

    def inactive(self, now):
        return (self.idle_since is not None and self.last_sample is not None
                and 0 <= now - self.last_sample <= MAX_SAMPLE_GAP
                and now - self.idle_since >= self.idle_seconds)
