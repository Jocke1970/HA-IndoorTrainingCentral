"""Standard BLE Heart Rate Service decoder; independent of transport.

Future ANT+ sources can publish the same normalized fields.
"""
def parse_heart_rate(data: bytes) -> dict:
    if len(data) < 2:
        raise ValueError("Truncated heart rate packet")
    flags = data[0]
    width = 2 if flags & 1 else 1
    pos = 1 + width
    if len(data) < pos:
        raise ValueError("Truncated heart rate value")
    bpm = int.from_bytes(data[1:pos], "little")
    if flags & 8:
        if len(data) < pos + 2:
            raise ValueError("Truncated energy field")
        pos += 2
    rr = None
    if flags & 16:
        if len(data) < pos + 2 or (len(data) - pos) % 2:
            raise ValueError("Truncated RR field")
        rr = round(int.from_bytes(data[-2:], "little") * 1000 / 1024, 1)
    contact_lost = bool(flags & 4) and not bool(flags & 2)
    return {"heart_rate_bpm": bpm if bpm and not contact_lost else None,
            "rr_interval_ms": rr if not contact_lost else None}
