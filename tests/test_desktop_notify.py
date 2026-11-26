import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprs_kiss_app import desktop_notify as d  # noqa: E402


def has(*names):
    return lambda n: f"/usr/bin/{n}" if n in names else None


class DesktopNotifyTest(unittest.TestCase):
    def test_gvariant_quotes(self):
        self.assertEqual(d.gvariant("it's \\ ok"), "'it\\'s \\\\ ok'")

    def test_linux_plain_then_notify_send(self):
        cands = d.commands("Zpráva od OK1ABC", "-1 'ahoj'", "message", "linux", False, has("gdbus", "notify-send"))
        self.assertEqual([c[0][0] for c in cands], ["gdbus", "notify-send"])
        gd = cands[0][0]
        self.assertIn("org.freedesktop.Notifications.Notify", gd)
        self.assertEqual(gd[gd.index("--") + 5], "'-1 \\'ahoj\\''")  # after "--": a text starting with "-" is no option
        self.assertEqual(cands[1][0][-2:], ["Zpráva od OK1ABC", "-1 'ahoj'"])

    def test_flatpak_uses_the_portal(self):
        cmd = d.commands("T", "x", "chat", "linux", True, has("gdbus"))[0][0]
        self.assertIn("org.freedesktop.portal.Notification.AddNotification", cmd)
        self.assertEqual(cmd[cmd.index("--") + 1], "'chat'")

    def test_windows_texts_go_in_the_environment(self):
        (cmd, env), = d.commands("Zpráva", "<b>&", "message", "win32")
        self.assertEqual(cmd[0], "powershell")
        self.assertEqual(env, {"APRS_KISS_N_TITLE": "Zpráva", "APRS_KISS_N_TEXT": "<b>&"})
        self.assertNotIn("<b>&", cmd[-1])

    def test_macos_texts_are_arguments(self):
        (cmd, env), = d.commands("Zpráva", 'say "hi"', "message", "darwin")
        self.assertEqual(cmd[0], "osascript")
        self.assertEqual(cmd[-2:], ["Zpráva", 'say "hi"'])

    def test_nothing_elsewhere(self):
        self.assertEqual(d.commands("a", "b", "message", "linux", False, has()), [])
        self.assertEqual(d.commands("a", "b", "message", "emscripten"), [])


if __name__ == "__main__":
    unittest.main()
