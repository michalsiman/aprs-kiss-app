"""The station server: the web password, who needs it, Transmit over a restart; the display's frame words."""

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aprs_kiss_app import server  # noqa: E402
from aprs_kiss_app.display import path_text  # noqa: E402
from aprs_kiss_core import packetinfo  # noqa: E402
from aprs_kiss_core.parser import parse  # noqa: E402


class PasswordTest(unittest.TestCase):
    def test_hash_and_check(self):
        stored = server.hash_password("tajne123", rounds=1000)
        self.assertTrue(stored.startswith("pbkdf2_sha256$1000$"))
        self.assertTrue(server.check_password("tajne123", stored))
        self.assertFalse(server.check_password("tajne124", stored))
        self.assertFalse(server.check_password("tajne123", "garbage"))
        self.assertNotEqual(server.hash_password("x", rounds=1000), server.hash_password("x", rounds=1000))

    def test_file(self):
        with tempfile.TemporaryDirectory() as d:
            folder = pathlib.Path(d)
            self.assertEqual(server.load_password(folder), "")
            server.save_password(folder, "abc")
            self.assertTrue(server.check_password("abc", server.load_password(folder)))
            self.assertEqual((folder / server.PASSWORD_FILE).stat().st_mode & 0o777, 0o600)
            server.save_password(folder, "")
            self.assertEqual(server.load_password(folder), "")

    def test_local(self):
        self.assertTrue(server.is_local("127.0.0.1"))
        self.assertTrue(server.is_local("::1"))
        self.assertFalse(server.is_local("192.168.1.20"))
        self.assertFalse(server.is_local(None))
        self.assertFalse(server.is_local("nonsense"))

    def test_state(self):
        with tempfile.TemporaryDirectory() as d:
            folder = pathlib.Path(d)
            self.assertEqual(server.load_state(folder), {})
            server.save_state(folder, {"tx": True})
            self.assertEqual(server.load_state(folder), {"tx": True})


class PacketInfoTest(unittest.TestCase):
    def test_kinds_and_words(self):
        pos = parse("OK1ABC-9>APRS,WIDE1-1:=4944.70N/01324.25E>On the road")
        self.assertEqual(packetinfo.kind(pos), "position")
        self.assertEqual(packetinfo.summary(pos), "49.74500, 13.40417 · On the road")
        msg = parse("OK1ABC>APRS::OK1SIM-7 :Ahoj{12")
        self.assertEqual(packetinfo.kind(msg), "message")
        self.assertEqual(packetinfo.summary(msg), "→ OK1SIM-7: Ahoj")
        obj = parse("OK1KPL-10>APRS:;439.350MO*111111z4946.27N/01327.78Er439.350MHz")
        self.assertEqual(packetinfo.kind(obj), "object")
        self.assertTrue(packetinfo.summary(obj).startswith("439.350MO · 49.77"))
        wx = parse("OK1WX-13>APRS:@111111z4942.12N/01326.46E_270/004g009t041r000p000P000h85b10142")
        self.assertEqual(packetinfo.kind(wx), "weather")
        self.assertIn("5.0 °C", packetinfo.summary(wx, lambda w: f"{w['temperature']:.1f} °C"))
        bln = parse("OK1ABC>APRS::BLN1     :Net tonight")
        self.assertEqual((packetinfo.kind(bln), packetinfo.summary(bln)), ("bulletin", "BLN1: Net tonight"))
        st = parse("OK1ABC>APRS:>Listening on 144.800")
        self.assertEqual((packetinfo.kind(st), packetinfo.summary(st)), ("status", "Listening on 144.800"))
        third = parse("OK0MIL-1>APRS:}OK1XYZ>APRS,TCPIP,OK0MIL-1*::OK1SIM-7 :Hi{3")
        self.assertEqual(packetinfo.kind(third), "thirdparty")
        self.assertEqual(packetinfo.summary(third), "OK1XYZ: → OK1SIM-7: Hi")

    def test_path(self):
        self.assertEqual(path_text(["OK0DIG*", "WIDE2-1"]), "OK0DIG*,WIDE2-1")
        self.assertEqual(path_text(["TCPIP*"]), "")
        self.assertEqual(path_text([]), "")


if __name__ == "__main__":
    unittest.main()
