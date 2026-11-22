"""USB GPS: NMEA parsing, reading a serial port (a pseudo-terminal here) and the engine's own position."""

import asyncio
import os
import pathlib
import sys
import tempfile
import time
import tty
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aprs_kiss_core import gps  # noqa: E402
from aprs_kiss_core.config import Config  # noqa: E402
from aprs_kiss_core.engine import Engine  # noqa: E402


def nmea(body: str) -> str:
    c = 0
    for ch in body:
        c ^= ord(ch)
    return f"${body}*{c:02X}"


RMC = nmea("GNRMC,153000.00,A,4937.2215,N,01309.7642,E,0.5,87.0,221126,,,A")
GGA = nmea("GNGGA,153000.00,4937.2215,N,01309.7642,E,1,09,0.9,412.3,M,45.0,M,,")
RMC_VOID = nmea("GPRMC,153001.00,V,,,,,,,221126,,,N")


class NmeaTest(unittest.TestCase):
    def test_checksum(self):
        self.assertTrue(gps.checksum_ok(RMC))
        self.assertFalse(gps.checksum_ok(RMC[:-1] + "0"))
        self.assertFalse(gps.checksum_ok("GNRMC,no dollar"))

    def test_fix(self):
        fix = gps.GpsFix()
        self.assertTrue(gps.parse_sentence(RMC, fix, now=100.0))
        self.assertTrue(gps.parse_sentence(GGA, fix, now=100.0))
        self.assertAlmostEqual(fix.latitude, 49.620358, places=5)
        self.assertAlmostEqual(fix.longitude, 13.162737, places=5)
        self.assertEqual((fix.satellites, fix.quality, fix.altitude_m), (9, 1, 412.3))
        self.assertEqual(fix.speed_kmh, 0.9)
        self.assertTrue(fix.usable(now=105.0))
        self.assertFalse(fix.usable(now=200.0))  # too old
        gps.parse_sentence(RMC_VOID, fix, now=106.0)
        self.assertFalse(fix.usable(now=106.0))  # lost the fix

    def test_south_west(self):
        fix = gps.GpsFix()
        gps.parse_sentence(nmea("GPRMC,000000,A,3352.1234,S,15112.5678,W,0,0,010126,,"), fix)
        self.assertLess(fix.latitude, 0)
        self.assertLess(fix.longitude, 0)


class ReaderTest(unittest.IsolatedAsyncioTestCase):
    async def test_reads_a_serial_port_and_finds_the_speed(self):
        master, slave = os.openpty()
        tty.setraw(slave)
        path = os.ttyname(slave)
        fixes, states = [], []
        reader = gps.GpsReader(path, 0, lambda f: fixes.append(f.latitude), lambda: states.append(1))

        async def feed():
            for _ in range(40):
                os.write(master, (RMC + "\r\n" + GGA + "\r\n").encode())
                await asyncio.sleep(0.05)

        feeder = asyncio.create_task(feed())
        await reader.start()
        for _ in range(60):
            if fixes:
                break
            await asyncio.sleep(0.05)
        await reader.stop()
        feeder.cancel()
        os.close(master)
        os.close(slave)
        self.assertTrue(fixes)
        self.assertAlmostEqual(fixes[-1], 49.620358, places=5)
        self.assertEqual(reader.speed, 9600)  # the first speed tried; a pty takes any


class EngineGpsTest(unittest.TestCase):
    def engine(self, **kw):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Engine(Config(callsign="OK1SIM-7", latitude=50.0, longitude=14.0, **kw).validate(), pathlib.Path(tmp.name))

    def test_typed_position_without_gps(self):
        eng = self.engine()
        self.assertIsNone(eng.gps)
        self.assertEqual(eng.my_position(), (50.0, 14.0))
        self.assertEqual(eng._position_comment("hi"), "hi")

    def test_gps_position_and_altitude(self):
        eng = self.engine(gps_source="usb", gps_device="/dev/ttyACM9")
        self.assertIsNotNone(eng.gps)
        self.assertEqual(eng.my_position(), (50.0, 14.0))  # no fix yet: the typed one
        now = time.time()
        gps.parse_sentence(RMC, eng.gps.fix, now)
        gps.parse_sentence(GGA, eng.gps.fix, now)
        lat, lon = eng.my_position()
        self.assertAlmostEqual(lat, 49.620358, places=5)
        self.assertEqual(eng._position_comment("KISS TNC app"), "/A=001353 KISS TNC app")  # 412.3 m
        self.assertTrue(eng.status()["gps"]["fix"])

    def test_gps_on_the_tnc_port_is_refused(self):
        eng = self.engine(gps_source="usb", gps_device="/dev/ttyACM1", connection="serial", device="/dev/ttyACM1")
        self.assertIsNone(eng.gps)
        self.assertIn("another port", eng.status()["gps"]["error"])


if __name__ == "__main__":
    unittest.main()
