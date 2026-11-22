"""What every screen of the app has in common, and small helpers."""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING, Any

import flet as ft

if TYPE_CHECKING:
    from ..app import App

MONO = "monospace"


class View:
    """One screen. `control` is built once; `refresh` brings it up to date when it is shown."""

    key = ""
    icon = ft.Icons.CIRCLE
    selected_icon: ft.IconData | None = None

    def __init__(self, app: App) -> None:
        self.app = app
        self.control = self.build()

    @property
    def t(self):
        return self.app.t

    @property
    def engine(self):
        return self.app.engine

    def build(self) -> ft.Control:
        raise NotImplementedError

    def on_event(self, kind: str, data: dict[str, Any]) -> None:
        """Called for every engine event, also while hidden. No page.update() here: the app batches it."""

    def refresh(self) -> None:
        """Called when the view is shown and, while shown, after events (rate limited by the app)."""

    def shown(self) -> None:
        self.refresh()


def short_path(path) -> str:
    """A path with the home folder as ~, shorter to read (and without the user name)."""
    from pathlib import Path  # noqa: PLC0415

    text, home = str(path), str(Path.home())
    return "~" + text[len(home):] if text == home or text.startswith(home + "/") or text.startswith(home + "\\") else text


def clock(ts: float | None) -> str:
    if not ts:
        return ""
    if time.time() - ts > 20 * 3600:
        return time.strftime("%d.%m. %H:%M", time.localtime(ts))
    return time.strftime("%H:%M:%S", time.localtime(ts))


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    deg = math.degrees(math.atan2(math.sin(dl) * math.cos(p2),
                                  math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl))) % 360
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][round(deg / 45) % 8]


def capped_append(lv: ft.ListView, control: ft.Control, limit: int) -> None:
    lv.controls.append(control)
    if len(lv.controls) > limit:
        del lv.controls[: len(lv.controls) - limit]
