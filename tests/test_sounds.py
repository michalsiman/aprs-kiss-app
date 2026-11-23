"""The beeps are valid WAV files of the expected length; the device language wins over the environment."""

import io
import pathlib
import sys
import unittest
import wave

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

try:
    from aprs_kiss_app import i18n, sounds  # needs flet
except ImportError:
    sounds = None


@unittest.skipIf(sounds is None, "flet is not installed")
class SoundsTest(unittest.TestCase):
    def test_wav(self):
        for kind, pieces in sounds.TONES.items():
            with wave.open(io.BytesIO(sounds.wav(pieces))) as w:
                self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate()), (1, 2, sounds.RATE))
                ms = w.getnframes() * 1000 / sounds.RATE
                self.assertAlmostEqual(ms, sum(p[1] for p in pieces), delta=2, msg=kind)
            self.assertIn(kind, sounds.SETTING)

    def test_device_language(self):
        try:
            i18n.DEVICE_LANGUAGE = "cs"
            self.assertEqual(i18n.Translator("").language, "cs")
            self.assertEqual(i18n.Translator("de").language, "de")  # a chosen language stays
        finally:
            i18n.DEVICE_LANGUAGE = None


if __name__ == "__main__":
    unittest.main()
