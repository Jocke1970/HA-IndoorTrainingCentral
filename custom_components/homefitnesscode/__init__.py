"""HomeFitnessCode / FTMS for Home Assistant."""
from pathlib import Path
from homeassistant.core import HomeAssistant
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, PLATFORMS
from .coordinator import HFCState
from .headwind import HeadwindState
from .entity_catalog import inferred_machine, registered_metrics
from homeassistant.helpers import entity_registry as er
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    await hass.http.async_register_static_paths([
        StaticPathConfig("/homefitnesscode/homefitnesscode-card.js",
                         str(Path(__file__).parent / "www" / "homefitnesscode-card.js"), False)
    ])
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Upgrade the beta's old HEADWIND entry in place: same config entry ID,
    # address and device identity. No manual deletion or re-pairing required.
    hint = inferred_machine(dict(entry.data), entry.title)
    if hint == "headwind" and entry.data.get("profile") != "wahoo_headwind":
        hass.config_entries.async_update_entry(entry, data={
            **entry.data, "profile": "wahoo_headwind", "machine": "headwind",
        })
    state = (HeadwindState(hass, entry)
             if entry.data.get('profile') == 'wahoo_headwind'
             else HFCState(hass, entry))
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = state
    await state.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    def prune_old_registry_entries() -> None:
        kind = state.data.get("machine_type", "auto")
        if kind not in ("headwind", "bike", "rower", "treadmill", "auto"):
            return  # Unknown BLE device gets a minimal diagnostic entity set.
        profile = entry.data.get("profile", "auto")
        if profile == "auto":
            transport = getattr(state, "transport", None)
            if getattr(transport, "tacx", None) is not None:
                profile = "tacx_fec"
            elif transport is not None and transport.connected and state.data.get("protocol") == "ftms":
                profile = "ftms"
        desired = registered_metrics(kind, profile)
        prefix = f"{entry.unique_id or entry.entry_id}_"
        registry = er.async_get(hass)
        for item in list(er.async_entries_for_config_entry(registry, entry.entry_id)):
            if item.unique_id.startswith(prefix) and item.unique_id[len(prefix):] not in desired:
                _LOGGER.info("Pruning obsolete HomeFitnessCode entity: %s", item.entity_id)
                registry.async_remove(item.entity_id)

    prune_old_registry_entries()
    entry.async_on_unload(state.async_add_listener(prune_old_registry_entries))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    state = hass.data[DOMAIN].pop(entry.entry_id)
    await state.shutdown()
    return True
