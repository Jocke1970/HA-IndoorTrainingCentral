"""Bluetooth transport, capability discovery and acknowledged FTMS commands."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import CONTROL_CHAR, DATA_CHARS, FEATURE_CHAR, RANGE_CHARS, STATUS_CHAR
from .protocol import PARSERS, encode_target, validate_reply

_LOGGER = logging.getLogger(__name__)


class Transport:
    def __init__(self, hass: HomeAssistant, address: str, preferred: str,
                 on_data: Callable[[dict], None], on_disconnect: Callable[[], None]):
        self.hass = hass
        self.address = address
        self.preferred = preferred
        self.on_data = on_data
        self.on_disconnect = on_disconnect
        self.client: BleakClient | None = None
        self.machine_type: str | None = None
        self.target_bits = 0
        self.has_features = False
        self.has_control = False
        self.armed = False
        self.ranges: dict[str, tuple[float, float, float]] = {}
        self._connect_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._waiter: asyncio.Future[bytes] | None = None
        self._expected: int | None = None

    @property
    def connected(self) -> bool:
        return self.client is not None and self.client.is_connected

    def _disconnected(self, _client: BleakClient) -> None:
        self.client = None
        self.has_control = False
        self.armed = False
        if self._waiter is not None and not self._waiter.done():
            self._waiter.set_exception(ConnectionError("FTMS disconnected"))
        self.on_disconnect()

    def _sample(self, _char: Any, payload: bytearray) -> None:
        if self.machine_type is None:
            return
        try:
            self.on_data(PARSERS[self.machine_type](bytes(payload)))
        except ValueError as err:
            _LOGGER.debug("Ignored malformed %s packet: %s", self.machine_type, err)

    def _status(self, _char: Any, payload: bytearray) -> None:
        # FTMS Fitness Machine Status: 0x01 stopped/paused, 0x02 safety key,
        # 0x03 started/resumed. This callback NEVER initiates motor control.
        if not payload:
            return
        code = payload[0]
        if code == 0x01:
            value = "paused" if len(payload) > 1 and payload[1] == 0x02 else "stopped"
            self.on_data({"session_status": value})
        elif code == 0x02:
            self.armed = False
            self.on_data({"session_status": "safety_stop"})
        elif code == 0x03:
            self.on_data({"session_status": "running"})

    def _ack(self, _char: Any, payload: bytearray) -> None:
        if (len(payload) >= 3 and payload[0] == 0x80
                and payload[1] == self._expected and self._waiter is not None
                and not self._waiter.done()):
            self._waiter.set_result(bytes(payload))

    async def connect(self) -> None:
        async with self._connect_lock:
            if self.connected:
                return
            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if ble_device is None:
                raise ConnectionError("No connectable Bluetooth scanner sees this device")
            client = await establish_connection(
                BleakClient, ble_device, "HomeFitnessCode / FTMS",
                disconnected_callback=self._disconnected,
            )
            try:
                services = client.services
                available = {kind: ch for kind, ch in DATA_CHARS.items()
                             if services.get_characteristic(ch)}
                if not available:
                    raise ConnectionError("No FTMS treadmill/bike/rower data characteristic")
                self.machine_type = (self.preferred if self.preferred in available
                                     else next(iter(available)))
                self.has_features = bool(services.get_characteristic(FEATURE_CHAR))
                self.target_bits = 0
                if self.has_features:
                    raw = await client.read_gatt_char(FEATURE_CHAR)
                    if len(raw) >= 8:
                        self.target_bits = int.from_bytes(raw[4:8], "little")
                self.ranges = {}
                for kind, char in RANGE_CHARS.items():
                    if not services.get_characteristic(char):
                        continue
                    raw = await client.read_gatt_char(char)
                    if len(raw) < 6:
                        continue
                    signed = kind in ("incline", "resistance")
                    factor = 100 if kind == "speed" else 10 if kind == "incline" else 1
                    self.ranges[kind] = (
                        int.from_bytes(raw[0:2], "little", signed=signed) / factor,
                        int.from_bytes(raw[2:4], "little", signed=signed) / factor,
                        int.from_bytes(raw[4:6], "little") / factor,
                    )
                # Subscriptions come before publishing connected=true.
                await client.start_notify(DATA_CHARS[self.machine_type], self._sample)
                if services.get_characteristic(STATUS_CHAR):
                    await client.start_notify(STATUS_CHAR, self._status)
                self.has_control = bool(services.get_characteristic(CONTROL_CHAR))
                if self.has_control:
                    await client.start_notify(CONTROL_CHAR, self._ack)
                self.armed = False
                self.client = client
            except Exception:
                await client.disconnect()
                raise

    async def disconnect(self) -> None:
        client, self.client = self.client, None
        self.armed = False
        self.has_control = False
        if client and client.is_connected:
            await client.disconnect()

    def supports_target(self, kind: str) -> bool:
        from .const import TARGET_BITS
        return (self.connected and self.has_control and self.has_features
                and bool(self.target_bits & (1 << TARGET_BITS[kind])))

    async def _write(self, payload: bytes, *, need_arm: bool = True) -> None:
        async with self._write_lock:
            if not self.connected or not self.has_control or self.client is None:
                raise ConnectionError("FTMS control not available")
            if need_arm and not self.armed:
                raise PermissionError("Press Arm control first")
            self._expected = payload[0]
            self._waiter = asyncio.get_running_loop().create_future()
            try:
                await self.client.write_gatt_char(CONTROL_CHAR, payload, response=True)
                result = await asyncio.wait_for(self._waiter, timeout=5)
                validate_reply(result, payload[0])
            finally:
                self._expected = None
                self._waiter = None

    async def arm(self) -> None:
        await self._write(b"\x00", need_arm=False)  # Request Control, 0x00
        self.armed = True

    async def target(self, kind: str, value: float) -> None:
        if not self.supports_target(kind):
            raise ValueError(f"{kind} target not advertised by machine")
        await self._write(encode_target(kind, value))

    async def session(self, action: str) -> None:
        if action == "start":
            await self._write(b"\x07")  # Start or Resume
        elif action == "stop":
            await self._write(b"\x08\x01")
        elif action == "pause":
            await self._write(b"\x08\x02")
        else:
            raise ValueError("Unknown FTMS session action")
