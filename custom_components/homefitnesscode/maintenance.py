"""Pure treadmill runtime and calendar-based lubrication accounting."""
from datetime import date, timedelta
import math


class Maintenance:
    def __init__(self, data=None):
        self.data = data or {"total_seconds": 0.0, "daily_seconds": {},
                             "first_use": None, "history": [], "warning": False}
        self.previous = None

    def interrupt(self):
        self.previous = None

    def sample(self, speed, monotonic, today):
        """Count only bounded intervals between observed moving samples."""
        try:
            moving = math.isfinite(float(speed)) and float(speed) > 0.2
        except (ValueError, TypeError):
            moving = False
        if not moving:
            self.interrupt()
            return
        day = today.isoformat()
        if self.data["first_use"] is None:
            self.data["first_use"] = day
        if self.previous is not None:
            elapsed = monotonic - self.previous
            if 0 < elapsed <= 5:
                self.data["total_seconds"] += elapsed
                daily = self.data["daily_seconds"]
                daily[day] = daily.get(day, 0) + elapsed
        self.previous = monotonic

    def snapshot(self, today):
        daily = self.data["daily_seconds"]
        cutoff = today - timedelta(days=27)
        weekly = sum(v for k, v in daily.items()
                     if cutoff <= date.fromisoformat(k) <= today) / 3600 / 4
        interval = 60 if weekly < 3 else 45 if weekly <= 5 else 30
        history = self.data["history"]
        last = history[-1] if history else None
        baseline = last["date"] if last else self.data["first_use"]
        remaining = None if baseline is None else interval - (today - date.fromisoformat(baseline)).days
        if remaining is not None and remaining <= 5:
            self.data["warning"] = True
        return {
            "total_runtime": round(self.data["total_seconds"] / 3600, 3),
            "runtime_since_lubrication": round((self.data["total_seconds"] - (last["total_seconds"] if last else 0)) / 3600, 3),
            "weekly_runtime_average": round(weekly, 3),
            "lubrication_interval": interval,
            "lubrication_remaining": remaining,
            "last_lubrication": last["date"] if last else None,
            "lubrication_due": self.data["warning"],
            "lubrication_overdue": remaining is not None and remaining <= 0,
            "factory_lubricated": not history,
            "first_use": self.data["first_use"],
        }

    def acknowledge(self, today):
        self.data["history"].append({"date": today.isoformat(),
                                     "total_seconds": self.data["total_seconds"]})
        self.data["warning"] = False
