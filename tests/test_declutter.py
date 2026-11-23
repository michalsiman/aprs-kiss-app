import math
import unittest

from aprs_kiss_app.declutter import CLOSE_X, CLOSE_Y, MAX_SHIFT, from_px, spread, to_px


def overlap(a, b, zoom):
    (ax, ay), (bx, by) = to_px(*a, zoom), to_px(*b, zoom)
    return abs(ax - bx) < CLOSE_X and abs(ay - by) < CLOSE_Y


def shift(a, b, zoom):
    (ax, ay), (bx, by) = to_px(*a, zoom), to_px(*b, zoom)
    return math.hypot(ax - bx, ay - by)


class DeclutterTest(unittest.TestCase):
    def test_pixels_round_trip(self):
        lat, lon = from_px(*to_px(49.7477, 13.3776, 12), 12)
        self.assertAlmostEqual(lat, 49.7477, places=6)
        self.assertAlmostEqual(lon, 13.3776, places=6)

    def test_same_place_is_spread_without_overlap(self):
        for n in range(2, 13):
            points = [(49.7, 13.4)] * n
            shown = spread(points, 14)
            self.assertTrue(all(p != points[0] for p in shown))  # the place is left for its dot
            for i in range(n):
                for j in range(i + 1, n):
                    self.assertFalse(overlap(shown[i], shown[j], 14), (n, i, j))

    def test_far_apart_stay_put(self):
        points = [(49.7, 13.4), (49.8, 13.6)]
        self.assertEqual(spread(points, 12), points)

    def test_zoomed_in_nothing_moves(self):
        points = [(49.7000, 13.4000), (49.7010, 13.4010)]
        self.assertNotEqual(spread(points, 10), points)
        self.assertEqual(spread(points, 7), points)  # a whole region on screen: nothing is moved
        self.assertEqual(spread(points, 18), points)

    def test_never_far_from_its_own_place(self):
        """A long chain of stations a little apart (a town zoomed out): nobody wanders off."""
        points = [(49.70 + 0.004 * k, 13.30 + 0.006 * k) for k in range(40)] + [(49.75, 13.37)] * 6
        for zoom in (9, 10, 11, 12):
            for a, b in zip(spread(points, zoom), points):
                self.assertLessEqual(shift(a, b, zoom), MAX_SHIFT + 0.5)

    def test_own_station_stays_and_others_go_around(self):
        for n in range(2, 10):
            points = [(49.7, 13.4)] * n
            shown = spread(points, 14, fixed=n - 1)
            self.assertEqual(shown[-1], points[-1])
            for i in range(n):
                for j in range(i + 1, n):
                    self.assertFalse(overlap(shown[i], shown[j], 14), (n, i, j))


if __name__ == "__main__":
    unittest.main()


class SharedPlaceTest(unittest.TestCase):
    def test_a_shared_place_is_left_free_for_the_dot(self):
        for n in (2, 3, 5):
            points = [(49.03, 14.0)] * n
            shown = spread(points, 13)
            for p in shown:
                self.assertNotEqual(p, points[0])  # nobody stays on the place
                self.assertFalse(overlap(p, points[0], 13))  # and nobody covers it
            for i in range(n):
                for j in range(i + 1, n):
                    self.assertFalse(overlap(shown[i], shown[j], 13))

    def test_own_station_still_stays(self):
        points = [(49.03, 14.0)] * 3
        shown = spread(points, 13, fixed=2)
        self.assertEqual(shown[2], points[2])
