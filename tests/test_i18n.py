import pathlib
import re
import string
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from aprs_kiss_app.i18n import LANGUAGES, SSID_LABELS, TEXTS, Translator, match_language, ssid_labels  # noqa: E402
from aprs_kiss_core.aprsis import licence_confirmed  # noqa: E402


def fields(text):
    return sorted(name for _, name, _, _ in string.Formatter().parse(text) if name)


class TranslationsTest(unittest.TestCase):
    def test_same_keys_as_english(self):
        en = set(TEXTS["en"])
        for code, texts in TEXTS.items():
            with self.subTest(code=code):
                self.assertEqual(set(texts) - en, set(), "unknown keys")
                self.assertEqual(en - set(texts), set(), "missing keys")

    def test_same_placeholders(self):
        for code, texts in TEXTS.items():
            for key, text in texts.items():
                with self.subTest(code=code, key=key):
                    self.assertEqual(fields(text), fields(TEXTS["en"][key]))
                    self.assertTrue(text.strip())

    def test_ssid_labels(self):
        for code in TEXTS:
            labels = ssid_labels(code)
            with self.subTest(code=code):
                self.assertEqual(len(labels), 16)
                for i, label in enumerate(labels):
                    self.assertTrue(re.match(rf"{i} – \S", label), label)
        self.assertEqual(set(SSID_LABELS) | {"cs", "en"}, set(TEXTS))

    def test_picker_lists_every_language(self):
        self.assertEqual(set(LANGUAGES), set(TEXTS))
        self.assertEqual(len(LANGUAGES), 15)

    def test_system_locale(self):
        cases = {"de_AT.UTF-8": "de", "cs_CZ.UTF-8": "cs", "sk_SK": "sk", "pt_BR.UTF-8": "pt_BR",
                 "pt_PT.UTF-8": "pt_BR", "nb_NO.UTF-8": "nb", "nn_NO": "nb", "no": "nb",
                 "sr_RS@latin": "sr", "uk_UA.UTF-8": "uk", "sv_FI.UTF-8": "sv", "en_GB:en": "en",
                 "ja_JP.UTF-8": None, "C": None, "": None}
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(match_language(value), expected)

    def test_translator_formats(self):
        self.assertEqual(Translator("de")("message_from", call="OK1ABC"), "Nachricht von OK1ABC")
        self.assertEqual(Translator("xx").language in TEXTS, True)

    def test_licence_sentence_in_every_language(self):
        statements = [t["licence_text"] for t in TEXTS.values()]
        for code, texts in TEXTS.items():
            with self.subTest(code=code):
                self.assertTrue(licence_confirmed(texts["licence_text"] + ".", statements))
                self.assertTrue(licence_confirmed("  " + texts["licence_text"].upper(), statements))
        self.assertFalse(licence_confirmed("yes", statements))
        self.assertFalse(licence_confirmed("", statements))


if __name__ == "__main__":
    unittest.main()
