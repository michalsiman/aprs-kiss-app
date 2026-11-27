"""The APRS & Packet app: one window, a navigation rail, a status bar and the screens."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import logging.handlers
import os
import re
from urllib.parse import quote
import sys
import threading
import time
import traceback
import weakref
from collections.abc import Awaitable
from datetime import date
from typing import Any

import flet as ft

from aprs_kiss_core import android_bt, android_usb, ble, drivedetect, profiles, roadalert, units
from . import android_notify, ble_flet, desktop_notify
from aprs_kiss_core.config import VERSION, Config, data_dir, load_config, save_config

from . import theme
from aprs_kiss_core.engine import Engine, TransmitRefused

from .about import show_about
from . import disclaimer, distribution, i18n, language, offline_map, updates, whatsnew
from .sounds import Sounds
from .i18n import Translator
from .phone_gps import PhoneGps
from .tracker_ui import PositionButton
from .symbols import symbol_info
from .views.base import View, adapt, clock, distance_text
from .views.bbs import BbsView
from .views.tak import TakView
from .views.chat import ChatView
from .views.files import FilesView, size_text
from .views.map import MapView
from .views.messages import MessagesView
from .views.monitor import MonitorView
from .views.settings import SettingsView
from .views.stations import StationsView, describe
from .views.terminal import TerminalView
from .views.thursday import ThursdayView

_LOGGER = logging.getLogger(__name__)

VIEWS = [MapView, MessagesView, ThursdayView, StationsView, TerminalView, ChatView, FilesView, MonitorView, BbsView,
         TakView, SettingsView]
# With BBS SERVER on the app is only the BBS; the monitor stays to see what the radio hears.
BBS_VIEWS = [BbsView, MonitorView, SettingsView]
TAK_VIEWS = [TakView, MonitorView, SettingsView]
# The menu in sections: APRS, packet radio, then the settings (a heading each on a phone, a gap on a computer).
SECTIONS = {"map": "aprs", "messages": "aprs", "thursday": "aprs", "stations": "aprs",
            "terminal": "packet", "chat": "packet", "files": "packet", "monitor": "packet", "bbs": "packet",
            "tak": "packet", "settings": "app"}
FLUSH_DELAY = 0.25
TICK_SECONDS = 5.0
THEME_EVERY = 6  # ticks: the desktop theme is looked at every 30 s


_LIVE_APPS: "weakref.WeakSet[App]" = weakref.WeakSet()
_LAST_SCREEN: list[str] = []  # the screen on show, for a new session in the same process (Android restarts)  # the app's sessions still running (normally one)

COMPACT_WIDTH = 700  # narrower than this (a phone): the compact layout

class App:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.folder = data_dir()
        self.engine: Engine | None = None
        self.views: list[View] = []
        self.current = 0
        self._history: list[str] = []  # the screens shown before, for the back gesture
        self._flush_pending = False
        self._closing = False
        self.update_state = updates.UpdateState()
        self._desktop_dark: bool | None = None
        self._building = False
        self.compact = False  # a phone: a menu sliding in from the side instead of the rail, a slimmer top bar

    # ─── start and stop ───────────────────────────────────────────────────

    async def start(self) -> None:
        page = self.page
        if self.mobile:
            # Android may restart the screen part of the app (the "Dart VM") while Python keeps running:
            # a new session starts, and the old one's engine would go on holding the radio's connection,
            # the GPS and the timers next to the new one. One app on a phone: the old one is stopped first.
            for old in [a for a in _LIVE_APPS if a is not self and not a._closing]:
                _LOGGER.warning("A new session while an old one still runs: stopping the old one")
                await old.shutdown()
        _LIVE_APPS.add(self)
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
        page.on_app_lifecycle_state_change = self._lifecycle  # phones: in the background or back

        android_usb.register()  # Android: a TNC on the phone's USB port
        android_bt.register()  # … or over Bluetooth (SPP)
        self.ble = ble_flet.setup()  # … or over Bluetooth LE (KISS over BLE), wherever the build has it
        self.ble_ok = False  # known after the first answer of the BLE extension (settings offer it then)
        if self.ble:
            page.run_task(self._check_ble)
        config = await asyncio.to_thread(load_config, self.folder)
        if config.connection in ("usb", "bt") and not self.mobile:  # settings copied from a phone
            config = Config.from_dict({**config.to_dict(), "connection": "tcp"}).validate()
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
        if config.map_paths:  # imported offline maps: opened before the map is drawn
            failed = await asyncio.to_thread(offline_map.set_custom_maps, config.map_paths)
            for path, err in failed:
                _LOGGER.warning("Offline map %s cannot be used: %s", path, err)
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
        first_start = language.needed(self) or disclaimer.needed(self)
        first_warning = lambda: disclaimer.show(self) if disclaimer.needed(self) else None  # noqa: E731
        if language.needed(self):
            language.show(self, then=first_warning)  # the very first start: the language, then the warning
        else:
            first_warning()
        whatsnew.check(self, first_start)  # after an update: what changed (a first start only remembers the version)
        self.phone_gps.sync()
        await self.apply_screen()
        page.run_task(self._tick)
        page.run_task(self._check_updates_later)
        page.run_task(self._watch_internet)

    async def _on_window_event(self, e: ft.WindowEvent) -> None:
        if e.type == ft.WindowEventType.CLOSE:
            self._confirm_quit()
        elif e.type in (ft.WindowEventType.BLUR, ft.WindowEventType.MINIMIZE, ft.WindowEventType.HIDE):
            self._window_away = True  # new messages: the system's notification
        elif e.type in (ft.WindowEventType.FOCUS, ft.WindowEventType.RESTORE, ft.WindowEventType.SHOW):
            self._window_away = False

    def _confirm_quit(self) -> None:
        """Closing the window stops receiving, beacons and the iGate, so ask first."""
        if self._closing:
            return
        st = self.engine.status()
        what = [self.t("quit_rx")]
        if (self.engine.config.beacon_minutes or self.engine.config.tracker_on) and st["tx_enabled"]:
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
        _LOGGER.info("Session ends: stopping the engine")
        self._closing = True
        if self.engine:
            with contextlib.suppress(Exception):
                await self.engine.stop()

    async def apply_config(self, config: Config) -> None:
        shown = ("language", "units_distance", "units_temperature", "units_pressure")  # the screens are built again
        language_changed = any(getattr(config, k) != getattr(self.engine.config, k) for k in shown)
        old = self.engine.config
        mode_changed = (config.bbs_enabled, config.tak_enabled) != (old.bbs_enabled, old.tak_enabled)
        t0 = time.monotonic()
        await asyncio.to_thread(save_config, config, self.folder)
        await self.engine.reconfigure(config)
        self.phone_gps.sync()
        await self.apply_screen()
        t1 = time.monotonic()
        if language_changed or mode_changed:
            self.build()
            # stay in the section whose switch was turned (on or off)
            self.select(("tak" if config.tak_enabled != old.tak_enabled else "bbs") if mode_changed else "settings")
        self.toast(self.t("saved"))
        self.refresh_now()
        _LOGGER.info("Settings applied: radio %.2f s, screen %.2f s", t1 - t0, time.monotonic() - t1)

    async def send_position_text(self, lat: float, lon: float, where: str, locator: bool = False) -> None:
        """A position (picked on the map) to everybody in the chat, or into a message being written;
        as coordinates, or as a Maidenhead locator ("LOC JO70XQ")."""
        from aprs_kiss_core.geotext import position_to_locator, write_position  # noqa: PLC0415

        text = f"LOC {position_to_locator(lat, lon)}" if locator else write_position(lat, lon)
        if where == "chat":
            if await self.guard(self.engine.send_chat(text)):
                self.toast(self.t("pos_sent_chat"))
        else:
            self.view("messages").insert_text(text)
            self.select("messages")

    async def show_point(self, lat: float, lon: float, label: str = "") -> None:
        """A position from a message or the chat on the map."""
        self.select("map")
        await self.view("map").show_point(lat, lon, label)
        self.page.update()

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

    @staticmethod
    def _menus() -> dict:
        """Pop-up menus (map tools, filters, ⋮), drop-down lists, dialogs and bottom sheets: the same thin
        grey frame and a shadow everywhere, so they stand out from the bars and the map under them."""
        frame = ft.BorderSide(1, ft.Colors.with_opacity(0.7, ft.Colors.OUTLINE))
        return {
            "popup_menu_theme": ft.PopupMenuTheme(
                color=ft.Colors.SURFACE_CONTAINER_HIGHEST, elevation=10, shadow_color=ft.Colors.BLACK,
                shape=ft.RoundedRectangleBorder(radius=10, side=frame)),
            "dropdown_theme": ft.DropdownTheme(menu_style=ft.MenuStyle(
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, elevation=10, shadow_color=ft.Colors.BLACK, side=frame,
                shape=ft.RoundedRectangleBorder(radius=10))),
            "dialog_theme": ft.DialogTheme(
                elevation=10, shadow_color=ft.Colors.BLACK, shape=ft.RoundedRectangleBorder(radius=24, side=frame)),
            "bottom_sheet_theme": ft.BottomSheetTheme(
                elevation=10, shadow_color=ft.Colors.BLACK,
                shape=ft.RoundedRectangleBorder(radius=ft.BorderRadius.only(top_left=24, top_right=24), side=frame)),
            # the bars at the bottom (TX sent, TNC not connected, a new message, a hazard on the road)
            "snackbar_theme": ft.SnackBarTheme(
                elevation=10, shape=ft.RoundedRectangleBorder(radius=10, side=frame)),
        }

    def _theme(self) -> ft.Theme:
        """Phones get smaller type and denser fields: their screens are narrow and many have large fonts set."""
        if not self.mobile:
            return ft.Theme(color_scheme_seed=ft.Colors.INDIGO, **self._menus())
        size = lambda n: ft.TextStyle(size=n, color=ft.Colors.ON_SURFACE)  # noqa: E731 - a style without a color turns black
        return ft.Theme(
            **self._menus(),
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
        self.toast(self.tnc_text.value if st["tnc_connected"] else (self.t.error(st.get("tnc_error")) or self.tnc_text.value or ""),
                   error=not st["tnc_connected"])

    @staticmethod
    def _lamp(content: str | ft.Control, on_click, tooltip: str | None = None, small: bool = False,
              large: bool = False) -> ft.Container:
        """One dashboard lamp: all the same height and frame, a word or an icon inside.
        small: half height, for the phone's TNC / IS / GPS block (two rows in the height of one lamp);
        large: a computer's top bar, which has the room."""
        if isinstance(content, str):
            # line height = font size: in the small lamps the text sits in the middle of the frame
            content = ft.Text(content, size=8 if small else 15 if large else 12, weight=ft.FontWeight.BOLD,
                              style=ft.TextStyle(height=1.0) if small else None)
        return ft.Container(content, on_click=on_click, tooltip=tooltip, height=12 if small else 36 if large else 26,
                            alignment=ft.Alignment.CENTER, data=1.0 if small else 2.0 if large else 1.5,
                            padding=ft.Padding.symmetric(horizontal=3 if small else 12 if large else 6),
                            border_radius=3 if small else 7 if large else 5,
                            border=ft.Border.all(1.0 if small else 2.0 if large else 1.5, ft.Colors.OUTLINE))

    def _light(self, key: str, state: str | None) -> None:
        """A lamp: "on" green, "tx" red and filled, None grey; hidden when the thing is not in use."""
        lamp = self.lamps[key]
        color = {"on": ft.Colors.GREEN, "tx": ft.Colors.RED, "armed": ft.Colors.RED}.get(state, ft.Colors.OUTLINE)
        lamp.border = ft.Border.all(lamp.data or 1.5, color)
        lamp.bgcolor = ft.Colors.RED if state == "tx" else None
        lamp.content.color = ft.Colors.WHITE if state == "tx" else color

    _on_air_until = 0.0

    _is_sent_until = 0.0
    IS_FLASH_SECONDS = 1.0

    def _on_air(self, line: str) -> None:
        """A frame went out by radio: the TX lamp is all red for about as long as it takes on air.
        Sent to APRS-IS: the IS lamp is all red for a second."""
        if " >> " not in line[:12]:
            return
        if "[IS] " in line[12:18]:
            self._is_sent_until = time.monotonic() + self.IS_FLASH_SECONDS
            try:
                self.page.run_task(self._off_air, self.IS_FLASH_SECONDS)
            except Exception:  # noqa: BLE001 - the page is gone
                pass
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
        now = time.monotonic()
        if now >= self._on_air_until and now >= self._is_sent_until and not self._closing:
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

    async def _check_ble(self) -> None:
        self.ble_ok = await ble.available()

    def _on_resize(self, e) -> None:
        if self.views and self._is_compact(getattr(e, "width", None)) != self.compact:
            self.build()

    async def _open_menu(self, _e=None) -> None:
        self._drawer_open = True
        self._update_back()
        await self.page.show_drawer()

    async def _close_menu(self) -> None:
        self._drawer_open = False
        self._update_back()
        await self.page.close_drawer()

    def _menu_dismissed(self, _e=None) -> None:
        self._drawer_open = False
        self._update_back()
        self.page.update()

    async def _menu_about(self, _e=None) -> None:
        await self._close_menu()
        show_about(self)

    async def _menu_selected(self, e) -> None:
        """A screen picked in the phone's menu: the menu slides away and the screen opens."""
        await self._close_menu()
        self.select(self.menu_views[e.control.selected_index].key)

    # ─── Android's back gesture ───────────────────────────────────────────
    # It closes the menu when it is open, else goes back to the screen shown before (like a browser),
    # and only from the first one leaves the app. Settings with unsaved changes ask first.

    _drawer_open = False
    MAX_HISTORY = 30

    def _update_back(self) -> None:
        """Let the system handle the gesture (leave the app) only when there is nothing to go back to."""
        view = self.page.views[0] if self.page.views else None
        if view is None:
            return
        inner = self._inner_back() is not None
        can = not (self._drawer_open or inner or self._history or self.current_key == "settings")
        if view.can_pop != can or view.on_confirm_pop is None:
            view.can_pop = can
            view.on_confirm_pop = self._back

    def _inner_back(self):
        """The screen on show when it has a step back of its own (an open conversation), else None."""
        index = getattr(self, "current", None)
        if index is None or not 0 <= index < len(self.views):
            return None
        view = self.views[index]
        return view if view.built and view.can_back() else None

    async def _back(self, e) -> None:
        _LOGGER.info("Back (screen %s, menu open %s)", self.current_key, self._drawer_open)
        view = e.control
        await view.confirm_pop(False)  # the app decides: never let the view itself go
        if self._drawer_open:
            await self._close_menu()
            return
        current = self._inner_back()
        if current is not None:
            current.go_back()  # e.g. from a conversation back to the list of them
            self._update_back()
            self.page.update()
            return
        while self._history and not self.has_view(self._history[-1]):
            self._history.pop()  # a screen of another mode (BBS, TAK) that is gone
        target = self._history[-1] if self._history else None
        if target is None and self.current_key == "settings" and self.has_view("settings") \
                and self.view("settings").dirty():
            target = "map" if self.has_view("map") and self.engine.config.configured else None
        if target is None:
            self._leave_app()
            return
        self.select(target, back=True)

    def _leave_app(self) -> None:
        """Nothing to go back to: to the background, as Android's own back does (receiving goes on)."""
        try:
            from aprs_kiss_core import android_usb  # noqa: PLC0415
            if android_usb.available():
                android_usb._activity().moveTaskToBack(True)
                return
        except Exception:  # noqa: BLE001 - not Android, or the call failed
            _LOGGER.debug("moveTaskToBack failed", exc_info=True)

    def _ask_unsaved(self, then: str, back: bool) -> None:
        """Leaving Settings with changes not saved: save them, or throw them away."""
        settings = self.view("settings")

        async def save(_e) -> None:
            self.page.pop_dialog()
            if await settings._save(None):
                self.select(then, back=back, force=True)
            else:
                self.page.update()  # the form shows what is wrong

        def discard(_e) -> None:
            self.page.pop_dialog()
            settings.discard()
            self.select(then, back=back, force=True)

        self.show_dialog(ft.AlertDialog(
            title=ft.Text(self.t("unsaved_title")),
            content=ft.Text(self.t("unsaved_text")),
            actions=[ft.TextButton(self.t("unsaved_discard"), on_click=discard),
                     ft.FilledButton(self.t("save"), icon=ft.Icons.SAVE, on_click=save)],
        ))

    def build(self) -> None:
        self.t = Translator(self.engine.config.language)
        conf = self.engine.config
        units.current = units.Units.choose(conf.units_distance, conf.units_temperature, i18n.system_country(),
                                           comma=self.t.language != "en", pressure=conf.units_pressure)
        self.compact = self._is_compact()
        # a new session after Android restarted the screen part: back on the screen the user had open
        key = self.current_key if self.views else (_LAST_SCREEN[0] if self.mobile and _LAST_SCREEN else "map")
        mode = self.engine.exclusive_mode
        classes = BBS_VIEWS if mode == "bbs" else TAK_VIEWS if mode == "tak" else VIEWS
        if self.mobile:  # BBS SERVER is for computers only
            classes = [c for c in classes if c is not BbsView]
        self.views = [cls(self) for cls in classes]
        self.menu_views = [v for v in self.views if v.in_menu]  # the screens in the menu (rail, drawer)
        if key not in {v.key for v in self.views}:
            key = self.views[0].key
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=88,
            destinations=[ft.NavigationRailDestination(
                icon=ft.Icon(v.icon), selected_icon=ft.Icon(v.selected_icon or v.icon), label=self.t(v.key),
                # a new section: a gap above it
                padding=ft.Padding.only(top=14) if i and SECTIONS.get(v.key) != SECTIONS.get(self.menu_views[i - 1].key)
                else None)
                for i, v in enumerate(self.menu_views)],
            on_change=lambda e: self.select(self.menu_views[e.control.selected_index].key),
        )
        # a phone: About is at the end of the menu (no room for its button in the top bar)
        self.about_item = ft.ListTile(leading=ft.Icon(ft.Icons.INFO_OUTLINE), title=ft.Text(self.t("about")),
                                      on_click=self._menu_about, content_padding=ft.Padding.only(left=28, right=12))
        # a phone: the screens in a menu that slides in from the left (the ☰ button) and hides again
        drawer_items: list[ft.Control] = [ft.Container(ft.Text("APRS & Packet", weight=ft.FontWeight.BOLD, size=16),
                                                       padding=ft.Padding.only(left=28, top=20, bottom=4))]
        self.drawer_dests: dict[str, ft.NavigationDrawerDestination] = {}
        section = None
        for v in self.menu_views:
            if SECTIONS.get(v.key) != section:
                section = SECTIONS.get(v.key)
                if section == "app":
                    drawer_items.append(ft.Divider(height=12))
                elif section:
                    drawer_items.append(ft.Container(
                        ft.Text(self.t(f"menu_{section}"), size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                        padding=ft.Padding.only(left=28, top=14, bottom=4)))
            self.drawer_dests[v.key] = ft.NavigationDrawerDestination(
                icon=ft.Icon(v.icon), selected_icon=ft.Icon(v.selected_icon or v.icon), label=self.t(v.key))
            drawer_items.append(self.drawer_dests[v.key])
        self.drawer = ft.NavigationDrawer(
            controls=drawer_items + [ft.Divider(), self.about_item],
            on_change=self._menu_selected, on_dismiss=self._menu_dismissed,
        )
        self.page.drawer = self.drawer if self.compact else None
        self.menu_btn = ft.IconButton(ft.Icons.MENU, tooltip=self.t("menu"), on_click=self._open_menu,
                                      visible=self.compact)
        pad = 6 if self.compact else 12
        # The map stays on screen under the other screens (they are opaque): hiding it would make
        # Flutter throw it away and build it again, tiles and all, at every return to it.
        self.holders = [ft.Container(v.control if v.built else None, visible=False, expand=True,
                                     padding=None if v.keep_alive else ft.Padding.all(pad),  # the map edge to edge
                                     bgcolor=None if v.keep_alive else ft.Colors.SURFACE,
                                     left=0, top=0, right=0, bottom=0)
                        for v in self.views]
        stacked = sorted(range(len(self.views)), key=lambda i: not self.views[i].keep_alive)  # the map at the bottom

        self.callsign = ft.Text(weight=ft.FontWeight.BOLD, size=18)
        self.symbol_pic = ft.Text(size=20)  # the profile's APRS symbol, as on the map
        # a tap on the callsign: pick another profile (SSID and symbol)
        self.callsign_btn = ft.Container(ft.Row([self.symbol_pic, self.callsign], spacing=6, tight=True,
                                                vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                         on_click=self._pick_profile, border_radius=6,
                                         padding=ft.Padding.symmetric(vertical=2),  # no side padding: room for the SSID
                                         tooltip=self.t("profile_pick"))
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
        self.update_btn = (self._lamp(ft.Icon(ft.Icons.NEW_RELEASES, size=16, color=ft.Colors.PRIMARY), open_release)
                           if self.compact else
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
        # On a phone TNC, IS and GPS share one block the height of a lamp (IS and GPS above, TNC below),
        # so the callsign with its SSID has room.
        # A computer: the same lamps, larger and side by side.
        small, large = self.compact, not self.compact
        self.lamps = {key: self._lamp(text, on_click, small=small and key != "tx", large=large)
                      for key, text, on_click in (
            ("tnc", "TNC", self._tnc_info), ("is", "IS", None),
            ("gps", ft.Icon(ft.Icons.SATELLITE_ALT, size=9 if small else 20), self._gps_info),  # a satellite, not a word
            ("tx", "TX", self._tx_tap))}
        # "send my position" (once, or again and again: the tracker), a lamp in the same frame on a phone
        self.position_btn = PositionButton(self, self.compact)
        if self.compact:
            self.callsign_btn.expand = True
            self.callsign.no_wrap = True
            self.callsign.overflow = ft.TextOverflow.ELLIPSIS
            links = ft.Column([ft.Row([self.lamps["is"], self.lamps["gps"]], spacing=2, tight=True),
                               self.lamps["tnc"]], spacing=2, tight=True,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            # IS and GPS side by side exactly as wide as TNC below them: 20 + 2 + 20 = 42
            for lamp in ("is", "gps"):
                self.lamps[lamp].width = 20
            self.lamps["tnc"].width = 42
            row = [self.menu_btn, self.callsign_btn, links, self.update_btn, self.position_btn.control, self.lamps["tx"]]
        status = ft.Container(
            ft.Row(
                row if self.compact else [
                    self.menu_btn,
                    self.callsign_btn,
                    ft.Container(expand=True),  # all the lamps on the right
                    self.lamps["tnc"], self.lamps["is"], self.lamps["gps"],
                    self.update_btn,
                    self.position_btn.control,
                    self.lamps["tx"],
                    ft.IconButton(ft.Icons.INFO_OUTLINE, tooltip=self.t("about"),
                                  on_click=lambda _e: show_about(self), visible=not self.compact),
                ],
                spacing=6 if self.compact else 10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            # a phone: the menu button close to the left edge, the TX lamp a little away from the right one
            padding=ft.Padding.only(left=2, right=10, top=2, bottom=2) if self.compact
            else ft.Padding.symmetric(horizontal=16, vertical=6),
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

    def _menu_index(self, view) -> int | None:
        """Where the screen is in the menu; a screen not in it marks the one it is reached from."""
        if not view.in_menu:
            parent = getattr(view, "menu_parent", None)
            view = next((v for v in self.menu_views if v.key == parent), None)
        return self.menu_views.index(view) if view in self.menu_views else None

    def has_view(self, key: str) -> bool:
        """In BBS SERVER mode only some of the views exist."""
        return any(v.key == key for v in self.views)

    def select(self, key: str, back: bool = False, force: bool = False) -> None:
        current = self.current_key if self.views and getattr(self, "current", None) is not None else None
        if (not force and not self._building and current == "settings" and key != "settings"
                and self.engine.config.configured and self.view("settings").dirty()):
            self._ask_unsaved(key, back)
            return
        if back:
            if self._history and self._history[-1] == key:
                self._history.pop()
        elif current and current != key and not self._building:
            self._history = [k for k in self._history if k != current][-self.MAX_HISTORY:] + [current]
        if key != "settings" and not self.engine.config.configured and self.has_view("settings"):
            # no callsign saved yet: nothing else can work, so Settings stays, with the callsign field
            key = "settings"
            if not self._building:  # a tap in the menu, not the screen being put together
                self.toast(self.t("call_required"), error=True)
                self.page.run_task(self.view("settings").require_call)
        index = next(i for i, v in enumerate(self.views) if v.key == key)
        _LAST_SCREEN[:] = [key]
        self.current = index
        self.rail.selected_index = self.drawer.selected_index = self._menu_index(self.views[index])
        if self.holders[index].content is not self.views[index].control:
            self.holders[index].content = self.views[index].control  # built the first time it is shown
        for i, holder in enumerate(self.holders):
            holder.visible = i == index or (self.views[i].keep_alive and holder.content is not None)
        self.views[index].shown()
        self._update_status()
        self._update_back()
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
        elif kind == "chat" and not data.get("entry", {}).get("out"):
            self._notify_chat(data["entry"])
        elif kind == "file_offer":
            self._file_offer(data)
        self._schedule_flush()

    def _file_offer(self, offer: dict[str, Any]) -> None:
        """Another station wants to send a file: take it or not (from any screen)."""
        remote = offer["remote"]

        def answer(yes: bool) -> None:
            self.page.pop_dialog()
            self.engine.answer_file(remote, yes)
            if yes and self.has_view("files"):
                self.select("files")

        self.sounds.play("message")
        if not self._foreground:
            android_notify.notify(self.t("files_offer_title"), self.t("files_offer_text", call=remote,
                                  name=offer["name"], size=size_text(offer["size"])), self.t("files"))
        elif self._window_away and not self.mobile:
            desktop_notify.notify(self.t("files_offer_title"), self.t("files_offer_text", call=remote,
                                  name=offer["name"], size=size_text(offer["size"])), "file")
        self.show_dialog(ft.AlertDialog(
            title=ft.Text(self.t("files_offer_title")),
            content=ft.Text(self.t("files_offer_text", call=remote, name=offer["name"], size=size_text(offer["size"]))),
            actions=[ft.TextButton(self.t("files_refuse"), on_click=lambda _e: answer(False)),
                     ft.FilledButton(self.t("files_accept_one"), icon=ft.Icons.DOWNLOAD, on_click=lambda _e: answer(True))],
        ))

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
            try:  # the app's clock must never stop: an error is logged, the next tick comes anyway
                if n % THEME_EVERY == 0 and self.engine.config.theme == "auto":
                    await self.apply_theme()
                self.refresh_now()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Tick")
            try:
                if not self._notify_asked and self.android and self._foreground and self.engine.config.configured:
                    self._notify_asked = True  # Android 13+: notifications (new messages) need a yes
                    android_notify.ask_permission()
                self._road_check()
                self._drive_check()
            except Exception:  # noqa: BLE001 - a warning is not worth stopping the app's clock
                logging.getLogger(__name__).exception("Road alerts")

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
        sym = self.engine.config.symbol or ""
        pic, name, _known = symbol_info(sym[:1], sym[1:], self.t.language) if len(sym) == 2 else ("", "", False)
        self.symbol_pic.value, self.symbol_pic.tooltip = pic, name or None
        self.symbol_pic.visible = bool(pic) and self.engine.config.configured
        self.tnc_dot.color = ft.Colors.GREEN if st["tnc_connected"] else ft.Colors.RED
        self.tnc_text.value = self.t("connected") if st["tnc_connected"] else self.t("disconnected")
        self.tnc_text.tooltip = None if st["tnc_connected"] else self.t.error(st.get("tnc_error")) or None
        aprsis = st.get("aprsis")
        self.is_box.visible = aprsis is not None
        if aprsis:
            self.is_dot.color = (ft.Colors.RED if time.monotonic() < self._is_sent_until else  # just sent
                                 ft.Colors.GREEN if aprsis["verified"] else
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
        sent_is = time.monotonic() < self._is_sent_until  # red for a second while something went to APRS-IS
        self._light("is", "tx" if aprsis and sent_is else "on" if aprsis and aprsis["verified"] else None)
        self.lamps["gps"].visible = gps is not None
        self._light("gps", "on" if gps and gps.get("fix") else None)
        # TX: red frame and text while transmitting is allowed, all red only while the radio is on air
        self._light("tx", ("tx" if on_air else "armed") if st["tx_enabled"] else None)
        # what a lamp means, on a computer when the mouse is over it (a phone tells it on a tap)
        self.lamps["tnc"].tooltip = f"TNC: {self.tnc_text.tooltip or self.tnc_text.value}"
        self.lamps["is"].tooltip = (f"APRS-IS: {aprsis.get('server') or ''} {aprsis.get('error') or ''}".strip()
                                    if aprsis else None)
        self.lamps["gps"].tooltip = f"GPS: {self.gps_box.tooltip or self.gps_text.value}" if gps else None
        self.lamps["tx"].tooltip = self.t("tx_on") if st["tx_enabled"] else self.t("tx_off")
        if hasattr(self, "position_btn"):
            self.position_btn.refresh()
        if self.has_view("messages"):
            messages = self.view("messages")
            badge = str(messages.unread_total) if messages.unread else None
            # on the plain and the selected icon: the count stays while Messages is open, until they are read
            for dest in (self.rail.destinations[self.menu_views.index(messages)],
                         self.drawer_dests["messages"]):
                dest.icon.badge = dest.selected_icon.badge = badge
            self.menu_btn.badge = badge  # the menu is closed on a phone: unread messages show on ☰

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

    INTERNET_EVERY = 60  # seconds between checks
    INTERNET_FAILS = 3  # failed checks in a row before the map goes offline…
    INTERNET_RETRY = 15  # …this many seconds apart
    RESUME_GRACE = 20  # back from the background: the phone's network wakes up first

    _foreground = True
    _resumed_at = 0.0

    def _lifecycle(self, e) -> None:
        state = getattr(e, "state", None)
        value = getattr(state, "value", state)
        _LOGGER.info("Lifecycle: %s (screen %s)", value, getattr(self, "current", None))
        if value in ("resume", "show"):
            if not self._foreground:
                self._resumed_at = time.monotonic()
                with contextlib.suppress(Exception):  # back on screen: the whole screen sent again, fresh
                    self.refresh_now()
            self._foreground = True
            with contextlib.suppress(Exception):  # a radio plugged in meanwhile: connect it now
                self.engine.connection.retry_now()
            if getattr(self, "_open_pending", None):  # a message notification was tapped (or the app opened)
                self._open_notified()
            if getattr(self, "_drive_pending", False):  # the notification was tapped (or the app opened): ask now
                self._drive_pending = False
                android_notify.cancel()
                self._offer_tracker()
        elif value in ("pause", "hide", "detach"):
            self._foreground = False

    def _checking_paused(self) -> bool:
        """In the background (or just back) a phone may cut the app off the network for a while
        (battery savers, Xiaomi above all): that is not "no internet" and must not flip the map."""
        return not self._foreground or time.monotonic() - self._resumed_at < self.RESUME_GRACE

    async def _watch_internet(self) -> None:
        """Every minute: can the map tiles be reached? Only after several failed tries in a row the
        maps switch to the offline map by themselves (and back as soon as the internet answers),
        with a short notice."""
        await asyncio.sleep(3)  # let the window come up first, so the notice is seen
        fails, first = 0, True
        while True:
            if self._checking_paused():
                await asyncio.sleep(5)
                continue
            up = await asyncio.to_thread(self._internet_up)
            if self._checking_paused():
                continue  # it went to the background while asking: the answer means nothing
            fails = 0 if up else fails + 1
            need = 1 if first else self.INTERNET_FAILS  # just started with no internet: offline at once
            first = False
            if (up and self.no_internet) or (fails >= need and not self.no_internet):
                self.no_internet = not up
                self.base_maps_changed()
                if not self.engine.config.map_offline:
                    self.toast(self.t("net_offline") if self.no_internet else self.t("net_online"), seconds=10)
                self.page.update()
            await asyncio.sleep(self.INTERNET_RETRY if 0 < fails < self.INTERNET_FAILS else self.INTERNET_EVERY)

    async def set_map_files(self, paths: list[str]) -> list:
        """The imported offline maps changed (settings): reopen them and redraw the maps."""
        self.engine.config.map_files = "\n".join(paths)
        failed = await asyncio.to_thread(offline_map.set_custom_maps, paths)
        self.base_maps_changed()
        self.save_config_soon()
        return failed

    def has_imported_maps(self) -> bool:
        return bool(offline_map.custom_maps())

    def wanted_map_mode(self) -> str:
        """What the user chose in the map menu."""
        conf = self.engine.config
        if not conf.map_offline:
            return "online"
        return "imported" if conf.map_imported and self.has_imported_maps() else "basic"

    def map_mode(self) -> str:
        """What is shown: without internet an offline map even when online was chosen."""
        if not self.offline_map():
            return "online"
        return "imported" if self.engine.config.map_imported and self.has_imported_maps() else "basic"

    def imported_shown(self) -> bool:
        return self.map_mode() == "imported"

    def set_map_mode(self, mode: str) -> None:
        conf = self.engine.config
        conf.map_offline = mode != "online"
        if mode != "online":
            conf.map_imported = mode == "imported"
        self.base_maps_changed()
        self.save_config_soon()
        if mode == "online" and self.no_internet:
            self.toast(self.t("net_offline"), seconds=6)
        self.page.update()

    def base_maps_changed(self) -> None:
        for v in self.views:
            if v.built and hasattr(v, "base_map_changed"):
                v.base_map_changed()

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
        self.update_state = await asyncio.to_thread(updates.check, self.folder, force, None,
                                                    self.engine.config.update_beta)
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

    _wakelock = None
    _screen_kept: bool | None = None

    async def apply_screen(self) -> None:
        """Settings › Keep the screen on: never, while TAK runs, or always (while the app is open)."""
        mode = self.engine.config.keep_screen_on
        want = mode == "always" or (mode == "tak" and self.engine.tak_mode)
        if want == self._screen_kept:
            return
        try:
            if self._wakelock is None:
                self._wakelock = ft.Wakelock()
            await (self._wakelock.enable() if want else self._wakelock.disable())
            self._screen_kept = want
        except Exception as err:  # noqa: BLE001 - e.g. not supported on this platform
            _LOGGER.info("Keep the screen on: %s", err)

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

    # ─── profiles: one callsign, up to three SSIDs with their own symbol ─────

    def _pick_profile(self, _e=None) -> None:
        conf = self.engine.config
        if not conf.configured or self.engine.exclusive_mode:
            return
        base = profiles.split_call(conf.callsign)[0]
        items = profiles.load(conf)

        def tile(i: int, p: dict) -> ft.Control:
            pic, name, _known = symbol_info(p["symbol"][:1], p["symbol"][1:], self.t.language)
            active = i == conf.profile
            return ft.ListTile(
                leading=ft.Text(pic, size=26), title=ft.Text(profiles.full_call(base, p["ssid"]),
                                                             weight=ft.FontWeight.BOLD if active else None),
                subtitle=ft.Text(name or p["symbol"]),
                trailing=ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.PRIMARY) if active else None,
                selected=active, on_click=lambda _e, i=i: self.page.run_task(self._use_profile, i),
            )

        def edit(_e) -> None:
            self.page.pop_dialog()
            self.select("settings")

        rows: list[ft.Control] = [tile(i, p) for i, p in enumerate(items)]
        if len(items) < profiles.MAX:
            rows.append(ft.Text(self.t("profile_add_hint"), size=12, color=ft.Colors.ON_SURFACE_VARIANT))
        self.show_dialog(ft.AlertDialog(
            title=ft.Text(self.t("profile_title")),
            content=ft.Column(rows, tight=True, width=360, spacing=4),
            actions=[ft.TextButton(self.t("profile_edit"), on_click=edit),
                     ft.TextButton(self.t("cancel"), on_click=lambda _e: self.page.pop_dialog())],
        ))

    async def _use_profile(self, index: int) -> None:
        """From now on everything goes out under this profile: saved, and the radio side set up again."""
        self.page.pop_dialog()
        conf = self.engine.config
        if index == conf.profile:
            return
        new = profiles.switch(conf, index)
        settings = self.view("settings") if self.has_view("settings") else None
        if settings:
            settings.discard()  # the form shows the new profile next time
        await self.apply_config(new)
        if settings and self.current_key == "settings":
            self.select("settings", force=True)
        self.toast(self.t("profile_now", call=new.callsign))

    # ─── on a phone: driving with the tracker off - offer to switch it on ─────

    _drive_pending = False
    _notify_asked = False
    _drive: drivedetect.DriveDetector | None = None
    _drive_asked: float | None = None  # the last offer: at most once an hour

    def _drive_check(self) -> None:
        engine, conf = self.engine, self.engine.config
        if not (self.mobile and conf.offer_tracker and conf.gps_source == "phone") or conf.tracker_on \
                or engine.exclusive_mode or not conf.configured or conf.offer_tracker_skip_day == date.today().isoformat():
            self._drive = None
            return
        if self._foreground and conf.run_background and not self._notify_asked:
            self._notify_asked = True  # Android 13+: notifications need a yes, asked while on screen
            android_notify.ask_permission()
        fix = engine.gps_fix()
        if not fix:
            return
        if self._drive is None:
            self._drive = drivedetect.DriveDetector(self._drive_asked)
        if not self._drive.update(time.time(), fix.latitude, fix.longitude, fix.speed_kmh):
            return
        self._drive_asked = self._drive.asked_at
        if self._foreground:
            self._offer_tracker()
        else:  # in the background: a notification; a tap brings the app back and it asks
            self._drive_pending = True
            android_notify.notify(self.t("drive_title"), self.t("drive_text"), self.t("drive_channel"))

    def _offer_tracker(self) -> None:
        if self.engine.config.tracker_on:
            return

        def answer(yes: bool) -> None:
            self.page.pop_dialog()
            if yes and not self.engine.config.tracker_on:
                self.position_btn._toggle(None)  # noqa: SLF001 - the same as the menu's "start"

        def not_today(_e) -> None:
            self.page.pop_dialog()
            self.engine.config.offer_tracker_skip_day = date.today().isoformat()
            self.save_config_soon()

        self.sounds.play("meet")
        self.show_dialog(ft.AlertDialog(
            title=ft.Text(self.t("drive_title")),
            content=ft.Column([ft.Text(self.t("drive_ask")),
                               ft.Text(self.t("drive_off_hint"), size=12, color=ft.Colors.ON_SURFACE_VARIANT)],
                              tight=True, spacing=10),
            actions_alignment=ft.MainAxisAlignment.END, actions_overflow_button_spacing=4,
            actions=[ft.TextButton(self.t("drive_today"), on_click=not_today),
                     ft.TextButton(self.t("drive_no"), on_click=lambda _e: answer(False)),
                     ft.FilledButton(self.t("drive_yes"), icon=ft.Icons.PLAY_ARROW, on_click=lambda _e: answer(True))],
        ))

    # ─── road incidents and moving stations ahead (while the tracker runs; both off by default) ─────

    def _road_check(self) -> None:
        engine, conf = self.engine, self.engine.config
        if not (conf.tracker_on and (conf.road_alerts or conf.meet_alerts)) or engine.exclusive_mode:
            return
        fix = engine.gps_fix()
        if not fix:
            return
        if not hasattr(self, "road_alerts"):
            self.road_alerts, self.meet_alerts = roadalert.RoadAlerts(), roadalert.RoadAlerts()
        course = roadalert.heading(fix.course, fix.speed_kmh, engine.my_track.get("track"))
        now, stations = time.time(), list(engine.station.heard.values())
        args = (now, fix.latitude, fix.longitude, course, stations, conf.road_alert_km, fix.speed_kmh)
        if conf.road_alerts and (found := self.road_alerts.check(*args)):
            self._warn_ahead(found, "road")  # one bubble at a time: stations wait for the next look
        elif conf.meet_alerts and (found := self.meet_alerts.check(
                *args, want=roadalert.moving_station(str(engine.me)), max_age=roadalert.STATION_MAX_AGE)):
            self._warn_ahead(found, "meet", course)

    def _warn_ahead(self, found: list, kind: str, course: float | None = None) -> None:
        """A bubble with the nearest one ahead (and how many more), and a sound."""
        entry, along, side = found[0]
        t = self.t
        if kind == "meet":
            how = roadalert.relation(course, entry) if course is not None else None
            where = t(f"meet_{how}" if how else "meet_ahead", d=distance_text(along))
        else:
            where = t("road_ahead", d=distance_text(along))
        if abs(side) >= 0.5:
            where += f" ({t('road_right' if side > 0 else 'road_left')})"
        pic, name, _known = symbol_info(entry.get("symbol_table"), entry.get("symbol"), t.language)
        speed = entry.get("speed")
        extra = units.current.speed(speed) if kind == "meet" and speed else (entry.get("comment") or "").strip()
        what = " · ".join(x for x in (entry["call"], name, extra) if x)
        lines = [ft.Text(where, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK_87),
                 ft.Text(what, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS, color=ft.Colors.BLACK_87)]
        if len(found) > 1:
            lines.append(ft.Text(t("road_more", n=len(found) - 1), size=12, color=ft.Colors.BLACK_87))
        self.sounds.play(kind)
        self.show_dialog(ft.SnackBar(
            ft.Row([ft.Text(pic or "⚠️", size=28), ft.Column(lines, spacing=2, tight=True, expand=True)],
                   spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ft.Colors.AMBER_200 if kind == "road" else ft.Colors.LIGHT_BLUE_100,
            behavior=ft.SnackBarBehavior.FLOATING, width=520,
            duration=20000 if kind == "road" else 10000, persist=False, show_close_icon=True,
            close_icon_color=ft.Colors.BLACK_87,
            action=ft.SnackBarAction(t("road_show"), text_color=ft.Colors.BROWN_900 if kind == "road" else ft.Colors.BLUE_900,
                                     on_click=lambda _e, c=entry["call"]: self.show_station(c)),
        ))

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

    _open_pending: tuple[str, str] | None = None  # a notification was posted: where a tap on it leads

    _window_away = False  # a computer: the window is not the active one (another app in front, minimized)

    def _away(self) -> bool:
        """Nobody is looking: the phone app in the background, or the computer's window not in front."""
        return not self._foreground or self._window_away

    def _system_notify(self, title: str, text: str, nid: int, unread: int = 0) -> bool:
        """The system's own notification (Android, Linux, Windows, macOS); False where there is none.
        `unread`: all unread messages, said under the message (Android: in the notification's header)."""
        sub = self.t("unread_total", n=unread) if unread > 1 else None
        if self.android:
            return android_notify.notify(title, text, self.t("messages"), channel=android_notify.MESSAGES_CHANNEL,
                                         nid=nid, silent=True, sub=sub, number=unread)  # the app beeps itself
        if self.mobile or getattr(self.page, "web", False):
            return False  # iOS: the app does not run in the background; a browser: no system of ours
        return desktop_notify.notify(title, f"{text}\n{sub}" if sub else text,
                                     "chat" if nid == android_notify.CHAT_ID else "message")

    def _notify_chat(self, entry: dict[str, Any]) -> None:
        """A chat line while nobody looks: a notification (on screen the chat shows it)."""
        if not self._away() or not self.has_view("chat"):
            return
        if self._system_notify(f"{self.t('chat')} · {entry['from']}", entry["text"], android_notify.CHAT_ID) \
                and self.android:
            self._open_pending = ("chat", "")  # a tap on it brings the app back: to the chat

    def _open_notified(self) -> None:
        """Back on screen after a message or chat notification: that conversation, the notification gone."""
        pending, self._open_pending = self._open_pending, None
        if not pending:
            return
        android_notify.cancel(android_notify.MESSAGE_ID)
        android_notify.cancel(android_notify.CHAT_ID)
        key, call = pending
        if not self.has_view(key):
            return
        if key == "messages":
            self.view("messages").open_conversation(call)
        self.select(key)

    def _notify_message(self, message: dict[str, Any]) -> None:
        if not self.has_view("messages"):
            return
        if self._away():  # the system's notification; on a phone a tap on it opens the conversation
            if self._system_notify(self.t("message_from", call=message["from"]), message["text"],
                                   android_notify.MESSAGE_ID, self.view("messages").unread_total) and self.android:
                self._open_pending = ("messages", message["from"])
                return  # a computer: the bar below waits in the window too
        if self.current_key == "messages" and self.view("messages").selected == message["from"].upper():
            return
        sender = message["from"]

        def open_it(_e) -> None:
            self.page.pop_dialog()
            self.view("messages").open_conversation(sender)
            self.select("messages")

        # persist=False: with an action button Flutter would keep the bar until it is closed by hand
        bar = ft.SnackBar(
            ft.Text(f"{self.t('message_from', call=sender)}: {message['text']}"),
            action=ft.SnackBarAction(label=self.t("messages"), on_click=open_it),
            duration=5000, persist=False,
            behavior=ft.SnackBarBehavior.FLOATING, width=520,
        )
        self._message_notice = (sender.upper(), bar)
        self.show_dialog(bar)

    _message_notice: tuple[str, ft.SnackBar] | None = None

    def message_read(self, call: str) -> None:
        """The conversation is on screen: the bar about its new message has nothing more to say."""
        notice = self._message_notice
        if notice and notice[0] == call.upper():
            self._message_notice = None
            if notice[1].open:
                notice[1].open = False
                try:
                    notice[1].update()
                except Exception:  # noqa: BLE001 - already gone
                    pass

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
            u = units.current
            wx = []
            if isinstance(weather.get("temperature"), (int, float)):
                wx.append(u.temperature_text(weather["temperature"]))
            if weather.get("humidity") is not None:
                wx.append(f"{weather['humidity']} %")
            if isinstance(weather.get("pressure"), (int, float)):
                wx.append(u.pressure_text(weather["pressure"]))
            if isinstance(weather.get("wind_speed"), (int, float)):
                wx.append(u.wind(weather["wind_speed"]))
            if wx:
                rows.append(ft.Text("🌦️ " + ", ".join(wx)))
        # aprslib: altitude in metres, speed in km/h
        shown = {"altitude": lambda v: units.current.length(v), "speed": lambda v: units.current.speed(v),
                 "course": lambda v: f"{v:.0f}°"}
        for key, show in shown.items():
            value = entry.get(key)
            if isinstance(value, (int, float)):
                rows.append(ft.Text(f"{self.t('st_' + key)}: {show(value)}"))
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
        books = callbook_links(call)
        if books:  # the operator in the public callbooks (the callsign without its SSID or /P), the station on aprs.fi
            actions.append(ft.PopupMenuButton(
                content=ft.Row([ft.Icon(ft.Icons.PERSON_SEARCH, color=ft.Colors.PRIMARY, size=18),
                                ft.Text(self.t("callbooks"), color=ft.Colors.PRIMARY)], spacing=6, tight=True),
                tooltip=self.t("callbooks"),
                items=[ft.PopupMenuItem(name, icon=ft.Icons.OPEN_IN_NEW,
                                        on_click=lambda _e, url=url: self.page.run_task(ft.UrlLauncher().launch_url, url))
                       for name, url in books]))
        actions.append(ft.TextButton(self.t("close"), on_click=lambda _e: self.page.pop_dialog()))
        self.show_dialog(ft.AlertDialog(
            title=ft.Text(f"{pic}  {call}"),
            content=ft.Column(rows, tight=True, spacing=6, width=420),
            actions=actions,
        ))


_CALLSIGN = re.compile(r"^(?:[A-Z]{1,2}[0-9]|[0-9][A-Z])[A-Z0-9]?[0-9]?[A-Z]{1,4}$")  # OK1SIM, 9A2XY, S57AB, DL1ABC


def qrz_url(call: str) -> str | None:
    """QRZ.com's page for a station: the base callsign (no -SSID, no /P), or None for an object, an item or a
    name that is not a callsign (REPEAT, 438.725BR)."""
    parts = [p for p in call.upper().split("-")[0].split("/") if p]
    base = max(parts, key=len, default="")  # OK1SIM/P, F/OK1SIM: the longest part is the callsign
    return f"https://www.qrz.com/db/{base}" if _CALLSIGN.match(base) else None


def callbook_links(call: str) -> list[tuple[str, str]]:
    """Public pages about a station, free to open: the callbooks (QRZ.com, HamQTH, QRZCQ: the operator, by the
    base callsign) and aprs.fi (this very station, with its SSID: its track and packets). Empty for an
    object, an item or a service name."""
    qrz = qrz_url(call)
    if not qrz:
        return []
    base = qrz.rsplit("/", 1)[1]
    station = call.upper().strip()
    return [("QRZ.com", qrz),
            ("HamQTH", f"https://www.hamqth.com/{base}"),
            ("QRZCQ", f"https://www.qrzcq.com/call/{base}"),
            ("aprs.fi", f"https://aprs.fi/#!call=a%2F{quote(station, safe='')}")]


LOG_FILE = "app.log"


def _log_to_file() -> None:
    """Also into a small file in the data folder (two of 512 kB at most): what went on before a freeze or a
    crash on a phone can be copied from About and sent."""
    root = logging.getLogger()
    if any(getattr(h, "_aprs_kiss", False) for h in root.handlers):
        return
    try:
        handler = logging.handlers.RotatingFileHandler(data_dir() / LOG_FILE, maxBytes=512_000, backupCount=1,
                                                       encoding="utf-8")
    except OSError:
        return
    handler._aprs_kiss = True
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)

    def on_error(loop, context) -> None:  # an error in a task nobody waits for: into the log too
        _LOGGER.error("Unhandled: %s", context.get("message"), exc_info=context.get("exception"))
        loop.default_exception_handler(context)

    with contextlib.suppress(RuntimeError):
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(on_error)
        threading.Thread(target=_watch_loop, args=(loop,), daemon=True, name="loop-watch").start()


def _watch_loop(loop: asyncio.AbstractEventLoop, every: float = 5, stuck: float = 10) -> None:
    """Is the app's event loop alive? Every few seconds it is asked to tick; when it has not for a while
    (something blocks it: then no tap, no back, no menu works), what every thread is doing goes to the log."""
    last = [time.monotonic()]
    reported = False

    def beat() -> None:
        last[0] = time.monotonic()

    while not loop.is_closed():
        with contextlib.suppress(RuntimeError):
            loop.call_soon_threadsafe(beat)
        time.sleep(every)
        late = time.monotonic() - last[0]
        if late > stuck and not reported:
            reported = True
            frames = sys._current_frames()  # noqa: SLF001 - the only way to see a blocked thread
            stacks = "\n".join(f"--- {t.name}\n" + "".join(traceback.format_stack(frames[t.ident]))
                               for t in threading.enumerate() if t.ident in frames)
            _LOGGER.error("The app is stuck for %.0f s; threads:\n%s", late, stacks)
        elif late <= stuck and reported:
            reported = False
            _LOGGER.warning("The app runs again")


async def main(page: ft.Page) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    _log_to_file()
    _LOGGER.info("APRS & Packet %s, data in %s", VERSION, data_dir())
    app = App(page)
    await app.start()
