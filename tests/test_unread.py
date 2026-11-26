"""Unread conversations survive a restart (and so an update) and can all be marked read."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

try:
    import flet  # noqa: F401
except ImportError:
    raise unittest.SkipTest("flet is not installed")

from aprs_kiss_app.views.messages import MessagesView, avatar_color, avatar_letter  # noqa: E402


class UnreadTest(unittest.TestCase):
    def _view(self, folder):
        view = MessagesView.__new__(MessagesView)
        view.app = SimpleNamespace(folder=Path(folder))
        view.unread = view._load_unread()
        return view

    def test_unread_kept_across_restart(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._view(d)
            v._set_unread("OK1ABC", True)
            v._set_unread("OK1ABC", True)
            v._set_unread("OK2XYZ", True)
            v._set_unread("OK2XYZ", False)
            again = self._view(d)
            self.assertEqual(again.unread, {"OK1ABC": 2})
            self.assertEqual(again.unread_total, 2)

    def test_first_form_of_the_file(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "unread.json").write_text('["OK1ABC", "ok2xyz"]', encoding="utf-8")
            self.assertEqual(self._view(d).unread, {"OK1ABC": 1, "OK2XYZ": 1})

    def test_no_file_or_broken_file(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self._view(d).unread, {})
            (Path(d) / "unread.json").write_text("{bad", encoding="utf-8")
            self.assertEqual(self._view(d).unread, {})


class AvatarTest(unittest.TestCase):
    def test_letter_from_the_suffix(self):
        self.assertEqual(avatar_letter("OK1TNT-14"), "T")
        self.assertEqual(avatar_letter("ok1sim"), "S")
        self.assertEqual(avatar_letter("9A2XY"), "X")
        self.assertEqual(avatar_letter("REPEAT"), "R")
        self.assertEqual(avatar_letter(""), "?")

    def test_same_letter_same_colour(self):
        self.assertEqual(avatar_color("T"), avatar_color("T"))
        self.assertNotEqual(avatar_color("A"), avatar_color("B"))


class SearchTest(unittest.TestCase):
    def test_fold_ignores_case_and_accents(self):
        fold = MessagesView._fold
        self.assertEqual(fold("Žluťoučký KŮŇ"), "zlutoucky kun")
        self.assertIn(fold("zdravim"), fold("Zdravím, tady OK1TNT"))


if __name__ == "__main__":
    unittest.main()
