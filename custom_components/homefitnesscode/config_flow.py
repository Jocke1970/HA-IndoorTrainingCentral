"""Bluetooth discovery and manual selection of local FTMS equipment."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import bluetooth

from .const import CAP_DEFAULTS, DOMAIN, MACHINE_OPTIONS, PROFILE_OPTIONS, SERVICE_FTMS


class HomeFitnessCodeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._found_address = None
        self._found_name = None

    async def async_step_bluetooth(self, discovery_info):
        self._found_address = discovery_info.address
        self._found_name = discovery_info.name or "FTMS machine"
        await self.async_set_unique_id(self._found_address)
        self._abort_if_unique_id_configured()
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="confirm",
                                        description_placeholders={"name": self._found_name})
        return self.async_create_entry(
            title=self._found_name,
            data={"address": self._found_address, "profile": "auto",
                  "machine": "auto", **{f"max_{k}": v for k, v in CAP_DEFAULTS.items()}}
        )

    async def async_step_user(self, user_input=None):
        devices = {
            dev.address: f"{dev.name or 'FTMS'} ({dev.address})"
            for dev in bluetooth.async_discovered_service_info(self.hass, connectable=True)
            if SERVICE_FTMS in [uuid.lower() for uuid in dev.service_uuids]
        }
        if not devices:
            return self.async_show_form(step_id="user", errors={"base": "no_devices"})
        if user_input is not None:
            address = user_input["address"]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=devices.get(address, address),
                data=user_input,
            )
        form = {
            vol.Required("address"): vol.In(devices),
            vol.Required("profile", default="auto"): vol.In(PROFILE_OPTIONS),
            vol.Required("machine", default="auto"): vol.In(MACHINE_OPTIONS),
        }
        for kind, default in CAP_DEFAULTS.items():
            form[vol.Required(f"max_{kind}", default=default)] = vol.Coerce(float)
        return self.async_show_form(step_id="user", data_schema=vol.Schema(form))
