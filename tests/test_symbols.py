"""APRS symbol names and pictures (no user interface needed)."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aprs_kiss_app.symbols import SYMBOLS, symbol_info  # noqa: E402
from aprs_kiss_core.config import Config  # noqa: E402


class SymbolTest(unittest.TestCase):
    def test_primary_and_alternate(self):
        self.assertEqual(symbol_info("/", ">", "cs")[:2], ("🚗", "Auto"))
        self.assertEqual(symbol_info("\\", "!", "en")[1], "Emergency")

    def test_overlays_with_a_meaning(self):
        self.assertEqual(symbol_info("I", "&")[1], "iGate (RX and TX)")
        self.assertEqual(symbol_info("L", "&")[1], "LoRa iGate")
        self.assertEqual(symbol_info("L", "#")[1], "LoRa digipeater")

    def test_other_overlay_uses_the_alternate_symbol(self):
        pic, name, known = symbol_info("O", "_")
        self.assertTrue(known)
        self.assertEqual(pic, symbol_info("\\", "_")[0])
        self.assertIn("overlay O", name)

    def test_unknown(self):
        self.assertEqual(symbol_info("/", "z"), ("📍", "/z", False))
        self.assertEqual(symbol_info(None, None)[2], False)

    def test_every_symbol_in_the_picker_is_known(self):
        for code, *_ in SYMBOLS:
            self.assertTrue(symbol_info(code[0], code[1])[2], code)

    def test_show_internet_is_saved(self):
        self.assertTrue(Config().show_internet)
        self.assertFalse(Config.from_dict({"show_internet": False}).show_internet)


if __name__ == "__main__":
    unittest.main()
