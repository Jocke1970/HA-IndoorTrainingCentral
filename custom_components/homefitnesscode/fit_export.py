"""Dependency-free FIT activity writer for treadmill journals.

Exports standard FIT records, lap, session and activity. Raw journals remain
authoritative; no invented Garmin identity or physiological metrics.
"""
from datetime import datetime, timezone
import json
import math
import struct
from uuid import UUID

EPOCH = datetime(1989, 12, 31, tzinfo=timezone.utc)
U8, U16, U32, S16, ENUM = 2, 0x84, 0x86, 0x83, 0
STRING, BYTE, FLOAT = 7, 13, 0x88
EXPORT_VERSION = 3
PROFILES = {"native": (255, 1, "HA-IndoorTrainingCentral"),
            "fenix7pro": (1, 4375, "fenix 7 Pro")}
FORMATS = {U8: ("B", 255), U16: ("H", 65535), U32: ("I", 4294967295),
           S16: ("h", 32767), ENUM: ("B", 255)}


def fit_time(value):
    return int((datetime.fromisoformat(value) - EPOCH).total_seconds())


def crc(data):
    value = 0
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0xA001 if value & 1 else 0)
    return value


def scaled(value, factor=1):
    if isinstance(value, (int, float)) and math.isfinite(value):
        return round(value * factor)
    return None


class Writer:
    def __init__(self):
        self.data = bytearray()

    def message(self, local, global_id, fields, values, developer=()):
        self.data.extend(struct.pack("<BBBH B", 0x40 | (0x20 if developer else 0) | local, 0, 0,
                                     global_id, len(fields)))
        for field in fields:
            number, kind = field[:2]
            size = field[2] if len(field) == 3 else struct.calcsize("<" + FORMATS[kind][0])
            self.data.extend(bytes((number, size, kind)))
        if developer:
            self.data.append(len(developer))
            for number, _ in developer:
                self.data.extend(bytes((number, 4, 0)))
        self.data.append(local)
        for field, value in zip(fields, values, strict=True):
            kind = field[1]
            if kind == STRING:
                size = field[2]
                self.data.extend(str(value).encode("utf-8")[:size-1].decode("utf-8", "ignore").encode("utf-8").ljust(size, b"\0"))
                continue
            if kind == BYTE:
                self.data.extend(bytes(value).ljust(field[2], b"\xff")[:field[2]])
                continue
            fmt, invalid = FORMATS[kind]
            try:
                encoded = struct.pack("<" + fmt, value if value is not None else invalid)
            except (struct.error, OverflowError):
                encoded = struct.pack("<" + fmt, invalid)
            self.data.extend(encoded)
        for _, value in developer:
            self.data.extend(struct.pack("<f", value) if value is not None and math.isfinite(value) else b"\xff"*4)

    def finish(self):
        header = struct.pack("<BBHI4s", 14, 0x20, 2100, len(self.data), b".FIT")
        header += struct.pack("<H", crc(header))
        result = header + self.data
        return bytes(result + struct.pack("<H", crc(result)))


def validate_fit(data):
    return (len(data) >= 16 and data[0] == 14 and data[8:12] == b".FIT"
            and struct.unpack_from("<I", data, 4)[0] == len(data) - 16
            and crc(data[:14]) == 0 and crc(data) == 0)


