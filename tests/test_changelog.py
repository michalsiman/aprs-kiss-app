import unittest
from pathlib import Path

from aprs_kiss_core.changelog import sections, since

ROOT = Path(__file__).resolve().parents[1]
TEXT = """# Changelog

intro

## Unreleased

- next

## 1.6.0 – 2026-12-01

- six

## 1.5.1 beta – 2026-11-30

- beta

## 1.5.0 – 2026-11-26

- five
"""


class ChangelogTest(unittest.TestCase):
    def test_sections(self):
        self.assertEqual([v for v, _ in sections(TEXT)], ["1.6.0", "1.5.1", "1.5.0"])
        self.assertNotIn("next", sections(TEXT)[0][1])

    def test_since_last_run(self):
        text = since(TEXT, "1.5.0", "1.6.0")
        self.assertIn("six", text)
        self.assertIn("beta", text)
        self.assertNotIn("five", text)
        self.assertNotIn("next", text)

    def test_unknown_previous_only_current(self):
        self.assertEqual(since(TEXT, "", "1.6.0"), "## 1.6.0 – 2026-12-01\n\n- six")

    def test_bundled_copy_is_current(self):
        """The app shows the copy in its package: it must be the same as the one in the repository."""
        self.assertEqual((ROOT / "src/aprs_kiss_app/CHANGELOG.md").read_text(encoding="utf-8"),
                         (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
                         "cp CHANGELOG.md src/aprs_kiss_app/")


if __name__ == "__main__":
    unittest.main()
