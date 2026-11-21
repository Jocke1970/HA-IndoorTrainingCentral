"""Explicit target controls. Exposed only when FTMS advertises support."""
from homeassistant.components.number import NumberEntity, NumberMode

from .const import DOMAIN
from .entity import HFCEntity
from .entity_catalog import targets_for

LABELS = {"speed": ("Target speed", "km/h"), "incline": ("Target incline", "%"),
          "resistance": ("Target resistance", None), "power": ("Target power", "W")}


class HFCTarget(HFCEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, key):
        label, unit = LABELS[key]
        super().__init__(coordinator, f"target_{key}", label)
        self.kind = key
        self._attr_native_unit_of_measurement = unit

    @property
    def available(self):
        return self.coordinator.can_target(self.kind) and self.coordinator.transport.armed

    @property
    def native_min_value(self):
        return self.coordinator.limits(self.kind)[0]

    @property
    def native_max_value(self):
        return self.coordinator.limits(self.kind)[1]

    @property
    def native_step(self):
        return self.coordinator.limits(self.kind)[2]

    @property
    def native_value(self):
        if self.kind in self.coordinator.targets:
            return self.coordinator.targets[self.kind]
        raw = self.coordinator.data.get({
            "speed": "speed_kmh", "incline": "incline_percent",
            "resistance": "resistance_level", "power": "power_w",
        }[self.kind])
        return raw

    async def async_set_native_value(self, value):
        await self.coordinator.set_target(self.kind, float(value))


async def async_setup_entry(hass, entry, async_add_entities):
    coord = hass.data[DOMAIN][entry.entry_id]
    added = set()

    def add_available_targets() -> None:
        profile = entry.data.get("profile", "auto")
        if profile == "auto" and getattr(coord.transport, "tacx", None) is not None:
            profile = "tacx_fec"
        targets = targets_for(coord.data.get("machine_type", "auto"), profile)
        new = [key for key in targets if key not in added]
        if new:
            added.update(new)
            async_add_entities([HFCTarget(coord, key) for key in new])

    if entry.data.get("profile") == "wahoo_headwind":
        return
    add_available_targets()
    entry.async_on_unload(coord.async_add_listener(add_available_targets))
