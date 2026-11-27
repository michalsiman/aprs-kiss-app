import unittest

from aprs_kiss_core.drivedetect import SNOOZE_SECONDS, DriveDetector

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

    def test_not_again_within_the_hour_even_after_a_stop(self):
        d = DriveDetector()
        for t in range(0, 120, 5):
            d.update(t, LAT, LON, 50.0)
        for t in range(120, 1800, 30):
            d.update(t, LAT, LON, 0.0)  # a long stop
        self.assertFalse(any(d.update(t, LAT, LON, 50.0) for t in range(1800, SNOOZE_SECONDS - 100, 5)))

    def test_remembers_the_last_question(self):
        d = DriveDetector(asked_at=0)
        self.assertFalse(any(d.update(t, LAT, LON, 50.0) for t in range(100, 400, 5)))

    def test_asks_again_after_the_snooze(self):
        d = DriveDetector()
        for t in range(0, 120, 5):
            d.update(t, LAT, LON, 50.0)
        later = SNOOZE_SECONDS + 200
        self.assertTrue(any(d.update(t, LAT, LON, 50.0) for t in range(later, later + 60, 5)))


if __name__ == "__main__":
    unittest.main()
