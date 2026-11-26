"""A notification of the computer's own system (Linux, Windows, macOS), without extra libraries.

- Linux: the desktop's notifications over D-Bus with `gdbus` (the Flatpak through the notification portal,
  which needs no extra permission); `notify-send` when there is no gdbus.
- Windows: a toast through PowerShell (WinRT), shown under "Windows PowerShell".
- macOS: `osascript` (display notification).

Each runs as its own process in a thread: a missing tool or a refused notification only means no
notification. The texts go as arguments or environment variables, never pasted into a command line.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading

_LOGGER = logging.getLogger(__name__)

APP_ID = "io.github.michalsiman.aprs_kiss_app"

_WINDOWS_SCRIPT = r"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null
$t = [Security.SecurityElement]::Escape($env:APRS_KISS_N_TITLE)
$b = [Security.SecurityElement]::Escape($env:APRS_KISS_N_TEXT)
$x = New-Object Windows.Data.Xml.Dom.XmlDocument
$x.LoadXml("<toast><visual><binding template='ToastGeneric'><text>$t</text><text>$b</text></binding></visual></toast>")
$id = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($id).Show([Windows.UI.Notifications.ToastNotification]::new($x))
"""

_MAC_SCRIPT = ["-e", "on run argv", "-e", "display notification (item 2 of argv) with title (item 1 of argv)",
               "-e", "end run"]


def gvariant(text: str) -> str:
    """A string in GVariant's text form (what gdbus takes as an argument)."""
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n") + "'"


def commands(title: str, text: str, tag: str, platform: str | None = None, flatpak: bool | None = None,
             which=shutil.which) -> list[tuple[list[str], dict[str, str] | None]]:
    """The command(s) to try, first that starts wins; each with extra environment variables or None."""
    platform = platform or sys.platform
    text = text[:300]
    if platform.startswith("linux"):
        flatpak = os.path.exists("/.flatpak-info") if flatpak is None else flatpak
        out = []
        if which("gdbus"):
            if flatpak:  # the portal: the notification is the app's own (its name and icon)
                out.append((["gdbus", "call", "--session", "--dest", "org.freedesktop.portal.Desktop",
                             "--object-path", "/org/freedesktop/portal/desktop",
                             "--method", "org.freedesktop.portal.Notification.AddNotification", "--", gvariant(tag),
                             "{'title': <%s>, 'body': <%s>, 'priority': <'high'>}" % (gvariant(title), gvariant(text))],
                            None))
            else:
                out.append((["gdbus", "call", "--session", "--dest", "org.freedesktop.Notifications",
                             "--object-path", "/org/freedesktop/Notifications",
                             "--method", "org.freedesktop.Notifications.Notify", "--", gvariant("APRS & Packet"), "0",
                             gvariant(APP_ID), gvariant(title), gvariant(text), "[]", "{'desktop-entry': <%s>}" % gvariant(APP_ID), "-1"], None))
        if which("notify-send"):
            out.append((["notify-send", "--app-name=APRS & Packet", f"--icon={APP_ID}", "--", title, text], None))
        return out
    if platform == "win32":
        return [(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                  "-Command", _WINDOWS_SCRIPT], {"APRS_KISS_N_TITLE": title, "APRS_KISS_N_TEXT": text})]
    if platform == "darwin":
        return [(["osascript", *_MAC_SCRIPT, title, text], None)]
    return []


def _run(cands: list[tuple[list[str], dict[str, str] | None]]) -> None:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # Windows: no console window flashing up
    for cmd, env in cands:
        try:
            done = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, timeout=20,
                                  env={**os.environ, **env} if env else None, creationflags=flags, check=False)
            if done.returncode == 0:
                return
            _LOGGER.info("Notification with %s: %s", cmd[0], done.stderr[:200])
        except (OSError, subprocess.SubprocessError) as err:
            _LOGGER.info("Notification with %s: %s", cmd[0], err)


def notify(title: str, text: str, tag: str = "message") -> bool:
    """Show the notification (in a thread, the next way when one fails); False when there is no way at all."""
    cands = commands(title, text, tag)
    if cands:
        threading.Thread(target=_run, args=(cands,), daemon=True, name="notify").start()
    return bool(cands)
