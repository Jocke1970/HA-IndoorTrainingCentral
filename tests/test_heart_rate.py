import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("hr", Path(__file__).parents[1] / "custom_components/homefitnesscode/heart_rate.py")
hr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hr)

def test_8_bit():
    assert hr.parse_heart_rate(bytes([0, 128]))["heart_rate_bpm"] == 128

def test_16_bit_and_rr():
    assert hr.parse_heart_rate(bytes([17, 44, 1, 0, 4])) == {"heart_rate_bpm": 300, "rr_interval_ms": 1000.0}

def test_contact_loss():
    assert hr.parse_heart_rate(bytes([4, 100]))["heart_rate_bpm"] is None

def test_bad_packet():
    with pytest.raises(ValueError):
        hr.parse_heart_rate(bytes([16, 100, 1]))
