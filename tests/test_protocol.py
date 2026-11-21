"""Offline fixtures for all three FTMS machines and control commands."""
import importlib.util
from pathlib import Path
from struct import pack
import pytest

path = Path(__file__).parents[1] / "custom_components/homefitnesscode/protocol.py"
spec = importlib.util.spec_from_file_location("hfc_protocol", path)
ftms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ftms)

def test_treadmill():
    flags = (1 << 2) | (1 << 3) | (1 << 8) | (1 << 10)
    data = pack("<HH", flags, 525) + (1234).to_bytes(3,"little") + pack("<hhBH",45,0,132,110)
    assert ftms.parse_treadmill(data) == {
        "speed_kmh": 5.25, "distance_km": 1.234,
        "incline_percent": 4.5, "heart_rate_bpm": 132, "elapsed_s": 110,
    }

def test_bike():
    flags = (1 << 2) | (1 << 5) | (1 << 6)
    assert ftms.parse_bike(pack("<HHHhh", flags, 3200, 172, 8, 225)) == {
        "speed_kmh": 32.0, "cadence_rpm": 86.0,
        "resistance_level": 8, "power_w": 225,
    }

def test_rower():
    flags = (1 << 2) | (1 << 3) | (1 << 5) | (1 << 11)
    data = pack("<HBH",flags,50,125) + (2000).to_bytes(3,"little") + pack("<HhH",135,180,480)
    result = ftms.parse_rower(data)
    assert result == {
        "stroke_rate_spm":25.0, "stroke_count":125,
        "distance_km":2.0, "pace_s_per_500m":135,
        "power_w":180, "elapsed_s":480,
    }

@pytest.mark.parametrize("parse", [ftms.parse_treadmill,ftms.parse_bike,ftms.parse_rower])
def test_truncated(parse):
    with pytest.raises(ValueError):
        parse(b"\x00\x00")

def test_more_data_bit():
    assert ftms.parse_bike(b"\x01\x00") == {}
    assert ftms.parse_rower(b"\x01\x00") == {}

def test_control_encoding():
    assert ftms.encode_target("speed",5.25) == b"\x02\x0d\x02"
    assert ftms.encode_target("incline",4.5) == b"\x03\x2d\x00"
    assert ftms.encode_target("power",175) == b"\x05\xaf\x00"
    ftms.validate_reply(b"\x80\x05\x01",5)
    with pytest.raises(ValueError):
        ftms.validate_reply(b"\x80\x05\x04",5)
