"""QRZ.com links: the base callsign only, nothing for objects and service names."""

import unittest

try:
    import flet  # noqa: F401
except ImportError:  # the CI tests the core without the UI
    raise unittest.SkipTest("flet is not installed")

from aprs_kiss_app.app import qrz_url  # noqa: E402


class QrzTest(unittest.TestCase):
    def test_base_callsign(self):
        self.assertEqual(qrz_url("OK5TVR-6"), "https://www.qrz.com/db/OK5TVR")
        self.assertEqual(qrz_url("dl1abc/p"), "https://www.qrz.com/db/DL1ABC")
        self.assertEqual(qrz_url("F/OK1SIM"), "https://www.qrz.com/db/OK1SIM")
        self.assertEqual(qrz_url("9A2XY"), "https://www.qrz.com/db/9A2XY")

    def test_not_a_callsign(self):
        for name in ("REPEAT", "438.725BR", "OK1PNK B", "WXBOT", "ANSRVR"):
            self.assertIsNone(qrz_url(name), name)


if __name__ == "__main__":
    unittest.main()
