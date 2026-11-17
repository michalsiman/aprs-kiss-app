"""Light or dark: the user's choice, or on "auto" what the desktop prefers.

Flutter follows the desktop's light/dark preference (on Linux the portal's
org.freedesktop.appearance color-scheme). Many desktops, Linux Mint's Cinnamon among them, leave that
at "no preference" and make things dark only through the theme, so then the GTK theme's name
decides ("Mint-Y-Dark-Aqua", "Adwaita-dark"). The portal is asked through `gdbus`, which works the
same inside the Flatpak sandbox.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import sys

import flet as ft

_LOGGER = logging.getLogger(__name__)

MODES = ("auto", "light", "dark")
_PORTAL = ["gdbus", "call", "--session", "--dest", "org.freedesktop.portal.Desktop",
           "--object-path", "/org/freedesktop/portal/desktop",
           "--method", "org.freedesktop.portal.Settings.ReadOne"]


def _read(namespace: str, key: str) -> str | None:
    try:
        out = subprocess.run([*_PORTAL, namespace, key], capture_output=True, text=True, timeout=2, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout


def parse_color_scheme(text: str | None) -> bool | None:
    """'(<uint32 1>,)' → True (dark), 2 → False (light), 0 or unknown → None."""
    m = re.search(r"uint32 (\d+)", text or "")
    return {1: True, 2: False}.get(int(m.group(1))) if m else None


def theme_is_dark(name: str | None) -> bool:
    return "dark" in (name or "").lower()


def desktop_prefers_dark() -> bool | None:
    """True/False when the Linux desktop says so, None when it can't be told (or not Linux). Blocking."""
    if not sys.platform.startswith("linux") or not shutil.which("gdbus"):
        return None
    pref = parse_color_scheme(_read("org.freedesktop.appearance", "color-scheme"))
    if pref is not None:
        return pref
    m = re.search(r"'([^']*)'", _read("org.gnome.desktop.interface", "gtk-theme") or "")
    return theme_is_dark(m.group(1)) if m else None


def theme_mode(choice: str, desktop_dark: bool | None) -> ft.ThemeMode:
    if choice == "light":
        return ft.ThemeMode.LIGHT
    if choice == "dark":
        return ft.ThemeMode.DARK
    if desktop_dark is None:
        return ft.ThemeMode.SYSTEM
    return ft.ThemeMode.DARK if desktop_dark else ft.ThemeMode.LIGHT
