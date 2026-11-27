"""Offline tests for Q5 FTMS status inference (no Home Assistant dependency)."""
import importlib.util
from pathlib import Path

path = Path(__file__).parents[1] / "custom_components/homefitnesscode/activity.py"
spec = importlib.util.spec_from_file_location("training_activity", path)
activity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(activity)
infer = activity.observed_session_status


def test_q5_speed_transitions_ready_to_running_then_stopped():
    state = "ready"
    state = infer("treadmill", state, {"speed_kmh": 0.0})
    assert state == "ready"
    state = infer("treadmill", state, {"speed_kmh": 1.0, "elapsed_s": 0})
    assert state == "running"
    state = infer("treadmill", state, {"speed_kmh": 4.5})
    assert state == "running"
    state = infer("treadmill", state, {"speed_kmh": 0.0, "elapsed_s": 0})
    assert state == "stopped"
    assert infer("treadmill", state, {"speed_kmh": 2.0}) == "running"


def test_explicit_ftms_status_and_safety_stop_take_precedence():
    assert infer("treadmill", "running", {"session_status": "paused"}) == "paused"
    assert infer("treadmill", "running", {"session_status": "safety_stop"}) == "safety_stop"
    assert infer("treadmill", "safety_stop", {"speed_kmh": 1.0}) == "safety_stop"
    assert infer("treadmill", "paused", {"speed_kmh": 0}) == "paused"


def test_no_false_state_changes_for_other_equipment_or_bad_readings():
    for machine in ("bike", "rower", "headwind", "auto"):
        assert infer(machine, "ready", {"speed_kmh": 5}) == "ready"
    for value in (None, "unavailable", float("nan"), -1):
        assert infer("treadmill", "ready", {"speed_kmh": value}) == "ready"
    assert infer("treadmill", "ready", {"distance_km": 0.1}) == "ready"
    assert infer("treadmill", "ready", {"speed_kmh": 0.2}) == "ready"
