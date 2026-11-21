"""Independent Wahoo HEADWIND BLE companion transport for HomeFitnessCode.

No control is written at boot or reconnect; writes always require an explicit
user-requested fan/mode entity call. The fan may autonomously use paired ANT+
or BLE sensors when its own HR/speed mode is selected.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .headwind_protocol import CONTROL, MODES, decode_notification, mode_command, percent_command

_LOGGER = logging.getLogger(__name__)


class HeadwindState(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for one independent fan, not the bike connection."""

    def __init__(self, hass, entry):
        super().__init__(
            hass, _LOGGER, name=f"homefitnesscode_headwind_{entry.entry_id}",
            update_interval=timedelta(seconds=15),
        )
        self.entry = entry
        self._client: BleakClient | None = None
        self._connect_lock = asyncio.Lock()
        self._command_lock = asyncio.Lock()
        self.data = {"connected": False, "machine_type": "headwind",
                     "protocol": "wahoo_headwind_ble",
                     "headwind_mode": "unknown", "fan_percent": None}

    @property
    def connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    def _disconnected(self, client: BleakClient) -> None:
        if client is not self._client:
            return
        self._client = None
        self.async_set_updated_data({
            **self.data, "connected": False, "headwind_mode": "unknown",
            "fan_percent": None,
        })

    def _notify(self, _char: Any, payload: bytearray) -> None:
        values = decode_notification(bytes(payload))
        if values:
            self.async_set_updated_data({**self.data, **values, "connected": self.connected})

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            await self.connect()
        except Exception as err:
            _LOGGER.debug("HEADWIND %s not connected: %s", self.entry.data["address"], err)
            return {**self.data, "connected": False}
        return {**self.data, "connected": self.connected}

    async def connect(self) -> None:
        async with self._connect_lock:
            if self.connected:
                return
            device = bluetooth.async_ble_device_from_address(
                self.hass, self.entry.data["address"], connectable=True
            )
            if device is None:
                raise ConnectionError("No Bluetooth adapter sees HEADWIND")
            client = await establish_connection(
                BleakClient, device, "Wahoo HEADWIND",
                disconnected_callback=self._disconnected,
            )
            try:
                if client.services.get_characteristic(CONTROL) is None:
                    raise ConnectionError("Wahoo HEADWIND BLE characteristic absent")
                await client.start_notify(CONTROL, self._notify)
                self._client = client
                self.async_set_updated_data({**self.data, "connected": True})
            except Exception:
                await client.disconnect()
                raise

    async def _send(self, command: bytes) -> None:
        async with self._command_lock:
            if not self.connected or self._client is None:
                raise ConnectionError("HEADWIND disconnected; no command sent")
            await self._client.write_gatt_char(CONTROL, command, response=True)
            # BLE write acknowledgement is not fan-state feedback.
            # Keep state from notifications, never publish an assumed speed.

    async def set_mode(self, mode: str) -> None:
        await self._send(mode_command(mode))

    async def set_percentage(self, percentage: int) -> None:
        if not isinstance(percentage, int) or not 0 <= percentage <= 100:
            raise ValueError("Fan speed outside 0..100%")
        if percentage == 0:
            await self.set_mode("off")
        else:
            async with self._command_lock:
                if not self.connected or self._client is None:
                    raise ConnectionError("HEADWIND disconnected")
                await self._client.write_gatt_char(
                    CONTROL, mode_command("manual"), response=True
                )
                await self._client.write_gatt_char(
                    CONTROL, percent_command(percentage), response=True
                )

    async def shutdown(self) -> None:
        async with self._connect_lock:
            client, self._client = self._client, None
            if client is not None and client.is_connected:
                await client.disconnect()
        # Never change physical fan mode/speed on HA shutdown.
