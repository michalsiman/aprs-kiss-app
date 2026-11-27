"""TAK: the app as a TAK station over the radio - a map of the TAK stations, GeoChat, our position.

Switching it on takes a typed sentence and turns everything else off, like BBS SERVER.
"""

from __future__ import annotations

import asyncio
import time

import flet as ft
import flet_map as fm

from aprs_kiss_core import units
from aprs_kiss_core.config import Config

from ..i18n import TEXTS
from ..legend import map_label
from .map_source import MapSourceButton
from .base import View, clock, distance_km, distance_short
from .bbs import _plain
from ..offline_map import LAND, MIN_ZOOM, BaseMap, ScaleBar, gestures
from .base import toggle
from .map import MapControls

TEAM_COLORS = {
    "White": "#9E9E9E", "Yellow": "#F9A825", "Orange": "#EF6C00", "Magenta": "#D81B60", "Red": "#E53935",
    "Maroon": "#880E4F", "Purple": "#8E24AA", "Dark Blue": "#283593", "Blue": "#1E88E5", "Cyan": "#00ACC1",
    "Teal": "#00897B", "Green": "#43A047", "Dark Green": "#1B5E20", "Brown": "#6D4C41",
}
AFFILIATION_COLORS = {"f": "#1E88E5", "h": "#E53935", "n": "#43A047", "u": "#F9A825"}


def tak_confirmed(text: str) -> bool:
    return bool(_plain(text)) and _plain(text) in {_plain(t["tak_confirm_text"]) for t in TEXTS.values()
                                                   if "tak_confirm_text" in t}


