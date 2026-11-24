import unittest

from aprs_kiss_core.geotext import find_positions, locator_to_position, write_position


class GeoTextTest(unittest.TestCase):
    def near(self, got, lat, lon):
        self.assertEqual(len(got), 1, got)
        self.assertAlmostEqual(got[0][0], lat, delta=0.001)
        self.assertAlmostEqual(got[0][1], lon, delta=0.001)

    def test_our_own_format_round_trip(self):
        self.near(find_positions(write_position(49.7475, 13.3776)), 49.7475, 13.3776)

    def test_decimal(self):
        self.near(find_positions("jsem na 49.7475, 13.3776 u Plzne"), 49.7475, 13.3776)
        self.near(find_positions("49.7475N 13.3776E"), 49.7475, 13.3776)
        self.near(find_positions("-33.8688, 151.2093"), -33.8688, 151.2093)

    def test_degrees_minutes_seconds(self):
        self.near(find_positions("49°44.85'N 13°22.66'E"), 49.7475, 13.3777)
        self.near(find_positions('49°44\'51"N 13°22\'39"E'), 49.7475, 13.3775)

    def test_aprs_and_locator(self):
        self.near(find_positions("pos 4944.85N/01322.66E ok"), 49.7475, 13.3777)
        lat, lon = locator_to_position("JO60UF")
        self.assertAlmostEqual(lat, 50.229, delta=0.01)
        self.assertAlmostEqual(lon, 13.708, delta=0.01)
        self.near(find_positions("loc jo60uf"), lat, lon)

    def test_locator_of_a_position_and_back(self):
        from aprs_kiss_core.geotext import position_to_locator
        self.assertEqual(position_to_locator(49.7475, 13.3776), "JN69QR")
        self.assertEqual(position_to_locator(50.229, 13.708), "JO60UF")
        lat, lon = locator_to_position(position_to_locator(-33.8688, 151.2093))
        self.assertAlmostEqual(lat, -33.8688, delta=0.05)
        self.assertAlmostEqual(lon, 151.2093, delta=0.05)
        self.near(find_positions("LOC JN69PS"), *locator_to_position("JN69PS"))

    def test_not_positions(self):
        for text in ("OK1SIM-7 145.800 MHz", "teplota 12.5, vlhkost 80", "verze 0.1.54", "438.725, 145.775",
                     "cas 12:30, 3 km", "OK1ABC"):
            self.assertEqual(find_positions(text), [], text)


if __name__ == "__main__":
    unittest.main()
