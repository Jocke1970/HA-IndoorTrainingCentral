"""User-initiated FTMS control. Never arm or start after reconnect."""
from homeassistant.components.button import ButtonEntity

from .const import DOMAIN
from .entity import HFCEntity
from .entity_catalog import buttons_for

ACTIONS = {"arm": "Aktivera styrning", "start": "Starta / fortsätt",
           "pause": "Pausa", "stop": "Stoppa"}


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
    added = set()

    def add_machine_buttons() -> None:
        new = [key for key in buttons_for(
            coord.data.get("machine_type", "auto"),
            entry.data.get("profile", "auto"),
        ) if key not in added]
        if new:
            added.update(new)
            async_add_entities([HFCButton(coord, key, ACTIONS[key]) for key in new])

    if entry.data.get("profile") == "wahoo_headwind":
        return
    add_machine_buttons()
    entry.async_on_unload(coord.async_add_listener(add_machine_buttons))
