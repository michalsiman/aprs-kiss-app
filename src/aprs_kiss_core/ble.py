"""A TNC over Bluetooth Low Energy: "KISS over BLE" (github.com/hessu/aprs-specs, BLE-KISS-API.md).

TNCs and radios that offer it: Mobilinkd TNC3/TNC4, PicoAPRS, the CA2RXU LoRa APRS Tracker (Bluetooth set to
KISS), B.B. Link, Vero VR-N76, BTECH UV-Pro, Radioddity GA-5WB … The only Bluetooth an iPhone has for a TNC.

The radio work is done by a *backend* (in the app: a Flet extension over universal_ble, aprs_kiss_app/ble_flet.py),
which scans, connects, writes the KISS bytes in pieces the link takes, and hands over what the TNC sends: in
pieces too, which the KISS decoder puts back together as from a serial line. Registered as the "ble" transport,
so the KISS logic in connection.py stays the same.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from typing import Protocol

from .connection import Streams, TncSettings, register_transport

_LOGGER = logging.getLogger(__name__)

KISS_SERVICE = "00000001-ba2a-46c9-ae49-01b0961f68bb"


class Backend(Protocol):
    async def ready(self) -> bool: ...  # this build can do Bluetooth LE

    async def scan(self, seconds: float) -> list[dict]: ...  # [{"id", "name", "rssi", "kiss"}]

    async def connect(self, device_id: str, on_data: Callable[[bytes], None],
                      on_lost: Callable[[str], None]) -> dict: ...

    async def write(self, data: bytes) -> None: ...

    async def disconnect(self) -> None: ...


_backend: Backend | None = None
found: list[str] = []  # the devices of the last scan, "name (id)", for the settings


def set_backend(backend: Backend) -> None:
    global _backend
    _backend = backend
    register_transport("ble", open_ble)


async def available() -> bool:
    if _backend is None:
        return False
    try:
        return await _backend.ready()
    except Exception:  # noqa: BLE001 - no extension in this build
        return False


def describe(device: dict) -> str:
    name = (device.get("name") or "").strip() or "?"
    return f"{name} ({device['id']})"


def device_id(text: str) -> str:
    """'ESP32 LoRa (AA:BB:CC:DD:EE:FF)' -> 'AA:BB:CC:DD:EE:FF'; an id on its own stays."""
    text = (text or "").strip()
    if text.endswith(")") and "(" in text:
        return text[text.rindex("(") + 1:-1].strip()
    return text


async def scan(seconds: float = 6) -> list[str]:
    """The devices around, those offering KISS first, as "name (id)"; remembered in `found`."""
    if _backend is None:
        raise OSError("Bluetooth LE is not available here")
    devices = await _backend.scan(seconds)
    kiss = [describe(d) for d in devices if d.get("kiss")]
    others = [describe(d) for d in devices if not d.get("kiss")]
    found[:] = kiss + others
    return list(found)


class _Writer:
    """Just enough of asyncio.StreamWriter for KissConnection: write, drain, close."""

    def __init__(self, backend: Backend) -> None:
        self._backend = backend
        self._pending = bytearray()
        self._closed = False

    def write(self, data: bytes) -> None:
        self._pending += data

    async def drain(self) -> None:
        if self._pending and not self._closed:
            data, self._pending = bytes(self._pending), bytearray()
            await self._backend.write(data)

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            task = asyncio.ensure_future(self._backend.disconnect())
            task.add_done_callback(lambda t: t.cancelled() or t.exception())


async def open_ble(settings: TncSettings) -> Streams:
    if _backend is None or not await available():
        raise OSError("Bluetooth LE is not available in this version of the app")
    wanted = device_id(settings.device)
    if not wanted:
        raise OSError("No Bluetooth LE device chosen: pick one in Settings › Connection")
    reader = asyncio.StreamReader()

    def on_data(data: bytes) -> None:
        if not reader.at_eof():
            reader.feed_data(data)

    def on_lost(reason: str) -> None:
        with contextlib.suppress(Exception):
            reader.set_exception(ConnectionResetError(reason or "Bluetooth LE TNC gone"))

    info = await _backend.connect(wanted, on_data, on_lost)
    _LOGGER.info("Bluetooth LE TNC connected: %s (MTU %s)", settings.device, (info or {}).get("mtu"))
    return reader, _Writer(_backend)
