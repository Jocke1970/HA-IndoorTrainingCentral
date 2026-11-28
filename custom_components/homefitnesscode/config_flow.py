"""Bluetooth discovery and manual selection of local FTMS equipment."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import bluetooth

from .const import CAP_DEFAULTS, DOMAIN, MACHINE_OPTIONS, PROFILE_OPTIONS, SERVICE_FTMS, TACX_FEC_SERVICE, SERVICE_HRS


class HomeFitnessCodeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._found_address = None
        self._found_name = None
        self._found_hrs = False

    async def async_step_bluetooth(self, discovery_info):
        self._found_address = discovery_info.address
        services = {str(x).lower() for x in discovery_info.service_uuids}
        self._found_hrs = SERVICE_HRS in services and not services.intersection({SERVICE_FTMS, TACX_FEC_SERVICE})
        self._found_name = discovery_info.name or "FTMS machine"
        await self.async_set_unique_id(self._found_address)
        self._abort_if_unique_id_configured()
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="confirm",
                                        description_placeholders={"name": self._found_name})
        is_headwind = self._found_name.upper().startswith(("HEADWIND", "KICKR HEADWIND"))
        return self.async_create_entry(
            title=self._found_name,
            data={"address": self._found_address,
                  "profile": "wahoo_headwind" if is_headwind else "ble_hrs" if self._found_hrs else "auto",
                  "machine": "headwind" if is_headwind else "heart_rate_monitor" if self._found_hrs else "auto",
                  **{f"max_{k}": v for k, v in CAP_DEFAULTS.items()}}
        )

    async def async_step_user(self, user_input=None):
        devices = {
            dev.address: f"{dev.name or 'FTMS'} ({dev.address})"
            for dev in bluetooth.async_discovered_service_info(self.hass, connectable=True)
            if dev.address
        }
        if not devices:
            return self.async_show_form(step_id="user", errors={"base": "no_devices"})
        if user_input is not None:
            address = user_input["address"]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            data = dict(user_input)
            name = devices.get(address, "")
            if (data.get("profile") == "auto" and
                    name.upper().startswith(("HEADWIND", "KICKR HEADWIND"))):
                data["profile"] = "wahoo_headwind"
                data["machine"] = "headwind"
            if data.get("profile") == "wahoo_headwind":
                data["machine"] = "headwind"
            if data.get("profile") == "ble_hrs" or data.get("machine") == "heart_rate_monitor":
                data.update(profile="ble_hrs", machine="heart_rate_monitor")
            return self.async_create_entry(title=name or address, data=data)
        form = {
            vol.Required("address"): vol.In(devices),
            vol.Required("profile", default="auto"): vol.In(PROFILE_OPTIONS),
            vol.Required("machine", default="auto"): vol.In(MACHINE_OPTIONS),
        }
        for kind, default in CAP_DEFAULTS.items():
            form[vol.Required(f"max_{kind}", default=default)] = vol.Coerce(float)
        return self.async_show_form(step_id="user", data_schema=vol.Schema(form))
