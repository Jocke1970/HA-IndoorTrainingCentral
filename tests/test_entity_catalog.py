"""Machine-specific entity registry policy, no Home Assistant installation needed."""
import importlib.util
from pathlib import Path
import pytest

path = Path(__file__).parents[1] / "custom_components/homefitnesscode/entity_catalog.py"
spec = importlib.util.spec_from_file_location("hfc_catalog", path)
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


def test_headwind_legacy_entry_is_recognized():
    assert catalog.inferred_machine({"profile": "auto", "machine": "auto"}, "HEADWIND 7185 (F7:83:65:04:F2:01)") == "headwind"
    expected = catalog.registered_metrics("headwind", "wahoo_headwind")
    assert {"connected", "headwind_mode", "fan_percent", "firmware_version", "headwind_fan", "headwind_mode_select"} == expected
    assert "target_speed" not in expected
    assert "start" not in expected


def test_tacx_only_has_cycling_sensors():
    assert catalog.inferred_machine({"profile": "auto"}, "Tacx Flux 05176") == "bike"
    expected = catalog.registered_metrics("bike", "auto")
    assert "cadence_rpm" in expected and "power_w" in expected
    assert "stroke_count" not in expected
    assert "incline_percent" not in expected
    assert "start" not in expected
    assert "target_power" in expected


def test_rower_and_treadmill_are_disjoint():
    rower = catalog.registered_metrics("rower", "ftms")
    treadmill = catalog.registered_metrics("treadmill", "ftms")
    assert "stroke_count" in rower and "target_speed" not in rower
    assert "target_speed" in treadmill and "stroke_count" not in treadmill
    assert "start" not in treadmill and "start" not in rower


def test_unclassified_device_only_has_status():
    assert catalog.inferred_machine({"profile": "auto", "machine": "auto"}, "Testmaskin FTMS / HFC") == "auto"
    assert catalog.registered_metrics("auto", "auto") == {
        "connected", "machine_type", "protocol", "session_status"
    }


def test_tacx_grade_profile():
    metrics = catalog.registered_metrics("bike", "tacx_fec")
    assert "target_incline" in metrics
    assert "target_resistance" not in metrics


def test_wp5000_diagnostics_do_not_allow_control():
    allowed = catalog.registered_metrics("rower", "christopeit_wp5000")
    assert "gatt_inventory" in allowed
    assert "armed" not in allowed
    assert not any(key.startswith("target_") for key in allowed)

def test_auto_bike_only_common_controls_until_identified():
    available = catalog.registered_metrics("bike", "auto")
    assert "target_power" in available
    assert "target_resistance" not in available
    assert "target_incline" not in available
