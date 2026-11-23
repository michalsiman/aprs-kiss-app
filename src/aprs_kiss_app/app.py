"""The APRS & Packet app: one window, a navigation rail, a status bar and the screens."""

from __future__ import annotations

import asyncio
import os
import contextlib
import logging
import time
from collections.abc import Awaitable
from typing import Any

import flet as ft

from aprs_kiss_core import android_usb
from aprs_kiss_core.config import VERSION, Config, data_dir, load_config, save_config

from . import theme
from aprs_kiss_core.engine import Engine, TransmitRefused

from .about import show_about
from . import disclaimer, distribution, language, updates
from .sounds import Sounds
from .i18n import Translator
from .phone_gps import PhoneGps
from .symbols import symbol_info
from .views.base import View, adapt, clock
from .views.bbs import BbsView
from .views.tak import TakView
from .views.chat import ChatView
from .views.map import MapView
from .views.messages import MessagesView
from .views.monitor import MonitorView
from .views.settings import SettingsView
from .views.stations import StationsView, describe
from .views.terminal import TerminalView
from .views.thursday import ThursdayView

_LOGGER = logging.getLogger(__name__)

VIEWS = [MapView, MessagesView, ThursdayView, StationsView, TerminalView, ChatView, MonitorView, BbsView, TakView,
         SettingsView]
# With BBS SERVER on the app is only the BBS; the monitor stays to see what the radio hears.
BBS_VIEWS = [BbsView, MonitorView, SettingsView]
TAK_VIEWS = [TakView, MonitorView, SettingsView]
FLUSH_DELAY = 0.25
TICK_SECONDS = 5.0
THEME_EVERY = 6  # ticks: the desktop theme is looked at every 30 s


COMPACT_WIDTH = 700  # narrower than this (a phone): the compact layout

