import unittest

from aprs_kiss_core.mapfilter import shown
from aprs_kiss_core.repeater import frequency, is_repeater, label


def e(call="OK0X", table="/", symbol="r", comment="", **kw):
    d = {"call": call, "symbol_table": table, "symbol": symbol, "comment": comment}
    d.update(kw)
    return d


class RepeaterTest(unittest.TestCase):
    def test_object_named_after_frequency(self):
        r = e("439.350MO", comment="439.350MHz T088 -760 OK0X Praded TV Tower, FM + DMR CC1", object_of="OK2JIB-2")
        self.assertTrue(is_repeater(r))
        self.assertEqual(label(r), "439.350 · 70 cm · DMR")

    def test_echolink_and_dstar_objects(self):
        svx = e("ER-OK0EB", "E", "0", "439.175MHz T077 R18k OK0EB Klet www.ok1ocb.cz", object_of="OK0EB")
        self.assertEqual(label(svx), "439.175 · 70 cm")
        dstar = e("OK0PI  B", "D", "a", "RNG0000 440 Voice 439.27500MHz -7.6000MHz", object_of="OK0PI-S")
        self.assertEqual(label(dstar), "439.275 · 70 cm")
        dv = e("OE3XVJ B", "D", "a", "RNG0001/A=000010 70cm Voice (D-Star) 438.22500MHz -7.6000MHz", object_of="X")
        self.assertEqual(label(dv), "438.225 · 70 cm · D-Star")

    def test_two_metres_and_odd_steps(self):
        self.assertEqual(label(e(comment="145.6625MHz -600 T088")), "145.6625 · 2 m")
        self.assertEqual(frequency(e(comment="145.600MHz")), 145.6)

    def test_mobile_with_qsy_frequency_is_not_a_repeater(self):
        self.assertFalse(is_repeater(e("SP3VZM-9", "/", "u", "145.500MHz/A=000458 APRSdroid")))
        self.assertFalse(is_repeater(e("SP3DAF-9", "/", ">", "439.200MHz T110 -760 Op. Mikolaj")))
        self.assertFalse(is_repeater(e("OK1ABC", "/", "-", "QTH 145.500MHz")))  # a house listening there
        self.assertIsNone(label(e("OK1ABC", "/", "-", "QTH 145.500MHz")))

    def test_repeater_symbol_without_frequency(self):
        r = e("OK0ABC", comment="Repeater Praha")
        self.assertTrue(is_repeater(r))
        self.assertIsNone(label(r))
        self.assertTrue(shown(r, {"repeater"}, 0))
        self.assertFalse(shown(e("OK1ABC", "/", "-"), {"repeater"}, 0))


if __name__ == "__main__":
    unittest.main()
