import unittest

from aprs_kiss_app.declutter import CLOSE_X, CLOSE_Y, from_px, groups, spread, to_px


def overlap(a, b, zoom):
    (ax, ay), (bx, by) = to_px(*a, zoom), to_px(*b, zoom)
    return abs(ax - bx) < CLOSE_X and abs(ay - by) < CLOSE_Y


class DeclutterTest(unittest.TestCase):
    def test_pixels_round_trip(self):
        lat, lon = from_px(*to_px(49.7477, 13.3776, 12), 12)
        self.assertAlmostEqual(lat, 49.7477, places=6)
        self.assertAlmostEqual(lon, 13.3776, places=6)

    def test_same_place_is_spread_without_overlap(self):
        for n in range(2, 13):
            points = [(49.7, 13.4)] * n
            shown = spread(points, 14)
            for i in range(n):
                for j in range(i + 1, n):
                    self.assertFalse(overlap(shown[i], shown[j], 14), (n, i, j))

    def test_far_apart_stay_put(self):
        points = [(49.7, 13.4), (49.8, 13.6)]
        self.assertEqual(spread(points, 12), points)

    def test_zooming_in_separates_the_group(self):
        points = [(49.7000, 13.4000), (49.7005, 13.4005), (49.9, 14.0)]
        self.assertEqual(groups(points, 10), [[0, 1]])
        self.assertEqual(groups(points, 18), [])

    def test_chain_of_close_points_is_one_group(self):
        points = [(49.7, 13.4), (49.7, 13.4002), (49.7, 13.4004)]
        self.assertEqual(groups(points, 13), [[0, 1, 2]])


if __name__ == "__main__":
    unittest.main()


class FixedTest(unittest.TestCase):
    def test_own_station_stays_and_others_circle_around(self):
        for n in range(2, 10):
            points = [(49.7, 13.4)] * n
            shown = spread(points, 14, fixed=n - 1)
            self.assertEqual(shown[-1], points[-1])
            for i in range(n):
                for j in range(i + 1, n):
                    self.assertFalse(overlap(shown[i], shown[j], 14), (n, i, j))
