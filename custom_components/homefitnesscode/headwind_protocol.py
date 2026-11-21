"""Wahoo KICKR HEADWIND BLE frame format (not standard FTMS).

Based on public reverse-engineering research. See docs/headwind.md.
This decoder does not assume a Bluetooth write is proof the fan changed.
"""

MODES = {"off": 1, "heart_rate": 2, "speed": 3, "manual": 4}
NAMES = {value: key for key, value in MODES.items()}
CONTROL = "a026e038-0a7d-4ab3-97fa-f1500f9feb8b"


def mode_command(mode: str) -> bytes:
    if mode not in MODES:
        raise ValueError("Unknown HEADWIND mode")
    return bytes((0x04, MODES[mode], 0, 0))


def percent_command(percent: int) -> bytes:
    if not isinstance(percent, int) or not 0 <= percent <= 100:
        raise ValueError("HEADWIND percentage must be integer 0..100")
    return bytes((0x02, percent, 0, 0))


def decode_notification(data: bytes) -> dict:
    if len(data) < 4:
        return {}
    if data[0] == 0xFD and data[3] in NAMES:
        return {"headwind_mode": NAMES[data[3]],
                "fan_percent": min(data[2], 100)}
    if data[0] == 0xFE and data[1] == 0x02 and data[2] == 0x01:
        return {"headwind_mode": "manual",
                "fan_percent": min(data[3], 100)}
    if data[0] == 0xFE and data[1] == 0x04 and data[3] == 0x01:
        return {"headwind_mode": "off", "fan_percent": 0}
    return {}
