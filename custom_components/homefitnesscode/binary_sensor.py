"""Connection health and explicit remote-control arm state."""
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass

from .const import DOMAIN
from .entity import HFCEntity


class HFCBinarySensor(HFCEntity, BinarySensorEntity):
    def __init__(self, coordinator, key, label):
        super().__init__(coordinator, key, label)
        if key == 'connected':
            self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self):
        return bool(self.coordinator.data.get(self.metric, False))

    @property
    def available(self):
        return self.metric == "connected" or self.coordinator.data.get("connected", False)


async def async_setup_entry(hass, entry, async_add_entities):
    coord = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HFCBinarySensor(coord, "connected", "Connected")])
    added = False

    def add_arm_for_machine() -> None:
        nonlocal added
        if added or coord.data.get("machine_type") not in ("treadmill", "bike", "rower"):
            return
        if entry.data.get("profile") == "christopeit_wp5000":
            return
        added = True
        async_add_entities([HFCBinarySensor(coord, "armed", "Control armed")])

    add_arm_for_machine()
    entry.async_on_unload(coord.async_add_listener(add_arm_for_machine))
