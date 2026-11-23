"""The Android USB serial driver, against stand-ins for Android's USB host classes."""

import struct
import unittest

from aprs_kiss_core import android_usb as au


class Endpoint:
    def __init__(self, direction, packet=64):
        self.direction, self.packet = direction, packet

    def getType(self):
        return au.XFER_BULK

    def getDirection(self):
        return self.direction

    def getMaxPacketSize(self):
        return self.packet


class Interface:
    def __init__(self, ident, cls, endpoints=()):
        self.ident, self.cls, self.endpoints = ident, cls, list(endpoints)

    def getId(self):
        return self.ident

    def getInterfaceClass(self):
        return self.cls

    def getEndpointCount(self):
        return len(self.endpoints)

    def getEndpoint(self, i):
        return self.endpoints[i]


class Device:
    def __init__(self, vendor, interfaces):
        self.vendor, self.interfaces = vendor, interfaces

    def getVendorId(self):
        return self.vendor

    def getProductId(self):
        return 1

    def getProductName(self):
        return "Test TNC"

    def getDeviceName(self):
        return "/dev/bus/usb/001/002"

    def getInterfaceCount(self):
        return len(self.interfaces)

    def getInterface(self, i):
        return self.interfaces[i]


class Connection:
    def __init__(self, incoming=b""):
        self.control, self.written, self.incoming = [], b"", incoming

    def claimInterface(self, itf, force):
        return True

    def releaseInterface(self, itf):
        return True

    def close(self):
        pass

    def controlTransfer(self, rtype, request, value, index, buf, length, timeout):
        self.control.append((rtype, request, value, index, bytes(buf) if buf else b""))
        return length

    def bulkTransfer(self, ep, buf, length, timeout):
        if ep.getDirection() == au.DIR_IN:
            data, self.incoming = self.incoming[:length], self.incoming[length:]
            buf[:len(data)] = data
            return len(data) or -1
        self.written += bytes(buf[:length])
        return length


class DeviceMap:
    def containsKey(self, name):
        return True


class Manager:
    def __init__(self, conn):
        self.conn = conn

    def openDevice(self, device):
        return self.conn

    def getDeviceList(self):
        return DeviceMap()


def cdc_device():
    return Device(0x36B7, [Interface(0, au.CDC_CONTROL),
                           Interface(1, au.CDC_DATA, [Endpoint(au.DIR_IN), Endpoint(0)])])


class AndroidUsbTest(unittest.TestCase):
    def test_pick(self):
        self.assertEqual(au._pick(cdc_device())[0], "cdc")
        ftdi = Device(au.VENDOR_FTDI, [Interface(0, 0xFF, [Endpoint(au.DIR_IN), Endpoint(0)])])
        self.assertEqual(au._pick(ftdi)[0], "ftdi")
        self.assertIsNone(au._pick(Device(0x1234, [Interface(0, 3)])))  # a keyboard, say

    def test_cdc_setup_read_write(self):
        conn = Connection(incoming=b"\xc0\x00abc\xc0")
        dev = cdc_device()
        port = au.UsbSerial(Manager(conn), dev, *au._pick(dev), 9600)
        self.assertIn((0x21, 0x20, 0, 0, struct.pack("<IBBB", 9600, 0, 0, 8)), conn.control)
        self.assertIn((0x21, 0x22, 3, 0, b""), conn.control)
        self.assertEqual(port.read(), b"\xc0\x00abc\xc0")
        self.assertEqual(port.read(), b"")  # nothing more: still attached
        port.write(b"\xc0\x00hello\xc0")
        self.assertEqual(conn.written, b"\xc0\x00hello\xc0")

    def test_ftdi_strips_status_bytes(self):
        packet = 8
        payload = b"0123456789"  # 6 per packet after the two status bytes
        wire = b"\x01\x60" + payload[:6] + b"\x01\x60" + payload[6:]
        conn = Connection(incoming=wire)
        dev = Device(au.VENDOR_FTDI, [Interface(0, 0xFF, [Endpoint(au.DIR_IN, packet), Endpoint(0, packet)])])
        port = au.UsbSerial(Manager(conn), dev, *au._pick(dev), 9600)
        self.assertIn((0x40, 0x03, 0x4138, 0, b""), conn.control)  # 9600 Bd
        got = b""
        while chunk := port.read():
            got += chunk
        self.assertEqual(got, payload)

    def test_ftdi_divisor(self):
        self.assertEqual(au.ftdi_divisor(9600), (0x4138, 0))
        self.assertEqual(au.ftdi_divisor(115200), (0x1A, 0))
        self.assertEqual(au.ftdi_divisor(38400), (0xC04E, 0))


if __name__ == "__main__":
    unittest.main()
