import unittest

from aprs_kiss_core import mapfilter
from aprs_kiss_core.config import Config
from aprs_kiss_core.mapfilter import is_moving, is_road, is_weather, shown
from aprs_kiss_core.station import _track

NOW = 1_000_000.0


def station(**kw):
    e = {"call": "OK1ABC", "count": 1, "first_heard": NOW - 3600, "last_heard": NOW - 60}
    e.update(kw)
    return e


class KindsTest(unittest.TestCase):
    def test_weather(self):
        self.assertTrue(is_weather(station(symbol_table="/", symbol="_")))
        self.assertTrue(is_weather(station(symbol_table="\\", symbol="_")))
        self.assertTrue(is_weather(station(symbol_table="/", symbol="-", weather={"temperature": 3})))
        self.assertFalse(is_weather(station(symbol_table="/", symbol=">")))

    def test_road(self):
        self.assertTrue(is_road(station(symbol_table="\\", symbol="'")))  # crash site
        self.assertTrue(is_road(station(symbol_table="\\", symbol="j")))  # work zone
        self.assertTrue(is_road(station(symbol_table="A", symbol="!")))  # overlaid emergency
        self.assertFalse(is_road(station(symbol_table="/", symbol="'")))  # small aircraft
        self.assertFalse(is_road(station(symbol_table="/", symbol="j")))  # jeep

    def test_moving_by_track(self):
        e = station()
        _track(e, NOW - 1200, 50.0, 14.0)
        _track(e, NOW - 300, 50.0, 14.0)  # still there 5 min ago…
        _track(e, NOW - 60, 50.01, 14.0)  # …and now a km further
        self.assertTrue(is_moving(e, NOW))
        self.assertFalse(is_moving(e, NOW + 1200))  # and then it stayed

    def test_standing_station_is_not_moving(self):
        e = station()
        _track(e, NOW - 3000, 50.0, 14.0)
        _track(e, NOW - 60, 50.0, 14.0)
        self.assertFalse(is_moving(e, NOW))

    def test_speed_reported_lately(self):
        self.assertTrue(is_moving(station(speed=50.0), NOW))
        self.assertFalse(is_moving(station(speed=50.0, last_heard=NOW - 1800), NOW))

    def test_new_station_shown_until_known(self):
        self.assertTrue(is_moving(station(first_heard=NOW - 120), NOW))
        self.assertFalse(is_moving(station(first_heard=NOW - 1200), NOW))


class ShownTest(unittest.TestCase):
    def test_no_filter_shows_all_and_kinds_add_up(self):
        house = station(symbol_table="/", symbol="-")
        wx = station(symbol_table="/", symbol="_")
        crash = station(symbol_table="\\", symbol="'")
        self.assertTrue(shown(house, set(), NOW))
        self.assertEqual([shown(x, {"weather"}, NOW) for x in (house, wx, crash)], [False, True, False])
        self.assertEqual([shown(x, {"weather", "road"}, NOW) for x in (house, wx, crash)], [False, True, True])

    def test_config_keeps_only_known_kinds(self):
        self.assertEqual(mapfilter.join(mapfilter.parse("road, weather,bogus")), "weather,road")
        conf = Config(callsign="OK1ABC", map_filters="moving,xyz")
        conf.validate()
        self.assertEqual(conf.map_filters, "moving")


if __name__ == "__main__":
    unittest.main()
