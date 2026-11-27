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

from .const import CONTROL_CHAR, DATA_CHARS, FEATURE_CHAR, RANGE_CHARS, STATUS_CHAR, TACX_RX, TACX_TX
from .capture import ProtocolCapture
from .profiles import make_profile
from .protocol import encode_target, validate_reply

_LOGGER = logging.getLogger(__name__)


class Transport:
    def __init__(self, hass: HomeAssistant, address: str, preferred: str, profile_name: str,
                 on_data: Callable[[dict], None], on_disconnect: Callable[[], None],
                 capture: ProtocolCapture | None = None,
                 on_frame: Callable[..., None] | None = None):
        self.hass = hass
        self.address = address
        self.preferred = preferred
        self.profile_name = profile_name
        self.profile = make_profile(profile_name)
        self.tacx = None
        self.on_data = on_data
        self.on_disconnect = on_disconnect
        self.capture = capture
        self.on_frame = on_frame
        self.gatt_inventory: list[str] = []
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

    def _capture(self, direction: str, characteristic: str, payload: bytes | bytearray | None = None,
                 *, decoded: dict | None = None, error: str | None = None,
                 protocol: str | None = None) -> None:
        if self.capture is not None:
            self.capture.record(direction, characteristic, payload, decoded=decoded,
                                error=error, protocol=protocol)
        if self.on_frame is not None:
            self.on_frame(direction, characteristic, payload, decoded=decoded,
                          error=error, protocol=protocol)

    def _disconnected(self, _client: BleakClient) -> None:
        self._capture("event", "connection", decoded={"status": "disconnected"})
        self.client = None
        self.tacx = None
        self.has_control = False
        self.armed = False
        if self._waiter is not None and not self._waiter.done():
            self._waiter.set_exception(ConnectionError("FTMS disconnected"))
        self.on_disconnect()

    def _sample(self, _char: Any, payload: bytearray) -> None:
        channel = DATA_CHARS.get(self.machine_type, "unknown_data")
        if self.machine_type is None:
            self._capture("rx", channel, payload, error="machine_type_unknown")
            return
        try:
            values = self.profile.parse(self.machine_type, bytes(payload))
        except ValueError as err:
            self._capture("rx", channel, payload, error=str(err))
            _LOGGER.debug("Ignored malformed %s packet: %s", self.machine_type, err)
        else:
            self._capture("rx", channel, payload, decoded=values)
            self.on_data(values)

    def _status(self, _char: Any, payload: bytearray) -> None:
        # FTMS status notifications are observation only; never trigger motor control.
        if not payload:
            self._capture("rx", STATUS_CHAR, payload, error="empty_status")
            return
        code = payload[0]
        values: dict = {}
        if code == 0x01:
            values = {"session_status": "reset"}
        elif code == 0x02:
            values = {"session_status": "paused" if len(payload) > 1
                      and payload[1] == 0x02 else "stopped"}
        elif code == 0x03:
            self.armed = False
            values = {"session_status": "safety_stop"}
        elif code == 0x04:
            values = {"session_status": "running"}
        self._capture("rx", STATUS_CHAR, payload, decoded=values,
                      error=None if values else f"unknown_status_opcode_{code:02x}")
        if values:
            self.on_data(values)

    def _ack(self, _char: Any, payload: bytearray) -> None:
        self._capture("rx", CONTROL_CHAR, payload)
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
                self.gatt_inventory = [f"{service.uuid}/{characteristic.uuid}"
                                       for service in services
                                       for characteristic in service.characteristics]
                self._capture("event", "gatt_inventory",
                              decoded={"characteristics": self.gatt_inventory})
                available = {kind: ch for kind, ch in DATA_CHARS.items()
                             if services.get_characteristic(ch)}
                if (not available and services.get_characteristic(TACX_RX)
                        and services.get_characteristic(TACX_TX)
                        and self.profile_name in ("auto", "tacx_fec")):
                    from pycycling.tacx_trainer_control import TacxTrainerControl
                    self.tacx = TacxTrainerControl(client)
                    self.machine_type = "bike"
                    self.tacx.set_general_fe_data_page_handler(self._tacx_general)
                    self.tacx.set_specific_trainer_data_page_handler(self._tacx_specific)
                    # Single BLE subscription: capture raw FE-C frames before handing
                    # them to pycycling 0.4.1's pinned parser.
                    await client.start_notify(TACX_TX, self._tacx_notification)
                    self.has_control = True
                    self.armed = False
                    self.client = client
                    self.on_data({"protocol": "tacx_fec", "machine_type": "bike"})
                    return
                if not available and self.profile_name == "christopeit_wp5000":
                    # Read-only GATT inventory. No speculative vendor writes.
                    self.machine_type = "rower"
                    services_found = []
                    for service in services:
                        for char in service.characteristics:
                            services_found.append(f"{service.uuid}/{char.uuid}")
                    self.client = client
                    self.has_control = False
                    self.armed = False
                    self.on_data({"protocol": "christopeit_wp5000_diagnostic",
                                  "machine_type": "rower",
                                  "gatt_inventory": services_found,
                                  "session_status": "diagnostic"})
                    return
                if not available:
                    raise ConnectionError("No supported FTMS or Tacx FE-C data characteristics")
                if self.profile_name == "tacx_fec":
                    raise ConnectionError("Tacx FE-C selected but unsupported on this device")
                self.machine_type = (self.preferred if self.preferred in available
                                     else next(iter(available)))
                self.on_data({"protocol": self.profile.name, "machine_type": self.machine_type})
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
        self.tacx = None
        self.armed = False
        self.has_control = False
        if client and client.is_connected:
            await client.disconnect()

    def supports_target(self, kind: str) -> bool:
        from .const import TARGET_BITS
        if self.tacx is not None:
            return self.connected and self.has_control and kind in ("power", "incline")
        return (self.connected and self.has_control and self.has_features
                and bool(self.target_bits & (1 << TARGET_BITS[kind])))


    def _tacx_notification(self, sender: Any, payload: bytearray) -> None:
        self._capture("rx", TACX_TX, payload, protocol="tacx_fec")
        if self.tacx is None:
            return
        try:
            # pycycling==0.4.1; isolate its private parser dependency here.
            self.tacx._fec_notification_handler(sender, payload)
        except (ValueError, IndexError, KeyError, AttributeError) as err:
            self._capture("event", "tacx_fec_parser", error=str(err),
                          protocol="tacx_fec")
            _LOGGER.debug("Ignored malformed Tacx FE-C packet: %s", err)

    def _tacx_general(self, data) -> None:
        # FE-C page 16 fields are rolling/partial; do not expose byte-sized
        # distance or elapsed values as cumulative workout totals.
        values = {"speed_kmh": round(data.speed * 3.6, 2)} if data.speed is not None else {}
        if data.heart_rate is not None:
            values["heart_rate_bpm"] = data.heart_rate
        self.on_data(values)

    def _tacx_specific(self, data) -> None:
        values = {}
        if data.instantaneous_power is not None and data.instantaneous_power != 0xFFF:
            values["power_w"] = data.instantaneous_power
        if data.instantaneous_cadence is not None and data.instantaneous_cadence != 0xFF:
            values["cadence_rpm"] = data.instantaneous_cadence
        self.on_data(values)

    async def _write(self, payload: bytes, *, need_arm: bool = True) -> None:
        async with self._write_lock:
            if not self.connected or not self.has_control or self.client is None:
                raise ConnectionError("FTMS control not available")
            if need_arm and not self.armed:
                raise PermissionError("Press Arm control first")
            self._expected = payload[0]
            self._waiter = asyncio.get_running_loop().create_future()
            try:
                self._capture("tx", CONTROL_CHAR, payload, decoded={"attempted": True})
                await self.client.write_gatt_char(CONTROL_CHAR, payload, response=True)
                result = await asyncio.wait_for(self._waiter, timeout=5)
                validate_reply(result, payload[0])
            finally:
                self._expected = None
                self._waiter = None

    async def arm(self) -> None:
        if self.tacx is not None and self.connected:
            # FE-C over BLE has no FTMS request-control opcode; local opt-in only.
            self.armed = True
            return
        await self._write(b"\x00", need_arm=False)  # Request Control, 0x00
        self.armed = True

    async def target(self, kind: str, value: float) -> None:
        if not self.supports_target(kind):
            raise ValueError(f"{kind} target not advertised by machine")
        if self.tacx is not None:
            if not self.armed:
                raise PermissionError("Tacx control is not armed")
            if kind == "power":
                self._capture("event", "tacx_fec_control",
                              decoded={"kind": "power", "target": value}, protocol="tacx_fec")
                await self.tacx.set_target_power(int(value))
                return
            if kind == "incline":
                self._capture("event", "tacx_fec_control",
                              decoded={"kind": "incline", "target": value}, protocol="tacx_fec")
                await self.tacx.set_track_resistance(value, 0.004)
                return
            raise ValueError("Tacx supports only power and simulated grade in this version")
        await self._write(encode_target(kind, value))

    async def session(self, action: str) -> None:
        if self.tacx is not None:
            raise ValueError("FE-C trainers are driven by pedaling; no start/stop command")
        if action == "start":
            await self._write(b"\x07")  # Start or Resume
        elif action == "stop":
            await self._write(b"\x08\x01")
        elif action == "pause":
            await self._write(b"\x08\x02")
        else:
            raise ValueError("Unknown FTMS session action")
