"""A TNC over classic Bluetooth (the serial port profile, SPP), for the Android app.

Bluetooth TNCs and radios with a KISS TNC inside (Mobilinkd TNC3, BTECH UV-Pro, Vero VR-N76, …) pair
with the phone in Android's Bluetooth settings; the app then lists the paired devices and opens an
RFCOMM socket to the chosen one, reached from Python with pyjnius like the USB driver.

Bluetooth Low Energy-only TNCs are not covered: they need GATT, not a serial socket.

Registered as the "bt" transport, so the KISS logic in connection.py stays the same.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
import time

from . import android_usb
from .connection import Streams, TncSettings, register_transport

_LOGGER = logging.getLogger(__name__)

SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"  # the serial port profile
CONNECT_PERMISSION = "android.permission.BLUETOOTH_CONNECT"  # Android 12 and later ask the user for it
PERMISSION_WAIT = 60.0
READ_SIZE = 1024


def available() -> bool:
    return android_usb.available()


def _jnius():
    return android_usb._jnius()


def _sdk() -> int:
    return int(_jnius().autoclass("android.os.Build$VERSION").SDK_INT)


def _adapter():
    jnius = _jnius()
    manager = jnius.cast("android.bluetooth.BluetoothManager", android_usb._activity().getSystemService("bluetooth"))
    adapter = manager.getAdapter() if manager else None
    if adapter is None:
        raise OSError("This phone has no Bluetooth")
    return adapter


def _allowed() -> bool:
    if _sdk() < 31:
        return True  # before Android 12 the install-time BLUETOOTH permission is enough
    return android_usb._activity().checkSelfPermission(CONNECT_PERMISSION) == 0


async def _permission() -> None:
    """Android 12+: ask the user once ("Nearby devices") and wait for the answer."""
    if _allowed():
        return
    android_usb._activity().requestPermissions([CONNECT_PERMISSION], 4711)
    deadline = time.monotonic() + PERMISSION_WAIT
    while time.monotonic() < deadline:
        await asyncio.sleep(0.5)
        if _allowed():
            return
    raise OSError("Not allowed to use Bluetooth: allow \"Nearby devices\" for the app")


def _describe(device) -> str:
    return f"{device.getName() or '?'} ({device.getAddress()})"


def _paired(adapter) -> list:
    jnius = _jnius()
    return [jnius.cast("android.bluetooth.BluetoothDevice", d) for d in adapter.getBondedDevices().toArray()]


def list_devices() -> list[str]:
    """The paired Bluetooth devices, "name (address)", for the settings (empty without the permission)."""
    if not available():
        return []
    with contextlib.suppress(Exception):
        if not _allowed():
            android_usb._activity().requestPermissions([CONNECT_PERMISSION], 4711)  # asked; listed next time
            return []
        adapter = _adapter()
        return [_describe(d) for d in _paired(adapter)]
    return []


def address_of(text: str) -> str:
    """'TNC3 (00:11:22:33:44:55)' -> '00:11:22:33:44:55'; an address on its own stays."""
    text = (text or "").strip()
    if text.endswith(")") and "(" in text:
        return text[text.rindex("(") + 1:-1].strip()
    return text


class BtSerial:
    """One RFCOMM socket; blocking calls, run from threads."""

    def __init__(self, adapter, device) -> None:
        jnius = _jnius()
        uuid = jnius.autoclass("java.util.UUID").fromString(SPP_UUID)
        with contextlib.suppress(Exception):
            adapter.cancelDiscovery()  # a running discovery slows a connection down a lot
        last = None
        self.socket = None
        # the secure socket first; some TNCs (no PIN, older modules) only take the insecure one
        for make in (device.createRfcommSocketToServiceRecord, device.createInsecureRfcommSocketToServiceRecord):
            sock = make(uuid)
            try:
                sock.connect()
                self.socket = sock
                break
            except Exception as err:  # noqa: BLE001 - JavaException: try the other kind
                last = err
                with contextlib.suppress(Exception):
                    sock.close()
        if self.socket is None:
            raise OSError(f"Could not connect to {_describe(device)}: {last}")
        self.input = self.socket.getInputStream()
        self.output = self.socket.getOutputStream()

    def read(self) -> bytes | None:
        """Bytes received (blocks until some come); None when the connection is gone."""
        buf = bytearray(READ_SIZE)
        try:
            n = self.input.read(buf, 0, READ_SIZE)
        except Exception:  # noqa: BLE001 - JavaException (IOException): the link dropped
            return None
        return bytes(buf[:n]) if n and n > 0 else None

    def write(self, data: bytes) -> None:
        self.output.write(bytearray(data), 0, len(data))
        self.output.flush()

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self.socket.close()


class _Writer:
    """Just enough of asyncio.StreamWriter for KissConnection: write, drain, close."""

    def __init__(self, port: BtSerial, stop: threading.Event) -> None:
        self._port, self._stop = port, stop
        self._pending = bytearray()

    def write(self, data: bytes) -> None:
        self._pending += data

    async def drain(self) -> None:
        if self._pending:
            data, self._pending = bytes(self._pending), bytearray()
            await asyncio.to_thread(self._port.write, data)

    def close(self) -> None:
        self._stop.set()
        self._port.close()  # unblocks the reading thread


async def open_bt(settings: TncSettings) -> Streams:
    await _permission()
    adapter = _adapter()
    if not adapter.isEnabled():
        raise OSError("Bluetooth is off: switch it on")
    devices = _paired(adapter)
    if not devices:
        raise OSError("No paired Bluetooth device: pair the TNC in Android's Bluetooth settings first")
    want = address_of(settings.device)
    device = next((d for d in devices if want and want.upper() in (d.getAddress().upper(), (d.getName() or "").upper())),
                  None)
    if device is None:
        raise OSError(f"The Bluetooth device {settings.device or '?'} is not paired")
    port = await asyncio.to_thread(BtSerial, adapter, device)
    _LOGGER.info("Bluetooth TNC connected: %s", _describe(device))

    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    stop = threading.Event()

    def pump() -> None:
        try:
            while not stop.is_set():
                chunk = port.read()
                if chunk is None:
                    if not stop.is_set():
                        loop.call_soon_threadsafe(reader.set_exception, ConnectionResetError("Bluetooth TNC gone"))
                    return
                loop.call_soon_threadsafe(reader.feed_data, chunk)
        except Exception as err:  # noqa: BLE001 - reported to the connection, which reconnects
            loop.call_soon_threadsafe(reader.set_exception, ConnectionError(str(err) or type(err).__name__))
        finally:
            port.close()
            with contextlib.suppress(Exception):
                _jnius().detach()

    threading.Thread(target=pump, name="aprs_kiss_bt", daemon=True).start()
    return reader, _Writer(port, stop)


def register() -> bool:
    """Offer the "bt" connection when running on Android."""
    if available():
        register_transport("bt", open_bt)
        return True
    return False
