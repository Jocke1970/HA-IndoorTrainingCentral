"""Pure FTMS codecs for treadmill, indoor bike and indoor rower.

See Bluetooth SIG Fitness Machine Service 1.0 and assigned numbers.
No Home Assistant imports; safe to run tests without physical equipment.
"""
from __future__ import annotations

from struct import pack


class Reader:
    def __init__(self, data: bytes):
        if len(data) < 2:
            raise ValueError("Truncated FTMS flags")
        self.flags = int.from_bytes(data[:2], "little")
        self.data = data
        self.pos = 2

    def take(self, length: int, signed: bool = False) -> int:
        end = self.pos + length
        if end > len(self.data):
            raise ValueError(f"Truncated FTMS payload at offset {self.pos}")
        result = int.from_bytes(self.data[self.pos:end], "little", signed=signed)
        self.pos = end
        return result

    def present(self, bit: int) -> bool:
        return bool(self.flags & (1 << bit))


def energy(r: Reader, out: dict) -> None:
    out["energy_kcal"] = r.take(2)
    r.take(2)  # kcal/h
    r.take(1)  # kcal/min


def common_tail(r: Reader, out: dict, *, energy_bit: int, heart_bit: int,
                met_bit: int, elapsed_bit: int, remaining_bit: int) -> None:
    if r.present(energy_bit):
        energy(r, out)
    if r.present(heart_bit):
        out["heart_rate_bpm"] = r.take(1)
    if r.present(met_bit):
        r.take(1)
    if r.present(elapsed_bit):
        out["elapsed_s"] = r.take(2)
    if r.present(remaining_bit):
        out["remaining_s"] = r.take(2)


def parse_treadmill(data: bytes) -> dict:
    r = Reader(data)
    out = {}
    if not r.present(0):  # More Data=0 -> instantaneous speed included
        out["speed_kmh"] = r.take(2) / 100
    if r.present(1):
        out["average_speed_kmh"] = r.take(2) / 100
    if r.present(2):
        out["distance_km"] = r.take(3) / 1000
    if r.present(3):
        out["incline_percent"] = r.take(2, signed=True) / 10
        r.take(2, signed=True)  # ramp angle
    if r.present(4):
        r.take(4)  # positive/negative elevation gain
    if r.present(5):
        r.take(1)  # instantaneous pace
    if r.present(6):
        r.take(1)  # average pace
    common_tail(r, out, energy_bit=7, heart_bit=8, met_bit=9,
                elapsed_bit=10, remaining_bit=11)
    if r.present(12):
        r.take(2)  # force on belt
        out["power_w"] = r.take(2, signed=True)
    return out


def parse_bike(data: bytes) -> dict:
    r = Reader(data)
    out = {}
    if not r.present(0):
        out["speed_kmh"] = r.take(2) / 100
    if r.present(1):
        out["average_speed_kmh"] = r.take(2) / 100
    if r.present(2):
        out["cadence_rpm"] = r.take(2) / 2
    if r.present(3):
        out["average_cadence_rpm"] = r.take(2) / 2
    if r.present(4):
        out["distance_km"] = r.take(3) / 1000
    if r.present(5):
        out["resistance_level"] = r.take(2, signed=True)
    if r.present(6):
        out["power_w"] = r.take(2, signed=True)
    if r.present(7):
        out["average_power_w"] = r.take(2, signed=True)
    common_tail(r, out, energy_bit=8, heart_bit=9, met_bit=10,
                elapsed_bit=11, remaining_bit=12)
    return out


def parse_rower(data: bytes) -> dict:
    r = Reader(data)
    out = {}
    if not r.present(0):
        out["stroke_rate_spm"] = r.take(1) / 2
        out["stroke_count"] = r.take(2)
    if r.present(1):
        out["average_stroke_rate_spm"] = r.take(1) / 2
    if r.present(2):
        out["distance_km"] = r.take(3) / 1000
    if r.present(3):
        out["pace_s_per_500m"] = r.take(2)
    if r.present(4):
        out["average_pace_s_per_500m"] = r.take(2)
    if r.present(5):
        out["power_w"] = r.take(2, signed=True)
    if r.present(6):
        out["average_power_w"] = r.take(2, signed=True)
    if r.present(7):
        out["resistance_level"] = r.take(2, signed=True)
    common_tail(r, out, energy_bit=8, heart_bit=9, met_bit=10,
                elapsed_bit=11, remaining_bit=12)
    return out


PARSERS = {"treadmill": parse_treadmill, "bike": parse_bike, "rower": parse_rower}


def encode_target(kind: str, value: float) -> bytes:
    """Encode confirmed target; caller must validate hardware/configured limits."""
    if kind == "speed":
        if not 0 <= value <= 100:
            raise ValueError("Speed outside valid protocol range")
        return bytes((0x02,)) + pack("<H", round(value * 100))
    if kind == "incline":
        if not -100 <= value <= 100:
            raise ValueError("Incline outside valid protocol range")
        return bytes((0x03,)) + pack("<h", round(value * 10))
    if kind == "resistance":
        if not -32768 <= value <= 32767:
            raise ValueError("Resistance outside valid protocol range")
        return bytes((0x04,)) + pack("<h", round(value))
    if kind == "power":
        if not 0 <= value <= 32767:
            raise ValueError("Power outside valid protocol range")
        return bytes((0x05,)) + pack("<h", round(value))
    raise ValueError(f"Unsupported target: {kind}")


def validate_reply(payload: bytes, expected: int) -> None:
    if len(payload) < 3 or payload[0] != 0x80 or payload[1] != expected:
        raise ValueError("Unexpected FTMS control response")
    if payload[2] != 0x01:
        raise ValueError(f"FTMS command 0x{expected:02x} rejected: code {payload[2]}")
