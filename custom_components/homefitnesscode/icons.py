"""Shared entity icons; no Home Assistant dependencies."""
ICONS = {
    "gatt_inventory": "mdi:format-list-bulleted",
    "protocol": "mdi:bluetooth",
    "speed_kmh": "mdi:speedometer",
    "average_speed_kmh": "mdi:speedometer-medium",
    "distance_km": "mdi:map-marker-distance",
    "incline_percent": "mdi:slope-uphill",
    "rr_interval_ms": "mdi:heart-flash",
    "heart_rate_bpm": "mdi:heart-pulse",
    "elapsed_s": "mdi:timer-outline",
    "remaining_s": "mdi:timer-sand",
    "energy_kcal": "mdi:fire",
    "power_w": "mdi:flash",
    "average_power_w": "mdi:flash-outline",
    "cadence_rpm": "mdi:rotate-right",
    "average_cadence_rpm": "mdi:rotate-right",
    "resistance_level": "mdi:weight",
    "stroke_rate_spm": "mdi:rowing",
    "average_stroke_rate_spm": "mdi:rowing",
    "stroke_count": "mdi:counter",
    "pace_s_per_500m": "mdi:timer-outline",
    "average_pace_s_per_500m": "mdi:timer-outline",
    "fan_percent": "mdi:fan",
    "firmware_version": "mdi:chip",
    "headwind_fan": "mdi:fan",
    "target_speed": "mdi:speedometer",
    "target_incline": "mdi:slope-uphill",
    "target_power": "mdi:flash",
    "target_resistance": "mdi:weight",
    "arm": "mdi:shield-check",
    "pause": "mdi:pause",
    "stop": "mdi:stop",
}
MACHINES = {
    "treadmill": "mdi:treadmill", "bike": "mdi:bicycle",
    "rower": "mdi:rowing", "heart_rate_monitor": "mdi:heart-box",
    "headwind": "mdi:fan",
}
STATUS = {
    "ready": "mdi:check-circle-outline", "running": "mdi:play-circle",
    "paused": "mdi:pause-circle", "stopped": "mdi:stop-circle",
    "safety_stop": "mdi:alert-octagon", "disconnected": "mdi:bluetooth-off",
    "reset": "mdi:restart", "diagnostic": "mdi:wrench",
}
FAN_MODES = {
    "off": "mdi:fan-off", "manual": "mdi:fan",
    "heart_rate": "mdi:heart-pulse", "speed": "mdi:speedometer",
}


def icon_for(metric, data):
    if metric == "machine_type":
        return MACHINES.get(data.get("machine_type"), "mdi:dumbbell")
    if metric == "session_status":
        return STATUS.get(data.get("session_status"), "mdi:help-circle-outline")
    if metric == "connected":
        return "mdi:bluetooth-connect" if data.get("connected") else "mdi:bluetooth-off"
    if metric == "armed":
        return "mdi:shield-check" if data.get("armed") else "mdi:shield-lock"
    if metric in ("headwind_mode", "headwind_mode_select"):
        return FAN_MODES.get(data.get("headwind_mode"), "mdi:fan")
    return ICONS.get(metric)
