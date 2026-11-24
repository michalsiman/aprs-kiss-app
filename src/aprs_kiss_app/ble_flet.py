"""The Bluetooth LE backend of aprs_kiss_core.ble in the app: the Flet extension flet_ble_kiss (universal_ble).

The Dart side (packages/flet-ble-kiss) comes into the app with `flet build` on every platform; a run from
source (pip, the desktop client) has no such extension: `ready()` finds out with a ping, and the
"Bluetooth LE" connection is offered only where it answered.
"""

from __future__ import annotations

import base64
import logging
from collections.abc import Callable
from typing import Optional

import flet as ft

from aprs_kiss_core import ble

_LOGGER = logging.getLogger(__name__)

PING_TIMEOUT = 4.0


@ft.control("BleKiss")
class BleKiss(ft.Service):
    """KISS over Bluetooth LE (the Dart service BleKissService)."""

    on_data: Optional[ft.ControlEventHandler["BleKiss"]] = None  # e.data: base64 of the bytes received
    on_lost: Optional[ft.ControlEventHandler["BleKiss"]] = None  # e.data: why


class FletBle:
    """ble.Backend through the BleKiss service; made in the page's context (main), used from the engine."""

    def __init__(self) -> None:
        self.service = BleKiss(on_data=self._data, on_lost=self._lost)
        self._ready: bool | None = None  # None: not asked yet
        self._on_data: Callable[[bytes], None] | None = None
        self._on_lost: Callable[[str], None] | None = None

    def _data(self, e) -> None:
        if self._on_data and e.data:
            self._on_data(base64.b64decode(e.data))

    def _lost(self, e) -> None:
        if self._on_lost:
            self._on_lost(str(e.data or ""))

    async def _call(self, method: str, args: dict | None = None, timeout: float = 30):
        try:
            return await self.service._invoke_method(method, args, timeout=timeout)
        except (TimeoutError, OSError):
            raise
        except Exception as err:  # noqa: BLE001 - the Dart side's error: for the connection's retry loop
            raise OSError(str(err) or type(err).__name__) from err

    async def ready(self) -> bool:
        if self._ready is None:
            try:
                self._ready = await self._call("ping", timeout=PING_TIMEOUT) == "ok"
            except Exception as err:  # noqa: BLE001 - no extension here (a run from source)
                _LOGGER.info("Bluetooth LE not available: %s", err)
                self._ready = False
        return self._ready

    async def scan(self, seconds: float) -> list[dict]:
        return list(await self._call("scan", {"seconds": seconds}, timeout=seconds + 30) or [])

    async def connect(self, device_id: str, on_data, on_lost) -> dict:
        self._on_data, self._on_lost = on_data, on_lost
        return await self._call("connect", {"id": device_id}, timeout=60) or {}

    async def write(self, data: bytes) -> None:
        await self._call("write", {"data": base64.b64encode(data).decode("ascii")}, timeout=30)

    async def disconnect(self) -> None:
        self._on_data = self._on_lost = None
        await self._call("disconnect", timeout=15)


def setup() -> FletBle | None:
    """Called in main (the page's context): the service, and the "ble" transport for the engine."""
    try:
        backend = FletBle()
    except Exception as err:  # noqa: BLE001 - no page context (tests)
        _LOGGER.info("Bluetooth LE backend not set up: %s", err)
        return None
    ble.set_backend(backend)
    return backend
