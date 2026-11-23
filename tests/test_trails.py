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


if __name__ == "__main__":
    unittest.main()