class App:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.folder = data_dir()
        self.engine: Engine | None = None
        self.views: list[View] = []
        self.current = 0
        self._flush_pending = False
        self._closing = False
        self.update_state = updates.UpdateState()
        self._desktop_dark: bool | None = None
        self._building = False
        self.compact = False  # a phone: a menu sliding in from the side instead of the rail, a slimmer top bar

    # ─── start and stop ───────────────────────────────────────────────────

    async def start(self) -> None:
        page = self.page
        page.title = "APRS & Packet"
        page.theme_mode = ft.ThemeMode.SYSTEM
        page.theme = self._theme()
        page.dark_theme = self._theme()
        page.padding = 0
        page.window.prevent_close = True
        page.window.on_event = self._on_window_event
        page.on_close = self._on_page_close  # web and mobile: the session ended
        page.window.min_width = 640
        page.window.min_height = 480
        page.on_resize = self._on_resize

        android_usb.register()  # Android: a TNC on the phone's USB port
        config = await asyncio.to_thread(load_config, self.folder)
        if config.gps_source == "phone" and not self.mobile:  # settings copied from a phone
            config = Config.from_dict({**config.to_dict(), "gps_source": "manual"}).validate()
        if self.mobile and config.gps_source == "manual" and not config.has_position:
            # a phone with no position typed in: its own GPS, so the map and the beacon know where we are
            config = Config.from_dict({**config.to_dict(), "gps_source": "phone"}).validate()
        if self.mobile and (config.bbs_enabled or config.connection == "serial" or config.gps_source == "usb"):
            # what a phone does not do: BBS SERVER, a USB GPS; a serial TNC is reached through USB instead
            config = Config.from_dict({**config.to_dict(), "bbs_enabled": False,
                                       "connection": ("usb" if android_usb.available() else "tcp")
                                       if config.connection == "serial" else config.connection,
                                       "gps_source": "manual"}).validate()
        self.engine = Engine(config, self.folder)
        self.sounds = Sounds(self)
        self.engine.add_listener(self._on_event)
        await self.engine.start()
        self.phone_gps = PhoneGps(self)
        await language.detect(page)  # phones say their language only this way
        await self.apply_theme()
        self.build()
        if not config.configured:
            self.select("settings")
        if language.needed(self) and config.disclaimer_accepted:
            config.language_asked = True  # an existing install: its language is set already
            self.save_config_soon()
        first_warning = lambda: disclaimer.show(self) if disclaimer.needed(self) else None  # noqa: E731
        if language.needed(self):
            language.show(self, then=first_warning)  # the very first start: the language, then the warning
        else:
            first_warning()
        self.phone_gps.sync()
        page.run_task(self._tick)
        page.run_task(self._check_updates_later)
        page.run_task(self._watch_internet)

    async def _on_window_event(self, e: ft.WindowEvent) -> None:
        if e.type == ft.WindowEventType.CLOSE:
            self._confirm_quit()

    def _confirm_quit(self) -> None:
        """Closing the window stops receiving, beacons and the iGate, so ask first."""
        if self._closing:
            return
        st = self.engine.status()
        what = [self.t("quit_rx")]
        if self.engine.config.beacon_minutes and st["tx_enabled"]:
            what.append(self.t("quit_beacon"))
        if self.engine.aprsis and (self.engine.config.igate_rx or self.engine.config.igate_tx):
            what.append(self.t("quit_igate"))
        if st["sessions"]:
            what.append(self.t("quit_sessions", n=len(st["sessions"])))

        async def quit_now(_e) -> None:
            self.page.pop_dialog()
            await self.shutdown()
            await self.page.window.destroy()

        async def minimize(_e) -> None:
            self.page.pop_dialog()
            self.page.window.minimized = True
            self.page.update()

        self.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text(self.t("quit_title")),
            content=ft.Column([ft.Text(self.t("quit_text")), *[ft.Text(f"• {w}") for w in what]],
                              tight=True, spacing=6, width=420),
            actions=[
                ft.TextButton(self.t("quit_minimize"), icon=ft.Icons.MINIMIZE, on_click=minimize),
                ft.TextButton(self.t("quit_stay"), on_click=lambda _e: self.page.pop_dialog()),
                ft.FilledButton(self.t("quit_yes"), icon=ft.Icons.POWER_SETTINGS_NEW, on_click=quit_now,
                                style=ft.ButtonStyle(bgcolor=ft.Colors.ERROR, color=ft.Colors.ON_ERROR)),
            ],
        ))

    async def _on_page_close(self, _e) -> None:
        await self.shutdown()

    async def shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        if self.engine:
            with contextlib.suppress(Exception):
                await self.engine.stop()

    async def apply_config(self, config: Config) -> None:
        language_changed = config.language != self.engine.config.language
        old = self.engine.config
        mode_changed = (config.bbs_enabled, config.tak_enabled) != (old.bbs_enabled, old.tak_enabled)
        t0 = time.monotonic()
        await asyncio.to_thread(save_config, config, self.folder)
        await self.engine.reconfigure(config)
        self.phone_gps.sync()
        t1 = time.monotonic()
        if language_changed or mode_changed:
            self.build()
            # stay in the section whose switch was turned (on or off)
            self.select(("tak" if config.tak_enabled != old.tak_enabled else "bbs") if mode_changed else "settings")
        self.toast(self.t("saved"))
        self.refresh_now()
        _LOGGER.info("Settings applied: radio %.2f s, screen %.2f s", t1 - t0, time.monotonic() - t1)

    async def set_position(self, lat: float, lon: float) -> None:
        """From the map: becomes my position, saved at once and shown in Settings."""
        conf = Config.from_dict({**self.engine.config.to_dict(), "latitude": lat, "longitude": lon}).validate()
        await self.apply_config(conf)
        self.view("settings").show_position(lat, lon)
        self.toast(self.t("position_set", lat=f"{lat:.5f}", lon=f"{lon:.5f}"))

    # ─── layout ───────────────────────────────────────────────────────────

    @property
    def mobile(self) -> bool:
        """A phone or tablet (Android, iOS): no BBS SERVER, no USB GPS. APRS_KISS_PHONE=1 pretends one (tests)."""
        return (self.page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
                or os.environ.get("APRS_KISS_PHONE") == "1")

    def _theme(self) -> ft.Theme:
        """Phones get smaller type and denser fields: their screens are narrow and many have large fonts set."""
        if not self.mobile:
            return ft.Theme(color_scheme_seed=ft.Colors.INDIGO)
        size = lambda n: ft.TextStyle(size=n, color=ft.Colors.ON_SURFACE)  # noqa: E731 - a style without a color turns black
        return ft.Theme(
            color_scheme_seed=ft.Colors.INDIGO,
            visual_density=ft.VisualDensity.COMPACT,
            text_theme=ft.TextTheme(
                body_large=size(14), body_medium=size(13), body_small=size(11),
                title_large=size(18), title_medium=size(14), title_small=size(13),
                label_large=size(13), label_medium=size(11), label_small=size(10),
                headline_small=size(19), headline_medium=size(22),
            ),
            input_decoration_theme=ft.InputDecorationTheme(
                dense=True, content_padding=ft.Padding.symmetric(horizontal=10, vertical=10)),
        )

    @property
    def fit_width(self) -> float | None:
        """On a phone: how wide a field or box on a screen may be (None: any width)."""
        if not self.compact:
            return None
        return max(220.0, (self.page.width or 400) - 56)

    def _tnc_info(self, _e=None) -> None:
        """A phone has no hover: a tap on "TNC" tells what is going on with it."""
        st = self.engine.status()
        self.toast(self.tnc_text.value if st["tnc_connected"] else (st.get("tnc_error") or self.tnc_text.value or ""),
                   error=not st["tnc_connected"])

    @staticmethod
    def _lamp(text: str, on_click) -> ft.Container:
        return ft.Container(ft.Text(text, size=12, weight=ft.FontWeight.BOLD), on_click=on_click,
                            padding=ft.Padding.symmetric(horizontal=5, vertical=1), border_radius=5,
                            border=ft.Border.all(1.5, ft.Colors.OUTLINE))

    def _light(self, key: str, state: str | None) -> None:
        """A lamp: "on" green, "tx" red and filled, None grey; hidden when the thing is not in use."""
        lamp = self.lamps[key]
        color = {"on": ft.Colors.GREEN, "tx": ft.Colors.RED, "armed": ft.Colors.RED}.get(state, ft.Colors.OUTLINE)
        lamp.border = ft.Border.all(1.5, color)
        lamp.bgcolor = ft.Colors.RED if state == "tx" else None
        lamp.content.color = ft.Colors.WHITE if state == "tx" else color

    _on_air_until = 0.0

    def _on_air(self, line: str) -> None:
        """A frame went out by radio: the TX lamp is all red for about as long as it takes on air."""
        if " >> " not in line[:12] or "[IS] " in line[12:18]:
            return
        conf = self.engine.config
        seconds = max(1.0, (len(line) - 12) * 8 / 1200 + (conf.txdelay_ms or 300) / 1000)  # 1200 Bd packet
        self._on_air_until = max(self._on_air_until, time.monotonic() + seconds)
        try:
            self.page.run_task(self._off_air, seconds)
        except Exception:  # noqa: BLE001 - the page is gone
            pass

    async def _off_air(self, seconds: float) -> None:
        await asyncio.sleep(seconds + 0.05)
        if time.monotonic() >= self._on_air_until and not self._closing:
            self.refresh_now()

    def _tx_tap(self, _e=None) -> None:
        if not self.engine.config.configured:
            self.toast(self.t("tx_off"))
            return
        self.engine.set_tx(not self.engine.station.tx_enabled)
        self.toast(self.t("tx_on") if self.engine.station.tx_enabled else self.t("tx_off"),
                   error=self.engine.station.tx_enabled)
        self.refresh_now()

    def _gps_info(self, _e=None) -> None:
        """A tap on "GPS": its state, or why there is no position."""
        gps = self.engine.status().get("gps") or {}
        self.toast(gps.get("error") or self.gps_text.value or "", error=not gps.get("fix"))

    def show_dialog(self, dialog: ft.DialogControl) -> None:
        """A dialog or message bar that fits the screen."""
        if self.compact:
            limit = max(200.0, (self.page.width or 400) - 120)
            if isinstance(dialog, ft.SnackBar):
                dialog.width = None
            else:
                adapt(dialog, limit)
                dialog.inset_padding = ft.Padding.symmetric(horizontal=16, vertical=24)
                dialog.content_padding = ft.Padding.only(left=18, right=18, top=12, bottom=8)
        else:
            adapt(dialog)
        self.page.show_dialog(dialog)

    def _is_compact(self, width: float | None = None) -> bool:
        page = self.page
        if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            return True
        width = width or getattr(page, "width", None) or 0
        return bool(width) and width < COMPACT_WIDTH

    def _on_resize(self, e) -> None:
        if self.views and self._is_compact(getattr(e, "width", None)) != self.compact:
            self.build()

    async def _open_menu(self, _e=None) -> None:
        await self.page.show_drawer()

    async def _menu_about(self, _e=None) -> None:
        await self.page.close_drawer()
        show_about(self)

    async def _menu_selected(self, e) -> None:
        """A screen picked in the phone's menu: the menu slides away and the screen opens."""
        await self.page.close_drawer()
        self.select(self.views[e.control.selected_index].key)

    def build(self) -> None:
        self.t = Translator(self.engine.config.language)
        self.compact = self._is_compact()
        key = self.current_key if self.views else "map"
        mode = self.engine.exclusive_mode
        classes = BBS_VIEWS if mode == "bbs" else TAK_VIEWS if mode == "tak" else VIEWS
        if self.mobile:  # BBS SERVER is for computers only
            classes = [c for c in classes if c is not BbsView]
        self.views = [cls(self) for cls in classes]
        if key not in {v.key for v in self.views}:
            key = self.views[0].key
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=88,
            destinations=[ft.NavigationRailDestination(icon=v.icon, selected_icon=v.selected_icon,
                                                       label=self.t(v.key)) for v in self.views],
            on_change=lambda e: self.select(self.views[e.control.selected_index].key),
        )
        # a phone: About is at the end of the menu (no room for its button in the top bar)
        self.about_item = ft.ListTile(leading=ft.Icon(ft.Icons.INFO_OUTLINE), title=ft.Text(self.t("about")),
                                      on_click=self._menu_about, content_padding=ft.Padding.only(left=28, right=12))
        # a phone: the screens in a menu that slides in from the left (the ☰ button) and hides again
        self.drawer = ft.NavigationDrawer(
            controls=[ft.Container(ft.Text("APRS & Packet", weight=ft.FontWeight.BOLD, size=16),
                                   padding=ft.Padding.only(left=28, top=20, bottom=12))]
            + [ft.NavigationDrawerDestination(icon=ft.Icon(v.icon), selected_icon=v.selected_icon, label=self.t(v.key))
               for v in self.views]
            + [ft.Divider(), self.about_item],
            on_change=self._menu_selected,
        )
        self.page.drawer = self.drawer if self.compact else None
        self.menu_btn = ft.IconButton(ft.Icons.MENU, tooltip=self.t("menu"), on_click=self._open_menu,
                                      visible=self.compact)
        pad = 6 if self.compact else 12
        # The map stays on screen under the other screens (they are opaque): hiding it would make
        # Flutter throw it away and build it again, tiles and all, at every return to it.
        self.holders = [ft.Container(v.control if v.built else None, visible=False, expand=True,
                                     padding=ft.Padding.all(pad), bgcolor=None if v.keep_alive else ft.Colors.SURFACE,
                                     left=0, top=0, right=0, bottom=0)
                        for v in self.views]
        stacked = sorted(range(len(self.views)), key=lambda i: not self.views[i].keep_alive)  # the map at the bottom

        self.callsign = ft.Text(weight=ft.FontWeight.BOLD, size=18)
        self.tnc_dot = ft.Icon(ft.Icons.CIRCLE, size=12)
        self.tnc_text = ft.Text(size=13)
        self.is_dot = ft.Icon(ft.Icons.CIRCLE, size=12)
        self.is_box = ft.Row([self.is_dot, ft.Text("APRS-IS", size=13)], spacing=4, tight=True)
        self.gps_dot = ft.Icon(ft.Icons.CIRCLE, size=12)
        self.gps_text = ft.Text(size=13)
        self.gps_box = ft.Row([self.gps_dot, ft.Text("GPS", size=13), self.gps_text], spacing=4, tight=True,
                              visible=False)
        open_release = lambda _e: self.page.run_task(self._open_release)  # noqa: E731
        # a phone: only an icon, the top bar is narrow (the version is in the message and in About)
        self.update_btn = (ft.IconButton(ft.Icons.NEW_RELEASES, icon_color=ft.Colors.PRIMARY, visible=False,
                                         on_click=open_release) if self.compact else
                           ft.FilledTonalButton(icon=ft.Icons.NEW_RELEASES, visible=False, on_click=open_release))
        self._show_update()
        self.tx_switch = ft.Switch(label=self.t("transmit"), on_change=self._tx_changed)
        self.tx_box = ft.Container(self.tx_switch, border_radius=20, padding=ft.Padding.symmetric(horizontal=10))
        if self.compact:
            self.tx_switch.label = None
        self.callsign.size = 16 if self.compact else 18
        self.tnc_text.visible = self.gps_text.visible = not self.compact
        # a phone: TNC, IS, GPS and TX as lamps on a dashboard - green when working, grey when not,
        # TX red while transmitting is on; a tap tells the state (TX: switches it)
        self.lamps = {key: self._lamp(text, on_click) for key, text, on_click in (
            ("tnc", "TNC", self._tnc_info), ("is", "IS", None), ("gps", "GPS", self._gps_info),
            ("tx", "TX", self._tx_tap))}
        if self.compact:
            self.callsign.expand = True
            self.callsign.no_wrap = True
            self.callsign.overflow = ft.TextOverflow.ELLIPSIS
            row = [self.menu_btn, self.callsign, self.lamps["tnc"], self.lamps["is"], self.lamps["gps"],
                   self.update_btn,
                   ft.IconButton(ft.Icons.SHARE_LOCATION, tooltip=self.t("beacon_now"), on_click=self._beacon_now,
                                 visible=not self.engine.exclusive_mode),
                   self.lamps["tx"]]
        status = ft.Container(
            ft.Row(
                row if self.compact else [
                    self.menu_btn,
                    self.callsign,
                    ft.Container(ft.Row([self.tnc_dot, ft.Text(self.t("tnc"), size=13), self.tnc_text], spacing=4,
                                        tight=True),
                                 on_click=self._tnc_info if self.compact else None),
                    self.is_box,
                    ft.Container(self.gps_box, on_click=self._gps_info if self.compact else None),
                    ft.Container(expand=True),
                    self.update_btn,
                    ft.IconButton(ft.Icons.SHARE_LOCATION, tooltip=self.t("beacon_now"), on_click=self._beacon_now,
                                  visible=not self.engine.exclusive_mode),
                    self.tx_box,
                    ft.IconButton(ft.Icons.INFO_OUTLINE, tooltip=self.t("about"),
                                  on_click=lambda _e: show_about(self), visible=not self.compact),
                ],
                spacing=4 if self.compact else 16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=2 if self.compact else 16, vertical=2 if self.compact else 6),
            bgcolor=ft.Colors.SURFACE_CONTAINER,
        )
        self.page.controls.clear()
        self.page.add(
            ft.SafeArea(
                ft.Row(
                    ([] if self.compact else [self.rail, ft.VerticalDivider(width=1)])
                    + [ft.Column([status, ft.Stack([self.holders[i] for i in stacked], expand=True)],
                                 expand=True, spacing=0)],
                    expand=True,
                    spacing=0,
                ),
                expand=True,
            )
        )
        self._building = True
        try:
            self.select(key)
        finally:
            self._building = False

    @property
    def current_key(self) -> str:
        return self.views[self.current].key if self.views else ""

    def view(self, key: str) -> View:
        v = next(v for v in self.views if v.key == key)
        v.control  # noqa: B018 - built on first use
        return v

    def has_view(self, key: str) -> bool:
        """In BBS SERVER mode only some of the views exist."""
        return any(v.key == key for v in self.views)

    def select(self, key: str) -> None:
        if key != "settings" and not self.engine.config.configured and self.has_view("settings"):
            # no callsign saved yet: nothing else can work, so Settings stays, with the callsign field
            key = "settings"
            if not self._building:  # a tap in the menu, not the screen being put together
                self.toast(self.t("call_required"), error=True)
                self.page.run_task(self.view("settings").require_call)
        index = next(i for i, v in enumerate(self.views) if v.key == key)
        self.current = index
        self.rail.selected_index = index
        self.drawer.selected_index = index
        if self.holders[index].content is not self.views[index].control:
            self.holders[index].content = self.views[index].control  # built the first time it is shown
        for i, holder in enumerate(self.holders):
            holder.visible = i == index or (self.views[i].keep_alive and holder.content is not None)
        self.views[index].shown()
        self._update_status()
        self.page.update()

    # ─── engine events ────────────────────────────────────────────────────

    def _on_event(self, kind: str, data: dict[str, Any]) -> None:
        self.sounds.on_event(kind, data)
        if kind == "monitor":
            self._on_air(data.get("line", ""))
        for v in self.views:
            if v.built:
                v.on_event(kind, data)
        if kind == "message":
            self._notify_message(data)
        self._schedule_flush()

    def _schedule_flush(self) -> None:
        if self._flush_pending or self._closing:
            return
        self._flush_pending = True
        try:
            self.page.run_task(self._flush)
        except Exception:  # noqa: BLE001 - the page is gone (session closed)
            self._flush_pending = False

    async def _flush(self) -> None:
        await asyncio.sleep(FLUSH_DELAY)
        self._flush_pending = False
        self.refresh_now()

    def refresh_now(self) -> None:
        if self._closing or not self.views:
            return
        if getattr(getattr(self.page, "session", None), "connection", True) is None:
            return  # the browser went away (web): nothing to draw until it reconnects
        self._update_status()
        try:
            self.views[self.current].refresh()
        except Exception:  # noqa: BLE001 - a view error must not stop the updates
            _LOGGER.exception("Refreshing %s failed", self.current_key)
        self.page.update()

    async def _tick(self) -> None:
        """Ages, map markers skipped by the rate limit and the like; on "auto", a changed desktop theme."""
        n = 0
        while not self._closing:
            await asyncio.sleep(TICK_SECONDS)
            n += 1
            if n % THEME_EVERY == 0 and self.engine.config.theme == "auto":
                await self.apply_theme()
            self.refresh_now()

    async def apply_theme(self) -> None:
        if self.engine.config.theme == "auto":
            self._desktop_dark = await asyncio.to_thread(theme.desktop_prefers_dark)
        mode = theme.theme_mode(self.engine.config.theme, self._desktop_dark)
        if mode != self.page.theme_mode:
            self.page.theme_mode = mode
            self.page.update()

    def set_theme(self, choice: str) -> None:
        """From Settings: applied at once and saved."""
        self.engine.config.theme = choice if choice in theme.MODES else "auto"
        self.page.run_task(asyncio.to_thread, save_config, self.engine.config, self.folder)
        self.page.run_task(self.apply_theme)

    def _update_status(self) -> None:
        st = self.engine.status()
        self.callsign.value = st["callsign"] or "—"
        self.tnc_dot.color = ft.Colors.GREEN if st["tnc_connected"] else ft.Colors.RED
        self.tnc_text.value = self.t("connected") if st["tnc_connected"] else self.t("disconnected")
        self.tnc_text.tooltip = None if st["tnc_connected"] else st.get("tnc_error")
        aprsis = st.get("aprsis")
        self.is_box.visible = aprsis is not None
        if aprsis:
            self.is_dot.color = (ft.Colors.GREEN if aprsis["verified"] else
                                 ft.Colors.AMBER if aprsis["connected"] else ft.Colors.RED)
        gps = st.get("gps")
        self.gps_box.visible = gps is not None
        if gps:
            # green: a fix · amber: the module talks, no fix yet · red: no module (or a setting is wrong)
            fix, talking = gps.get("fix"), gps.get("connected")
            self.gps_dot.color = ft.Colors.GREEN if fix else ft.Colors.AMBER if talking else ft.Colors.RED
            accuracy = gps.get("accuracy")
            self.gps_text.value = ((f"±{accuracy:.0f} m" if accuracy else self.t("gps_phone")) if fix and gps.get("phone")
                                   else self.t("gps_sats", n=gps["satellites"]) if fix else
                                   self.t("gps_nofix") if talking else self.t("disconnected"))
            self.gps_box.tooltip = gps.get("error") or None
        self.tx_switch.value = st["tx_enabled"]
        self.tx_switch.disabled = not self.engine.config.configured
        self.tx_switch.tooltip = self.t("tx_on") if st["tx_enabled"] else self.t("tx_off")
        on_air = time.monotonic() < self._on_air_until
        self.tx_box.bgcolor = (ft.Colors.RED if on_air else ft.Colors.ERROR_CONTAINER) if st["tx_enabled"] else None
        self._light("tnc", "on" if st["tnc_connected"] else None)
        self.lamps["is"].visible = aprsis is not None
        self._light("is", "on" if aprsis and aprsis["verified"] else None)
        self.lamps["gps"].visible = gps is not None
        self._light("gps", "on" if gps and gps.get("fix") else None)
        # TX: red frame and text while transmitting is allowed, all red only while the radio is on air
        self._light("tx", ("tx" if on_air else "armed") if st["tx_enabled"] else None)
        if self.has_view("messages"):
            messages = self.view("messages")
            dest = self.rail.destinations[self.views.index(messages)]
            dest.badge = str(len(messages.unread)) if messages.unread else None
            self.drawer.controls[1 + self.views.index(messages)].icon.badge = dest.badge
            self.menu_btn.badge = dest.badge  # the menu is closed on a phone: unread messages show on ☰

    # ─── new versions ─────────────────────────────────────────────────────

    # ─── internet: the map falls back to the offline map without it ──────

    no_internet = False

    @staticmethod
    def _internet_up() -> bool:
        import socket  # noqa: PLC0415

        host = os.environ.get("APRS_KISS_TILE_CHECK_HOST", "tile.openstreetmap.org")  # tests point it elsewhere
        try:
            with socket.create_connection((host, 443), timeout=4):
                return True
        except OSError:
            return False

    async def _watch_internet(self) -> None:
        """Every minute: can the map tiles be reached? If not, the maps switch to the offline map by
        themselves (and back when the internet returns), with a short notice."""
        await asyncio.sleep(3)  # let the window come up first, so the notice is seen
        while True:
            up = await asyncio.to_thread(self._internet_up)
            if up == self.no_internet:  # changed
                self.no_internet = not up
                for v in self.views:
                    if v.built and hasattr(v, "base_map_changed"):
                        v.base_map_changed()
                if not self.engine.config.map_offline:
                    self.toast(self.t("net_offline") if self.no_internet else self.t("net_online"), seconds=10)
                self.page.update()
            await asyncio.sleep(60)

    def offline_map(self) -> bool:
        """The offline base map: chosen by the user, or because there is no internet."""
        return bool(self.engine.config.map_offline or self.no_internet)

    async def _check_updates_later(self) -> None:
        """Once a day at most, a while after the start so it does not slow it down."""
        self.update_state = await asyncio.to_thread(updates.load, self.folder)
        self._show_update()
        await asyncio.sleep(10)
        if self.engine.config.check_updates and not self._closing and not distribution.store_updates():
            await self.check_updates(force=False)

    async def check_updates(self, force: bool = True) -> None:
        self.update_state = await asyncio.to_thread(updates.check, self.folder, force)
        self._show_update()
        st = self.update_state
        if st.available and st.notified != st.latest and not self._closing:
            st.notified = st.latest
            await asyncio.to_thread(updates.save, self.folder, st)
            self.show_dialog(ft.SnackBar(
                ft.Text(self.t("update_available", version=st.latest)),
                action=ft.SnackBarAction(label=self.t("update_download" if self.android else "update_show"),
                                         on_click=lambda _e: self.page.run_task(self._open_release)),
                duration=10000, behavior=ft.SnackBarBehavior.FLOATING, width=520,
            ))
        self.refresh_now()

    @property
    def android(self) -> bool:
        return self.page.platform == ft.PagePlatform.ANDROID

    def update_url(self) -> str:
        """Android: the new .apk itself (the browser downloads it, a tap installs it); elsewhere the release page."""
        st = self.update_state
        return st.apk_url if self.android and st.apk_url else st.url

    async def _open_release(self) -> None:
        url = self.update_url()
        await ft.UrlLauncher().launch_url(url)
        if url.endswith(".apk"):
            self.toast(self.t("update_apk_hint"), seconds=10)

    def _show_update(self) -> None:
        st = self.update_state
        if distribution.store_updates():  # Google Play updates it
            st = self.update_state = updates.UpdateState()
        self.update_btn.visible = st.available
        if isinstance(self.update_btn, ft.FilledTonalButton):
            self.update_btn.content = self.t("update_button", version=st.latest)
        self.update_btn.tooltip = self.t("update_button", version=st.latest)
        if self.compact:  # the menu's About item says it too
            self.about_item.subtitle = ft.Text(self.t("update_button", version=st.latest), color=ft.Colors.PRIMARY,
                                               size=12) if st.available else None

    def _tx_changed(self, e) -> None:
        self.engine.set_tx(bool(e.control.value))

    # ─── helpers for the views ────────────────────────────────────────────

    def save_config_soon(self) -> None:
        """Save a view-only choice in the background; the connection is not restarted."""
        self.page.run_task(asyncio.to_thread, save_config, self.engine.config, self.folder)

    def set_show_internet(self, value: bool) -> None:
        """Map and station list share this choice; it is saved, the connection is not restarted."""
        self.engine.config.show_internet = value
        self.save_config_soon()
        for key in ("map", "stations"):
            if self.has_view(key):
                self.view(key).force()
        self.refresh_now()

    def tracked(self) -> set[str]:
        return {c.strip().upper() for c in self.engine.config.tracked_callsigns.replace(" ", ",").split(",")
                if c.strip()}

    def toast(self, text: str, error: bool = False, seconds: float = 4) -> None:
        self.show_dialog(ft.SnackBar(
            ft.Text(text, color=ft.Colors.ON_ERROR_CONTAINER if error else None),
            bgcolor=ft.Colors.ERROR_CONTAINER if error else None,
            behavior=ft.SnackBarBehavior.FLOATING, width=520, duration=int(seconds * 1000),
        ))

    async def guard(self, coro: Awaitable[Any]) -> bool:
        """Run a send; show why it was refused. True when it went out."""
        try:
            await coro
            return True
        except TransmitRefused:
            self.toast(self.t("tx_refused"), error=True)
        except (ConnectionError, ValueError, OSError) as err:
            self.toast(f"{self.t('not_sent')}: {err}", error=True)
        return False

    def _notify_message(self, message: dict[str, Any]) -> None:
        if not self.has_view("messages"):
            return
        if self.current_key == "messages" and self.view("messages").selected == message["from"].upper():
            return
        sender = message["from"]

        def open_it(_e) -> None:
            self.page.pop_dialog()
            self.view("messages").open_conversation(sender)
            self.select("messages")

        self.show_dialog(ft.SnackBar(
            ft.Text(f"{self.t('message_from', call=sender)}: {message['text']}"),
            action=ft.SnackBarAction(label=self.t("messages"), on_click=open_it),
            duration=5000,
            behavior=ft.SnackBarBehavior.FLOATING, width=520,
        ))

    async def _beacon_now(self, _e) -> None:
        if not self.engine.my_position():
            self.toast(f"{self.t('not_sent')}: {self.t('position_hint')}", error=True)
            return
        if await self.guard(self.engine.send_position()):
            self.toast(self.t("position_sent"))

    def show_station(self, call: str) -> None:
        entry = self.engine.station.heard.get(call)
        if not entry:
            return
        pic, symbol_name, _known = symbol_info(entry.get("symbol_table"), entry.get("symbol"), self.t.language)
        rows: list[ft.Control] = [ft.Text(describe(self, entry))]
        if symbol_name:
            rows.append(ft.Text(f"{self.t('symbol')}: {symbol_name} "
                                f"({entry.get('symbol_table') or '/'}{entry.get('symbol') or ''})",
                                size=12, color=ft.Colors.ON_SURFACE_VARIANT))
        now = time.time()
        rows.append(ft.Text(f"{self.t('last_heard')}: {clock(entry['last_heard'])} ({self.t.age(now - entry['last_heard'])})"))
        weather = entry.get("weather")
        if isinstance(weather, dict) and weather:
            wx = []
            if weather.get("temperature") is not None:
                wx.append(f"{weather['temperature']:.1f} °C")
            if weather.get("humidity") is not None:
                wx.append(f"{weather['humidity']} %")
            if weather.get("pressure") is not None:
                wx.append(f"{weather['pressure']} hPa")
            if weather.get("wind_speed") is not None:
                wx.append(f"{weather['wind_speed']} m/s")
            if wx:
                rows.append(ft.Text("🌦️ " + ", ".join(wx)))
        for key in ("altitude", "speed", "course"):
            if entry.get(key) is not None:
                rows.append(ft.Text(f"{key}: {entry[key]}"))
        if entry.get("path"):
            rows.append(ft.Text(", ".join(entry["path"]), size=12, color=ft.Colors.ON_SURFACE_VARIANT))
        if entry.get("last_raw"):
            rows.append(ft.Text(entry["last_raw"], size=11, font_family="monospace", selectable=True,
                                color=ft.Colors.ON_SURFACE_VARIANT))

        async def on_map(_e) -> None:
            self.page.pop_dialog()
            self.select("map")
            await self.view("map").centre(entry["latitude"], entry["longitude"])

        def message(_e) -> None:
            self.page.pop_dialog()
            self.view("messages").compose_to(call)
            self.select("messages")

        actions = [ft.TextButton(self.t("send_message"), icon=ft.Icons.MAIL, on_click=message)]
        if entry.get("latitude") is not None:
            actions.insert(0, ft.TextButton(self.t("show_on_map"), icon=ft.Icons.MAP, on_click=on_map))
        actions.append(ft.TextButton(self.t("close"), on_click=lambda _e: self.page.pop_dialog()))
        self.show_dialog(ft.AlertDialog(
            title=ft.Text(f"{pic}  {call}"),
            content=ft.Column(rows, tight=True, spacing=6, width=420),
            actions=actions,
        ))


async def main(page: ft.Page) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    _LOGGER.info("APRS & Packet %s, data in %s", VERSION, data_dir())
    app = App(page)
    await app.start()
