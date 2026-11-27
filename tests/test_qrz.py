"""QRZ.com links: the base callsign only, nothing for objects and service names."""

import unittest

try:
    import flet  # noqa: F401
except ImportError:  # the CI tests the core without the UI
    raise unittest.SkipTest("flet is not installed")

from aprs_kiss_app.app import callbook_links, qrz_url  # noqa: E402


class QrzTest(unittest.TestCase):
    def test_base_callsign(self):
        self.assertEqual(qrz_url("OK5TVR-6"), "https://www.qrz.com/db/OK5TVR")
        self.assertEqual(qrz_url("dl1abc/p"), "https://www.qrz.com/db/DL1ABC")
        self.assertEqual(qrz_url("F/OK1SIM"), "https://www.qrz.com/db/OK1SIM")
        self.assertEqual(qrz_url("9A2XY"), "https://www.qrz.com/db/9A2XY")

    def test_callbooks(self):
        self.assertEqual(callbook_links("OK1SIM-7"), [
            ("QRZ.com", "https://www.qrz.com/db/OK1SIM"),
            ("HamQTH", "https://www.hamqth.com/OK1SIM"),
            ("QRZCQ", "https://www.qrzcq.com/call/OK1SIM"),
            ("aprs.fi", "https://aprs.fi/#!call=a%2FOK1SIM-7"),
        ])
        self.assertEqual(callbook_links("REPEAT"), [])

    def test_not_a_callsign(self):
        for name in ("REPEAT", "438.725BR", "OK1PNK B", "WXBOT", "ANSRVR"):
            self.assertIsNone(qrz_url(name), name)


if __name__ == "__main__":
    unittest.main()
