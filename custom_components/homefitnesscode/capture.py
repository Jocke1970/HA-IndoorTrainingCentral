"""Bounded, opt-in in-memory protocol frame capture.

No persistent files, no Bluetooth writes, no credentials. An administrator can
export a stopped or running capture as JSON Lines via the WebSocket API.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone


MAX_SECONDS = 600
MAX_RECORDS = 3000
MAX_BYTES = 750_000
SCHEMA_VERSION = 1


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class ProtocolCapture:
    """One recording session for one config entry, disabled by default."""

    def __init__(self) -> None:
        self.active = False
        self.records: list[dict] = []
        self.bytes_used = 0
        self.started_at: str | None = None
        self.stopped_at: str | None = None
        self.stop_reason: str | None = None
        self._start_monotonic = 0.0
        self._deadline = 0.0
        self.profile: str | None = None
        self.device_name: str | None = None

    def start(self, *, profile: str, device_name: str) -> dict:
        """Start fresh; restarting intentionally discards the prior buffer."""
        if self.active:
            return self.status()
        self.records.clear()
        self.bytes_used = 0
        self.active = True
        self.profile = profile
        self.device_name = device_name
        self.started_at = utc_iso()
        self.stopped_at = None
        self.stop_reason = None
        self._start_monotonic = time.monotonic()
        self._deadline = self._start_monotonic + MAX_SECONDS
        return self.status()

    def _expire(self) -> None:
        if self.active and time.monotonic() >= self._deadline:
            self.stop("timeout")

    def stop(self, reason: str = "manual") -> dict:
        if self.active:
            self.active = False
            self.stopped_at = utc_iso()
            self.stop_reason = reason
        return self.status()

    def record(
        self,
        direction: str,
        characteristic: str,
        payload: bytes | bytearray | None = None,
        *,
        decoded: dict | None = None,
        error: str | None = None,
        protocol: str | None = None,
    ) -> None:
        """Record a frame as seen on the wire; never interpret bytes here."""
        if not self.active:
            return
        self._expire()
        if not self.active:
            return
        if direction not in ("rx", "tx", "event"):
            raise ValueError("Invalid capture direction")
        row = {
            "type": "frame",
            "timestamp": utc_iso(),
            "direction": direction,
            "characteristic": characteristic,
            "protocol": protocol or self.profile,
            "hex": bytes(payload).hex() if payload is not None else None,
        }
        if decoded is not None:
            row["decoded"] = decoded
        if error is not None:
            row["decode_error"] = str(error)[:256]
        length = len(json.dumps(row, ensure_ascii=False, separators=(",", ":"),
                                default=str).encode("utf-8")) + 1
        if self.bytes_used + length > MAX_BYTES:
            self.stop("byte_limit")
            return
        self.records.append(row)
        self.bytes_used += length
        if len(self.records) >= MAX_RECORDS:
            self.stop("record_limit")

    def status(self) -> dict:
        self._expire()
        remaining = max(0, int(self._deadline - time.monotonic())) if self.active else 0
        return {
            "active": self.active,
            "count": len(self.records),
            "bytes": self.bytes_used,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "stop_reason": self.stop_reason,
            "seconds_remaining": remaining,
            "max_seconds": MAX_SECONDS,
            "max_records": MAX_RECORDS,
            "max_bytes": MAX_BYTES,
        }

    def export_jsonl(self) -> str:
        self._expire()
        if self.started_at is None:
            return ""
        header = {
            "type": "capture_meta",
            "schema": SCHEMA_VERSION,
            "device_name": self.device_name,
            "protocol": self.profile,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "stop_reason": self.stop_reason,
            "record_count": len(self.records),
            "bytes": self.bytes_used,
            "active_at_export": self.active,
            "capture_scope": "active_ha_ble_connection_only",
        }
        return "\n".join(json.dumps(item, ensure_ascii=False, separators=(",", ":"),
                                    default=str) for item in (header, *self.records)) + "\n"
