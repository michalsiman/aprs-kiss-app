import unittest

from aprs_kiss_core.spotting import Spot, SpotError, build, mhz


class SpottingTest(unittest.TestCase):
    def test_aprs2sota(self):
        to, text = build(Spot("SOTA", "ok/pl-001", "145.500", "fm", "CQ SOTA"), "OK1SIM-7")
        self.assertEqual(to, "APRS2SOTA")
        self.assertEqual(text, "OK/PL-001 145.5 FM OK1SIM CQ SOTA")

    def test_apspot(self):
        self.assertEqual(build(Spot("POTA", "CZ-0001", "7144", "SSB", "cq"), "OK1SIM-7"),
                         ("APSPOT", "! POTA CZ-0001 7.144 SSB cq"))
        self.assertEqual(build(Spot("WWFF", "OKFF-0001", "7.032", "CW"), "OK1SIM")[1], "! WWFF OKFF-0001 7.032 CW")
        self.assertEqual(build(Spot("SOTA", "OK/PL-001", "7.032", "CW", gateway="APSPOT"), "OK1SIM")[0], "APSPOT")

    def test_modes_and_test(self):
        self.assertIn(" DATA", build(Spot("POTA", "CZ-0001", "14.074", "FT8"), "OK1SIM")[1])
        self.assertEqual(build(Spot("POTA", "CZ-0001", "7.1", "SSB", "hi", test=True), "OK1SIM")[1],
                         "! POTA CZ-0001 7.1 SSB aptest hi")
        self.assertTrue(build(Spot("SOTA", "OK/PL-001", "7.1", "SSB", test=True), "OK1SIM")[1].endswith("TEST"))

    def test_fits_one_message(self):
        _to, text = build(Spot("SOTA", "OK/PL-001", "145.500", "FM", "x" * 100), "OK1SIM")
        self.assertEqual(len(text), 67)

    def test_wrong(self):
        with self.assertRaises(SpotError) as e:
            build(Spot("SOTA", "PL-001", "7.1", "SSB"), "OK1SIM")
        self.assertEqual((e.exception.code, e.exception.example), ("spot_bad_ref", "OK/PL-001"))
        with self.assertRaises(SpotError):
            mhz("abc")
        self.assertEqual(mhz("7031.2k"), "7.0312")
        self.assertEqual(mhz("144,320"), "144.32")


if __name__ == "__main__":
    unittest.main()
