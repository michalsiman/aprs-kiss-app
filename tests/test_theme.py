import pathlib
import sys
import unittest

import flet as ft

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from aprs_kiss_app.theme import parse_color_scheme, theme_is_dark, theme_mode  # noqa: E402


class ThemeTest(unittest.TestCase):
    def test_portal_color_scheme(self):
        self.assertIs(parse_color_scheme("(<uint32 1>,)\n"), True)
        self.assertIs(parse_color_scheme("(<<uint32 2>>,)"), False)
        self.assertIsNone(parse_color_scheme("(<uint32 0>,)"))
        self.assertIsNone(parse_color_scheme(None))
        self.assertIsNone(parse_color_scheme("Error: no such interface"))

    def test_theme_name(self):
        self.assertTrue(theme_is_dark("Mint-Y-Dark-Aqua"))
        self.assertTrue(theme_is_dark("Adwaita-dark"))
        self.assertFalse(theme_is_dark("Mint-Y-Aqua"))
        self.assertFalse(theme_is_dark(None))

    def test_mode(self):
        self.assertEqual(theme_mode("light", True), ft.ThemeMode.LIGHT)
        self.assertEqual(theme_mode("dark", False), ft.ThemeMode.DARK)
        self.assertEqual(theme_mode("auto", True), ft.ThemeMode.DARK)
        self.assertEqual(theme_mode("auto", False), ft.ThemeMode.LIGHT)
        self.assertEqual(theme_mode("auto", None), ft.ThemeMode.SYSTEM)
        self.assertEqual(theme_mode("bogus", None), ft.ThemeMode.SYSTEM)


if __name__ == "__main__":
    unittest.main()
