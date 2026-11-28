"""Pure entity icon policy tests."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("itc_icons", Path(__file__).parents[1] / "custom_components/homefitnesscode/icons.py")
icons = importlib.util.module_from_spec(spec)
spec.loader.exec_module(icons)


def test_dynamic_icons():
    assert icons.icon_for("connected", {"connected": True}) == "mdi:bluetooth-connect"
    assert icons.icon_for("connected", {}) == "mdi:bluetooth-off"
    assert icons.icon_for("armed", {"armed": True}) == "mdi:shield-check"
    assert icons.icon_for("armed", {}) == "mdi:shield-lock"
    assert icons.icon_for("machine_type", {"machine_type": "bike"}) == "mdi:bicycle"
    assert icons.icon_for("session_status", {"session_status": "safety_stop"}) == "mdi:alert-octagon"
    assert icons.icon_for("headwind_mode_select", {"headwind_mode": "heart_rate"}) == "mdi:heart-pulse"


def test_static_icons_and_native_battery_icon():
    assert icons.icon_for("rr_interval_ms", {}) == "mdi:heart-flash"
    assert icons.icon_for("heart_rate_bpm", {}) == "mdi:heart-pulse"
    assert icons.icon_for("battery_percent", {}) is None
