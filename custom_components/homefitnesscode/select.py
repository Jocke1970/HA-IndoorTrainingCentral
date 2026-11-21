"""Wahoo HEADWIND hardware control mode selector.

Heart-rate and speed modes require sensors paired *on the fan* using Wahoo app.
This select does not inject Tacx telemetry into the Wahoo fan over BLE.
"""
from homeassistant.components.select import SelectEntity
from .const import DOMAIN
from .entity import HFCEntity

MODES = ["off", "manual", "heart_rate", "speed"]


class HFCHeadwindMode(HFCEntity, SelectEntity):
    _attr_options = MODES

    def __init__(self, coordinator):
        super().__init__(coordinator, "headwind_mode_select", "HEADWIND mode")

    @property
    def available(self):
        return self.coordinator.connected

    @property
    def current_option(self):
        mode = self.coordinator.data.get("headwind_mode")
        return mode if mode in MODES else None

    async def async_select_option(self, option):
        await self.coordinator.set_mode(option)


async def async_setup_entry(hass, entry, async_add_entities):
    if entry.data.get("profile") != "wahoo_headwind":
        return
    async_add_entities([HFCHeadwindMode(hass.data[DOMAIN][entry.entry_id])])
