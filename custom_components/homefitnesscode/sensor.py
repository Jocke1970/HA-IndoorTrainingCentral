"""Telemetry for treadmill, indoor cycle trainer and indoor rower."""
from homeassistant.components.sensor import SensorEntity, SensorStateClass

from .const import DOMAIN
from .entity import HFCEntity
from .entity_catalog import sensors_for

# metric: label, unit, machine types
METRICS = {
    "machine_type": ("Machine type", None, None),
    "gatt_inventory": ("GATT discovery", None, None),
    "protocol": ("Protocol", None, None),
    "session_status": ("Workout status", None, None),
    "speed_kmh": ("Speed", "km/h", ("treadmill", "bike")),
    "average_speed_kmh": ("Average speed", "km/h", ("treadmill", "bike")),
    "distance_km": ("Distance", "km", None),
    "incline_percent": ("Incline", "%", ("treadmill",)),
    "battery_percent": ("Battery", "%", ("heart_rate_monitor",)),
    "rr_interval_ms": ("RR interval", "ms", ("heart_rate_monitor",)),
    "heart_rate_bpm": ("Heart rate", "bpm", None),
    "elapsed_s": ("Elapsed time", "s", None),
    "remaining_s": ("Remaining time", "s", None),
    "energy_kcal": ("Calories", "kcal", None),
    "power_w": ("Power", "W", None),
    "average_power_w": ("Average power", "W", ("bike", "rower")),
    "cadence_rpm": ("Cadence", "rpm", ("bike",)),
    "average_cadence_rpm": ("Average cadence", "rpm", ("bike",)),
    "resistance_level": ("Resistance", None, ("bike", "rower")),
    "stroke_rate_spm": ("Stroke rate", "strokes/min", ("rower",)),
    "average_stroke_rate_spm": ("Average stroke rate", "strokes/min", ("rower",)),
    "stroke_count": ("Stroke count", None, ("rower",)),
    "pace_s_per_500m": ("500 m pace", "s/500m", ("rower",)),
    "average_pace_s_per_500m": ("Average 500 m pace", "s/500m", ("rower",)),
}


class HFCSensor(HFCEntity, SensorEntity):
    def __init__(self, coordinator, key, label, unit, allowed):
        super().__init__(coordinator, key, label)
        self._attr_native_unit_of_measurement = unit
        self.allowed = allowed
        if key not in ("machine_type", "protocol", "session_status", "gatt_inventory", "headwind_mode", "firmware_version"):
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def available(self):
        return ((self.metric in ("machine_type", "protocol") or self.coordinator.data.get("connected", False))
                and (self.allowed is None or
                     self.coordinator.data.get("machine_type") in self.allowed)
                and self.metric in self.coordinator.data
                and self.coordinator.data.get(self.metric) is not None)

    @property
    def extra_state_attributes(self):
        attributes = super().extra_state_attributes
        if self.metric == "gatt_inventory":
            attributes["characteristics"] = self.coordinator.data.get("gatt_inventory", [])
        return attributes

    @property
    def native_value(self):
        return ("Ready" if self.coordinator.data.get(self.metric) else "None") if self.metric == "gatt_inventory" else self.coordinator.data.get(self.metric)


async def async_setup_entry(hass, entry, async_add_entities):
    coord = hass.data[DOMAIN][entry.entry_id]
    profile = entry.data.get("profile", "auto")
    added = set()

    def add_for_machine() -> None:
        keys = sensors_for(coord.data.get("machine_type", "auto"), profile)
        new = [key for key in keys if key not in added]
        if new:
            added.update(new)
            async_add_entities([
                HFCSensor(coord, key, *METRICS[key])
                if key in METRICS else HFCSensor(coord, key, {
                    "headwind_mode": "Fan mode", "fan_percent": "Fan speed",
                    "firmware_version": "HEADWIND firmware",
                }[key], "%" if key == "fan_percent" else None, None)
                for key in new
            ])

    add_for_machine()
    entry.async_on_unload(coord.async_add_listener(add_for_machine))
