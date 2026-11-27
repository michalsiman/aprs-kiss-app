import unittest

from aprs_kiss_core import localwx

HERE = (50.0, 14.0)
NOW = 100_000.0


def station(lat, lon, at=NOW - 60, **wx):
    return {"latitude": lat, "longitude": lon, "weather": wx, "weather_at": at, "last_heard": at}


class LocalWeatherTest(unittest.TestCase):
    def test_average_of_the_stations_near(self):
        heard = {"A": station(50.05, 14.0, temperature=10.0, humidity=80, pressure=1010.0),
                 "B": station(50.0, 14.1, temperature=12.0, pressure=1014.0),
                 "FAR": station(50.5, 14.0, temperature=30.0)}  # ~55 km away
        wx = localwx.around(heard, HERE, NOW)
        self.assertAlmostEqual(wx["temperature"], 11.0)
        self.assertEqual(wx["humidity"], 80)
        self.assertAlmostEqual(wx["pressure"], 1012.0)
        self.assertEqual(wx["stations"], 2)

    def test_old_reports_do_not_count(self):
        heard = {"A": station(50.0, 14.0, at=NOW - 3 * 3600, temperature=10.0)}
        self.assertIsNone(localwx.around(heard, HERE, NOW))

    def test_the_weather_time_not_the_last_packet(self):
        heard = {"A": station(50.0, 14.0, at=NOW - 3 * 3600, temperature=10.0)}
        heard["A"]["last_heard"] = NOW  # a status or position since, no new weather
        self.assertIsNone(localwx.around(heard, HERE, NOW))

    def test_no_position_no_temperature(self):
        heard = {"A": station(50.0, 14.0, temperature=10.0), "B": {"weather": {"humidity": 50}}}
        self.assertIsNone(localwx.around(heard, None, NOW))
        self.assertIsNone(localwx.around({"B": station(50.0, 14.0, humidity=50)}, HERE, NOW))

    def test_nonsense_humidity_and_pressure_are_left_out(self):
        heard = {"A": station(50.0, 14.0, temperature=5.0, humidity=0, pressure=10.0)}
        wx = localwx.around(heard, HERE, NOW)
        self.assertNotIn("humidity", wx)
        self.assertNotIn("pressure", wx)


if __name__ == "__main__":
    unittest.main()
