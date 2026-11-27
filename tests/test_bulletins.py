"""Bulletins: addressees, received packets, the board and the gaps between our copies."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aprs_kiss_core import bulletins as bln  # noqa: E402
from aprs_kiss_core.parser import parse  # noqa: E402


class BulletinTest(unittest.TestCase):
    def test_addressee_and_kind(self):
        self.assertEqual(bln.addressee("1"), "BLN1")
        self.assertEqual(bln.addressee("a"), "BLNA")
        self.assertEqual(bln.addressee("2", "wx"), "BLN2WX")
        for bad in (("", ""), ("12", ""), ("A", "WX"), ("1", "TOOLONG"), ("1", "W-X")):
            with self.assertRaises(ValueError):
                bln.addressee(*bad)
        self.assertEqual(bln.kind_of("BLN3"), "bulletin")
        self.assertEqual(bln.kind_of("BLNQ"), "announcement")
        self.assertEqual(bln.kind_of("BLN4CLUB"), "group")
        self.assertEqual(bln.kind_of("NWS-WARN"), "nws")
        self.assertEqual(bln.kind_of("OK1ABC"), "")

    def test_from_packet(self):
        b = bln.from_packet(parse("OK1ABC>APRS,WIDE1-1::BLN2WX   :Storm warning{12"))
        self.assertEqual((b["addressee"], b["kind"], b["group"], b["text"]), ("BLN2WX", "group", "WX", "Storm warning"))
        a = bln.from_packet(parse("OK1ABC>APRS::BLNA     :Hamfest Sat"))
        self.assertEqual((a["addressee"], a["kind"]), ("BLNA", "announcement"))
        n = bln.from_packet(parse("K1ABC>APRS::NWS-WARN :Flood"))
        self.assertEqual(n["kind"], "nws")
        self.assertIsNone(bln.from_packet(parse("OK1ABC>APRS::OK1SIM   :hi{1")))
        self.assertIsNone(bln.from_packet(parse("OK1ABC>APRS::BLN1     :")))

    def test_board(self):
        board = bln.Board()
        item = {"from": "OK1ABC", "addressee": "BLN1", "kind": "bulletin", "line": "1", "group": "", "text": "a"}
        self.assertIsNotNone(board.add(item, 100, "internet", 30))
        self.assertIsNone(board.add(item, 200, "radio"))
        self.assertEqual(board.heard[0]["via"], "radio")
        self.assertIsNotNone(board.add({**item, "text": "b"}, 300, "internet"))
        self.assertEqual(len(board.heard), 1)
        self.assertTrue(board.shown({"via": "internet", "km": 40}, 50))
        self.assertFalse(board.shown({"via": "internet", "km": 60}, 50))
        self.assertFalse(board.shown({"via": "internet"}, 50))
        self.assertTrue(board.shown({"via": "internet"}, 0))
        self.assertTrue(board.expire(300 + 13 * 3600))
        self.assertEqual(board.heard, [])

    def test_our_copies(self):
        board = bln.Board()
        e = board.start("BLN1", "net", "radio", 4, 0)
        gaps = []
        now = 0
        while board.due(now) or now < e["until"]:
            if board.due(now):
                board.sent(e, now)
                gaps.append(e["next"] - now)
                now = e["next"]
            else:
                break
        self.assertEqual(gaps[:4], [60, 300, 600, 1200])
        self.assertLessEqual(e["sent"], 4 * 3 + 4)
        a = board.start("BLNA", "hamfest", "both", 24, 0)
        a["sent"] = 9
        self.assertEqual(board.gap(a), 3600)
        board.start("BLN1", "net again", "radio", 1, 0)
        self.assertEqual([m["text"] for m in board.mine], ["hamfest", "net again"])
        self.assertTrue(board.expire(4000))
        self.assertEqual([m["addressee"] for m in board.mine], ["BLNA"])


if __name__ == "__main__":
    unittest.main()
