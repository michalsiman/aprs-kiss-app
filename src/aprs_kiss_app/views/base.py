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

    # Heavy screens (maps, long forms) are built the first time they are shown: switching modes or
    # starting the app then sends far less to the window. Their on_event only marks them stale.
    lazy = False

    def __init__(self, app: App) -> None:
        self.app = app
        self._control: ft.Control | None = None
        if not self.lazy:
            self._control = adapt(self.build(), app.fit_width)

    @property
    def built(self) -> bool:
        return self._control is not None

    @property
    def control(self) -> ft.Control:
        if self._control is None:
            self._control = adapt(self.build(), self.app.fit_width)
        return self._control

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


def _uppercase(field: ft.TextField) -> None:
    """Callsigns are capitals whatever is typed (phone keyboards often ignore the capitalization hint)."""
    original = field.on_change

    async def on_change(e) -> None:
        value = field.value or ""
        if value != value.upper():
            field.value = value.upper()
            field.update()
        if original:
            result = original(e)
            if hasattr(result, "__await__"):
                await result

    field.on_change = on_change


def _wrapping(box: ft.Checkbox) -> ft.Control:
    """A checkbox whose label wraps onto more lines (Flutter's own label stays on one line)."""
    text, box.label = box.label, None
    handler = box.on_change

    async def toggle(e) -> None:
        if box.disabled:
            return
        box.value = not box.value
        box.update()
        if handler:
            result = handler(ft.Event("change", box))
            if hasattr(result, "__await__"):
                await result

    return ft.Row([box, ft.Container(ft.Text(text), expand=True, on_click=toggle)],
                  spacing=0, visible=box.visible, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def _children(control: ft.Control) -> list:
    out = []
    for name in ("content", "controls", "actions", "title"):
        value = getattr(control, name, None)
        if isinstance(value, ft.Control):
            out.append(value)
        elif isinstance(value, list):
            out.extend(c for c in value if isinstance(c, ft.Control))
    return out


def adapt(control: ft.Control, fit_width: float | None = None) -> ft.Control:
    """Make a built screen or dialog fit: capitals in callsign fields, and on a phone
    (`fit_width` set) no field or box wider than the screen and checkbox labels that wrap."""
    stack, seen = [(control, None)], set()
    while stack:
        c, parent = stack.pop()
        if id(c) in seen:
            continue
        seen.add(id(c))
        if isinstance(c, ft.TextField) and c.capitalization == ft.TextCapitalization.CHARACTERS:
            _uppercase(c)
        if fit_width:
            width = getattr(c, "width", None)
            if isinstance(width, (int, float)) and width > fit_width:
                c.width = fit_width if isinstance(c, (ft.TextField, ft.Dropdown)) else None
            if (isinstance(c, ft.Checkbox) and isinstance(c.label, str) and isinstance(parent, ft.Column)
                    and c in parent.controls):
                parent.controls[parent.controls.index(c)] = _wrapping(c)  # a long label wraps
        stack.extend((child, c) for child in _children(c))
    return control
