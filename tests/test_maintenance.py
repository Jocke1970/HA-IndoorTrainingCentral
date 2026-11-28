import importlib.util
from pathlib import Path
from datetime import date, timedelta

spec = importlib.util.spec_from_file_location("maintenance", Path(__file__).parents[1] / "custom_components/homefitnesscode/maintenance.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Maintenance = module.Maintenance


def test_runtime_and_disconnect():
    m = Maintenance()
    d = date(2026, 11, 28)
    m.sample(3, 10, d)
    m.sample(3, 12, d)
    m.sample(0, 13, d)
    m.sample(3, 20, d)
    m.sample(3, 100, d)
    assert m.data["total_seconds"] == 2
    assert m.snapshot(d)["factory_lubricated"]
    assert m.snapshot(d)["last_lubrication"] is None


def test_manual_thresholds_and_ack():
    d = date(2026, 11, 28)
    m = Maintenance()
    m.sample(3, 0, d)
    for hours, expected in [(11.9, 60), (12, 45), (20, 45), (20.1, 30)]:
        m.data["daily_seconds"][d.isoformat()] = hours * 3600
        assert m.snapshot(d)["lubrication_interval"] == expected
    assert m.snapshot(d + timedelta(days=55))["lubrication_due"]
    m.acknowledge(d + timedelta(days=55))
    assert not m.snapshot(d + timedelta(days=55))["lubrication_due"]
    assert not m.snapshot(d + timedelta(days=55))["factory_lubricated"]


def test_restart_does_not_count_gap():
    d = date(2026, 11, 28)
    m = Maintenance()
    m.sample(3, 1, d)
    m.sample(3, 3, d)
    restored = Maintenance(m.data)
    restored.sample(3, 1000, d)
    assert restored.data["total_seconds"] == 2
