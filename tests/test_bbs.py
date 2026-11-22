"""The BBS server: commands, messages on disk, access rules, settings and the engine wiring."""

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aprs_kiss_core.ax25 import Address, Frame  # noqa: E402
from aprs_kiss_core.bbs import BbsConfigError, BbsServer, Store  # noqa: E402
from aprs_kiss_core.bbs.storage import update_settings  # noqa: E402
from aprs_kiss_core.config import Config  # noqa: E402
from aprs_kiss_core.engine import Engine, TransmitRefused  # noqa: E402


class Bbs:
    """A BBS with the text it sends collected per station."""

    def __init__(self, folder, **kw):
        self.out, self.dropped = {}, []
        self.server = BbsServer(pathlib.Path(folder), "OK1SIM-1", "0.0.1",
                                lambda r, t: self.out.setdefault(r, []).append(t), self.dropped.append, **kw)

    def say(self, remote, *lines):
        for line in lines:
            self.server.receive(remote, line + "\r")
        return self.take(remote)

    def take(self, remote):
        text = "".join(self.out.pop(remote, []))
        return text.replace("\r", "\n")


class BbsServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = pathlib.Path(self.tmp.name) / "bbs"
        self.bbs = Bbs(self.folder)

    def tearDown(self):
        self.tmp.cleanup()

    def test_folder_starts_with_editable_files(self):
        for name in ("bbs.toml", "welcome.txt", "help.txt", "info.txt", "messages"):
            self.assertTrue((self.folder / name).exists(), name)

    def test_czech_templates(self):
        folder = pathlib.Path(self.tmp.name) / "cs"
        Bbs(folder, language="cs")
        self.assertIn("Vítej", (folder / "welcome.txt").read_text(encoding="utf-8"))

    def test_session(self):
        s = self.bbs.server
        s.connected("OK1ABC-7")
        hello = self.bbs.take("OK1ABC-7")
        self.assertTrue(hello.startswith("[APRSKISS-0.0.1-H$]"))
        self.assertIn("Welcome to APRS & Packet BBS (OK1SIM-1)", hello)
        self.assertIn("N <name>", hello)
        self.assertTrue(hello.rstrip().endswith("OK1SIM-1 BBS>"))
        self.assertIn("OK, name: Tom", self.bbs.say("OK1ABC-7", "n Tom"))
        # send a personal message to OK1XYZ
        self.assertIn("Subject:", self.bbs.say("OK1ABC-7", "S OK1XYZ"))
        self.bbs.say("OK1ABC-7", "Meeting")
        out = self.bbs.say("OK1ABC-7", "Line one", "Line two", "/EX")
        self.assertIn("Message #1 saved.", out)
        # the file on disk
        text = (self.folder / "messages" / "000001.txt").read_text(encoding="utf-8")
        self.assertIn("From: OK1ABC", text)
        self.assertIn("Line one\nLine two", text)
        # a bulletin, ended with Ctrl-Z without Enter
        self.bbs.say("OK1ABC-7", "SB ALL", "Net tonight")
        self.bbs.server.receive("OK1ABC-7", "20:00 on 145.500\r\x1a")
        self.assertIn("Message #2 saved.", self.bbs.take("OK1ABC-7"))
        # another user sees the bulletin but not the personal message
        s.connected("OK1QQQ")
        self.bbs.take("OK1QQQ")
        listing = self.bbs.say("OK1QQQ", "L")
        self.assertIn("Net tonight", listing)
        self.assertNotIn("Meeting", listing)
        self.assertIn("No message #1.", self.bbs.say("OK1QQQ", "R 1"))
        self.assertIn("not yours", self.bbs.say("OK1QQQ", "K 2"))
        # the recipient reads and kills it
        s.connected("OK1XYZ-9")
        welcome = self.bbs.take("OK1XYZ-9")
        self.assertIn("unread personal: 1", welcome)
        read = self.bbs.say("OK1XYZ-9", "RM")
        self.assertIn("Subject: Meeting", read)
        self.assertIn("Line one\nLine two", read)
        self.assertIn("No unread messages.", self.bbs.say("OK1XYZ-9", "RM"))
        self.assertIn("1 messages killed.", self.bbs.say("OK1XYZ-9", "KM"))
        self.assertNotIn(1, s.store.messages)
        # bye
        self.assertIn("73 de OK1SIM-1", self.bbs.say("OK1XYZ-9", "B"))
        self.assertEqual(self.bbs.dropped, ["OK1XYZ-9"])
        self.assertIn("Unknown command XYZ", self.bbs.say("OK1QQQ", "xyz"))

    def test_abort_and_line_limit(self):
        (self.folder / "bbs.toml").write_text('[limits]\nmax_message_lines = 2\n', encoding="utf-8")
        self.bbs.server.reload()
        self.bbs.server.connected("OK1ABC")
        self.bbs.take("OK1ABC")
        self.assertIn("Aborted.", self.bbs.say("OK1ABC", "S OK1XYZ", "x", "/ABORT"))
        out = self.bbs.say("OK1ABC", "S OK1XYZ", "subj", "a", "b")
        self.assertIn("limit of 2 lines", out)
        self.assertIn("Message #1 saved.", out)

    def test_access_rules_and_sessions(self):
        (self.folder / "bbs.toml").write_text('[access]\nmode = "list"\ndeny = ["OK1BAD-5"]\n[limits]\nmax_sessions = 1\n',
                                              encoding="utf-8")
        s = self.bbs.server
        s.reload()
        self.assertFalse(s.can_accept("OK1NEW"))  # not in users.toml
        self.assertTrue(s.can_accept("OK1SIM-7"))  # the sysop always
        s.connected("OK1SIM-7")
        self.assertFalse(s.can_accept("OK1SIM-9"))  # max_sessions
        self.assertFalse(s.can_accept("OK1BAD"))

    def test_bad_settings(self):
        (self.folder / "bbs.toml").write_text('[limits]\nmax_sessions = "two"\n', encoding="utf-8")
        with self.assertRaises(BbsConfigError):
            self.bbs.server.reload()
        (self.folder / "bbs.toml").write_text('[limits\n', encoding="utf-8")
        with self.assertRaises(BbsConfigError):
            self.bbs.server.reload()

    def test_users_saved_and_numbers_not_reused(self):
        s = self.bbs.server
        s.connected("OK1ABC")
        self.bbs.say("OK1ABC", "N Tom", "NQ Plzen", "S OK1XYZ", "a", "b", "/EX", "S OK1XYZ", "c", "d", "/EX", "K 2")
        again = Bbs(self.folder).server
        self.assertEqual(again.users.get("OK1ABC-3").name, "Tom")
        self.assertEqual(again.users.get("OK1ABC").qth, "Plzen")
        msg = Store(self.folder).add("P", "OK1ABC", "OK1XYZ", "", "e", "f")
        self.assertEqual(msg.number, 3)

    def test_timeout_purge_and_beacon(self):
        (self.folder / "bbs.toml").write_text('[limits]\nidle_timeout_sec = 60\nkeep_personal_days = 1\n'
                                              '[beacon]\nevery_min = 1\n', encoding="utf-8")
        s = self.bbs.server
        s.reload()
        s.store.add("P", "OK1ABC", "OK1XYZ", "", "old", "x", now=1000.0)
        s.store.add("P", "OK1ABC", "OK1QQQ", "", "new", "y")
        s.connected("OK1ABC")
        now = s.conns["OK1ABC"].last + 120
        beacon = s.tick(now)
        self.assertEqual(self.bbs.dropped, ["OK1ABC"])  # idle
        self.assertEqual(sorted(s.store.messages), [2])  # the old one purged
        self.assertEqual(beacon, "OK1SIM-1 APRS & Packet BBS - 1 msgs. Mail for: OK1QQQ")


class BbsLimitsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = pathlib.Path(self.tmp.name) / "bbs"
        self.bbs = Bbs(self.folder)

    def tearDown(self):
        self.tmp.cleanup()

    def test_settings_edited_in_place(self):
        update_settings(self.folder, {("limits", "max_sessions"): 3, ("limits", "idle_timeout_sec"): 90,
                                      ("limits", "max_tx_min"): 2, ("limits", "max_messages"): 7,
                                      ("extra", "new_key"): "x"})
        text = (self.folder / "bbs.toml").read_text(encoding="utf-8")
        self.assertIn("# Connections at the same time.", text)  # comments stay
        self.assertIn("max_sessions = 3\n", text)
        self.assertIn("[extra]\nnew_key = \"x\"", text)
        self.bbs.server.reload()
        st = self.bbs.server.settings
        self.assertEqual((st.max_sessions, st.idle_timeout_sec, st.max_tx_min, st.max_messages), (3, 90, 2, 7))

    def test_old_minutes_timeout_still_read(self):
        (self.folder / "bbs.toml").write_text("[limits]\nidle_timeout_min = 3\n", encoding="utf-8")
        self.bbs.server.reload()
        self.assertEqual(self.bbs.server.settings.idle_timeout_sec, 180)

    def test_tx_time_limit(self):
        update_settings(self.folder, {("limits", "max_tx_min"): 1})
        s = self.bbs.server
        s.reload()
        s.connected("OK1ABC")
        self.bbs.take("OK1ABC")
        for _ in range(30):  # each H sends ~650 bytes, about 5 s of airtime
            if "OK1ABC" not in s.conns:
                break
            self.bbs.server.receive("OK1ABC", "H\r")
        self.assertIn("TX time limit of 1 min reached", self.bbs.take("OK1ABC"))
        self.assertEqual(self.bbs.dropped, ["OK1ABC"])

    def test_full_bbs_refuses_new_messages(self):
        update_settings(self.folder, {("limits", "max_messages"): 1})
        s = self.bbs.server
        s.reload()
        s.connected("OK1ABC")
        self.bbs.take("OK1ABC")
        self.assertIn("Message #1 saved.", self.bbs.say("OK1ABC", "S OK1XYZ", "a", "b", "/EX"))
        self.assertIn("the BBS is full (1 messages)", self.bbs.say("OK1ABC", "S OK1XYZ"))

    def test_broken_edit_is_not_written(self):
        before = (self.folder / "bbs.toml").read_text(encoding="utf-8")
        (self.folder / "bbs.toml").write_text(before + "\n[broken\n", encoding="utf-8")
        with self.assertRaises(BbsConfigError):
            update_settings(self.folder, {("limits", "max_sessions"): 1})


