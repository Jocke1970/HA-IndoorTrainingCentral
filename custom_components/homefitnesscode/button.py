"""User-initiated FTMS control. Never arm or start after reconnect."""
from homeassistant.components.button import ButtonEntity

from .const import DOMAIN
from .entity import HFCEntity

ACTIONS = {"arm": "Arm remote control", "start": "Start / resume",
           "pause": "Pause", "stop": "Stop"}


class HFCButton(HFCEntity, ButtonEntity):
    def __init__(self, coordinator, action, label):
        super().__init__(coordinator, action, label)
        self.action = action

    @property
    def available(self):
        t = self.coordinator.transport
        return bool(t.connected and t.has_control and
                    (self.action == "arm" or (t.armed and t.tacx is None)))

    async def async_press(self):
        await self.coordinator.command(self.action)


async def async_setup_entry(hass, entry, async_add_entities):
    coord = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HFCButton(coord, key, name) for key, name in ACTIONS.items()])
