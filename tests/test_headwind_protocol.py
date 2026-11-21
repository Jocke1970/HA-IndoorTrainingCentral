"""Wahoo HEADWIND byte frames, pure tests with no HA dependencies."""
import importlib.util
from pathlib import Path
import pytest

path = Path(__file__).parents[1] / "custom_components/homefitnesscode/headwind_protocol.py"
spec = importlib.util.spec_from_file_location("headwind_protocol", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


@pytest.mark.parametrize("mode,frame", [
    ("off", b"\x04\x01\x00\x00"),
    ("heart_rate", b"\x04\x02\x00\x00"),
    ("speed", b"\x04\x03\x00\x00"),
    ("manual", b"\x04\x04\x00\x00")
])
def test_modes(mode, frame):
    assert mod.mode_command(mode) == frame


def test_manual_percent():
    assert mod.percent_command(25) == b"\x02\x19\x00\x00"
    with pytest.raises(ValueError):
        mod.percent_command(101)


def test_notification_full_state():
    assert mod.decode_notification(b"\xfd\x01\x2d\x04") == {
        "headwind_mode": "manual", "fan_percent": 45,
    }


def test_notification_updates():
    assert mod.decode_notification(b"\xfe\x02\x01\x3c") == {
        "headwind_mode": "manual", "fan_percent": 60,
    }
    assert mod.decode_notification(b"\xfe\x04\x01\x01") == {
        "headwind_mode": "off", "fan_percent": 0,
    }
    assert mod.decode_notification(b"\x00\x00") == {}
