"""Native Home Assistant Fan entity for Wahoo KICKR HEADWIND."""
from homeassistant.components.fan import FanEntity, FanEntityFeature

from .const import DOMAIN
from .entity import HFCEntity


class HFCHeadwindFan(HFCEntity, FanEntity):
    _attr_supported_features = (FanEntityFeature.TURN_ON |
                                FanEntityFeature.TURN_OFF |
                                FanEntityFeature.SET_SPEED)
    _attr_speed_count = 100

    def __init__(self, coordinator):
        super().__init__(coordinator, "headwind_fan", "HEADWIND")
        self._attr_icon = "mdi:fan"

    @property
    def available(self):
        return self.coordinator.connected

    @property
    def is_on(self):
        mode = self.coordinator.data.get("headwind_mode")
        return mode != "off" if mode in ("off", "manual", "speed", "heart_rate") else None

    @property
    def percentage(self):
        return self.coordinator.data.get("fan_percent")

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        if percentage is not None:
            await self.coordinator.set_percentage(int(percentage))
        else:
            # Keep the owner’s existing HR sensor workflow. A normal Fan Turn On
            # must never silently switch into fixed manual speed.
            await self.coordinator.set_mode("heart_rate")

    async def async_turn_off(self, **kwargs):
        await self.coordinator.set_mode("off")

    async def async_set_percentage(self, percentage):
        await self.coordinator.set_percentage(int(percentage))


async def async_setup_entry(hass, entry, async_add_entities):
    if entry.data.get("profile") != "wahoo_headwind":
        return
    async_add_entities([HFCHeadwindFan(hass.data[DOMAIN][entry.entry_id])])
