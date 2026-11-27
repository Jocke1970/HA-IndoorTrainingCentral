"""Test treadmill raw journaling, persistence, crash replay and sensor resets."""
import asyncio
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

path = Path(__file__).parents[1] / "custom_components/homefitnesscode/workout.py"
spec = importlib.util.spec_from_file_location("workout", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

FTMS = "00002acd-0000-1000-8000-00805f9b34fb"


def send(journal, *, speed=0, dist=0, sec=0, kcal=0, incline=0):
    journal.on_frame("rx", FTMS, bytes.fromhex("010203"),
                     decoded={"speed_kmh": speed, "distance_km": dist,
                              "elapsed_s": sec, "energy_kcal": kcal,
                              "incline_percent": incline})


@pytest.mark.asyncio
async def test_auto_session_reset_and_restart(tmp_path):
    j = m.WorkoutJournal(tmp_path, "id/../../unsafe", "Q5-6Y 73A9")
    await j.async_prepare()
    assert ".." not in j.directory.as_posix()
    assert not j.active
    send(j, speed=0)
    send(j, speed=1, dist=0.001, sec=2)
    assert j.active
    send(j, speed=3, dist=0.02, sec=34, kcal=1, incline=3)
    send(j, speed=0, dist=0, sec=0, kcal=0, incline=0)
    j.close("stopped")
    await j.shutdown()
    assert len(j.history) == 1
    summary = j.history[0]
    assert summary["distance_km"] == 0.02
    assert summary["elapsed_s"] == 34
    assert summary["max_speed_kmh"] == 3
    assert summary["max_incline_percent"] == 3
    assert summary["energy_kcal"] == 1
    assert summary["raw_frames"] >= 3
    assert summary["complete"]
    assert summary["reason"] == "stopped"
    raw = next(j.directory.glob("*.jsonl"))
    text = raw.read_text(encoding="utf-8")
    assert '"hex":"010203"' in text
    assert '"session_end"' in text
    again = m.WorkoutJournal(tmp_path, "id/../../unsafe", "Q5-6Y 73A9")
    await again.async_prepare()
    assert again.history[0]["distance_km"] == 0.02
    await again.shutdown()


@pytest.mark.asyncio
async def test_manual_stop_and_new_session(tmp_path):
    j = m.WorkoutJournal(tmp_path, "a", "Walking pad")
    await j.async_prepare()
    send(j, speed=1)
    j.close("manual")
    await asyncio.sleep(.01)
    send(j, speed=0)
    send(j, speed=2)
    assert j.active
    j.close("manual")
    await j.shutdown()
    assert len(j.history) == 2
    assert len(list(j.directory.glob("*.jsonl"))) == 2


@pytest.mark.asyncio
async def test_raw_status_and_diagnostics_are_kept(tmp_path):
    j = m.WorkoutJournal(tmp_path, "b", "Pad")
    await j.async_prepare()
    send(j, speed=1)
    j.on_frame("rx", "00002ada-0000-1000-8000-00805f9b34fb",
               b"\x04", decoded={"session_status":"running"})
    j.on_frame("rx", "00002acd-0000-1000-8000-00805f9b34fb",
               b"\x01", error="Invalid FTMS flags")
    j.close()
    await j.shutdown()
    raw = next(j.directory.glob("*.jsonl")).read_text()
    assert '"hex":"04"' in raw
    assert "Invalid FTMS flags" in raw


@pytest.mark.asyncio
async def test_interrupted_recovery_from_raw(tmp_path):
    root = tmp_path / "c"
    raw = root / "20261127T190000Z-deadbeef.jsonl"
    m._append_rows(raw, [
        {"type":"session_start","timestamp":"2026-11-27T19:00:00+00:00",
         "device_name":"Q5", "protocol":"ftms"},
        {"type":"frame","timestamp":"2026-11-27T19:05:00+00:00",
         "characteristic":FTMS, "decoded":{"elapsed_s":300,
                                            "distance_km":0.5,
                                            "speed_kmh":3.0}},
    ])
    with raw.open("a") as out:
        out.write('{"corrupt":')
    j = m.WorkoutJournal(tmp_path, "c", "Q5")
    await j.async_prepare()
    assert j.history[0]["complete"] is False
    assert j.history[0]["reason"] == "interrupted"
    assert j.history[0]["distance_km"] == 0.5
    await j.shutdown()
