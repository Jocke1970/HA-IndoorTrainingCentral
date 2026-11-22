"""Administrator-only websocket commands for opt-in protocol capture."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "homefitnesscode/protocol_capture",
    vol.Required("entry_id"): str,
    vol.Required("action"): vol.In(("status", "start", "stop", "export")),
})
@callback
def ws_protocol_capture(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Manage the bounded capture associated with an installed device."""
    state = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if state is None or not hasattr(state, "capture"):
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND,
                              "Training device is not configured")
        return
    capture = state.capture
    action = msg["action"]
    if action == "start":
        status = capture.start(
            profile=str(state.data.get("protocol") or state.entry.data.get("profile", "auto")),
            device_name=state.entry.title,
        )
        transport = getattr(state, "transport", None)
        inventory = getattr(transport, "gatt_inventory", None)
        if inventory:
            capture.record("event", "gatt_inventory",
                           decoded={"characteristics": list(inventory)})
            status = capture.status()
    elif action == "stop":
        status = capture.stop()
    else:
        status = capture.status()
    if action == "export":
        connection.send_result(msg["id"], {
            "status": status,
            "jsonl": capture.export_jsonl(),
        })
    else:
        connection.send_result(msg["id"], status)


def async_register(hass: HomeAssistant) -> None:
    """Register command once at integration initialization."""
    websocket_api.async_register_command(hass, ws_protocol_capture)
