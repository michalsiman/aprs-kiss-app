"""New-version check: version comparison and the once-a-day rule (no network)."""

import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aprs_kiss_app import updates  # noqa: E402


class UpdatesTest(unittest.TestCase):
    def test_versions(self):
        self.assertEqual(updates.parse_version("v0.1.10"), (0, 1, 10))
        self.assertTrue(updates.is_newer("0.1.10", "0.1.9"))
        self.assertTrue(updates.is_newer("v0.2.0", "0.1.9"))
        self.assertFalse(updates.is_newer("0.1.3", "0.1.3"))
        self.assertFalse(updates.is_newer("", "0.1.3"))
        self.assertFalse(updates.is_newer("0.1.2", "0.1.3"))

    def test_once_a_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = pathlib.Path(tmp)
            with mock.patch.object(updates, "fetch_latest", return_value=("9.9.9", "https://x")) as fetch:
                st = updates.check(folder, now=1000.0)
                self.assertTrue(st.available)
                updates.check(folder, now=1000.0 + 3600)
                self.assertEqual(fetch.call_count, 1)  # within a day: not asked again
                updates.check(folder, now=1000.0 + 25 * 3600)
                self.assertEqual(fetch.call_count, 2)
                updates.check(folder, force=True, now=1000.0 + 25 * 3600 + 1)
                self.assertEqual(fetch.call_count, 3)

    def test_failure_is_remembered_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(updates, "fetch_latest", side_effect=OSError("offline")):
                st = updates.check(pathlib.Path(tmp), now=5.0)
            self.assertEqual(st.error, "offline")
            self.assertFalse(st.available)


if __name__ == "__main__":
    unittest.main()
