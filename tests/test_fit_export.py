"""Independent FIT decoder checks against Garmin's official SDK."""
import importlib.util
import json
from pathlib import Path

import pytest
from garmin_fit_sdk import Decoder, Stream

spec = importlib.util.spec_from_file_location("fit_export", Path(__file__).parents[1] / "custom_components/homefitnesscode/fit_export.py")
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)


@pytest.mark.parametrize("profile", ["native", "fenix7pro"])
def test_activity_sdk(tmp_path, profile):
    raw = tmp_path / "pass.jsonl"
    start = "2026-11-28T20:05:04+00:00"
    rows = [
        {"type": "session_start", "timestamp": start},
        {"type": "frame", "timestamp": start, "direction": "rx",
         "characteristic": "00002acd-0000-1000-8000-00805f9b34fb",
         "decoded": {"speed_kmh": 3.6, "distance_km": 0.001, "incline_percent": 2}},
        {"type": "heart_rate", "timestamp": start, "bpm": 90, "rr_interval_ms": 667},
        {"type": "frame", "timestamp": "2026-11-28T20:05:05+00:00", "direction": "rx",
         "characteristic": "00002acd-0000-1000-8000-00805f9b34fb",
         "decoded": {"speed_kmh": 3.6, "distance_km": 0.002, "incline_percent": 2}},
    ]
    raw.write_text("\n".join(map(json.dumps, rows)), encoding="utf-8")
    summary = {"started_at": start, "elapsed_s": 2, "distance_km": .002,
               "average_speed_kmh": 3.6, "max_speed_kmh": 3.6,
               "average_heart_rate_bpm": 90, "max_heart_rate_bpm": 90,
               "heart_rate_source": "M7", "device_name": "Q5",
               "average_met": 3.3, "max_met": 3.4, "met_minutes": .11}
    target = fit.export_fit(raw, summary, profile=profile)
    assert fit.validate_fit(target.read_bytes())
    decoder = Decoder(Stream.from_file(str(target)))
    assert decoder.check_integrity()
    decoder = Decoder(Stream.from_file(str(target)))
    messages, errors = decoder.read()
    assert not errors, errors
    for name in ("file_id_mesgs", "activity_mesgs", "session_mesgs", "lap_mesgs", "record_mesgs", "hrv_mesgs"):
        assert messages.get(name), name
    session = messages["session_mesgs"][0]
    assert session["total_distance"] == pytest.approx(2)
    assert session["total_timer_time"] == pytest.approx(2)
    record = messages["record_mesgs"][0]
    assert record["heart_rate"] == 90
    assert record["speed"] == pytest.approx(1)
    assert record["grade"] == pytest.approx(2)
    rr = messages["hrv_mesgs"][0]["time"]
    assert (rr[0] if isinstance(rr, list) else rr) == pytest.approx(.667)
    damaged = bytearray(target.read_bytes())
    damaged[20] ^= 1
    assert not fit.validate_fit(damaged)
    assert raw.exists()
