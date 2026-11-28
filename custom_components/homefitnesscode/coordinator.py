"""Connection lifecycle, telemetry and conservative remote-control safety."""
from __future__ import annotations

import logging
import asyncio
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
from .activity import observed_session_status
from .maintenance import Maintenance
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

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
            capture=self.capture, on_frame=self._journal_frame,
        )
        self.data = {"connected": False, "armed": False, "session_status": "unknown",
                     "machine_type": initial_kind,
                     "protocol": entry.data.get("profile", "auto")}
        self.targets: dict[str, float] = {}
        self.maintenance = Maintenance()
        self._maintenance_store = Store(hass, 1, f'{DOMAIN}.maintenance.{entry.entry_id}')
        self._maintenance_loaded = False
        self.hr_preference = None  # None = automatic; empty string = machine

    def _journal_frame(self, direction, characteristic, payload, **kwargs):
        journal = self.workouts
        if not journal.active and direction == 'rx' and characteristic.lower().startswith('00002acd'):
            bands = {key: state for key, state in self.hass.data.get(DOMAIN, {}).items()
                     if state.data.get('machine_type') == 'heart_rate_monitor'}
            selected = self.hr_preference if self.hr_preference is not None else next(iter(bands), None)
            journal.hr_source_id = selected or None
            journal.hr_source_name = bands[selected].entry.title if selected in bands else None
        journal.on_frame(direction, characteristic, payload, **kwargs)

    async def async_prepare_maintenance(self):
        self.maintenance = Maintenance(await self._maintenance_store.async_load())
        self._maintenance_loaded = True

    def _maintenance_snapshot(self):
        return self.maintenance.snapshot(dt_util.now().date())

    def _schedule_maintenance_save(self):
        self._maintenance_store.async_delay_save(lambda: self.maintenance.data, 15)

    async def acknowledge_lubrication(self):
        if self.data.get('machine_type') != 'treadmill' or not self._maintenance_loaded:
            raise ValueError('Treadmill maintenance not available')
        self.maintenance.acknowledge(dt_util.now().date())
        await self._maintenance_store.async_save(self.maintenance.data)
        self.async_set_updated_data({**self.data, **self._maintenance_snapshot()})

    def _received(self, values: dict[str, Any]) -> None:
        machine = self.transport.machine_type or self.data["machine_type"]
        status = observed_session_status(
            machine, self.data.get("session_status", "unknown"), values
        )
        if machine == 'heart_rate_monitor' and self.transport.connected and 'heart_rate_bpm' in values:
            for state in self.hass.data.get(DOMAIN, {}).values():
                if state.data.get('machine_type') == 'treadmill' and hasattr(state, 'workouts'):
                    state.workouts.record_heart_rate(self.entry.entry_id, values['heart_rate_bpm'], values.get('rr_interval_ms'))
        maintenance = {}
        if machine == "treadmill" and self._maintenance_loaded:
            if values.get("session_status") in ("paused", "stopped", "safety_stop", "reset"):
                self.maintenance.interrupt()
            elif "speed_kmh" in values:
                self.maintenance.sample(values["speed_kmh"], asyncio.get_running_loop().time(), dt_util.now().date())
            maintenance = self._maintenance_snapshot()
            self._schedule_maintenance_save()
        self.async_set_updated_data({
            **self.data, **values, **maintenance, "connected": self.transport.connected,
            "armed": self.transport.armed, "machine_type": machine,
            "session_status": status,
        })

    def _disconnected(self) -> None:
        self.maintenance.interrupt()
        if self._maintenance_loaded and self.data.get('machine_type') == 'treadmill':
            self._schedule_maintenance_save()
        self.targets.clear()  # no stale commands after reconnect
        self.workouts.close("bluetooth_disconnected")
        self.async_set_updated_data({
            **self.data, "connected": False, "armed": False,
            "session_status": "disconnected",
        })

    async def _async_update_data(self) -> dict:
        self.workouts.tick()
        if self._maintenance_loaded and self.data.get('machine_type') == 'treadmill':
            self.data = {**self.data, **self._maintenance_snapshot()}
            self._schedule_maintenance_save()
        try:
            await self.transport.connect()
        except Exception as err:
            # Keep config entry installed even if the equipment is off.
            _LOGGER.debug("FTMS waiting for %s: %s", self.entry.data["address"], err)
            return {**self.data, "connected": False, "armed": False, "session_status": "disconnected"}
        connected = self.transport.connected
        if self.transport.machine_type == "heart_rate_monitor" and (not self.transport._hr_at or asyncio.get_running_loop().time() - self.transport._hr_at > 10):
            self.data = {**self.data, "heart_rate_bpm": None, "rr_interval_ms": None}
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
        if self._maintenance_loaded and self.data.get('machine_type') == 'treadmill':
            await self._maintenance_store.async_save(self.maintenance.data)
