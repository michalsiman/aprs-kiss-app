"""#APRSThursday: the net's time window, the message text and the engine's handling of HOTG traffic."""

import asyncio
import datetime as dt
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aprs_kiss_core import thursday  # noqa: E402
from aprs_kiss_core.config import Config  # noqa: E402
from aprs_kiss_core.engine import Engine  # noqa: E402


def ts(*args):
    return dt.datetime(*args, tzinfo=dt.timezone.utc).timestamp()


class WindowTest(unittest.TestCase):
    def test_thursday_utc(self):
        self.assertTrue(thursday.is_active(ts(2026, 11, 26, 0, 0)))  # Thursday 00:00 UTC
        self.assertTrue(thursday.is_active(ts(2026, 11, 26, 23, 59, 59)))
        self.assertFalse(thursday.is_active(ts(2026, 11, 25, 23, 59, 59)))  # Wednesday
        self.assertFalse(thursday.is_active(ts(2026, 11, 27, 0, 0)))  # Friday

    def test_window(self):
        thu, fri = ts(2026, 11, 26), ts(2026, 11, 27)
        self.assertEqual(thursday.window(ts(2026, 11, 22, 16, 0)), (thu, fri))  # Sunday: the next one
        self.assertEqual(thursday.window(ts(2026, 11, 26, 12, 0)), (thu, fri))  # during it
        self.assertEqual(thursday.window(ts(2026, 11, 27, 0, 0)), (ts(2026, 12, 3), ts(2026, 12, 4)))

    def test_compose(self):
        self.assertEqual(thursday.compose("  Hello   from Stod "), "CQ HOTG Hello from Stod")
        long = thursday.compose("x" * 100)
        self.assertEqual(len(long), 67)
        self.assertTrue(thursday.is_group_text("cq hotg hi"))
        self.assertEqual(thursday.strip_prefix("CQ HOTG Hi there"), "Hi there")
        # how ANSRVR passes on another member's message
        self.assertTrue(thursday.is_group_text("N:HOTG Enjoy APRS!!"))
        self.assertEqual(thursday.strip_prefix("N:HOTG Greetings from Ohio"), "Greetings from Ohio")
        self.assertFalse(thursday.is_group_text("N:HOTGX not ours"))
        self.assertTrue(thursday.is_server("ANSRVR"))
        self.assertFalse(thursday.is_server("OK1ABC"))


class EngineThursdayTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = Engine(Config(callsign="OK1SIM-7").validate(), pathlib.Path(self.tmp.name))
        self.sent = []

        async def send_message(to, text, want_ack=True, via="both"):
            self.sent.append((to, text, via))
            return type("Msg", (), {"text": text, "msg_id": str(len(self.sent)), "as_dict": lambda self: {}})()

        self.engine.station.send_message = send_message

    async def asyncTearDown(self):
        self.tmp.cleanup()

    def relay(self, sender, text, via="internet"):
        self.engine._on_message({"from": sender, "text": text, "received_at": 1000.0, "via": via})

    async def test_check_in_and_group_traffic(self):
        await self.engine.send_thursday("Hello from Stod", via="internet")
        self.assertEqual(self.sent, [("ANSRVR", "CQ HOTG Hello from Stod", "internet")])
        self.assertTrue(self.engine.thursday_member_until())
        self.assertGreater(self.engine.thursday_wait(), 29 * 60)
        with self.assertRaises(ValueError):  # one CQ per 30 minutes
            await self.engine.send_thursday("again")
        self.relay("ANSRVR", "Message has been sent to HOTG")
        self.relay("W1ABC-9", "CQ HOTG Greetings from Maine")
        self.relay("W1ABC-9", "CQ HOTG Greetings from Maine", via="radio")  # same relay twice
        self.assertEqual([(e["kind"], e["text"]) for e in self.engine.thursday],
                         [("out", "Hello from Stod"), ("server", "Message has been sent to HOTG"),
                          ("in", "Greetings from Maine")])
        self.assertEqual(list(self.engine.messages), [])  # the inbox stays for real conversations
        self.relay("OK1ABC", "ahoj")
        self.assertEqual(len(self.engine.messages), 1)

    async def test_leave(self):
        await self.engine.send_thursday("hi")
        await self.engine.leave_thursday()
        self.assertEqual(self.sent[-1][:2], ("ANSRVR", "U HOTG"))
        self.assertFalse(self.engine.thursday_member_until())

    async def test_saved(self):
        await self.engine.send_thursday("hi")
        state = self.engine._state()
        self.assertEqual(state["thursday"][0]["text"], "hi")
        self.assertTrue(state["thursday_joined"])


if __name__ == "__main__":
    unittest.main()
