"""Unread conversations survive a restart (and so an update) and can all be marked read."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from aprs_kiss_app.views.messages import MessagesView


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
            v._set_unread("OK2XYZ", True)
            v._set_unread("OK2XYZ", False)
            self.assertEqual(self._view(d).unread, {"OK1ABC"})

    def test_no_file_or_broken_file(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self._view(d).unread, set())
            (Path(d) / "unread.json").write_text("{bad", encoding="utf-8")
            self.assertEqual(self._view(d).unread, set())


if __name__ == "__main__":
    unittest.main()
