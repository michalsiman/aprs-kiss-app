import unittest

from aprs_kiss_core.geotext import find_callsigns, resolve_callsign


class MentionsTest(unittest.TestCase):
    def test_callsigns_in_a_text(self):
        self.assertEqual(find_callsigns("OK6DJ-6 11/25 08:37 7.52km WSW 24F 89% 1020.1mbar"), ["OK6DJ-6"])
        self.assertEqual(find_callsigns("OK1FRN-12 Wind 275@0 Rain1h 0.0"), ["OK1FRN-12"])
        self.assertEqual(find_callsigns("ahoj ok1abc, pozdrav od G4XYZ a 2E0ABC, i OK1ABC"),
                         ["OK1ABC", "G4XYZ", "2E0ABC"])
        self.assertEqual(find_callsigns("nearest"), [])
        self.assertEqual(find_callsigns("145.500 MHz, 7.52km, 1020mbar, QTH JO70XQ"), [])  # a locator is no callsign

    def test_resolve(self):
        heard = {"OK1FRN-12": {"latitude": 49.8, "longitude": 13.3, "last_heard": 10},
                 "OK1FRN-9": {"latitude": 49.9, "longitude": 13.4, "last_heard": 20},
                 "OK1XX": {"last_heard": 30}}
        self.assertEqual(resolve_callsign("OK1FRN-12", heard), "OK1FRN-12")
        self.assertEqual(resolve_callsign("OK1FRN", heard), "OK1FRN-9")  # the most recently heard
        self.assertIsNone(resolve_callsign("OK1FRN-5", heard))
        self.assertIsNone(resolve_callsign("OK1XX", heard))  # no position



class PlaceLinksTest(unittest.TestCase):
    def test_links(self):
        from aprs_kiss_core.geotext import place_links
        links = place_links(49.89049, 13.38598, "WARN3166")
        self.assertEqual(links["geo"], "geo:49.89049,13.38598?q=49.89049,13.38598(WARN3166)")
        self.assertTrue(links["apple"].startswith("https://maps.apple.com/?daddr=49.89049,13.38598"))
        self.assertIn("mlat=49.89049&mlon=13.38598", links["osm"])
        self.assertTrue(links["text"].startswith("WARN3166: 49.89049, 13.38598 (JN69QV)"))
        self.assertEqual(place_links(50, 14)["geo"], "geo:50.00000,14.00000?q=50.00000,14.00000")


if __name__ == "__main__":
    unittest.main()
