"""The bundled offline map: the data is there and cities come in by zoom."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aprs_kiss_app import offline_map  # noqa: E402


class OfflineMapTest(unittest.TestCase):
    def test_data(self):
        d = offline_map.data()
        self.assertGreater(len(d["borders"]), 300)
        self.assertGreater(len(d["coast"]), 500)
        names = {c[0] for c in d["cities"]}
        for city in ("Prague", "Plzeň", "Brno", "Ostrava", "Vienna", "Berlin", "Bratislava"):
            self.assertIn(city, names)
        lat, lon = next((c[1], c[2]) for c in d["cities"] if c[0] == "Plzeň")
        self.assertAlmostEqual(lat, 49.74, delta=0.1)
        self.assertAlmostEqual(lon, 13.37, delta=0.1)

    def test_cities_by_zoom(self):
        counts = [len(offline_map.city_markers(level)) for level in range(len(offline_map.TIERS))]
        self.assertEqual(counts, sorted(set(counts)))  # strictly more at every step
        self.assertLess(counts[0], 80)
        all_ = counts[-1]
        self.assertEqual(offline_map.tier(3), 0)
        self.assertEqual(offline_map.tier(5), 1)
        self.assertEqual(offline_map.tier(7), 2)
        self.assertEqual(offline_map.tier(9), 3)
        layers = offline_map.OfflineLayers(3)
        self.assertFalse(layers.zoomed(3.5))
        self.assertTrue(layers.zoomed(8))
        self.assertEqual(len(layers.cities.markers), all_)


if __name__ == "__main__":
    unittest.main()
