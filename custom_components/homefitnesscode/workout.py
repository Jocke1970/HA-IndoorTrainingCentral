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
from pathlib import Path
import re
import time
from uuid import uuid4

IDLE_FINISH_SECONDS = 15
MAX_SESSION_SECONDS = 6 * 3600
MAX_SESSION_BYTES = 30_000_000
PRE_ROLL_FRAMES = 120
MAX_QUEUE = 5000
KEEP_HISTORY = 20
SCHEMA = 1

METRICS = ("speed_kmh", "distance_km", "elapsed_s", "incline_percent",
           "energy_kcal", "heart_rate_bpm", "power_w")


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
    started = None
    finished = None
    samples = 0
    maxima: dict[str, float] = {}
    last_positive_time = None
    last_movement = None
    bytes_read = 0
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
            elif row.get("type") == "frame":
                decoded = row.get("decoded") or {}
                if not isinstance(decoded, dict):
                    continue
                if row.get("characteristic", "").lower().endswith("2acd-0000-1000-8000-00805f9b34fb"):
                    samples += 1
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
    return {
        "id": path.stem,
        "device_name": started.get("device_name", ""),
        "machine_type": "treadmill",
        "started_at": started.get("timestamp"),
        "ended_at": finished.get("timestamp") if finished else last_positive_time,
        "reason": finished.get("reason") if finished else "interrupted",
        "complete": finished is not None,
        "distance_km": round(maxima.get("distance_km", 0), 3),
        "elapsed_s": round(elapsed),
        "energy_kcal": round(maxima.get("energy_kcal", 0), 1),
        "max_speed_kmh": round(maxima.get("speed_kmh", 0), 2),
        "max_incline_percent": round(maxima.get("incline_percent", 0), 2),
        "max_heart_rate_bpm": round(maxima.get("heart_rate_bpm", 0)),
        "raw_frames": samples,
        "raw_bytes": bytes_read,
        "file": path.name,
    }


def _write_summary(raw: Path) -> dict | None:
    summary = replay_session(raw)
    if summary is None:
        return None
    target = raw.with_suffix(".summary.json")
    temporary = target.with_suffix(".summary.json.tmp")
    temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    return summary


def _recover(directory: Path) -> list[dict]:
    directory.mkdir(parents=True, exist_ok=True)
    raw_files = sorted(directory.glob("*.jsonl"), reverse=True)
    result = []
    for path in raw_files[:KEEP_HISTORY]:
        summary_path = path.with_suffix(".summary.json")
        try:
            if summary_path.is_file():
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            else:
                summary = _write_summary(path)
            if summary:
                result.append(summary)
        except (OSError, ValueError):
            continue
    return result[:KEEP_HISTORY]


class WorkoutJournal:
    """Per-device, nonblocking raw FTMS treadmill session recorder."""

    def __init__(self, base: Path, entry_id: str, device_name: str):
        self.directory = Path(base) / safe_segment(entry_id)
        self.device_name = device_name
        self.history: list[dict] = []
        self.active = False
        self.finalizing = False
        self.error: str | None = None
        self.path: Path | None = None
        self.started_at: str | None = None
        self._start_mono = 0.0
        self._last_moving = 0.0
        self._last_elapsed = 0.0
        self._last_dist = 0.0
        self._maxima: dict[str, float] = {}
        self._bytes_queued = 0
        self._preroll = deque(maxlen=PRE_ROLL_FRAMES)
        self._queue: asyncio.Queue[tuple[Path, dict] | None] = asyncio.Queue(maxsize=MAX_QUEUE)
        self._worker: asyncio.Task | None = None
        self._saves: set[asyncio.Task] = set()

    async def async_prepare(self) -> None:
        self.history = await asyncio.to_thread(_recover, self.directory)
        self._worker = asyncio.create_task(self._write_loop())

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
        self.finalizing = False
        self.error = None
        self.started_at = timestamp
        self._start_mono = now
        self._last_moving = now
        self._last_elapsed = 0.0
        self._last_dist = 0.0
        self._maxima = {}
        self._bytes_queued = 0
        self._enqueue(self.path, {"type": "session_start", "schema": SCHEMA,
                                  "timestamp": timestamp, "device_name": self.device_name,
                                  "protocol": "ftms"})
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
        if not self.active:
            self._preroll.append(frame)
            # Do not start a phantom session just because device reports old time/distance.
            if is_treadmill and speed > 0.2:
                self._start(now, timestamp)
            return
        if self.path is None:
            return
        if not self._enqueue(self.path, frame):
            self.close("write_queue_full")
            return
        if is_treadmill:
            for key in METRICS:
                v = values.get(key)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    self._maxima[key] = max(self._maxima.get(key, 0), float(v))
            elapsed = float(values.get("elapsed_s") or 0)
            distance = float(values.get("distance_km") or 0)
            if speed > 0.2 or elapsed > self._last_elapsed or distance > self._last_dist:
                self._last_moving = now
            self._last_elapsed = max(elapsed, self._last_elapsed)
            self._last_dist = max(distance, self._last_dist)
            if now - self._start_mono >= MAX_SESSION_SECONDS:
                self.close("duration_limit")
            elif self._bytes_queued >= MAX_SESSION_BYTES:
                self.close("size_limit")
            elif speed <= 0.2 and now - self._last_moving >= IDLE_FINISH_SECONDS:
                self.close("stopped")

    def tick(self) -> None:
        if self.active and time.monotonic() - self._last_moving >= IDLE_FINISH_SECONDS:
            self.close("stopped")

    def close(self, reason: str = "manual") -> None:
        if not self.active:
            return
        self.active = False
        self.finalizing = True
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
            summary = await asyncio.to_thread(_write_summary, path)
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
            "saving": self.finalizing,
            "error": self.error,
            "started_at": self.started_at if self.active else None,
            "distance_km": round(self._maxima.get("distance_km", 0), 3) if self.active else 0,
            "elapsed_s": round(self._maxima.get("elapsed_s", 0)) if self.active else 0,
            "raw_bytes": self._bytes_queued if self.active else 0,
            "raw_path": str(self.path) if self.active and self.path else None,
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
