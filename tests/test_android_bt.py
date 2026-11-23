"""The Android Bluetooth (SPP) driver, against stand-ins for Android's Bluetooth classes."""

import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aprs_kiss_core import android_bt as bt  # noqa: E402


class Stream:
    def __init__(self, data=b""):
        self.data, self.written = data, b""

    def read(self, buf, off, length):
        chunk, self.data = self.data[:length], self.data[length:]
        buf[off:off + len(chunk)] = chunk
        return len(chunk) or -1

    def write(self, buf, off, length):
        self.written += bytes(buf[off:off + length])

    def flush(self):
        pass


class Socket:
    def __init__(self, ok=True, data=b""):
        self.ok, self.closed = ok, False
        self.inp, self.out = Stream(data), Stream()

    def connect(self):
        if not self.ok:
            raise RuntimeError("read failed, socket might closed")

    def getInputStream(self):
        return self.inp

    def getOutputStream(self):
        return self.out

    def close(self):
        self.closed = True


class Device:
    def __init__(self, secure_ok=True, data=b""):
        self.secure = Socket(secure_ok, data)
        self.insecure = Socket(True, data)

    def createRfcommSocketToServiceRecord(self, uuid):
        return self.secure

    def createInsecureRfcommSocketToServiceRecord(self, uuid):
        return self.insecure

    def getName(self):
        return "TNC3"

    def getAddress(self):
        return "00:11:22:33:44:55"


class UUID:
    @staticmethod
    def fromString(text):
        return text


class Jnius:
    @staticmethod
    def autoclass(name):
        return UUID


class Adapter:
    def cancelDiscovery(self):
        pass


class AndroidBtTest(unittest.TestCase):
    def test_address(self):
        self.assertEqual(bt.address_of("TNC3 (00:11:22:33:44:55)"), "00:11:22:33:44:55")
        self.assertEqual(bt.address_of("00:11:22:33:44:55"), "00:11:22:33:44:55")

    def test_read_write(self):
        with mock.patch.object(bt, "_jnius", return_value=Jnius):
            port = bt.BtSerial(Adapter(), Device(data=b"\xc0\x00abc\xc0"))
        self.assertEqual(port.read(), b"\xc0\x00abc\xc0")
        self.assertIsNone(port.read())  # the stream ended: the link is gone
        port.write(b"\xc0\x00hi\xc0")
        self.assertEqual(port.output.written, b"\xc0\x00hi\xc0")

    def test_insecure_fallback(self):
        dev = Device(secure_ok=False)
        with mock.patch.object(bt, "_jnius", return_value=Jnius):
            port = bt.BtSerial(Adapter(), dev)
        self.assertIs(port.socket, dev.insecure)
        self.assertTrue(dev.secure.closed)


if __name__ == "__main__":
    unittest.main()
