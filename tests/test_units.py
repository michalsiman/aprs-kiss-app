import os
import unittest
from unittest import mock

from aprs_kiss_app import i18n
from aprs_kiss_core.units import Units, system_distance, system_pressure, system_temperature


class UnitsTest(unittest.TestCase):
    def test_metric(self):
        u = Units("km", "C", comma=True)
        self.assertEqual(u.distance_text(0.35), "350 m")
        self.assertEqual(u.distance_text(4.254), "4,25 km")
        self.assertEqual(u.distance_short(12.4), "12 km")
        self.assertEqual(u.speed(90), "90 km/h")
        self.assertEqual(u.temperature_text(4.8), "4,8 °C")
        self.assertEqual(u.reach_choices(), ((20, "20"), (50, "50"), (100, "100")))

    def test_imperial(self):
        u = Units("mi", "F")
        self.assertEqual(u.distance_text(0.1), "330 ft")
        self.assertEqual(u.distance_text(16.09344), "10.0 mi")
        self.assertEqual(u.distance_short(4.0), "2.5 mi")
        self.assertEqual(u.speed(100), "62 mph")
        self.assertEqual(u.length(100), "328 ft")
        self.assertEqual(u.temperature_text(0), "32.0 °F")
        self.assertEqual(u.temperature_text(-40), "-40.0 °F")
        self.assertEqual(u.reach_choices(), ((16, "10"), (48, "30"), (97, "60")))
        self.assertAlmostEqual(u.to_km(u.from_km(50)), 50)

    def test_pressure(self):
        self.assertEqual(Units().pressure_text(1013.25), "1013 hPa")
        self.assertEqual(Units(pressure="inHg").pressure_text(1013.25), "29.92 inHg")
        self.assertEqual(Units(comma=True, pressure="inHg").pressure_text(1013.25), "29,92 inHg")
        self.assertEqual([system_pressure(c) for c in ("US", "GB", "AU", "CZ", None)],
                         ["inHg", "hPa", "hPa", "hPa", "hPa"])
        self.assertEqual(Units.choose("", "", "US").pressure, "inHg")
        self.assertEqual(Units.choose("", "", "US", pressure="hPa").pressure, "hPa")

    def test_system_default(self):
        self.assertEqual((system_distance("US"), system_temperature("US")), ("mi", "F"))
        self.assertEqual((system_distance("GB"), system_temperature("GB")), ("mi", "C"))
        self.assertEqual((system_distance("CZ"), system_temperature("CZ")), ("km", "C"))
        self.assertEqual((system_distance(None), system_temperature(None)), ("km", "C"))
        self.assertEqual(Units.choose("", "", "US"), Units("mi", "F", pressure="inHg"))
        self.assertEqual(Units.choose("km", "", "US"), Units("km", "F", pressure="inHg"))

    def test_country_from_the_environment(self):
        with mock.patch.object(i18n, "DEVICE_COUNTRY", None), \
                mock.patch.dict(os.environ, {"LC_MEASUREMENT": "", "LC_ALL": "", "LANG": "en_US.UTF-8"}):
            self.assertEqual(i18n.system_country(), "US")
        with mock.patch.object(i18n, "DEVICE_COUNTRY", "GB"):
            self.assertEqual(i18n.system_country(), "GB")


if __name__ == "__main__":
    unittest.main()