def export_fit(raw, summary, *, profile="native", target=None):
    """Export one record per second, excluding pre-roll and idle close delay."""
    manufacturer, product, creator = PROFILES[profile]
    start = fit_time(summary["started_at"])
    duration = int(summary["elapsed_s"])
    if duration <= 0:
        raise ValueError("FIT requires positive training time")
    end = start + duration
    buckets = {}
    rr_buckets = {}
    external = summary.get("heart_rate_source") != "training_machine"
    with raw.open(encoding="utf-8") as file:
        for line in file:
            try:
                row = json.loads(line)
                stamp = fit_time(row["timestamp"])
            except (ValueError, KeyError, TypeError):
                continue
            if not start <= stamp <= end:
                continue
            if row.get("type") == "heart_rate" and external:
                buckets.setdefault(stamp, {})["heart_rate_bpm"] = row.get("bpm")
                rr = row.get("rr_interval_ms")
                if isinstance(rr, (int, float)) and math.isfinite(rr) and 250 <= rr <= 3000:
                    rr_buckets.setdefault(stamp, []).append(round(rr))
            elif (row.get("type") == "frame" and row.get("direction") == "rx"
                  and row.get("characteristic", "").lower().startswith("00002acd")):
                values = row.get("decoded") or {}
                bucket = buckets.setdefault(stamp, {})
                for key in ("speed_kmh", "distance_km", "incline_percent", "heart_rate_bpm"):
                    if key in values and not (external and key == "heart_rate_bpm"):
                        bucket[key] = values[key]
    if not any(any(v.get(k) is not None for k in ("speed_kmh", "distance_km", "heart_rate_bpm", "incline_percent")) for v in buckets.values()):
        raise ValueError("FIT requires at least one valid record")
    w = Writer()
    w.message(0, 0, [(0, ENUM), (1, U16), (2, U16), (4, U32)], [4, manufacturer, product, start])
    w.message(6, 23, [(253,U32),(0,U8),(2,U16),(4,U16),(27,STRING,40)],
              [start,0,manufacturer,product,creator])
    for index, name in enumerate((summary.get("device_name"), summary.get("heart_rate_source")), 1):
        if name and name != "training_machine":
            w.message(6, 23, [(253,U32),(0,U8),(27,STRING,80)], [start,index,name])
    w.message(7, 207, [(1,BYTE,16),(3,U8),(4,U32)],
              [UUID("9bed1f83-e4b1-4eb6-9035-c15972a15a4e").bytes,0,EXPORT_VERSION])
    for number, name, unit in ((0,"met","MET"),(1,"average_met","MET"),
                               (2,"max_met","MET"),(3,"met_minutes","MET-min")):
        w.message(8,206,[(0,U8),(1,U8),(2,U8),(3,STRING,32),(8,STRING,16)],
                  [0,number,FLOAT & 0x1f,name,unit])
    event = [(253, U32), (0, ENUM), (1, ENUM)]
    w.message(1, 21, event, [start, 0, 0])
    fields = [(253, U32), (3, U8), (5, U32), (6, U16), (9, S16)]
    for stamp, v in sorted(buckets.items()):
        for rr in rr_buckets.get(stamp, ()):
            w.message(9, 78, [(0, U16)], [rr])
        speed, grade = v.get("speed_kmh"), v.get("incline_percent")
        met = None
        if isinstance(speed,(int,float)) and isinstance(grade,(int,float)) and 0.2 < speed <= 30 and 0 <= grade <= 30:
            h, vert = (0.1,1.8) if speed < 8 else (0.2,0.9)
            met = (3.5 + speed * 1000 / 60 * (h + vert * grade / 100)) / 3.5
        if not any(v.get(k) is not None for k in ("speed_kmh","distance_km","incline_percent","heart_rate_bpm")):
            continue
        w.message(2, 20, fields, [stamp, scaled(v.get("heart_rate_bpm")),
                  scaled(v.get("distance_km"), 100000),
                  scaled(v.get("speed_kmh"), 1000 / 3.6),
                  scaled(v.get("incline_percent"), 100)], developer=((0,met),))
    w.message(1, 21, event, [end, 0, 4])
    common = [end, start, duration * 1000, duration * 1000,
              scaled(summary.get("distance_km"), 100000),
              scaled(summary.get("energy_kcal")),
              scaled(summary.get("average_speed_kmh"), 1000 / 3.6),
              scaled(summary.get("max_speed_kmh"), 1000 / 3.6),
              scaled(summary.get("average_heart_rate_bpm")),
              scaled(summary.get("max_heart_rate_bpm")) or None]
    w.message(3, 19, [(253,U32),(2,U32),(7,U32),(8,U32),(9,U32),(11,U16),
                      (13,U16),(14,U16),(15,U8),(16,U8),(25,ENUM),(254,U16)],
              common + [1,0])
    w.message(4, 18, [(253,U32),(2,U32),(7,U32),(8,U32),(9,U32),(11,U16),
                      (14,U16),(15,U16),(16,U8),(17,U8),(5,ENUM),(6,ENUM),
                      (25,U16),(26,U16),(254,U16)], common + [1,1,0,1,0],
              developer=tuple((i,summary.get(k)) for i,k in ((1,"average_met"),(2,"max_met"),(3,"met_minutes"))))
    offset = int(datetime.fromisoformat(summary["started_at"]).astimezone().utcoffset().total_seconds())
    w.message(5, 34, [(253,U32),(0,U32),(1,U16),(2,ENUM),(3,ENUM),(4,ENUM),(5,U32)],
              [end,duration*1000,1,0,26,1,end+offset])
    data = w.finish()
    if not validate_fit(data):
        raise ValueError("FIT CRC or length check failed")
    target = target if target is not None else raw.with_suffix(".fit")
    temporary = target.with_suffix(".fit.tmp")
    temporary.write_bytes(data)
    if not validate_fit(temporary.read_bytes()):
        raise ValueError("FIT disk verification failed")
    temporary.replace(target)
    return target
