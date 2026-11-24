import asyncio
import unittest

from aprs_kiss_core import ble, connection
from aprs_kiss_core.ax25 import kiss_frame
from aprs_kiss_core.connection import KissConnection, TncSettings


class FakeBackend:
    """A BLE KISS TNC that sends in 20-byte pieces, as over a link with the smallest MTU."""

    def __init__(self, ready=True):
        self._ready = ready
        self.written = bytearray()
        self.connected_to = None
        self.disconnects = 0
        self.on_data = self.on_lost = None

    async def ready(self):
        return self._ready

    async def scan(self, seconds):
        return [{"id": "11:22", "name": "Phone", "rssi": -40, "kiss": False},
                {"id": "AA:BB", "name": "LoRa Tracker", "rssi": -70, "kiss": True}]

    async def connect(self, device_id, on_data, on_lost):
        self.connected_to, self.on_data, self.on_lost = device_id, on_data, on_lost
        return {"mtu": 23}

    async def write(self, data):
        self.written += data

    async def disconnect(self):
        self.disconnects += 1

    def send(self, data: bytes):
        for i in range(0, len(data), 20):
            self.on_data(data[i:i + 20])


class BleTest(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        ble._backend = None
        ble.found.clear()

    def test_device_id(self):
        self.assertEqual(ble.device_id("LoRa Tracker (AA:BB:CC:DD:EE:FF)"), "AA:BB:CC:DD:EE:FF")
        self.assertEqual(ble.device_id("3F2504E0-4F89-11D3-9A0C-0305E82C3301"), "3F2504E0-4F89-11D3-9A0C-0305E82C3301")
        self.assertEqual(ble.device_id(""), "")

    async def test_scan_puts_kiss_devices_first(self):
        ble.set_backend(FakeBackend())
        self.assertEqual(await ble.scan(1), ["LoRa Tracker (AA:BB)", "Phone (11:22)"])
        self.assertEqual(ble.found[0], "LoRa Tracker (AA:BB)")

    async def test_not_available_without_backend_or_extension(self):
        self.assertFalse(await ble.available())
        ble.set_backend(FakeBackend(ready=False))
        self.assertFalse(await ble.available())
        with self.assertRaises(OSError):
            await ble.open_ble(TncSettings(kind="ble", device="X (AA:BB)"))

    async def test_frames_in_pieces_both_ways(self):
        backend = FakeBackend()
        ble.set_backend(backend)
        frames = []
        conn = KissConnection(TncSettings(kind="ble", device="LoRa Tracker (AA:BB)"), frames.append)
        await conn.start()
        for _ in range(50):
            if conn.connected:
                break
            await asyncio.sleep(0.01)
        self.assertTrue(conn.connected)
        self.assertEqual(backend.connected_to, "AA:BB")
        long_frame = bytes(range(1, 120))  # several pieces, and one more frame in the same stream
        backend.send(kiss_frame(long_frame) + kiss_frame(b"short"))
        await asyncio.sleep(0.05)
        self.assertEqual(frames, [long_frame, b"short"])
        await conn.send(b"to the radio")
        self.assertEqual(bytes(backend.written), kiss_frame(b"to the radio"))
        await conn.stop()

    async def test_a_lost_link_is_reconnected(self):
        backend = FakeBackend()
        ble.set_backend(backend)
        conn = KissConnection(TncSettings(kind="ble", device="AA:BB"), lambda f: None)
        old = connection.RECONNECT_MIN
        connection.RECONNECT_MIN = 0.05
        try:
            await conn.start()
            await asyncio.sleep(0.05)
            first = backend.on_lost
            first("Bluetooth LE link lost")
            await asyncio.sleep(0.3)
            self.assertTrue(conn.connected)
            self.assertIsNot(backend.on_lost, first)  # connected again
            self.assertGreaterEqual(backend.disconnects, 1)
        finally:
            connection.RECONNECT_MIN = old
            await conn.stop()


if __name__ == "__main__":
    unittest.main()