class TakView(View):
    key = "tak"
    lazy = True
    icon = ft.Icons.RADAR_OUTLINED if hasattr(ft.Icons, "RADAR_OUTLINED") else ft.Icons.RADAR
    selected_icon = ft.Icons.RADAR

    def build(self) -> ft.Control:
        self._signature = None
        self._centred = False
        on = self.engine.tak_mode
        self.switch = ft.Switch(label=None if on else self.t("tak"), value=on, on_change=self._toggle,
                                scale=0.75 if on else None)
        # off: the whole explanation, wrapped; on: one short line (the rest in its tooltip)
        self.state = ft.Text(size=12 if on else 15, weight=ft.FontWeight.BOLD if on else ft.FontWeight.W_500,
                             no_wrap=on, overflow=ft.TextOverflow.ELLIPSIS if on else None, expand=on)
        self.hint = ft.Text(size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        if not on:
            header = ft.Container(
                ft.Column([ft.Row([ft.Icon(ft.Icons.RADAR, color=ft.Colors.PRIMARY), self.switch]), self.state,
                           self.hint], spacing=4, tight=True),
                padding=12, border_radius=8, bgcolor=ft.Colors.SURFACE_CONTAINER,
            )
            return ft.Column([header], expand=True)
        compact = self.app.compact
        # Running: one slim line - the two screens (map, GeoChat), who we are, the warnings, "send my position"
        # and the switch, small; the long texts went to tooltips and to the top bar's TX lamp.
        self.tx_warn = ft.IconButton(ft.Icons.WARNING_AMBER, icon_color=ft.Colors.ERROR, icon_size=20,
                                     tooltip=self.t("tak_tx_needed"),
                                     on_click=lambda _e: self.app.toast(self.t("tak_tx_needed"), error=True))
        self.tab = "map"
        self.unread = 0
        self.map_tab = toggle(ft.Icons.MAP_OUTLINED, ft.Icons.MAP, True, self.t("map"), lambda _e: self._show("map"))
        self.chat_tab = toggle(ft.Icons.CHAT_OUTLINED, ft.Icons.CHAT, False, self.t("tak_chat"),
                               lambda _e: self._show("chat"))
        position = ft.IconButton(ft.Icons.MY_LOCATION, tooltip=self.t("tak_send_position"), on_click=self._position)
        if compact:  # a phone: the buttons on one line, who we are on the next, whole
            self.state.expand, self.state.no_wrap = False, False
            line = ft.Column([
                ft.Row([self.map_tab, self.chat_tab, ft.Container(expand=True), self.tx_warn, position, self.switch],
                       spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(self.state, padding=ft.Padding.only(left=8, bottom=4)),
            ], spacing=0, tight=True)
        else:
            line = ft.Row([ft.Icon(ft.Icons.RADAR, color=ft.Colors.PRIMARY), self.state, self.tx_warn, position,
                           self.switch], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        header = ft.Container(
            line,
            padding=ft.Padding.symmetric(horizontal=4), border_radius=8, bgcolor=ft.Colors.SURFACE_CONTAINER,
        )
        here = self.engine.my_position()
        self.markers = fm.MarkerLayer(markers=[])
        self._zoom = 12 if here else 7
        self.base = BaseMap(self.markers, here or (49.8, 15.5), self._zoom)
        self._camera_asked = 0.0
        self.map = fm.Map(
            expand=True, bgcolor=LAND,  # light in the dark mode too, like all the maps
            initial_center=fm.MapLatitudeLongitude(*(here or (49.8, 15.5))), initial_zoom=self._zoom, min_zoom=MIN_ZOOM,
            layers=self.base.layers(self.app.offline_map(), self.app.imported_shown(), self.engine.config.map_online), on_pointer_up=self._gesture_end,
            interaction_configuration=gestures(),
        )
        self.source_btn = MapSourceButton(self.app)
        self.offline_btn = self.source_btn.control
        self.controls = MapControls(self.map, self.t, lambda: self.app.page.run_task(self._ask_camera, 0.7))
        map_tools = ft.Container(self.offline_btn, left=8, top=8, border_radius=8,
                                 bgcolor=ft.Colors.with_opacity(0.85, ft.Colors.SURFACE))
        self.scale = ScaleBar()
        self.scale.show((here or (49.8, 15.5))[0], self._zoom)
        map_box = ft.Container(ft.Stack([self.map, map_tools, self.controls.control, self.scale.control,
                                         self.base.credit], expand=True),
                               expand=True, border_radius=8)
        self.stations = ft.ListView(spacing=0, height=170)
        self.chat = ft.ListView(expand=True, spacing=6, auto_scroll=True, auto_scroll_animation=0, padding=ft.Padding.all(6))
        self.to = ft.Dropdown(dense=True, width=130 if compact else 150, value="",
                              options=[ft.DropdownOption(key="", text=self.t("tak_everybody"))])
        self.text = ft.TextField(hint_text=self.t("type_here"), expand=True, dense=True, on_submit=self._send)
        # the team's moves shown in GeoChat: who appeared, who moved how far
        self.moves: list[dict] = []
        self._placed = {uid: (st["lat"], st["lon"], time.time()) for uid, st in self.engine.tak_stations.items()}
        self._seen_time = max((c["time"] for c in self.engine.tak_chat), default=0)
        chat_box = ft.Container(self.chat, expand=True, border_radius=8, bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST)
        send_row = ft.Row([self.to, self.text, ft.IconButton(ft.Icons.SEND, tooltip=self.t("send"), on_click=self._send)])
        if compact:
            # a phone: map and GeoChat are two screens; the map stays loaded under the chat (no rebuild)
            self.chat_layer = ft.Container(ft.Column([chat_box, send_row], expand=True, spacing=6),
                                           bgcolor=ft.Colors.SURFACE, visible=False, left=0, top=0, right=0, bottom=0)
            self._typing_hides = [header]
            self.text.on_focus = lambda _e: self._typing(True)
            self.text.on_blur = lambda _e: self._typing(False)
            return ft.Column([header, ft.Stack([map_box, self.chat_layer], expand=True)], expand=True, spacing=6)
        panel = ft.Container(
            ft.Column([
                ft.Text(self.t("tak_stations"), weight=ft.FontWeight.BOLD), self.stations,
                ft.Text(self.t("tak_chat"), weight=ft.FontWeight.BOLD), chat_box, send_row,
            ], expand=True, spacing=6),
            width=380,
        )
        return ft.Column([header, ft.Row([map_box, panel], expand=True,
                                         vertical_alignment=ft.CrossAxisAlignment.STRETCH)], expand=True)

    def _show(self, tab: str) -> None:
        """A phone: the map or GeoChat; opening GeoChat reads the new messages."""
        self.tab = tab
        self.map_tab.selected, self.chat_tab.selected = tab == "map", tab == "chat"
        self.chat_layer.visible = tab == "chat"
        if tab == "chat":
            self.unread = 0
        self.chat_tab.badge = str(self.unread) if self.unread else None
        self.app.page.update()

    def _typing(self, on: bool) -> None:
        for control in self._typing_hides:
            control.visible = not on
        self.app.page.update()

    def base_map_changed(self) -> None:
        """Called by the app when the internet goes away or returns."""
        if hasattr(self, "map"):
            self.map.layers = self.base.layers(self.app.offline_map(), self.app.imported_shown(), self.engine.config.map_online)
            self.source_btn.refresh()

    def _gesture_end(self, _e=None) -> None:
        self.app.page.run_task(self._ask_camera, 0.8)

    async def _ask_camera(self, delay: float = 0) -> None:
        """Where the map looks (asked after a gesture, not sent for every frame): the offline map follows."""
        await asyncio.sleep(delay)
        self._camera_asked = time.monotonic()
        try:
            camera = await self.map.get_camera()
        except Exception:  # noqa: BLE001 - the map is not on screen
            return
        lon = (camera.center.longitude + 180) % 360 - 180
        self.controls.rotated(camera.rotation)
        self.scale.show(camera.center.latitude, camera.zoom)
        self.base.moved(camera.center.latitude, lon, camera.zoom, self.app.offline_map())
        self.app.page.update()  # the needle, the scale, the offline map: only what changed is sent

    def on_event(self, kind, data) -> None:
        if kind in ("tak", "gps", "update"):
            self._signature = None
        if kind == "tak" and hasattr(self, "_seen_time"):
            self._count_unread()  # also while another screen is open

    # ─── drawing ──────────────────────────────────────────────────────────

    def refresh(self) -> None:
        eng = self.engine
        if hasattr(self, "map") and self.app.offline_map() and time.monotonic() - self._camera_asked > 2:
            self._camera_asked = time.monotonic()
            self.app.page.run_task(self._ask_camera)
        now = time.time()
        stations = eng.tak_stations
        here = eng.my_position()
        signature = (eng.tak_mode, eng.station.tx_enabled, len(stations), max((s["received"] for s in stations.values()),
                     default=0), len(eng.tak_chat), int(now // 30), here)
        if signature == self._signature:
            return
        self._signature = signature
        conf = eng.config
        if eng.tak_mode:
            self.state.value = self.t("tak_running", call=eng.tak_callsign, team=conf.tak_team, n=len(stations))
            self.state.tooltip = self.t("tak_running", call=eng.tak_callsign, team=conf.tak_team, n=len(stations))
            self.state.color = ft.Colors.GREEN
            self.hint.value = "" if eng.station.tx_enabled else self.t("tak_tx_needed")
            self.tx_warn.visible = not eng.station.tx_enabled
        else:
            self.state.value, self.state.color, self.hint.value = self.t("tak_off"), None, ""
        self.hint.visible = bool(self.hint.value)
        if not eng.tak_mode:
            return
        if here and not self._centred:
            self._centred = True
            self.app.page.run_task(self.map.center_on, fm.MapLatitudeLongitude(*here), 12)
        markers = [self._marker(s["lat"], s["lon"], s["callsign"], self._color(s), s["stale"] and now > s["stale"])
                   for s in stations.values()]
        if here:
            markers.append(self._marker(*here, eng.tak_callsign, TEAM_COLORS.get(conf.tak_team, "#00ACC1"), False,
                                        me=True))
        self.markers.markers = markers
        rows = sorted(stations.values(), key=lambda s: -s["received"])
        self.stations.controls = [ft.ListTile(
            leading=ft.Icon(ft.Icons.CIRCLE, color=self._color(s), size=14),
            title=ft.Text(s["callsign"], weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(" · ".join(x for x in (s["team"], s["role"], clock(s["received"]),
                                                     units.current.speed(s["speed"] * 3.6) if s["speed"] else "") if x),
                             size=12),
            dense=True, on_click=lambda _e, st=s: self.app.page.run_task(
                self.map.center_on, fm.MapLatitudeLongitude(st["lat"], st["lon"]), 14),
        ) for s in rows] or [ft.Text(self.t("tak_no_stations"), color=ft.Colors.ON_SURFACE_VARIANT)]
        current = self.to.value
        self.to.options = [ft.DropdownOption(key="", text=self.t("tak_everybody"))] + [
            ft.DropdownOption(key=s["uid"], text=s["callsign"]) for s in rows]
        self.to.value = current if any(o.key == current for o in self.to.options) else ""
        self._watch_team(stations, now)
        self._count_unread()
        items = sorted([*eng.tak_chat, *self.moves], key=lambda c: c["time"])
        self.chat.controls = [self._move_line(c) if "move" in c else self._bubble(c) for c in items] or [
            ft.Text(self.t("tak_no_chat"), color=ft.Colors.ON_SURFACE_VARIANT)]

    MOVE_M = 200  # a station has to move this far before GeoChat says so…
    MOVE_EVERY = 120  # …and at most once in this many seconds per station

    def _watch_team(self, stations: dict, now: float) -> None:
        """Who appeared on the map, who moved how far: lines in GeoChat between the messages."""
        for uid, st in stations.items():
            where = (st["lat"], st["lon"])
            before = self._placed.get(uid)
            if before is None:
                self.moves.append({"time": now, "move": self.t("tak_appeared", call=st["callsign"])})
            elif (now - before[2] >= self.MOVE_EVERY
                  and distance_km(*before[:2], *where) * 1000 >= self.MOVE_M):
                metres = distance_km(*before[:2], *where) * 1000
                far = distance_short(metres / 1000)
                self.moves.append({"time": now, "move": self.t("tak_moved", call=st["callsign"], far=far)})
            else:
                continue
            self._placed[uid] = (*where, now)
        del self.moves[:-100]

    def _count_unread(self) -> None:
        """New GeoChat messages while the map is shown: a number on the GeoChat icon and a message."""
        new = [c for c in self.engine.tak_chat if c["time"] > self._seen_time and not c.get("out")]
        if not new:
            return
        self._seen_time = max(c["time"] for c in new)
        if self.app.compact and self.tab != "chat" or self.app.current_key != self.key:
            self.unread += len(new)
            if self.app.compact:
                self.chat_tab.badge = str(self.unread)
            last = new[-1]
            self.app.toast(f"{self.t('tak_chat')} · {last['from']}: {last['text']}")

    def _move_line(self, c: dict) -> ft.Control:
        return ft.Row([ft.Text(f"{clock(c['time'])}  {c['move']}", size=11, italic=True,
                               color=ft.Colors.ON_SURFACE_VARIANT)], alignment=ft.MainAxisAlignment.CENTER)

    def _color(self, s: dict) -> str:
        return TEAM_COLORS.get(s.get("team") or "", AFFILIATION_COLORS.get(s["type"].split("-")[1] if
                                                                          s["type"].count("-") else "", "#1E88E5"))

    def _marker(self, lat: float, lon: float, label: str, color: str, stale: bool, me: bool = False) -> fm.Marker:
        dot = ft.Container(width=16 if me else 14, height=16 if me else 14, border_radius=8, bgcolor=color,
                           border=ft.Border.all(2, ft.Colors.WHITE if me else ft.Colors.BLACK),
                           opacity=0.45 if stale else 1.0)
        tag = map_label(label, bold=True, opacity=0.6 if stale else 1.0)
        return fm.Marker(coordinates=fm.MapLatitudeLongitude(lat, lon), width=120, height=44,
                         content=ft.Column([dot, tag], spacing=2, tight=True,
                                           horizontal_alignment=ft.CrossAxisAlignment.CENTER))

    def _bubble(self, c: dict) -> ft.Control:
        out = c.get("out")
        who = (f"→ {c.get('to_callsign') or self.t('tak_everybody')}" if out else c["from"]
               + ("" if c.get("to") in ("All", "All Chat Rooms") else " → " + self.engine.tak_callsign))
        box = ft.Container(
            ft.Column([ft.Text(who, size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                       ft.Text(c["text"], selectable=True),
                       ft.Text(clock(c["time"]), size=10, color=ft.Colors.ON_SURFACE_VARIANT)], spacing=1, tight=True),
            padding=ft.Padding.symmetric(horizontal=10, vertical=6), border_radius=10,
            bgcolor=ft.Colors.PRIMARY_CONTAINER if out else ft.Colors.SURFACE_CONTAINER_HIGH,
        )
        return ft.Row([box], alignment=ft.MainAxisAlignment.END if out else ft.MainAxisAlignment.START)

    # ─── actions ──────────────────────────────────────────────────────────

    async def _position(self, _e) -> None:
        if await self.app.guard(self.engine.send_tak_position()):
            self.app.toast(self.t("position_sent"))

    async def _send(self, _e) -> None:
        text = (self.text.value or "").strip()
        if not text:
            return
        to = self.to.value or ""
        name = next((s["callsign"] for s in self.engine.tak_stations.values() if s["uid"] == to), "")
        if await self.app.guard(self.engine.send_tak_chat(text, to, name)):
            self.text.value = ""
            self._signature = None
            self.refresh()
            self.app.page.update()

    async def _toggle(self, e) -> None:
        if not e.control.value:
            await self._apply(False)
            return
        if self.engine.config.tak_sentence_ok:  # the sentence was typed once already (kept across updates)
            await self._apply(True)
            return
        e.control.value = False
        self.app.page.update()
        field = ft.TextField(autofocus=True, width=520)
        error = ft.Text("", color=ft.Colors.ERROR, size=12)

        async def enable(_e) -> None:
            if not tak_confirmed(field.value or ""):
                error.value = self.t("bbs_confirm_wrong")
                self.app.page.update()
                return
            self.app.page.pop_dialog()
            self.engine.config.tak_sentence_ok = True
            await self._apply(True)

        field.on_submit = enable
        self.app.show_dialog(ft.AlertDialog(
            modal=True, title=ft.Text(self.t("tak_confirm_title")),
            content=ft.Column([ft.Text(self.t("tak_confirm_ask")),
                               ft.Text(self.t("tak_confirm_text"), weight=ft.FontWeight.BOLD, selectable=True),
                               field, error], tight=True, width=520),
            actions=[ft.TextButton(self.t("cancel"), on_click=lambda _e: self.app.page.pop_dialog()),
                     ft.FilledButton(self.t("bbs_enable"), icon=ft.Icons.RADAR, on_click=enable)],
        ))

    async def _apply(self, on: bool) -> None:
        data = {**self.engine.config.to_dict(), "tak_enabled": on}  # carries tak_sentence_ok
        if on:
            data["bbs_enabled"] = False  # one exclusive mode at a time
        await self.app.apply_config(Config.from_dict(data).validate())
