import unittest

import aprslib

from aprs_kiss_core.aprs import MIC_E_STATUS, mic_e


def decode(dest, info):
    return aprslib.parse(f"OK1SIM-9>{dest},WIDE1-1:{info}")


class MicETest(unittest.TestCase):
    def test_round_trip(self):
        for lat, lon in ((49.74751, 13.37763), (-33.8688, 151.2093), (40.7128, -74.006), (51.5, -0.12),
                         (35.0, 105.5), (0.01, 179.99), (-12.5, -5.25)):
            dest, info = mic_e(lat, lon, "/>", "en_route", course=88, speed_kmh=50, altitude_m=350, comment="hi")
            p = decode(dest, info)
            self.assertAlmostEqual(p["latitude"], lat, delta=0.0002, msg=(lat, lon))
            self.assertAlmostEqual(p["longitude"], lon, delta=0.0002, msg=(lat, lon))
            self.assertEqual(p["course"], 88)
            self.assertAlmostEqual(p["speed"], 50, delta=1.9)  # whole knots
            self.assertEqual(p["altitude"], 350)
            self.assertEqual(p["symbol_table"] + p["symbol"], "/>")
            self.assertEqual(p["comment"], "hi")

    def test_statuses(self):
        for status, bits in MIC_E_STATUS.items():
            p = decode(*mic_e(49.7, 13.3, "/[", status))
            self.assertEqual(p["mbits"], bits, status)
        self.assertIn("Emergency", decode(*mic_e(49.7, 13.3, "/[", "emergency"))["mtype"])

    def test_standing_still(self):
        p = decode(*mic_e(49.7, 13.3, "/-", "off_duty", course=0, speed_kmh=0))
        self.assertEqual(p["speed"], 0)
        self.assertEqual(p["course"], 0)
        dest, info = mic_e(49.7, 13.3, "/-")
        self.assertEqual(len(dest), 6)
        self.assertLess(len(info), len("=4942.00N/01318.00E-"))


if __name__ == "__main__":
    unittest.main()
