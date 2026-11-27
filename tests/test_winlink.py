import random
import unittest

from aprs_kiss_core import winlink


class WinlinkTest(unittest.TestCase):
    def test_answer_as_winlink_shows_it(self):
        ans = winlink.answer("425", "ABC123", random.Random(1))
        self.assertEqual(len(ans), 6)
        self.assertEqual(ans[:3], "1B2")  # Winlink's example: ABC123, 425 → 1B2 + three more

    def test_short_password(self):
        with self.assertRaises(ValueError):
            winlink.answer("729", "ABC123")
        with self.assertRaises(ValueError):
            winlink.answer("123", "")

    def test_challenge(self):
        self.assertEqual(winlink.find_challenge("Login [425]:"), "425")
        self.assertEqual(winlink.find_challenge("425"), "425")
        self.assertIsNone(winlink.find_challenge("You have 2 messages"))
        self.assertIsNone(winlink.find_challenge("1) 11/27 123 from 456"))  # two numbers: not a challenge

    def test_session(self):
        s = winlink.Session()
        self.assertIsNone(s.challenge_in("Login [425]:", 100))  # not asked
        s.ask(100)
        self.assertEqual(s.challenge_in("Login [425]:", 110), "425")
        self.assertIsNone(s.challenge_in("Login [425]:", 100 + winlink.CHALLENGE_SECONDS + 1))
        s.answered(110)
        self.assertTrue(s.logged_in(110 + 3600))
        self.assertFalse(s.logged_in(110 + winlink.LOGIN_SECONDS + 1))

    def test_body_lines(self):
        self.assertEqual(winlink.body_lines("Hello\n\nsecond line"), ["Hello", "second line"])
        long = " ".join(["word"] * 30)
        lines = winlink.body_lines(long)
        self.assertTrue(all(len(x) <= 67 for x in lines))
        self.assertEqual(" ".join(lines), long)


if __name__ == "__main__":
    unittest.main()
