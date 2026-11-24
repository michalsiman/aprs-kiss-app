import unittest

from aprs_kiss_core.drivedetect import SNOOZE_SECONDS, STILL_SECONDS, DriveDetector

LAT, LON = 50.0, 14.0


class DriveTest(unittest.TestCase):
    def test_a_minute_at_speed_asks_once(self):
        d = DriveDetector()
        asked = [d.update(t, LAT, LON + t * 0.00001, 40.0) for t in range(0, 120, 5)]  # speed, little distance
        self.assertEqual(asked.count(True), 1)
        self.assertGreaterEqual(asked.index(True) * 5, 60)

    def test_walking_or_a_jumpy_fix_does_not(self):
        d = DriveDetector()
        self.assertFalse(any(d.update(t, LAT, LON + (t % 2) * 0.0002, 4.0) for t in range(0, 600, 5)))

    def test_no_speed_but_distance(self):
        d = DriveDetector()
        self.assertTrue(any(d.update(t, LAT + t * 0.00004, LON, None) for t in range(0, 180, 5)))

    def test_new_trip_after_standing_still(self):
        d = DriveDetector()
        for t in range(0, 120, 5):
            d.update(t, LAT, LON, 50.0)
        self.assertFalse(any(d.update(t, LAT, LON, 50.0) for t in range(120, 600, 5)))  # the same trip
        for t in range(600, 600 + STILL_SECONDS + 30, 30):
            d.update(t, LAT, LON, 0.0)
        start = 600 + STILL_SECONDS + 60
        self.assertTrue(any(d.update(t, LAT, LON, 50.0) for t in range(start, start + 120, 5)))

    def test_asks_again_after_the_snooze(self):
        d = DriveDetector()
        for t in range(0, 120, 5):
            d.update(t, LAT, LON, 50.0)
        later = SNOOZE_SECONDS + 200
        self.assertTrue(any(d.update(t, LAT, LON, 50.0) for t in range(later, later + 60, 5)))


if __name__ == "__main__":
    unittest.main()
