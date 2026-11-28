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


def test_bike_coasting_is_not_pedalling():
    m = activity.ActivityMonitor("indoor_bike")
    assert m.observe(0, "start", {"cadence_rpm": 65}) is True
    for now in (1, 6, 11, 16):
        assert m.observe(now, str(now), {"cadence_rpm": 0, "speed_kmh": 30}) is False
    assert m.inactive(16)
    assert m.idle_timestamp == "1"
    assert m.observe(17, "resume", {"cadence_rpm": 30}) is True
    assert not m.inactive(17)


def test_rower_slow_strokes_and_pause():
    m = activity.ActivityMonitor("rower")
    assert m.observe(0, "0", {"stroke_count": 10}) is None
    for now in range(1, 31):
        count = 10 + now // 6
        m.observe(now, str(now), {"stroke_count": count})
        assert not m.inactive(now)
    for now in range(31, 51):
        m.observe(now, str(now), {"stroke_count": 15})
    assert not m.inactive(50)
    m.observe(51, "51", {"stroke_count": 15})
    assert m.inactive(51)
    assert m.observe(52, "52", {"stroke_count": 16}) is True
    assert not m.inactive(52)


def test_missing_or_invalid_telemetry_does_not_trigger_pause():
    m = activity.ActivityMonitor("treadmill")
    m.observe(0, "0", {"speed_kmh": 3})
    m.observe(1, "1", {"speed_kmh": 0})
    assert m.observe(10, "10", {"distance_km": 0.1}) is None
    assert not m.inactive(20)
    m.observe(20, "20", {"speed_kmh": 0})
    assert not m.inactive(20)
    assert m.idle_timestamp == "20"


def test_custom_idle_threshold_and_rower_counter_reset():
    m = activity.ActivityMonitor("rower", idle_seconds=5)
    m.observe(0, "0", {"stroke_count": 100})
    assert m.observe(1, "1", {"stroke_count": 0}) is None
    assert m.observe(2, "2", {"stroke_count": 1}) is True
    m.observe(3, "3", {"stroke_count": 1})
    m.observe(8, "8", {"stroke_count": 1})
    assert m.inactive(8)
