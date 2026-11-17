"""The APRS & Packet app: one window, a navigation rail, a status bar and the screens."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Awaitable
from typing import Any

import flet as ft

from aprs_kiss_core.config import VERSION, Config, data_dir, load_config, save_config
from aprs_kiss_core.engine import Engine, TransmitRefused

from .about import show_about
from .i18n import Translator
from .symbols import symbol_info
from .views.base import View, clock
from .views.chat import ChatView
from .views.map import MapView
from .views.messages import MessagesView
from .views.monitor import MonitorView
from .views.settings import SettingsView
from .views.stations import StationsView, describe
from .views.terminal import TerminalView

_LOGGER = logging.getLogger(__name__)

VIEWS = [MapView, MessagesView, StationsView, TerminalView, ChatView, MonitorView, SettingsView]
FLUSH_DELAY = 0.25
TICK_SECONDS = 5.0


class App:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.folder = data_dir()
        self.engine: Engine | None = None
        self.views: list[View] = []
        self.current = 0
        self._flush_pending = False
        self._closing = False

    # ─── start and stop ───────────────────────────────────────────────────

    async def start(self) -> None:
        page = self.page
        page.title = "APRS & Packet"
        page.theme_mode = ft.ThemeMode.SYSTEM
        page.theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)
        page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)
        page.padding = 0
        page.window.prevent_close = True
        page.window.on_event = self._on_window_event
        page.on_close = self._on_page_close  # web and mobile: the session ended
        page.window.min_width = 640
        page.window.min_height = 480

        config = await asyncio.to_thread(load_config, self.folder)
        self.engine = Engine(config, self.folder)
        self.engine.add_listener(self._on_event)
        await self.engine.start()
        self.build()
        if not config.configured:
            self.select("settings")
        page.run_task(self._tick)

    async def _on_window_event(self, e: ft.WindowEvent) -> None:
        if e.type == ft.WindowEventType.CLOSE:
            await self.shutdown()
            await self.page.window.destroy()

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
        await asyncio.to_thread(save_config, config, self.folder)
        await self.engine.reconfigure(config)
        if language_changed:
            self.build()
            self.select("settings")
        self.toast(self.t("saved"))
        self.refresh_now()

    # ─── layout ───────────────────────────────────────────────────────────

    def build(self) -> None:
        self.t = Translator(self.engine.config.language)
        key = self.current_key if self.views else "map"
        self.views = [cls(self) for cls in VIEWS]
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=88,
            destinations=[ft.NavigationRailDestination(icon=v.icon, selected_icon=v.selected_icon,
                                                       label=self.t(v.key)) for v in self.views],
            on_change=lambda e: self.select(self.views[e.control.selected_index].key),
        )
        self.holders = [ft.Container(v.control, visible=False, expand=True, padding=ft.Padding.all(12))
                        for v in self.views]

        self.callsign = ft.Text(weight=ft.FontWeight.BOLD, size=18)
        self.tnc_dot = ft.Icon(ft.Icons.CIRCLE, size=12)
        self.tnc_text = ft.Text(size=13)
        self.is_dot = ft.Icon(ft.Icons.CIRCLE, size=12)
        self.is_box = ft.Row([self.is_dot, ft.Text("APRS-IS", size=13)], spacing=4, tight=True)
        self.tx_switch = ft.Switch(label=self.t("transmit"), on_change=self._tx_changed)
        self.tx_box = ft.Container(self.tx_switch, border_radius=20, padding=ft.Padding.symmetric(horizontal=10))
        status = ft.Container(
            ft.Row(
                [
                    self.callsign,
                    ft.Row([self.tnc_dot, ft.Text(self.t("tnc"), size=13), self.tnc_text], spacing=4, tight=True),
                    self.is_box,
                    ft.Container(expand=True),
                    ft.IconButton(ft.Icons.SHARE_LOCATION, tooltip=self.t("beacon_now"), on_click=self._beacon_now),
                    self.tx_box,
                    ft.IconButton(ft.Icons.INFO_OUTLINE, tooltip=self.t("about"),
                                  on_click=lambda _e: show_about(self)),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=6),
            bgcolor=ft.Colors.SURFACE_CONTAINER,
        )
        self.page.controls.clear()
        self.page.add(
            ft.SafeArea(
                ft.Row(
                    [
                        self.rail,
                        ft.VerticalDivider(width=1),
                        ft.Column([status, ft.Stack(self.holders, expand=True)], expand=True, spacing=0),
                    ],
                    expand=True,
                    spacing=0,
                ),
                expand=True,
            )
        )
        self.select(key)

    @property
    def current_key(self) -> str:
        return self.views[self.current].key if self.views else ""

    def view(self, key: str) -> View:
        return next(v for v in self.views if v.key == key)

    def select(self, key: str) -> None:
        index = next(i for i, v in enumerate(self.views) if v.key == key)
        self.current = index
        self.rail.selected_index = index
        for i, holder in enumerate(self.holders):
            holder.visible = i == index
        self.views[index].shown()
        self._update_status()
        self.page.update()

    # ─── engine events ────────────────────────────────────────────────────

    def _on_event(self, kind: str, data: dict[str, Any]) -> None:
        for v in self.views:
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
        self._update_status()
        try:
            self.views[self.current].refresh()
        except Exception:  # noqa: BLE001 - a view error must not stop the updates
            _LOGGER.exception("Refreshing %s failed", self.current_key)
        self.page.update()

    async def _tick(self) -> None:
        """Ages, map markers skipped by the rate limit and the like."""
        while not self._closing:
            await asyncio.sleep(TICK_SECONDS)
            self.refresh_now()

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
        self.tx_switch.value = st["tx_enabled"]
        self.tx_switch.disabled = not self.engine.config.configured
        self.tx_switch.tooltip = self.t("tx_on") if st["tx_enabled"] else self.t("tx_off")
        self.tx_box.bgcolor = ft.Colors.ERROR_CONTAINER if st["tx_enabled"] else None
        messages = self.view("messages")
        dest = self.rail.destinations[self.views.index(messages)]
        dest.badge = str(len(messages.unread)) if messages.unread else None

    def _tx_changed(self, e) -> None:
        self.engine.set_tx(bool(e.control.value))

    # ─── helpers for the views ────────────────────────────────────────────

    def set_show_internet(self, value: bool) -> None:
        """Map and station list share this choice; it is saved, the connection is not restarted."""
        self.engine.config.show_internet = value
        self.page.run_task(asyncio.to_thread, save_config, self.engine.config, self.folder)
        for key in ("map", "stations"):
            self.view(key).force()
        self.refresh_now()

    def tracked(self) -> set[str]:
        return {c.strip().upper() for c in self.engine.config.tracked_callsigns.replace(" ", ",").split(",")
                if c.strip()}

    def toast(self, text: str, error: bool = False) -> None:
        self.page.show_dialog(ft.SnackBar(
            ft.Text(text, color=ft.Colors.ON_ERROR_CONTAINER if error else None),
            bgcolor=ft.Colors.ERROR_CONTAINER if error else None,
            behavior=ft.SnackBarBehavior.FLOATING, width=520,
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
        if self.current_key == "messages" and self.view("messages").selected == message["from"].upper():
            return
        sender = message["from"]

        def open_it(_e) -> None:
            self.page.pop_dialog()
            self.view("messages").open_conversation(sender)
            self.select("messages")

        self.page.show_dialog(ft.SnackBar(
            ft.Text(f"{self.t('message_from', call=sender)}: {message['text']}"),
            action=ft.SnackBarAction(label=self.t("messages"), on_click=open_it),
            duration=5000,
            behavior=ft.SnackBarBehavior.FLOATING, width=520,
        ))

    async def _beacon_now(self, _e) -> None:
        if not self.engine.config.has_position:
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
        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text(f"{pic}  {call}"),
            content=ft.Column(rows, tight=True, spacing=6, width=420),
            actions=actions,
        ))


async def main(page: ft.Page) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    _LOGGER.info("APRS & Packet %s, data in %s", VERSION, data_dir())
    app = App(page)
    await app.start()
