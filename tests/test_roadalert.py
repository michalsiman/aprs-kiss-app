import unittest

from aprs_kiss_core.config import Config
from aprs_kiss_core.roadalert import REPEAT_SECONDS, RoadAlerts, ahead, heading

NOW = 1_000_000.0
LAT, LON = 50.0, 14.0
KM_LAT = 1 / 111.195  # one km north in degrees


def incident(call, dnorth_km, deast_km, symbol="'", table="\\", age=60):
    import math
    return {"call": call, "symbol_table": table, "symbol": symbol, "last_heard": NOW - age,
            "latitude": LAT + dnorth_km * KM_LAT,
            "longitude": LON + deast_km * KM_LAT / math.cos(math.radians(LAT))}


class CorridorTest(unittest.TestCase):
    def test_straight_ahead_behind_and_aside(self):
        north = 0.0
        self.assertAlmostEqual(ahead(LAT, LON, north, LAT + 3 * KM_LAT, LON, 5)[0], 3, places=2)
        self.assertIsNone(ahead(LAT, LON, north, LAT - 3 * KM_LAT, LON, 5))  # behind
        self.assertIsNone(ahead(LAT, LON, north, LAT + 8 * KM_LAT, LON, 5))  # too far
        self.assertIsNone(incident_ahead(1, 3))  # 1 km ahead, 3 km to the side: off the road
        self.assertIsNotNone(incident_ahead(4, 1.8))  # 4 km ahead the corridor is 2 km wide each side

    def test_heading_east(self):
        a = ahead(LAT, LON, 90.0, *_pos(0.5, 3), 5)
        self.assertAlmostEqual(a[0], 3, places=1)
        self.assertAlmostEqual(a[1], -0.5, places=1)  # north of an eastward road: on the left

    def test_lobe_wide_in_town_narrow_fast(self):
        diagonal = _pos(2, 2)  # 45° off, 2.8 km away
        beside = _pos(0.05, 1.5)  # straight to the right, 1.5 km
        self.assertIsNotNone(ahead(LAT, LON, 0.0, *diagonal, 5, 25))
        self.assertIsNone(ahead(LAT, LON, 0.0, *diagonal, 5, 110))
        self.assertIsNotNone(ahead(LAT, LON, 0.0, *beside, 5, 25))
        self.assertIsNone(ahead(LAT, LON, 0.0, *beside, 5, 110))
        self.assertIsNotNone(ahead(LAT, LON, 0.0, *_pos(4.8, 0.3), 5, 110))  # straight ahead: the whole way
        for speed in (10, 50, 130):
            self.assertIsNone(ahead(LAT, LON, 0.0, *_pos(-0.3, 0.1), 5, speed))  # behind: never
        self.assertIsNotNone(ahead(LAT, LON, 0.0, *_pos(0.1, 0.4), 5, 130))  # right next to us, in front

    def test_heading_from_gps_or_track(self):
        self.assertEqual(heading(270.0, 50.0, None), 270.0)
        self.assertIsNone(heading(270.0, 2.0, None))  # standing: the GPS course is noise
        track = [[NOW - 30, LAT, LON], [NOW, LAT, LON + 0.01]]
        self.assertAlmostEqual(heading(None, None, track), 90.0, delta=1)
        self.assertIsNone(heading(None, None, [[NOW - 30, LAT, LON], [NOW, LAT, LON + 0.0001]]))


def _pos(dnorth, deast):
    i = incident("x", dnorth, deast)
    return i["latitude"], i["longitude"]


def incident_ahead(dnorth, deast):
    return ahead(LAT, LON, 0.0, *_pos(dnorth, deast), 5)


class AlertsTest(unittest.TestCase):
    def test_once_each_nearest_first_and_only_incidents(self):
        alerts = RoadAlerts()
        stations = [incident("FAR", 4, 0), incident("NEAR", 1, 0.2),
                    incident("HOUSE", 2, 0, symbol="-", table="/"), incident("OLD", 2, 0, age=4 * 3600),
                    incident("BEHIND", -2, 0)]
        found = alerts.check(NOW, LAT, LON, 0.0, stations, 5)
        self.assertEqual([f[0]["call"] for f in found], ["NEAR", "FAR"])
        self.assertEqual(alerts.check(NOW + 60, LAT, LON, 0.0, stations, 5), [])
        again = alerts.check(NOW + REPEAT_SECONDS + 1, LAT, LON, 0.0, stations, 5)
        self.assertEqual(len(again), 2)

    def test_no_heading_no_alert(self):
        self.assertEqual(RoadAlerts().check(NOW, LAT, LON, None, [incident("A", 1, 0)], 5), [])

    def test_config_distance(self):
        conf = Config(callsign="OK1ABC", road_alert_km=7)
        conf.validate()
        self.assertEqual(conf.road_alert_km, 5)


if __name__ == "__main__":
    unittest.main()
