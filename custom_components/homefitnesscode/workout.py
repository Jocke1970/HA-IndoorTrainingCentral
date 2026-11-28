"""Crash-recoverable treadmill workout journal built from received FTMS frames.

Raw session frames are stored ONLY under /config/homefitnesscode/sessions/<entry_id>.
In-memory metrics are for UI; completed workout summaries are REPLAYED from JSONL.
No Bluetooth control commands, no writes into custom_components.
"""
from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import time
from uuid import uuid4

from .activity import ActivityMonitor
from .fit_export import export_fit, EXPORT_VERSION, validate_fit, PROFILES

IDLE_FINISH_SECONDS = 15
MAX_SESSION_SECONDS = 6 * 3600
MAX_SESSION_BYTES = 30_000_000
PRE_ROLL_FRAMES = 120
MAX_QUEUE = 5000
KEEP_HISTORY = 20
SCHEMA = 1

METRICS = ("speed_kmh", "distance_km", "elapsed_s", "incline_percent",
           "energy_kcal", "heart_rate_bpm", "power_w")


class MetAccumulator:
    """Estimated gross MET from treadmill speed and grade; never bridge stale data."""
    def __init__(self):
        self.previous = None
        self.current = None
        self.peak = None
        self.seconds = 0.0
        self.integral = 0.0

    def add(self, timestamp, values):
        speed = values.get("speed_kmh")
        grade = values.get("incline_percent")
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                   and math.isfinite(v) for v in (speed, grade)):
            self.previous = None
            self.current = None
            return
        if not 0 <= speed <= 30 or not 0 <= grade <= 30:
            self.previous = None
            self.current = None
            return
        if self.previous is not None:
            old_time, old_met = self.previous
            dt = timestamp - old_time
            if 0 < dt <= 5 and old_met is not None:
                self.seconds += dt
                self.integral += old_met * dt
        if speed <= 0.2:
            met = None
        else:
            metres_min = speed * 1000 / 60
            horizontal, vertical = (0.1, 1.8) if speed < 8 else (0.2, 0.9)
            met = (3.5 + metres_min * (horizontal + vertical * grade / 100)) / 3.5
            self.peak = met if self.peak is None else max(self.peak, met)
        self.current = met
        self.previous = (timestamp, met)

    def metrics(self):
        return {
            "current_met": round(self.current, 2) if self.current is not None else None,
            "average_met": round(self.integral / self.seconds, 2) if self.seconds else None,
            "max_met": round(self.peak, 2) if self.peak is not None else None,
            "met_minutes": round(self.integral / 60, 2),
            "met_coverage_s": round(self.seconds, 2),
            "met_method": "acsm_estimate_speed_switch_8_kmh",
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def safe_segment(value: str) -> str:
    """Never allow HA config entry IDs to escape the designated directory."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", value)[:80] or "device"


def _append_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"), default=str))
            file.write("\n")


def replay_session(path: Path) -> dict | None:
    """Derive a finished/incomplete workout from persisted wire frames."""
    met = MetAccumulator()
    started = None
    finished = None
    samples = 0
    external_hr = []
    machine_hr = []
    maxima: dict[str, float] = {}
    last_positive_time = None
    last_movement = None
    bytes_read = 0
    pauses = []
    pause_start = None
    with path.open(encoding="utf-8") as file:
        for line in file:
            try:
                row = json.loads(line)
                if row.get("type") == "session_pause" and pause_start is None:
                    pause_start = datetime.fromisoformat(row["timestamp"])
                elif row.get("type") == "session_resume" and pause_start is not None:
                    resume = datetime.fromisoformat(row["timestamp"])
                    if resume >= pause_start:
                        pauses.append((pause_start, resume))
                    pause_start = None
            except (ValueError, KeyError, TypeError):
                continue

    def excluded(row):
        try:
            ts = datetime.fromisoformat(row["timestamp"])
            return (any(a <= ts < b for a,b in pauses)
                    or (pause_start is not None and ts >= pause_start)
                    or (started and started.get("timestamp") and ts < datetime.fromisoformat(started["timestamp"])))
        except (ValueError, KeyError, TypeError):
            return False

    with path.open(encoding="utf-8") as file:
        for line in file:
            bytes_read += len(line.encode("utf-8"))
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue  # power loss can truncate last line
            if row.get("type") == "session_start":
                started = row
            elif row.get("type") == "session_end":
                finished = row
            elif row.get("type") == "heart_rate":
                if excluded(row):
                    continue
                bpm = row.get("bpm")
                if isinstance(bpm, (int, float)) and 0 < bpm <= 255:
                    external_hr.append(bpm)
            elif row.get("type") == "frame":
                decoded = row.get("decoded") or {}
                if not isinstance(decoded, dict):
                    continue
                if row.get("characteristic", "").lower().endswith("2acd-0000-1000-8000-00805f9b34fb"):
                    samples += 1
                    if excluded(row):
                        met.previous = None
                        met.current = None
                        continue
                    if started and row.get("direction") == "rx":
                        try:
                            ts = datetime.fromisoformat(row["timestamp"])
                            if ts >= datetime.fromisoformat(started["timestamp"]):
                                met.add(ts.timestamp(), decoded)
                        except (KeyError, ValueError, TypeError):
                            pass
                    bpm = decoded.get("heart_rate_bpm")
                    if isinstance(bpm, (int, float)) and 0 < bpm <= 255:
                        machine_hr.append(bpm)
                    for key in METRICS:
                        value = decoded.get(key)
                        if isinstance(value, (int, float)) and not isinstance(value, bool):
                            maxima[key] = max(maxima.get(key, 0), float(value))
                    if (decoded.get("speed_kmh") or 0) > 0.2:
                        last_movement = row.get("timestamp")
                    last_positive_time = row.get("timestamp")
    if started is None:
        return None
    elapsed = maxima.get("elapsed_s", 0)
    if elapsed <= 0 and last_movement and started.get("timestamp"):
        try:
            elapsed = max(0, (datetime.fromisoformat(last_movement) -
                              datetime.fromisoformat(started["timestamp"])).total_seconds())
        except (ValueError, TypeError):
            pass
    wall_elapsed = elapsed
    if pauses or pause_start is not None:
        try:
            start_dt = datetime.fromisoformat(started["timestamp"])
            end_dt = pause_start or datetime.fromisoformat((finished or {}).get("timestamp") or last_movement)
            # FIT timestamps use whole seconds; keep summaries aligned.
            wall_elapsed = int(end_dt.timestamp()) - int(start_dt.timestamp())
            elapsed = max(0, wall_elapsed - sum(int(b.timestamp())-int(a.timestamp()) for a,b in pauses))
        except (ValueError, KeyError, TypeError):
            pass
    hr = external_hr if external_hr else machine_hr if not started.get("hr_source_id") else []
    return {
        "id": path.stem,
        "device_name": started.get("device_name", ""),
        "machine_type": "treadmill",
        "started_at": started.get("timestamp"),
        "ended_at": finished.get("timestamp") if finished else last_positive_time,
        "reason": finished.get("reason") if finished else "interrupted",
        "complete": finished is not None and finished.get("reason") in ("stopped", "manual"),
        "distance_km": round(maxima.get("distance_km", 0), 3),
        "average_speed_kmh": round(maxima.get("distance_km", 0) * 3600 / elapsed, 2)
        if elapsed > 0 else 0,
        "elapsed_s": round(elapsed),
        "total_elapsed_s": round(wall_elapsed),
        "paused_s": max(0, round(wall_elapsed - elapsed)),
        "energy_kcal": round(maxima.get("energy_kcal", 0), 1),
        "max_speed_kmh": round(maxima.get("speed_kmh", 0), 2),
        "max_incline_percent": round(maxima.get("incline_percent", 0), 2),
        "max_heart_rate_bpm": round(max(hr)) if hr else 0,
        "average_heart_rate_bpm": round(sum(hr) / len(hr), 1) if hr else None,
        "heart_rate_samples": len(hr),
        "heart_rate_source": started.get("hr_source_name") or "training_machine",
        **met.metrics(),
        "raw_frames": samples,
        "raw_bytes": bytes_read,
        "file": path.name,
    }


def write_metadata(target: Path, data: dict) -> None:
    temporary = target.with_name(target.name + "." + uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def _write_summary(raw: Path, profile: str = "native") -> dict | None:
    summary = replay_session(raw)
    if summary is None:
        return None
    target = raw.with_suffix(".summary.json")
    if target.is_file():
        try:
            old = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(old.get("session_name"), str):
                summary["session_name"] = old["session_name"]
        except (OSError, ValueError):
            pass
    summary.setdefault("session_name", "Löpband")
    if summary.get("complete") and summary.get("elapsed_s", 0) > 0:
        try:
            summary["fit_file"] = export_fit(raw, summary, profile=profile).name
            summary["fit_export_version"] = EXPORT_VERSION
            summary["fit_profile"] = profile
            summary["fit_available"] = True
            summary["raw_available"] = True
        except (OSError, ValueError, TypeError, OverflowError) as err:
            summary["fit_error"] = str(err)[:160]
    write_metadata(target, summary)
    return summary


def _recover(directory: Path, profile: str = "native") -> list[dict]:
    directory.mkdir(parents=True, exist_ok=True)
    ids = {p.stem for p in directory.glob("*.jsonl")}
    ids.update(p.name.removesuffix(".summary.json") for p in directory.glob("*.summary.json"))
    result = []
    for session_id in sorted(ids, reverse=True):
        path = directory / (session_id + ".jsonl")
        summary_path = directory / (session_id + ".summary.json")
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else None
            if path.is_file() and (not summary or "met_method" not in summary
                    or (summary.get("complete") and (summary.get("fit_export_version") != EXPORT_VERSION
                        or not path.with_suffix(".fit").is_file()))):
                summary = _write_summary(path, summary.get("fit_profile", profile) if summary else profile)
            if summary:
                summary["raw_available"] = path.is_file()
                fit = path.with_suffix(".fit")
                summary["fit_available"] = fit.is_file() and validate_fit(fit.read_bytes())
                result.append(summary)
            if len(result) >= KEEP_HISTORY:
                break
        except (OSError, ValueError, TypeError):
            continue
    return result[:KEEP_HISTORY]


class WorkoutJournal:
    """Per-device, nonblocking raw FTMS treadmill session recorder."""

    def __init__(self, base: Path, entry_id: str, device_name: str):
        self.directory = Path(base) / safe_segment(entry_id)
        self.device_name = device_name
        self.history: list[dict] = []
        self.fit_profile = "native"
        self._settings_lock = asyncio.Lock()
        self.active = False
        self.paused = False
        self.pause_pending = False
        self.activity_monitor = ActivityMonitor()
        self.finalizing = False
        self.error: str | None = None
        self.path: Path | None = None
        self.started_at: str | None = None
        self.hr_source_id = None
        self.hr_source_name = None
        self._met = MetAccumulator()
        self._start_mono = 0.0
        self._last_moving = 0.0
        self._last_elapsed = 0.0
        self._last_dist = 0.0
        self._maxima: dict[str, float] = {}
        self._await_stationary = False
        self._bytes_queued = 0
        self._preroll = deque(maxlen=PRE_ROLL_FRAMES)
        self._queue: asyncio.Queue[tuple[Path, dict] | None] = asyncio.Queue(maxsize=MAX_QUEUE)
        self._worker: asyncio.Task | None = None
        self._saves: set[asyncio.Task] = set()

    async def async_prepare(self) -> None:
        self.fit_profile = await asyncio.to_thread(self._load_profile)
        self.history = await asyncio.to_thread(_recover, self.directory, self.fit_profile)
        self._worker = asyncio.create_task(self._write_loop())

    def _load_profile(self):
        try:
            profile = json.loads((self.directory / "settings.json").read_text(encoding="utf-8")).get("fit_profile")
            return profile if profile in PROFILES else "native"
        except (OSError, ValueError, TypeError, AttributeError):
            return "native"

    async def set_fit_profile(self, profile):
        if profile not in PROFILES:
            raise ValueError("Invalid FIT profile")
        async with self._settings_lock:
            await asyncio.to_thread(write_metadata, self.directory / "settings.json",
                                    {"fit_profile": profile, "retain_raw": True})
            self.fit_profile = profile

    def _enqueue(self, path: Path, item: dict) -> bool:
        if self._queue.full():
            self.error = "write_queue_full"
            return False
        self._queue.put_nowait((path, item))
        self._bytes_queued += len(json.dumps(item, separators=(",", ":"), default=str))
        return True

    async def _write_loop(self) -> None:
        """Serial batched disk writes, never blocking HA's BLE notification loop."""
        while True:
            first = await self._queue.get()
            if first is None:
                self._queue.task_done()
                return
            group = [first]
            while len(group) < 100:
                try:
                    next_item = self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                if next_item is None:
                    # Terminate only after preceding data flushed.
                    self._queue.task_done()
                    await self._write_batch(group)
                    return
                group.append(next_item)
            await self._write_batch(group)

    async def _write_batch(self, group: list[tuple[Path, dict]]) -> None:
        try:
            by_path: dict[Path, list[dict]] = {}
            for path, row in group:
                by_path.setdefault(path, []).append(row)
            for path, rows in by_path.items():
                await asyncio.to_thread(_append_rows, path, rows)
        except OSError as err:
            self.error = "disk_write_error: " + str(err)[:160]
            self.active = False
        finally:
            for _ in group:
                self._queue.task_done()

    def _start(self, now: float, timestamp: str) -> None:
        filename = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8] + ".jsonl"
        self.path = self.directory / filename
        self.active = True
        self.paused = False
        self.pause_pending = False
        self.finalizing = False
        self.error = None
        self.started_at = timestamp
        self._met = MetAccumulator()
        self._start_mono = now
        self._last_moving = now
        self._last_elapsed = 0.0
        self._last_dist = 0.0
        self._maxima = {}
        self._bytes_queued = 0
        self._enqueue(self.path, {"type": "session_start", "schema": SCHEMA,
                                  "timestamp": timestamp, "device_name": self.device_name,
                                  "protocol": "ftms", "hr_source_id": self.hr_source_id,
                                  "hr_source_name": self.hr_source_name})
        for frame in self._preroll:
            self._enqueue(self.path, frame)
        self._preroll.clear()

    def on_frame(self, direction: str, characteristic: str, payload: bytes | bytearray | None,
                 *, decoded: dict | None = None, error: str | None = None,
                 protocol: str | None = None) -> None:
        """Tee transport frames into session journal without changing control."""
        if self._worker is None:
            return
        now = time.monotonic()
        timestamp = utc_now()
        frame = {"type": "frame", "timestamp": timestamp, "direction": direction,
                 "characteristic": characteristic, "protocol": protocol or "ftms",
                 "hex": bytes(payload).hex() if payload is not None else None}
        if decoded is not None:
            frame["decoded"] = decoded
        if error is not None:
            frame["decode_error"] = str(error)[:160]
        values = decoded or {}
        is_treadmill = (direction == "rx" and
                        characteristic.lower().endswith("2acd-0000-1000-8000-00805f9b34fb"))
        speed = float(values.get("speed_kmh") or 0) if is_treadmill else 0
        moving = self.activity_monitor.observe(now, timestamp, values) if is_treadmill else None
        if not self.active:
            self._preroll.append(frame)
            if moving is False:
                self._await_stationary = False
            # Only physical movement starts a pass. Manual stop must not
            # instantly create another session while belt is still moving.
            if moving is True and not self._await_stationary:
                self._start(now, timestamp)
                self._met.add(now, values)
            return
        if self.path is None:
            return
        if moving is True and self.paused:
            if not self._enqueue(self.path, {"type": "session_resume", "timestamp": timestamp}):
                self.close("write_queue_full")
                return
            self.paused = self.pause_pending = False
        if not self._enqueue(self.path, frame):
            self.close("write_queue_full")
            return
        if is_treadmill:
            self._met.add(now, values)
            for key in METRICS:
                v = values.get(key)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    self._maxima[key] = max(self._maxima.get(key, 0), float(v))
            elapsed = float(values.get("elapsed_s") or 0)
            distance = float(values.get("distance_km") or 0)
            # Elapsed time can continue increasing when a belt is stationary:
            # do not confuse that with actual treadmill movement.
            if moving is True:
                self._last_moving = now
            self._last_elapsed = max(elapsed, self._last_elapsed)
            self._last_dist = max(distance, self._last_dist)
            if now - self._start_mono >= MAX_SESSION_SECONDS:
                self.close("duration_limit")
            elif self._bytes_queued >= MAX_SESSION_BYTES:
                self.close("size_limit")
            elif self.activity_monitor.inactive(now):
                self._offer_pause()

    def record_heart_rate(self, source_id, bpm, rr_ms=None):
        """Store only live notifications from the selected source during motion."""
        if (not self.active or self.paused or self.path is None or source_id != self.hr_source_id
                or time.monotonic() - self._last_moving > 5
                or not isinstance(bpm, (int, float)) or not 0 < bpm <= 255):
            return
        if not self._enqueue(self.path, {"type": "heart_rate", "timestamp": utc_now(),
                                         "source_id": source_id, "bpm": bpm, "rr_interval_ms": rr_ms}):
            self.close("write_queue_full")
        elif self._bytes_queued >= MAX_SESSION_BYTES:
            self.close("size_limit")

    def _offer_pause(self):
        if not self.active or self.paused or self.path is None:
            return
        if self.activity_monitor.idle_timestamp is None:
            # Missing telemetry is not confirmed stationary motion.
            return
        if self._enqueue(self.path, {"type": "session_pause", "timestamp": self.activity_monitor.idle_timestamp}):
            self.paused = self.pause_pending = True

    def keep_paused(self):
        self.pause_pending = False

    def tick(self) -> None:
        if self.active:
            now = time.monotonic()
            if now - self._start_mono >= MAX_SESSION_SECONDS:
                self.close("duration_limit")
            elif self.activity_monitor.inactive(now):
                self._offer_pause()

    def close(self, reason: str = "manual") -> None:
        if not self.active:
            return
        self.active = False
        self.paused = self.pause_pending = False
        self.finalizing = True
        self._await_stationary = reason in ("manual", "size_limit", "duration_limit")
        if self.path is None:
            return
        path = self.path
        self._enqueue(path, {"type": "session_end", "timestamp": utc_now(), "reason": reason})
        task = asyncio.create_task(self._finalize(path))
        self._saves.add(task)
        task.add_done_callback(self._saves.discard)

    async def _finalize(self, path: Path) -> None:
        try:
            await self._queue.join()
            summary = await asyncio.to_thread(_write_summary, path, self.fit_profile)
            if summary:
                self.history = [summary] + [item for item in self.history
                                            if item.get("id") != summary["id"]]
                self.history = self.history[:KEEP_HISTORY]
        except (OSError, ValueError) as err:
            self.error = "summary_error: " + str(err)[:160]
        finally:
            self.finalizing = False

    def status(self) -> dict:
        return {
            "active": self.active,
            "paused": self.paused,
            "pause_pending": self.pause_pending,
            "idle_seconds": self.activity_monitor.idle_seconds,
            "hr_source_id": self.hr_source_id,
            "hr_source_name": self.hr_source_name,
            "saving": self.finalizing,
            "error": self.error,
            "started_at": self.started_at if self.active else None,
            "distance_km": round(self._maxima.get("distance_km", 0), 3) if self.active else 0,
            "elapsed_s": round(self._maxima.get("elapsed_s", 0)) if self.active else 0,
            "raw_bytes": self._bytes_queued if self.active else 0,
            "raw_path": str(self.path) if self.active and self.path else None,
            **(self._met.metrics() if self.active else MetAccumulator().metrics()),
            "fit_profile": self.fit_profile,
            "retain_raw": True,
            "recent": self.history[:8],
            "storage_directory": str(self.directory),
        }

    async def shutdown(self) -> None:
        if self.active:
            self.close("integration_unload")
        if self._saves:
            await asyncio.gather(*self._saves, return_exceptions=True)
        if self._worker:
            await self._queue.put(None)
            await self._worker
            self._worker = None
