"""A TNC on the phone's USB port (USB OTG), for the Android app.

Android has no serial ports for apps: a USB serial adapter is driven through the USB host API
(UsbManager), reached from Python with pyjnius. Supported are CDC-ACM devices (the Quansheng
radios with the F4HWN KISS firmware, Arduino-style TNCs, most modern TNCs) and Silicon Labs
CP210x adapters (Digirig and many cables). The first time, Android asks the user to allow
the app to use the device.

Registered as the "usb" transport, so the KISS logic in connection.py stays the same.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import struct
import sys
import threading
import time

from .connection import Streams, TncSettings, register_transport

_LOGGER = logging.getLogger(__name__)

CDC_CONTROL, CDC_DATA = 0x02, 0x0A
VENDOR_CP210X = 0x10C4
DIR_IN = 0x80  # UsbConstants.USB_DIR_IN
XFER_BULK = 2  # UsbConstants.USB_ENDPOINT_XFER_BULK
PERMISSION_ACTION = "io.github.michalsiman.aprs_kiss_app.USB_PERMISSION"
PERMISSION_WAIT = 60.0  # seconds to wait for the user to answer Android's question
READ_TIMEOUT_MS = 200


def available() -> bool:
    """Running inside the Android app (where pyjnius and the activity exist)."""
    return bool(os.getenv("MAIN_ACTIVITY_HOST_CLASS_NAME")) or hasattr(sys, "getandroidapilevel")


def _jnius():
    import jnius  # noqa: PLC0415 - only on Android

    return jnius


def _activity():
    jnius = _jnius()
    host = os.getenv("MAIN_ACTIVITY_HOST_CLASS_NAME")
    if not host:
        raise OSError("The Android activity was not found")
    return jnius.autoclass(host).mActivity


def _usb_manager():
    jnius = _jnius()
    return jnius.cast("android.hardware.usb.UsbManager", _activity().getSystemService("usb"))


def _devices(manager) -> list:
    """The plugged-in USB devices that are serial ports we can drive."""
    jnius = _jnius()
    out = []
    for obj in manager.getDeviceList().values().toArray():
        device = jnius.cast("android.hardware.usb.UsbDevice", obj)
        if _pick(device):
            out.append(device)
    return out


def _endpoints(interface):
    bulk_in = bulk_out = None
    for i in range(interface.getEndpointCount()):
        ep = interface.getEndpoint(i)
        if ep.getType() != XFER_BULK:
            continue
        if ep.getDirection() == DIR_IN:
            bulk_in = bulk_in or ep
        else:
            bulk_out = bulk_out or ep
    return bulk_in, bulk_out


def _describe(device) -> str:
    name = device.getProductName() or device.getDeviceName()
    return f"{name} ({device.getVendorId():04x}:{device.getProductId():04x})"


def _pick(device):
    """(kind, control interface, data interface) when this device is a serial port we can drive."""
    control = data = None
    for i in range(device.getInterfaceCount()):
        itf = device.getInterface(i)
        cls = itf.getInterfaceClass()
        if cls == CDC_CONTROL and control is None:
            control = itf
        elif cls == CDC_DATA and data is None and all(_endpoints(itf)):
            data = itf
    if data is not None:
        return "cdc", control, data
    if device.getVendorId() == VENDOR_CP210X and device.getInterfaceCount():
        itf = device.getInterface(0)
        if all(_endpoints(itf)):
            return "cp210x", itf, itf
    return None


class UsbSerial:
    """One opened USB serial device; blocking calls, run from threads."""

    def __init__(self, manager, device, kind, control, data, baudrate: int) -> None:
        self.manager, self.device, self.kind = manager, device, kind
        self.name = device.getDeviceName()
        self.conn = manager.openDevice(device)
        if self.conn is None:
            raise OSError(f"Could not open {_describe(device)}")
        self.interfaces = [i for i in {id(x): x for x in (control, data) if x is not None}.values()]
        for itf in self.interfaces:
            if not self.conn.claimInterface(itf, True):
                self.close()
                raise OSError(f"{_describe(device)} is in use")
        self.control_index = (control or data).getId()
        self.ep_in, self.ep_out = _endpoints(data)
        self._setup(baudrate)

    def _ctrl(self, request_type: int, request: int, value: int, payload: bytes | None = None) -> None:
        buf = bytearray(payload) if payload else None
        self.conn.controlTransfer(request_type, request, value, self.control_index, buf, len(payload or b""), 1000)

    def _setup(self, baudrate: int) -> None:
        if self.kind == "cdc":
            # SET_LINE_CODING (baud, 1 stop bit, no parity, 8 bits), then DTR and RTS on
            self._ctrl(0x21, 0x20, 0, struct.pack("<IBBB", baudrate, 0, 0, 8))
            self._ctrl(0x21, 0x22, 0x03)
        else:  # CP210x: enable, 8N1, baud rate, DTR and RTS on
            self._ctrl(0x41, 0x00, 0x0001)
            self._ctrl(0x41, 0x03, 0x0800)
            self._ctrl(0x41, 0x1E, 0, struct.pack("<I", baudrate))
            self._ctrl(0x41, 0x07, 0x0303)

    def read(self) -> bytes | None:
        """Bytes received (b"" when nothing came within the timeout); None when the device is gone."""
        size = max(64, self.ep_in.getMaxPacketSize())
        buf = bytearray(size)
        n = self.conn.bulkTransfer(self.ep_in, buf, size, READ_TIMEOUT_MS)
        if n and n > 0:
            return bytes(buf[:n])
        return b"" if self.attached() else None

    def write(self, data: bytes) -> None:
        view = memoryview(data)
        while view:
            chunk = bytes(view[:4096])
            n = self.conn.bulkTransfer(self.ep_out, bytearray(chunk), len(chunk), 2000)
            if n is None or n < 0:
                raise ConnectionError("Writing to the USB TNC failed")
            view = view[n:]

    def attached(self) -> bool:
        with contextlib.suppress(Exception):
            return self.manager.getDeviceList().containsKey(self.name)
        return False

    def close(self) -> None:
        with contextlib.suppress(Exception):
            for itf in self.interfaces:
                self.conn.releaseInterface(itf)
            self.conn.close()


class _Writer:
    """Just enough of asyncio.StreamWriter for KissConnection: write, drain, close."""

    def __init__(self, port: UsbSerial, stop: threading.Event) -> None:
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


_last_request: dict[str, float] = {}


async def _permission(manager, device) -> None:
    """Ask Android for access to the device (once a minute at most) and wait for the answer."""
    if manager.hasPermission(device):
        return
    name = device.getDeviceName()
    if time.monotonic() - _last_request.get(name, -PERMISSION_WAIT) >= PERMISSION_WAIT:
        _last_request[name] = time.monotonic()
        jnius = _jnius()
        activity = _activity()
        intent = jnius.autoclass("android.content.Intent")(PERMISSION_ACTION)
        intent.setPackage(activity.getPackageName())
        pending = jnius.autoclass("android.app.PendingIntent")
        flags = 0x04000000  # FLAG_IMMUTABLE: we only look at hasPermission afterwards
        manager.requestPermission(device, pending.getBroadcast(activity, 0, intent, flags))
    deadline = time.monotonic() + PERMISSION_WAIT
    while time.monotonic() < deadline:
        await asyncio.sleep(0.5)
        if manager.hasPermission(device):
            return
    raise OSError(f"Not allowed to use {_describe(device)}: allow it when Android asks")


def list_devices() -> list[str]:
    """The USB serial devices plugged in now, for the settings."""
    if not available():
        return []
    with contextlib.suppress(Exception):
        return [_describe(d) for d in _devices(_usb_manager())]
    return []


async def open_usb(settings: TncSettings) -> Streams:
    manager = _usb_manager()
    devices = _devices(manager)
    if not devices:
        raise OSError("No USB TNC plugged in (an OTG adapter may be needed)")
    want = (settings.device or "").strip()
    device = next((d for d in devices if want and want in _describe(d)), devices[0])
    await _permission(manager, device)
    kind, control, data = _pick(device)
    port = await asyncio.to_thread(UsbSerial, manager, device, kind, control, data, settings.baudrate or 9600)
    _LOGGER.info("USB TNC opened: %s, %s", _describe(device), kind)

    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    stop = threading.Event()

    def pump() -> None:
        try:
            while not stop.is_set():
                chunk = port.read()
                if chunk is None:
                    loop.call_soon_threadsafe(reader.set_exception, ConnectionResetError("USB TNC unplugged"))
                    return
                if chunk:
                    loop.call_soon_threadsafe(reader.feed_data, chunk)
        except Exception as err:  # noqa: BLE001 - reported to the connection, which reconnects
            loop.call_soon_threadsafe(reader.set_exception, ConnectionError(str(err) or type(err).__name__))
        finally:
            port.close()
            with contextlib.suppress(Exception):
                _jnius().detach()

    threading.Thread(target=pump, name="aprs_kiss_usb", daemon=True).start()
    return reader, _Writer(port, stop)


def register() -> bool:
    """Offer the "usb" connection when running on Android."""
    if available():
        register_transport("usb", open_usb)
        return True
    return False
