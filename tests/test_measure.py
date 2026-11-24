import unittest

try:
    import flet  # noqa: F401
except ImportError:  # the CI tests the core without the UI
    raise unittest.SkipTest("flet is not installed")

from aprs_kiss_app.views.base import bearing_deg, distance_km, distance_text


class MeasureTest(unittest.TestCase):
    def test_distance_and_direction(self):
        # Plzeň -> Praha: about 85 km to the east-north-east
        km = distance_km(49.7477, 13.3776, 50.0755, 14.4378)
        self.assertAlmostEqual(km, 84.9, delta=1.0)
        self.assertAlmostEqual(bearing_deg(49.7477, 13.3776, 50.0755, 14.4378), 64, delta=2)
        self.assertAlmostEqual(bearing_deg(50.0, 14.0, 51.0, 14.0), 0, delta=0.01)
        self.assertAlmostEqual(bearing_deg(50.0, 14.0, 49.0, 14.0), 180, delta=0.01)

    def test_text(self):
        self.assertEqual(distance_text(0.4567), "457 m")
        self.assertEqual(distance_text(3.456), "3.46 km")
        self.assertEqual(distance_text(33.71), "33.7 km")
        self.assertEqual(distance_text(345.6), "346 km")


if __name__ == "__main__":
    unittest.main()
