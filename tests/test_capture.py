"""Bounded protocol-capture tests; runs without Home Assistant imports."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

path = Path(__file__).parents[1] / "custom_components/homefitnesscode/capture.py"
spec = importlib.util.spec_from_file_location("protocol_capture", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_capture_off_by_default_and_empty_export():
    capture = mod.ProtocolCapture()
    capture.record("rx", "0x2AD1", b"\\x12\\x34")
    assert capture.status()["count"] == 0
    assert capture.export_jsonl() == ""


def test_start_capture_and_export_all_frames_in_order():
    capture = mod.ProtocolCapture()
    capture.start(profile="ftms", device_name="WP5000")
    capture.record("rx", "2ad1", bytes.fromhex("1234"),
                   decoded={"stroke_rate_spm": 25})
    capture.record("rx", "2ad1", bytes.fromhex("ff"),
                   error="Truncated FTMS payload")
    capture.record("event", "gatt_inventory",
                   decoded={"characteristics": ["2ad1"]})
    capture.stop()
    rows = [json.loads(line) for line in capture.export_jsonl().splitlines()]
    assert rows[0]["type"] == "capture_meta"
    assert rows[0]["device_name"] == "WP5000"
    assert rows[0]["capture_scope"] == "active_ha_ble_connection_only"
    assert rows[0]["record_count"] == 3
    assert [row["hex"] for row in rows[1:]] == ["1234", "ff", None]
    assert rows[2]["decode_error"] == "Truncated FTMS payload"
    assert all(row["timestamp"].endswith("+00:00") for row in rows[1:])


def test_stop_does_not_drop_data_and_restart_clears_data():
    capture = mod.ProtocolCapture()
    capture.start(profile="ftms", device_name="Test")
    capture.record("rx", "a", b"\\x01")
    capture.stop()
    capture.record("rx", "a", b"\\x02")
    assert capture.status()["count"] == 1
    capture.start(profile="ftms", device_name="Test2")
    assert capture.status()["count"] == 0
    assert capture.status()["active"] is True


def test_time_limit_stops_even_without_new_packets():
    capture = mod.ProtocolCapture()
    with patch.object(mod.time, "monotonic", side_effect=[100.0, 100.0, 100.0, 701.0, 702.0]):
        capture.start(profile="ftms", device_name="Demo")
        assert not capture.status()["active"]
        assert capture.status()["stop_reason"] == "timeout"


def test_record_limit():
    capture = mod.ProtocolCapture()
    with patch.object(mod, "MAX_RECORDS", 2):
        capture.start(profile="ftms", device_name="Demo")
        capture.record("rx", "ch", b"\\x00")
        capture.record("rx", "ch", b"\\x01")
        assert capture.status()["stop_reason"] == "record_limit"
        assert capture.status()["count"] == 2


def test_byte_limit():
    capture = mod.ProtocolCapture()
    with patch.object(mod, "MAX_BYTES", 15):
        capture.start(profile="ftms", device_name="Demo")
        capture.record("rx", "ch", b"\\x01")
        assert capture.status()["stop_reason"] == "byte_limit"
        assert capture.status()["count"] == 0


def test_direction_validation_and_export_without_finished_capture():
    capture = mod.ProtocolCapture()
    capture.start(profile="ftms", device_name="Demo")
    with pytest.raises(ValueError):
        capture.record("invalid", "ch", b"")
    assert json.loads(capture.export_jsonl().splitlines()[0])["active_at_export"] is True