class EngineBbsTest(unittest.IsolatedAsyncioTestCase):
    async def test_engine_answers_on_the_bbs_ssid(self):
        with tempfile.TemporaryDirectory() as tmp:
            eng = Engine(Config(callsign="OK1SIM-7", bbs_enabled=True, bbs_ssid=1).validate(), pathlib.Path(tmp))
            sent = []

            async def send_frame(raw):
                sent.append(Frame.decode(raw))

            eng.send_frame = send_frame
            self.assertEqual(str(eng.bbs_call), "OK1SIM-1")
            self.assertTrue((pathlib.Path(tmp) / "bbs" / "bbs.toml").exists())
            sabm = Frame(Address.parse("OK1SIM-1"), Address.parse("OK1ABC"), [], b"", 0x2F | 0x10, None, True)
            eng._on_frame(sabm.encode())  # transmitting is off: refused
            self.assertNotIn("OK1ABC", eng.bbs_sessions)
            eng.set_tx(True)
            eng._on_frame(sabm.encode())
            self.assertIn("OK1ABC", eng.bbs_sessions)
            self.assertIn("OK1ABC", eng.bbs.conns)
            for s in eng.bbs_sessions.values():
                s.close()

    async def test_bbs_mode_switches_everything_else_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            conf = Config(callsign="OK1SIM-7", bbs_enabled=True, bbs_ssid=1, aprsis_enabled=True,
                          licence_confirmed=True, igate_rx=True, accept_incoming=True).validate()
            eng = Engine(conf, pathlib.Path(tmp))
            self.assertTrue(eng.bbs_mode)
            self.assertIsNone(eng.aprsis)
            self.assertFalse(eng.igate_rx or eng.accept_incoming)
            eng.set_tx(True)
            with self.assertRaises(TransmitRefused):
                await eng.send_aprs_message("OK1ABC", "hi")
            with self.assertRaises(TransmitRefused):
                eng.connect("OK0BBS")
            with self.assertRaises(TransmitRefused):
                await eng.send_chat("hi")
            # an APRS position heard on the radio is ignored
            eng._on_frame(Frame(Address.parse("APRS"), Address.parse("OK1XYZ"), [], b"!4942.00N/01318.00E-").encode())
            self.assertEqual(eng.station.heard, {})
            self.assertTrue(eng.monitor)  # the monitor still shows what the radio hears

    async def test_same_ssid_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            eng = Engine(Config(callsign="OK1SIM-1", bbs_enabled=True, bbs_ssid=1).validate(), pathlib.Path(tmp))
            self.assertIsNone(eng.bbs)
            self.assertIn("another SSID", eng.bbs_error)


if __name__ == "__main__":
    unittest.main()
