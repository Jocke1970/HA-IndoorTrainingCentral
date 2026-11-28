"""Garmin SDK FIT activity writer for treadmill journals.

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
EXPORT_VERSION = 6
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
    pauses = []
    pause_start = None
    session_end = None
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
            if stamp < start:
                continue
            kind = row.get("type")
            if kind == "session_pause" and pause_start is None:
                pause_start = stamp
            elif kind == "session_resume" and pause_start is not None:
                if stamp >= pause_start:
                    pauses.append((pause_start, stamp))
                pause_start = None
            elif kind == "session_end":
                session_end = stamp
            if kind in ("session_pause", "session_resume", "session_end"):
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
    if pause_start is not None:
        end = pause_start
    elif pauses:
        end = session_end if session_end is not None else max(buckets, default=start)
    if pauses or pause_start is not None:
        end = max(start, end)
        pauses = [(max(start,a), min(end,b)) for a,b in pauses if start <= a < b <= end]
        duration = end - start - sum(b-a for a,b in pauses)
    elapsed = end - start
    if duration <= 0:
        raise ValueError("FIT requires positive active time")
    def included(stamp):
        return start <= stamp <= end and not any(a <= stamp < b for a,b in pauses) and (pause_start is None or stamp < pause_start)
    buckets = {t:v for t,v in buckets.items() if included(t)}
    if not any(any(v.get(k) is not None for k in ("speed_kmh", "distance_km", "heart_rate_bpm", "incline_percent")) for v in buckets.values()):
        raise ValueError("FIT requires at least one valid record")
    from garmin_fit_sdk import Encoder, Decoder, Stream, Profile, BASE_TYPE
    ids = Profile["mesg_num"]
    app = {"application_id": list(UUID("9bed1f83-e4b1-4eb6-9035-c15972a15a4e").bytes),
           "developer_data_index": 0, "application_version": EXPORT_VERSION}
    descriptions = {}
    for number, name, unit, native in ((0,"met","MET","RECORD"),(1,"average_met","MET","SESSION"),
                                       (2,"max_met","MET","SESSION"),(3,"met_minutes","MET-min","SESSION")):
        descriptions[number] = {"developer_data_id_mesg": app,
            "field_description_mesg": {"developer_data_index": 0, "field_definition_number": number,
                "fit_base_type_id": BASE_TYPE["FLOAT32"], "field_name": name,
                "units": unit, "native_mesg_num": ids[native]}}
    encoder = Encoder(field_descriptions=descriptions)
    def write(kind, **values):
        encoder.on_mesg(ids[kind], {k:v for k,v in values.items() if v is not None})
    write("FILE_ID", type="activity", manufacturer=manufacturer, product=product, time_created=start)
    write("DEVICE_INFO", timestamp=start, device_index=0, manufacturer=manufacturer, product=product, product_name=creator)
    for index,name in enumerate((summary.get("device_name"),summary.get("heart_rate_source")),1):
        if name and name != "training_machine":
            write("DEVICE_INFO", timestamp=start, device_index=index, product_name=name)
    write("DEVELOPER_DATA_ID", **app)
    for desc in descriptions.values():
        write("FIELD_DESCRIPTION", **desc["field_description_mesg"])
    write("EVENT", timestamp=start, event="timer", event_type="start")
    pending = iter(pauses)
    next_pause = next(pending, None)
    for stamp,v in sorted(buckets.items()):
        while next_pause is not None and next_pause[1] <= stamp:
            write("EVENT", timestamp=next_pause[0], event="timer", event_type="stop_all")
            write("EVENT", timestamp=next_pause[1], event="timer", event_type="start")
            next_pause = next(pending, None)
        speed, grade = v.get("speed_kmh"), v.get("incline_percent")
        met = None
        if isinstance(speed,(int,float)) and isinstance(grade,(int,float)) and 0.2 < speed <= 30 and 0 <= grade <= 30:
            h, vert = (0.1,1.8) if speed < 8 else (0.2,0.9)
            met = (3.5 + speed * 1000 / 60 * (h + vert * grade / 100)) / 3.5
        if rr_buckets.get(stamp):
            write("HRV", time=[rr/1000 for rr in rr_buckets[stamp]])
        if not any(v.get(k) is not None for k in ("speed_kmh","distance_km","incline_percent","heart_rate_bpm")):
            continue
        write("RECORD", timestamp=stamp, heart_rate=scaled(v.get("heart_rate_bpm")),
              distance=v["distance_km"]*1000 if v.get("distance_km") is not None else None,
              speed=speed/3.6 if speed is not None else None, grade=grade,
              developer_fields={0:met} if met is not None else None)
    while next_pause is not None:
        write("EVENT", timestamp=next_pause[0], event="timer", event_type="stop_all")
        write("EVENT", timestamp=next_pause[1], event="timer", event_type="start")
        next_pause = next(pending, None)
    write("EVENT", timestamp=end, event="timer", event_type="stop_all")
    common = dict(timestamp=end, start_time=start, total_elapsed_time=elapsed, total_timer_time=duration,
                  total_distance=summary.get("distance_km",0)*1000,
                  total_calories=scaled(summary.get("energy_kcal")),
                  avg_speed=summary.get("distance_km",0)*1000/duration,
                  max_speed=summary.get("max_speed_kmh",0)/3.6,
                  avg_heart_rate=scaled(summary.get("average_heart_rate_bpm")),
                  max_heart_rate=scaled(summary.get("max_heart_rate_bpm")) or None,
                  sport="running", message_index=0)
    write("LAP", **common)
    write("SESSION", **common, sub_sport="treadmill", first_lap_index=0, num_laps=1,
          developer_fields={i:summary[k] for i,k in ((1,"average_met"),(2,"max_met"),(3,"met_minutes")) if summary.get(k) is not None})
    offset = int(datetime.fromisoformat(summary["started_at"]).astimezone().utcoffset().total_seconds())
    write("ACTIVITY", timestamp=end, total_timer_time=duration, num_sessions=1,
          local_timestamp=end+offset, type="manual", event="activity", event_type="stop")
    data = bytes(encoder.close())
    if not validate_fit(data) or not Decoder(Stream.from_byte_array(bytearray(data))).check_integrity():
        raise ValueError("FIT integrity check failed")
    messages, errors = Decoder(Stream.from_byte_array(bytearray(data))).read()
    if errors or not all(messages.get(k) for k in ("file_id_mesgs","record_mesgs","lap_mesgs","session_mesgs","activity_mesgs")):
        raise ValueError(f"FIT SDK validation failed: {errors}")
    target = target if target is not None else raw.with_suffix(".fit")
    temporary = target.with_suffix(".fit.tmp")
    temporary.write_bytes(data)
    if not validate_fit(temporary.read_bytes()):
        raise ValueError("FIT disk verification failed")
    temporary.replace(target)
    return target
