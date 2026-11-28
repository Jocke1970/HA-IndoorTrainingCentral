"""Test treadmill raw journaling, persistence, crash replay and sensor resets."""
import asyncio
from datetime import datetime, timezone
import importlib.util
import sys
import types
import json
from pathlib import Path
from unittest.mock import patch

import pytest

path = Path(__file__).parents[1] / "custom_components/homefitnesscode/workout.py"
package = sys.modules.setdefault("itc_test_package", types.ModuleType("itc_test_package"))
package.__path__ = [str(Path(__file__).parents[1] / "custom_components/homefitnesscode")]
spec = importlib.util.spec_from_file_location("itc_test_package.workout", path)
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


@pytest.mark.asyncio
async def test_manual_save_while_belt_moving_does_not_create_new_session(tmp_path):
    j = m.WorkoutJournal(tmp_path, "id", "Q5")
    await j.async_prepare()
    send(j, speed=1)
    j.close("manual")
    send(j, speed=2)
    assert j.active is False
    send(j, speed=0)
    send(j, speed=1.5)
    assert j.active is True
    j.close("manual")
    await j.shutdown()
    assert len(j.history) == 2


@pytest.mark.asyncio
async def test_stationary_elapsed_increasing_does_not_keep_workout_alive(tmp_path):
    j = m.WorkoutJournal(tmp_path, "id", "Q5")
    await j.async_prepare()
    with patch.object(m.time, "monotonic", side_effect=[100, 101, 108, 115, 116]):
        send(j, speed=1, sec=2)
        send(j, speed=0, sec=10)
        send(j, speed=0, sec=17)
        send(j, speed=0, sec=24)
        j.tick()
    assert j.active and j.paused and j.pause_pending
    j.keep_paused()
    assert j.paused and not j.pause_pending
    send(j, speed=2, sec=20)
    assert j.active and not j.paused
    j.close("manual")
    await j.shutdown()
    assert j.history[0]["reason"] == "manual"


def test_replay_multiple_pauses(tmp_path):
    raw = tmp_path / "pass.jsonl"
    def row(kind, second, **extra):
        return dict(type=kind, timestamp=f"2026-11-28T20:00:{second:02d}+00:00", **extra)
    def frame(second, speed=3.6):
        return row("frame", second, direction="rx", characteristic=FTMS,
                   decoded={"speed_kmh":speed,"incline_percent":0,"elapsed_s":second})
    m._append_rows(raw, [row("session_start",0),frame(0),frame(4),
        frame(5,0),row("heart_rate",6,bpm=200),row("session_pause",5),
        row("session_resume",20),frame(20),frame(24),
        row("session_pause",25),row("session_resume",40),frame(40),frame(44),
        row("session_pause",45),row("session_end",59,reason="manual")])
    summary=m.replay_session(raw)
    assert summary["elapsed_s"] == 15
    assert summary["total_elapsed_s"] == 45
    assert summary["paused_s"] == 30
    assert summary["heart_rate_samples"] == 0
    assert summary["average_met"] == pytest.approx(2.71, abs=.01)
    assert summary["met_coverage_s"] == 12
