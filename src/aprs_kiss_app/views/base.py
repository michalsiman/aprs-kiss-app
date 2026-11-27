"""What every screen of the app has in common, and small helpers."""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING, Any

import flet as ft
from aprs_kiss_core import units

if TYPE_CHECKING:
    from ..app import App

MONO = "monospace"
LONG_LABEL = 28  # characters: longer field labels go above the field on a phone


class View:
    """One screen. `control` is built once; `refresh` brings it up to date when it is shown."""

    key = ""
    icon = ft.Icons.CIRCLE
    selected_icon: ft.IconData | None = None

    # Heavy screens (maps, long forms) are built the first time they are shown: switching modes or
    # starting the app then sends far less to the window. Their on_event only marks them stale.
    lazy = False
    in_menu = True  # False: reached from another screen (APRS Thursday from Messages › Services), not the menu
    keep_alive = False  # stays under the other screens instead of being hidden (the map)

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

    def can_back(self) -> bool:
        """Something inside the screen to go back from (an open conversation on a phone)."""
        return False

    def go_back(self) -> None:
        """Android's back gesture when can_back(): one step back inside the screen."""


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


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """The initial direction from the first point to the second, degrees from north (0–360)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    return math.degrees(math.atan2(math.sin(dl) * math.cos(p2),
                                   math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl))) % 360


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][round(bearing_deg(lat1, lon1, lat2, lon2) / 45) % 8]


def distance_text(km: float) -> str:
    """A distance in the units the user has chosen ("4.25 km", "2.64 mi")."""
    return units.current.distance_text(km)


def distance_short(km: float) -> str:
    """A distance for a list ("3.4 km", "12 km", "350 m"; or mi / ft)."""
    return units.current.distance_short(km)


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
            label = getattr(c, "label", None)
            if (isinstance(c, (ft.TextField, ft.Dropdown)) and isinstance(label, str) and len(label) > LONG_LABEL
                    and isinstance(parent, (ft.Column, ft.Row)) and c in parent.controls and not c.expand):
                # a long label would wrap inside the border, over the value: above the field instead
                c.label = None
                parent.controls[parent.controls.index(c)] = ft.Column(
                    [ft.Text(label, size=12, color=ft.Colors.ON_SURFACE_VARIANT), c], spacing=2, visible=c.visible)
            if (isinstance(c, ft.Checkbox) and isinstance(c.label, str) and isinstance(parent, ft.Column)
                    and c in parent.controls):
                parent.controls[parent.controls.index(c)] = _wrapping(c)  # a long label wraps
        stack.extend((child, c) for child in _children(c))
    return control


def toggle(icon: str, selected_icon: str, selected: bool, tooltip: str, on_click) -> ft.IconButton:
    """An on/off icon, the same on every screen: the plain (or crossed-out) icon when off, the filled one on a tinted background when on."""
    return ft.IconButton(icon, selected_icon=selected_icon, selected=selected, tooltip=tooltip, on_click=on_click,
                         style=ft.ButtonStyle(bgcolor={ft.ControlState.SELECTED:
                                                       ft.Colors.with_opacity(0.18, ft.Colors.PRIMARY)}))



CHECK_TEXT_WIDTH = 170  # the box, the icon and this fit a pop-up menu (Flutter: at most 280 wide)


def check_item(text: str, icon, value: bool, on_change) -> tuple[ft.PopupMenuItem, ft.Checkbox]:
    """An on/off line in a menu: a box (an empty faint frame when off) with the icon and text as its label.
    The tap belongs to the box, so the menu stays open; it closes with back or a tap outside it."""
    box = ft.Checkbox(
        # a long text (French, Spanish, Ukrainian…) wraps to a second line instead of running out of the menu,
        # which Flutter keeps at most 280 wide
        label=ft.Row([ft.Icon(icon), ft.Text(text, max_width=CHECK_TEXT_WIDTH)], spacing=12, tight=True),
        value=value, on_change=on_change,
        border_side={ft.ControlState.DEFAULT: ft.BorderSide(1.5, ft.Colors.with_opacity(0.4, ft.Colors.ON_SURFACE)),
                     ft.ControlState.SELECTED: ft.BorderSide(0, ft.Colors.TRANSPARENT)},
    )
    return ft.PopupMenuItem(content=box), box


def walkie_talkie(color, size: float = 24) -> ft.Control:
    """A handheld radio (Material has no such icon): our own drawing, tinted like an icon."""
    return ft.Image(src="walkie_talkie.svg", width=size, height=size, color=color,
                    color_blend_mode=ft.BlendMode.SRC_IN)


class ViaPicker:
    """How a message goes: two on/off icons, the radio and the internet (one or both, never none), remembered
    in a config field until changed. Only the radio while APRS-IS is off (then the icons are hidden)."""

    WAYS = ("radio", "internet", "both")

    def __init__(self, app, field: str, default) -> None:
        self.app, self.field, self.default = app, field, default  # default(): the way while none was chosen
        t = app.t
        self.radio = toggle(walkie_talkie(ft.Colors.with_opacity(0.35, ft.Colors.ON_SURFACE)),
                            walkie_talkie(ft.Colors.PRIMARY), False, t("via_radio"),
                            lambda _e: self._flip(self.radio, self.net))
        self.net = toggle(ft.Icons.PUBLIC, ft.Icons.PUBLIC, False, t("via_internet"),
                          lambda _e: self._flip(self.net, self.radio))
        for b in (self.radio, self.net):  # off: faint; on: the accent colour on a tint
            b.icon_color = ft.Colors.with_opacity(0.35, ft.Colors.ON_SURFACE)
            b.selected_icon_color = ft.Colors.PRIMARY
        self.control = ft.Row([self.radio, self.net], spacing=2, tight=True)
        self.sync()

    def saved(self) -> str:
        way = getattr(self.app.engine.config, self.field, "")
        return way if way in self.WAYS else self.default()

    def sync(self) -> None:
        """Show the saved way (and the icons only with APRS-IS)."""
        way = self.saved()
        self.radio.selected, self.net.selected = way in ("radio", "both"), way in ("internet", "both")
        self.control.visible = self.app.engine.aprsis is not None

    def value(self) -> str:
        if not self.control.visible:
            return "radio"
        radio, net = self.radio.selected, self.net.selected
        return "both" if radio and net else "internet" if net else "radio"

    def _flip(self, button, other) -> None:
        if button.selected and not other.selected:  # one of them stays on: a message must go somewhere
            self.app.toast(self.app.t("via_one_needed"))
            return
        button.selected = not button.selected
        setattr(self.app.engine.config, self.field, self.value())
        self.app.save_config_soon()  # remembered until changed
        self.app.page.update()


STAY_WIDTH = 250  # the tappable width of a menu line that keeps the menu open


def stay_item(content: ft.Control, on_click, disabled: bool = False) -> tuple[ft.PopupMenuItem, ft.Container]:
    """A menu line whose tap does its thing and leaves the menu open (the tap belongs to the inner box, not to
    the menu item, which would close the menu); back or a tap outside closes it. The box's content can be
    replaced later (refresh)."""
    box = ft.Container(content, on_click=on_click, disabled=disabled, width=STAY_WIDTH,
                       padding=ft.Padding.symmetric(vertical=10), alignment=ft.Alignment.CENTER_LEFT)
    return ft.PopupMenuItem(content=box, disabled=disabled), box


def menu_line(icon, text: str, color=None) -> ft.Control:
    """An icon and a text as a menu item shows them (for stay_item)."""
    return ft.Row([ft.Icon(icon, color=color), ft.Text(text, color=color, max_width=STAY_WIDTH - 40)],
                  spacing=12, tight=True)


def message_text(app, text: str, **kwargs) -> ft.Text:
    """A received or sent text; web links in it underlined and clickable, opening after a warning (anybody can
    send anything: the page may be harmful). Without links the text stays selectable."""
    from aprs_kiss_core.links import split_links  # noqa: PLC0415

    parts = split_links(text)
    if not any(url for _piece, url in parts):
        return ft.Text(text, selectable=True, **kwargs)
    spans = [ft.TextSpan(piece, style=ft.TextStyle(color=ft.Colors.PRIMARY, decoration=ft.TextDecoration.UNDERLINE),
                         on_click=lambda _e, url=url: confirm_link(app, url)) if url else ft.TextSpan(piece)
             for piece, url in parts]
    return ft.Text(spans=spans, **kwargs)


def confirm_link(app, url: str) -> None:
    """Before a link from a message opens: where it leads, and that nobody vouches for it."""
    t = app.t

    async def go(_e) -> None:
        app.page.pop_dialog()
        await ft.UrlLauncher().launch_url(url)

    app.show_dialog(ft.AlertDialog(
        icon=ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.ERROR),
        title=ft.Text(t("link_title")),
        content=ft.Column([
            ft.Text(url, selectable=True, size=13, font_family="monospace", color=ft.Colors.PRIMARY),
            ft.Text(t("link_warning")),
        ], tight=True, spacing=12, width=420),
        actions=[ft.TextButton(t("cancel"), on_click=lambda _e: app.page.pop_dialog()),
                 ft.FilledButton(t("link_open"), icon=ft.Icons.OPEN_IN_NEW, on_click=go)],
    ))
