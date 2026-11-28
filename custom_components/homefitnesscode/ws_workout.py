"""Read stored treadmill workouts and manually finalize current session (admin only)."""
from __future__ import annotations

import probatio
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN


@websocket_api.require_admin
@websocket_api.websocket_command({
    probatio.Required("type"): "homefitnesscode/workouts",
    probatio.Required("entry_id"): str,
    probatio.Required("action"): str,
    probatio.Optional("hr_source"): str,
})
@callback
def ws_workouts(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    state = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if state is None or not hasattr(state, "workouts"):
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND,
                              "No workout journal for this equipment")
        return
    if msg["action"] not in ("status", "save", "hr_source"):
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT,
                              "Unknown workout command")
        return
    journal = state.workouts
    if msg["action"] == "hr_source":
        source = msg.get("hr_source", "")
        band = hass.data.get(DOMAIN, {}).get(source)
        if source and (band is None or band.data.get("machine_type") != "heart_rate_monitor"):
            connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, "Invalid heart rate source")
            return
        if journal.active:
            connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, "Heart rate source locked during workout")
            return
        state.hr_preference = source
    elif msg["action"] == "save":
        journal.close("manual")
    else:
        journal.tick()
    connection.send_result(msg["id"], journal.status())


def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_workouts)
