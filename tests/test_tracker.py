import unittest

from aprs_kiss_core.tracker import PROFILES, Tracker, course_speed


class FixedTest(unittest.TestCase):
    def test_first_at_once_then_every_n_minutes(self):
        t = Tracker(mode="fixed", fixed_minutes=2)
        self.assertEqual(t.why(0, 0, None), "start")
        t.sent(0, None, (50, 14))
        self.assertIsNone(t.why(119, 50, 90))
        self.assertEqual(t.why(120, 50, 90), "time")


class SmartTest(unittest.TestCase):
    def setUp(self):
        self.t = Tracker(mode="smart", profile="car", still_minutes=60)
        self.t.sent(0, 90, (50.0, 14.0))

    def test_standing_still_once_an_hour(self):
        self.assertEqual(self.t.rate(0), 3600)
        self.assertIsNone(self.t.why(3599, 0, None, (50.0, 14.0)))
        self.assertEqual(self.t.why(3600, 0, None, (50.0, 14.0)), "time")

    def test_faster_means_more_often(self):
        p = PROFILES["car"]
        self.assertEqual(self.t.rate(120), p.fast_rate)
        self.assertEqual(self.t.rate(p.fast_speed), p.fast_rate)
        self.assertEqual(self.t.rate(45), p.fast_rate * p.fast_speed / 45)
        self.assertEqual(self.t.rate(10), p.slow_rate)
        self.assertLess(self.t.rate(80), self.t.rate(30))

    def test_corner_pegging(self):
        p = PROFILES["car"]
        # 50 km/h: threshold 10 + 80/50 = 11.6 degrees
        self.assertIsNone(self.t.why(p.turn_time - 1, 50, 180))  # too soon after the last one
        self.assertEqual(self.t.why(p.turn_time, 50, 180), "turn")
        self.assertIsNone(self.t.why(p.turn_time, 50, 95))  # a small bend
        self.assertEqual(self.t.why(p.turn_time, 50, 350), "turn")  # across north: 100 degrees

    def test_moved_without_speed(self):
        p = PROFILES["car"]
        self.assertEqual(self.t.why(p.slow_rate, None, None, (50.02, 14.0)), "moved")
        self.assertIsNone(self.t.why(p.slow_rate, None, None, (50.001, 14.0)))


class CourseSpeedTest(unittest.TestCase):
    def test_extension(self):
        self.assertEqual(course_speed(88.4, 66.7), "088/036")
        self.assertEqual(course_speed(0, 50), "360/027")  # north is 360, 000 means unknown
        self.assertEqual(course_speed(90, 0.5), "")
        self.assertEqual(course_speed(None, 50), "")


if __name__ == "__main__":
    unittest.main()


class EngineTrackerTest(unittest.IsolatedAsyncioTestCase):
    async def test_tracker_sends_gps_position_only_when_it_can(self):
        import pathlib
        import tempfile
        from unittest import mock

        from aprs_kiss_core.config import Config
        from aprs_kiss_core.engine import Engine

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        eng = Engine(Config(callsign="OK1SIM-7", gps_source="phone", tracker_minutes=2).validate(),
                     pathlib.Path(tmp.name))
        sent = []
        eng.station.send_position = mock.AsyncMock(side_effect=lambda *a, **k: sent.append(a))
        self.assertIsNone(await eng.tracker_tick(1000))  # off
        eng.set_tracking(True)
        self.assertIsNone(await eng.tracker_tick(1000))  # no GPS yet
        eng.gps.push(49.75, 13.38, speed_ms=15.0, course=88.0)
        self.assertIsNone(await eng.tracker_tick(1000))  # transmitting is off
        eng.station.tx_enabled = True
        self.assertEqual(await eng.tracker_tick(1000), "start")
        self.assertEqual(sent[-1][:2], (49.75, 13.38))
        self.assertTrue(sent[-1][2].startswith("088/029"))  # course and speed (54 km/h = 29 kn)
        self.assertIsNone(await eng.tracker_tick(1060))
        self.assertEqual(await eng.tracker_tick(1120), "time")
        eng.set_tracking(False)
        self.assertIsNone(await eng.tracker_tick(5000))
        self.assertEqual(len(sent), 2)


class SendNowTest(unittest.IsolatedAsyncioTestCase):
    async def test_position_now_follows_the_aprsis_switch(self):
        import pathlib
        import tempfile
        from unittest import mock

        from aprs_kiss_core.config import Config
        from aprs_kiss_core.engine import Engine

        for on in (False, True):
            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            eng = Engine(Config(callsign="OK1SIM-7", latitude=49.7, longitude=13.4, beacon_is=on).validate(),
                         pathlib.Path(tmp.name))
            eng.station.send_position = mock.AsyncMock()
            await eng.send_position()
            self.assertEqual(eng.station.send_position.call_args.kwargs["to_is"], on)
