"""The bundled offline map: the data is there and cities come in by zoom."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import json  # noqa: E402

try:
    from aprs_kiss_app import offline_map  # needs flet
except ImportError:
    offline_map = None

DATA = pathlib.Path(__file__).resolve().parents[1] / "src/aprs_kiss_app/offline/world.json"


class OfflineMapTest(unittest.TestCase):
    def test_data(self):
        d = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertGreater(len(d["borders"]), 300)
        self.assertGreater(len(d["coast"]), 500)
        names = {c[0] for c in d["cities"]}
        for city in ("Prague", "Plzeň", "Brno", "Ostrava", "Vienna", "Berlin", "Bratislava"):
            self.assertIn(city, names)
        lat, lon = next((c[1], c[2]) for c in d["cities"] if c[0] == "Plzeň")
        self.assertAlmostEqual(lat, 49.74, delta=0.1)
        self.assertAlmostEqual(lon, 13.37, delta=0.1)

    @unittest.skipIf(offline_map is None, "flet is not installed")
    def test_cities_by_zoom(self):
        counts = [len(offline_map.city_markers(level)) for level in range(len(offline_map.TIERS))]
        self.assertEqual(counts, sorted(set(counts)))  # strictly more at every step
        self.assertLess(counts[0], 80)
        all_ = counts[-1]
        self.assertEqual(offline_map.tier(3), 0)
        self.assertEqual(offline_map.tier(5), 1)
        self.assertEqual(offline_map.tier(7), 2)
        self.assertEqual(offline_map.tier(9), 3)
        layers = offline_map.OfflineLayers(49.7, 13.4, 3)  # the whole world
        self.assertEqual(len(layers.cities.markers), counts[0])
        self.assertFalse(layers.moved(20, -60, 3.2))
        self.assertTrue(layers.moved(49.7, 13.4, 9))  # zoomed in: all cities, but only around Plzeň
        self.assertLess(len(layers.cities.markers), all_ / 5)
        names = {m.content.controls[1].value for m in layers.cities.markers}
        self.assertIn("Prague", names)
        self.assertNotIn("Madrid", names)

    @unittest.skipIf(offline_map is None, "flet is not installed")
    def test_region(self):
        """Zoomed in, only a box around the middle goes to the screen, and much fewer points."""
        d = offline_map.data()
        everything = sum(map(len, d["borders"])) + sum(map(len, d["coast"]))
        near = offline_map.Region.around(49.7, 13.4, 9)
        self.assertTrue(near.contains(50.08, 14.43))  # Prague, ~90 km
        self.assertFalse(near.contains(40.4, -3.7))  # Madrid
        self.assertGreater(near.north - near.south, 5)  # at least ~300 km each way
        points = sum(map(len, offline_map.clip(d["borders"] + d["coast"], near)))
        self.assertLess(points, everything / 20)
        self.assertTrue(near.covers(49.9, 13.6, 9.2))  # a short pan: nothing new
        self.assertFalse(near.covers(49.7, 13.4, 11))  # zoomed: finer lines
        self.assertFalse(near.covers(53.5, 13.4, 9))  # far away
        world = offline_map.Region.around(49.7, 13.4, 3)
        self.assertTrue(world.contains(-33.9, 151.2))
        self.assertLess(sum(map(len, offline_map.clip(d["coast"], world))), sum(map(len, d["coast"])) / 2)

    def test_scale_bar(self):
        if offline_map is None:
            self.skipTest("flet is not installed")
        self.assertEqual(offline_map.ScaleBar.pick(10, 90), (500, 50))  # 10 m/px: 500 m in 50 px
        self.assertEqual(offline_map.ScaleBar.pick(100, 90)[0], 5000)
        self.assertEqual(offline_map.ScaleBar.pick(30, 90)[0], 2000)
        bar = offline_map.ScaleBar()
        bar.show(49.7, 10)  # Plzeň, zoom 10: about 98 m per pixel
        self.assertEqual(bar.label.value, "5 km")
        bar.show(49.7, 16)
        self.assertEqual(bar.label.value, "100 m")

    def test_clip_line_reaches_the_edge(self):
        if offline_map is None:
            self.skipTest("flet is not installed")
        region = offline_map.Region(0, 10, 0, 10, 0.01, 5)
        pieces = offline_map.clip([[[5, -5], [5, 5], [5, 15], [5, 25]]], region)
        self.assertEqual(pieces, [[[5, -5], [5, 5], [5, 15]]])


if __name__ == "__main__":
    unittest.main()
