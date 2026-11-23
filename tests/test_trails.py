"""Each station's positions in the last hour, kept in memory for the map's trails."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aprs_kiss_core import station as st  # noqa: E402


class TrailTest(unittest.TestCase):
    def test_track(self):
        e = {}
        st._track(e, 0, 49.70, 13.40)
        st._track(e, 60, 49.70001, 13.40001)  # a few metres: the same point, seen later
        self.assertEqual(len(e["track"]), 1)
        self.assertEqual(e["track"][0][0], 60)
        st._track(e, 120, 49.71, 13.42)
        st._track(e, 180, 49.72, 13.44)
        self.assertEqual([p[1] for p in e["track"]], [49.70, 49.71, 49.72])
        st._track(e, 120 + st.TRACK_SECONDS + 1, 49.73, 13.46)  # an hour later: the old points drop out
        self.assertEqual([p[1] for p in e["track"]], [49.72, 49.73])

    def test_cap(self):
        e = {}
        for i in range(st.TRACK_POINTS + 30):
            st._track(e, i, 49.0 + i * 0.01, 13.0)
        self.assertEqual(len(e["track"]), st.TRACK_POINTS)

    def test_impossible_jump_starts_the_trail_again(self):
        e = {}
        st._track(e, 0, 49.70, 13.40)
        st._track(e, 60, 49.71, 13.41)  # 1.3 km in a minute: a car
        st._track(e, 120, 50.50, 12.00)  # 130 km in a minute: not one station
        self.assertEqual([(p[1], p[2]) for p in e["track"]], [(50.50, 12.00)])
        st._track(e, 3720, 50.30, 12.50)  # 40 km in an hour: fine
        self.assertEqual(len(e["track"]), 2)


class ObjectTest(unittest.TestCase):
    def station(self):
        from aprs_kiss_core.parser import parse
        s = st.Station(st.StationConfig("OK1SIM-7", [], "/-", ""), lambda *_: None, parse,
                       lambda *_: None, lambda *_: None, lambda: None, lambda: 1)
        return s, parse

    def test_objects_are_their_own_places(self):
        s, parse = self.station()
        for raw in ("DB0YC>APRS,TCPIP*:;DB0YC-R  *111111z5012.34N/01234.56ErRPT 439.000MHz",
                    "DB0YC>APRS,TCPIP*:;DB0YC-B  *111111z4901.00N/01301.00ErRPT 145.600MHz",
                    "DB0YC>APRS,TCPIP*:!4930.00N/01300.00E#digi"):
            s.handle_is_packet({**parse(raw), "raw": raw})
        self.assertAlmostEqual(s.heard["DB0YC-R"]["latitude"], 50.2057, places=3)
        self.assertEqual(s.heard["DB0YC-R"]["object_of"], "DB0YC")
        self.assertAlmostEqual(s.heard["DB0YC-B"]["latitude"], 49.0167, places=3)
        self.assertEqual(s.heard["DB0YC"]["latitude"], 49.5)
        self.assertEqual(len(s.heard["DB0YC"]["track"]), 1)  # the sender did not jump between its objects

    def test_killed_object_goes_away(self):
        s, parse = self.station()
        s.handle_is_packet(parse("DB0YC>APRS,TCPIP*:;EVENT    *111111z5012.34N/01234.56E/x") | {"raw": ""})
        self.assertIn("EVENT", s.heard)
        s.handle_is_packet(parse("DB0YC>APRS,TCPIP*:;EVENT    _111111z5012.34N/01234.56E/x") | {"raw": ""})
        self.assertNotIn("EVENT", s.heard)


if __name__ == "__main__":
    unittest.main()
