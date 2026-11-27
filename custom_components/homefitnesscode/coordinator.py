"""Connection lifecycle, telemetry and conservative remote-control safety."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import CAP_DEFAULTS, DOMAIN
from .transport import Transport
from .capture import ProtocolCapture
from .workout import WorkoutJournal
from .entity_catalog import inferred_machine

_LOGGER = logging.getLogger(__name__)


class HFCState(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        super().__init__(hass, _LOGGER, name=f"{DOMAIN}_{entry.entry_id}",
                         update_interval=timedelta(seconds=15))
        self.entry = entry
        self.capture = ProtocolCapture()
        self.workouts = WorkoutJournal(hass.config.path("homefitnesscode", "sessions"),
                                       entry.entry_id, entry.title)
        initial_kind = inferred_machine(dict(entry.data), entry.title)
        self.transport = Transport(
            hass, entry.data["address"], initial_kind,
            entry.data.get("profile", "auto"), self._received, self._disconnected,
            capture=self.capture, on_frame=self.workouts.on_frame,
        )
        self.data = {"connected": False, "armed": False, "session_status": "unknown",
                     "machine_type": initial_kind,
                     "protocol": entry.data.get("profile", "auto")}
        self.targets: dict[str, float] = {}

    def _received(self, values: dict[str, Any]) -> None:
        self.async_set_updated_data({
            **self.data, **values, "connected": self.transport.connected,
            "armed": self.transport.armed,
            "machine_type": self.transport.machine_type or self.data["machine_type"],
        })

    def _disconnected(self) -> None:
        self.targets.clear()  # no stale commands after reconnect
        self.workouts.close("bluetooth_disconnected")
        self.async_set_updated_data({
            **self.data, "connected": False, "armed": False,
            "session_status": "disconnected",
        })

    async def _async_update_data(self) -> dict:
        self.workouts.tick()
        try:
            await self.transport.connect()
        except Exception as err:
            # Keep config entry installed even if the equipment is off.
            _LOGGER.debug("FTMS waiting for %s: %s", self.entry.data["address"], err)
            return {**self.data, "connected": False, "armed": False, "session_status": "disconnected"}
        connected = self.transport.connected
        return {
            **self.data, "connected": connected,
            "armed": self.transport.armed,
            "machine_type": self.transport.machine_type or self.data["machine_type"],
            "session_status": (
                "ready" if connected and self.data.get("session_status") == "disconnected"
                else self.data.get("session_status", "unknown")
            ),
        }

    def can_target(self, kind: str) -> bool:
        machine = self.transport.machine_type
        relevant = {
            "speed": ("treadmill",),
            "incline": ("treadmill",),
            "resistance": ("bike", "rower"),
            "power": ("bike", "rower"),
        }
        return (machine in relevant[kind] or (machine == "bike" and kind == "incline" and self.transport.tacx is not None)) and self.transport.supports_target(kind)

    def limits(self, kind: str) -> tuple[float, float, float]:
        user_max = float(self.entry.data.get(f"max_{kind}", CAP_DEFAULTS[kind]))
        lower, upper, step = self.transport.ranges.get(kind, (0, user_max, 1))
        upper = max(lower, min(user_max, upper))
        return lower, upper, max(step, 0.1)

    async def set_target(self, kind: str, value: float) -> None:
        if not self.can_target(kind):
            raise ValueError("This machine does not advertise target control")
        lower, upper, _step = self.limits(kind)
        if not lower <= value <= upper:
            raise ValueError(f"Target must be between {lower} and {upper}")
        await self.transport.target(kind, value)
        self.targets[kind] = value
        self._received({})

    async def command(self, action: str) -> None:
        if action == "arm":
            await self.transport.arm()
        else:
            await self.transport.session(action)
        session_states = {"start": "running", "pause": "paused", "stop": "stopped"}
        self._received({"session_status": session_states[action]}
                       if action in session_states else {})

    async def shutdown(self) -> None:
        await self.transport.disconnect()
        await self.workouts.shutdown()
