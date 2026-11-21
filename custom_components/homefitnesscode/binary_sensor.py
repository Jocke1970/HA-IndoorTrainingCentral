"""Connection health and explicit remote-control arm state."""
from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN
from .entity import HFCEntity


class HFCBinarySensor(HFCEntity, BinarySensorEntity):
    def __init__(self, coordinator, key, label):
        super().__init__(coordinator, key, label)

    @property
    def is_on(self):
        return bool(self.coordinator.data.get(self.metric, False))

    @property
    def available(self):
        return self.metric == "connected" or self.coordinator.data.get("connected", False)


async def async_setup_entry(hass, entry, async_add_entities):
    coord = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        HFCBinarySensor(coord, "connected", "Connected"),
        HFCBinarySensor(coord, "armed", "Control armed"),
    ])
