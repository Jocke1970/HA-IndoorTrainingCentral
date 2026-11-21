"""HomeFitnessCode / FTMS for Home Assistant."""
from pathlib import Path
from homeassistant.core import HomeAssistant
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, PLATFORMS
from .coordinator import HFCState


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    await hass.http.async_register_static_paths([
        StaticPathConfig("/homefitnesscode/homefitnesscode-card.js",
                         str(Path(__file__).parent / "www" / "homefitnesscode-card.js"), False)
    ])
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    state = HFCState(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = state
    await state.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    state = hass.data[DOMAIN].pop(entry.entry_id)
    await state.shutdown()
    return True
