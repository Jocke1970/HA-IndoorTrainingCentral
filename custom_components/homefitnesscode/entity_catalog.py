"""Which HA entities belong to each machine? Pure functions for offline tests.

Never expose a treadmill start button on a bike or unknown BLE peripheral.
"""
from __future__ import annotations

COMMON_SENSORS = ("machine_type", "protocol", "session_status")
TYPE_SENSORS = {
    "treadmill": ("speed_kmh", "average_speed_kmh", "distance_km",
                  "incline_percent", "heart_rate_bpm", "elapsed_s",
                  "remaining_s", "energy_kcal", "power_w"),
    "bike": ("speed_kmh", "average_speed_kmh", "distance_km",
             "cadence_rpm", "average_cadence_rpm", "power_w",
             "average_power_w", "resistance_level", "heart_rate_bpm",
             "elapsed_s", "remaining_s", "energy_kcal"),
    "rower": ("pace_s_per_500m", "average_pace_s_per_500m",
              "stroke_rate_spm", "average_stroke_rate_spm", "stroke_count",
              "distance_km", "power_w", "average_power_w",
              "resistance_level", "heart_rate_bpm", "elapsed_s",
              "remaining_s", "energy_kcal"),
    "headwind": ("headwind_mode", "fan_percent", "firmware_version"),
}
MACHINE_NUMBERS = {
    "treadmill": ("speed", "incline"),
    "bike": ("power", "resistance"),
    "rower": ("resistance", "power"),
}
MACHINE_BUTTONS = {
    "treadmill": ("arm", "start", "pause", "stop"),
    "bike": ("arm",),
    "rower": ("arm",),
}


def inferred_machine(data: dict, name: str) -> str:
    """Conservative hint while equipment is powered off, not capability proof."""
    profile = data.get("profile", "auto")
    selected = data.get("machine", "auto")
    upper = name.upper()
    if profile == "wahoo_headwind" or upper.startswith(("HEADWIND", "KICKR HEADWIND")):
        return "headwind"
    if selected in TYPE_SENSORS:
        return selected
    if profile == "christopeit_wp5000" or "WP5000" in upper or "RODD" in upper:
        return "rower"
    if profile == "tacx_fec" or "TACX" in upper or "FLUX" in upper:
        return "bike"
    if any(word in upper for word in ("LÖPBAND", "TREADMILL", "WALKING PAD")):
        return "treadmill"
    return "auto"


def sensors_for(kind: str, profile: str) -> tuple[str, ...]:
    if kind == "headwind":
        return TYPE_SENSORS["headwind"]
    keys = COMMON_SENSORS + TYPE_SENSORS.get(kind, ())
    if profile == "christopeit_wp5000":
        keys += ("gatt_inventory",)
    return keys


def targets_for(kind: str, profile: str) -> tuple[str, ...]:
    if profile == "christopeit_wp5000" or kind == "headwind":
        return ()
    if kind == "bike" and profile == "tacx_fec":
        return ("power", "incline")
    if kind == "bike" and profile == "auto":
        # Auto can discover FTMS or Tacx FE-C. The FE-C grade target is
        # added once FE-C is identified, without creating all target types.
        return ("power", "resistance")
    return MACHINE_NUMBERS.get(kind, ())


def buttons_for(kind: str, profile: str) -> tuple[str, ...]:
    if profile == "christopeit_wp5000" or kind == "headwind":
        return ()
    return MACHINE_BUTTONS.get(kind, ())


def registered_metrics(kind: str, profile: str) -> set[str]:
    """All entities that should remain in the registry for a known machine."""
    if kind == "headwind":
        return {"connected", *TYPE_SENSORS["headwind"],
                "headwind_fan", "headwind_mode_select"}
    result = {"connected", *sensors_for(kind, profile)}
    if kind in MACHINE_NUMBERS and profile != "christopeit_wp5000":
        result.add("armed")
        result.update(buttons_for(kind, profile))
        result.update("target_" + target for target in targets_for(kind, profile))
    return result
