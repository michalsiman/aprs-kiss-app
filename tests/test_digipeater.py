"""APRS digipeater: what is repeated and how the path is rewritten (New-N paradigm)."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aprs_kiss_core.ax25 import CONTROL_UI, Address, Frame  # noqa: E402
from aprs_kiss_core import digipeater as dg  # noqa: E402

ME = Address.parse("OK1SIM-2")


def frame(path, source="OK1ABC-9", ui=True):
    return Frame(Address.parse("APRS"), Address.parse(source), [Address.parse(p) for p in path], b"=test",
                 CONTROL_UI if ui else 0x00)


def path_of(f):
    return ",".join(str(a) + ("*" if a.repeated else "") for a in f.path) if f else None


class DigipeaterTest(unittest.TestCase):
    def test_fill_in(self):
        self.assertEqual(path_of(dg.repeat(frame(["WIDE1-1", "WIDE2-1"]), ME, "fillin")), "OK1SIM-2*,WIDE2-1")
        self.assertIsNone(dg.repeat(frame(["WIDE2-2"]), ME, "fillin"))  # fill-in does only WIDE1-1

    def test_wide(self):
        self.assertEqual(path_of(dg.repeat(frame(["WIDE2-2"]), ME, "wide")), "OK1SIM-2*,WIDE2-1")
        self.assertEqual(path_of(dg.repeat(frame(["OK0DIG*", "WIDE2-1"]), ME, "wide")), "OK0DIG*,OK1SIM-2*,WIDE2*")
        self.assertEqual(path_of(dg.repeat(frame(["WIDE1-1", "WIDE2-1"]), ME, "wide")), "OK1SIM-2*,WIDE2-1")
        self.assertIsNone(dg.repeat(frame(["WIDE7-7"]), ME, "wide"))  # more hops than allowed
        self.assertIsNotNone(dg.repeat(frame(["WIDE3-3"]), ME, "wide", max_hops=3))
        self.assertIsNone(dg.repeat(frame(["WIDE2*"]), ME, "wide"))  # nothing left to use

    def test_by_name(self):
        self.assertEqual(path_of(dg.repeat(frame(["OK1SIM-2", "WIDE2-1"]), ME, "fillin")), "OK1SIM-2*,WIDE2-1")
        self.assertIsNone(dg.repeat(frame(["OK1SIM-3"]), ME, "fillin"))  # another SSID is another station
        relay = dg.parse_aliases("RELAY, TRACE")
        self.assertEqual(path_of(dg.repeat(frame(["RELAY"]), ME, "off", relay)), "OK1SIM-2*")
        # by name also connected-mode frames (a BBS reached through us); WIDE only for UI frames
        self.assertIsNotNone(dg.repeat(frame(["OK1SIM-2"], ui=False), ME, "fillin"))
        self.assertIsNone(dg.repeat(frame(["WIDE1-1"], ui=False), ME, "fillin"))

    def test_never(self):
        self.assertIsNone(dg.repeat(frame(["WIDE1-1"], source="OK1SIM-2"), ME, "wide"))  # our own
        self.assertIsNone(dg.repeat(frame(["OK1SIM-2*", "WIDE2-1"]), ME, "wide"))  # been through us
        self.assertIsNone(dg.repeat(frame(["WIDE1-1"]), ME, "off"))

    def test_full_path_is_not_made_longer(self):
        full = ["D1*", "D2*", "D3*", "D4*", "D5*", "D6*", "D7*", "WIDE2-2"]
        out = dg.repeat(frame(full), ME, "wide")
        self.assertEqual(len(out.path), 8)
        self.assertEqual(str(out.path[-1]) + ("*" if out.path[-1].repeated else ""), "WIDE2-1")

    def test_dedupe(self):
        d = dg.Dedupe(30)
        f = frame(["WIDE1-1"])
        self.assertTrue(d.fresh(f, now=0))
        self.assertFalse(d.fresh(frame(["DIGI1*", "WIDE2-1"]), now=10))  # the same packet via another way
        self.assertTrue(d.fresh(f, now=31))

    def test_encodes(self):
        out = dg.repeat(frame(["WIDE2-2"]), ME, "wide")
        again = Frame.decode(out.encode())
        self.assertEqual(path_of(again), "OK1SIM-2*,WIDE2-1")


if __name__ == "__main__":
    unittest.main()
