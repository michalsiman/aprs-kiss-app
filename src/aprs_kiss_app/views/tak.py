"""TAK: the app as a TAK station over the radio - a map of the TAK stations, GeoChat, our position.

Switching it on takes a typed sentence and turns everything else off, like BBS SERVER.
"""

from __future__ import annotations

import time

import flet as ft
import flet_map as fm

from aprs_kiss_core.config import Config

from ..i18n import TEXTS
from .base import View, clock
from .bbs import _plain
from ..offline_map import ATTRIBUTION, MIN_ZOOM, OfflineLayers
from .map import TILES, USER_AGENT

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
        self.switch = ft.Switch(label=self.t("tak"), value=on, on_change=self._toggle)
        self.state = ft.Text(size=15, weight=ft.FontWeight.BOLD)
        self.hint = ft.Text(size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        header = ft.Container(
            ft.Column([ft.Row([ft.Icon(ft.Icons.RADAR, color=ft.Colors.PRIMARY), self.switch]), self.state, self.hint],
                      spacing=4, tight=True),
            padding=12, border_radius=8, bgcolor=ft.Colors.SURFACE_CONTAINER,
        )
        if not on:
            return ft.Column([header], expand=True)
        here = self.engine.my_position()
        self.markers = fm.MarkerLayer(markers=[])
        self._zoom = 12 if here else 7
        self.offline: OfflineLayers | None = None
        self.tiles = fm.TileLayer(url_template=TILES, user_agent_package_name=USER_AGENT, max_zoom=19)
        self.map = fm.Map(
            expand=True, bgcolor=ft.Colors.SURFACE,
            initial_center=fm.MapLatitudeLongitude(*(here or (49.8, 15.5))), initial_zoom=self._zoom, min_zoom=MIN_ZOOM,
            layers=self._layers(), on_position_change=self._moved,
        )
        self.offline_btn = ft.IconButton(ft.Icons.CLOUD_OFF_OUTLINED, selected_icon=ft.Icons.CLOUD_OFF,
                                         selected=self.app.offline_map(), tooltip=self.t("map_offline"),
                                         on_click=self._toggle_offline)
        compact = self.app.compact
        self.stations = ft.ListView(spacing=0, height=90 if compact else 170)
        self.chat = ft.ListView(expand=True, spacing=6, auto_scroll=True, padding=ft.Padding.all(6))
        self.to = ft.Dropdown(dense=True, width=150, value="", options=[ft.DropdownOption(key="", text=self.t("tak_everybody"))])
        self.text = ft.TextField(hint_text=self.t("type_here"), expand=True, dense=True, on_submit=self._send)
        panel = ft.Container(
            ft.Column([
                ft.Row([ft.FilledTonalButton(self.t("tak_send_position"), icon=ft.Icons.MY_LOCATION,
                                             on_click=self._position), self.offline_btn]),
                ft.Text(self.t("tak_stations"), weight=ft.FontWeight.BOLD), self.stations,
                ft.Text(self.t("tak_chat"), weight=ft.FontWeight.BOLD),
                ft.Container(self.chat, expand=True, border_radius=8, bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST),
                ft.Row([self.to, self.text, ft.IconButton(ft.Icons.SEND, tooltip=self.t("send"), on_click=self._send)]),
            ], expand=True, spacing=6),
            width=None if compact else 380,
            expand=compact,
        )
        if compact:  # a phone: the map above, stations and GeoChat below
            return ft.Column([header, ft.Container(self.map, expand=True, border_radius=8), panel], expand=True)
        return ft.Column([header, ft.Row([ft.Container(self.map, expand=True, border_radius=8), panel], expand=True,
                                         vertical_alignment=ft.CrossAxisAlignment.STRETCH)], expand=True)

    def base_map_changed(self) -> None:
        """Called by the app when the internet goes away or returns."""
        if hasattr(self, "map"):
            self.map.layers = self._layers()
            self.offline_btn.selected = self.app.offline_map()

    def _layers(self) -> list:
        """OpenStreetMap tiles, or the bundled offline map (the same choice as on the APRS map)."""
        if self.app.offline_map():
            if self.offline is None:
                self.offline = OfflineLayers(self._zoom)
            base, credit = self.offline.layers, f"{ATTRIBUTION} (offline)"
        else:
            base, credit = [self.tiles], "© OpenStreetMap contributors"
        return [*base, self.markers, fm.SimpleAttribution(text=credit, alignment=ft.Alignment.BOTTOM_RIGHT)]

    def _toggle_offline(self, _e) -> None:
        conf = self.engine.config
        conf.map_offline = not conf.map_offline
        self.offline_btn.selected = self.app.offline_map()
        self.map.layers = self._layers()
        self.app.save_config_soon()
        self.app.page.update()

    def _moved(self, e) -> None:
        zoom = getattr(getattr(e, "camera", None), "zoom", None)
        if zoom is not None:
            self._zoom = zoom
            if self.offline and self.app.offline_map() and self.offline.zoomed(zoom):
                self.offline.cities.update()

    def on_event(self, kind, data) -> None:
        if kind in ("tak", "gps", "update"):
            self._signature = None

    # ─── drawing ──────────────────────────────────────────────────────────

    def refresh(self) -> None:
        eng = self.engine
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
            self.state.color = ft.Colors.GREEN
            self.hint.value = "" if eng.station.tx_enabled else self.t("tak_tx_needed")
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
                                                     f"{s['speed'] * 3.6:.0f} km/h" if s["speed"] else "") if x),
                             size=12),
            dense=True, on_click=lambda _e, st=s: self.app.page.run_task(
                self.map.center_on, fm.MapLatitudeLongitude(st["lat"], st["lon"]), 14),
        ) for s in rows] or [ft.Text(self.t("tak_no_stations"), color=ft.Colors.ON_SURFACE_VARIANT)]
        current = self.to.value
        self.to.options = [ft.DropdownOption(key="", text=self.t("tak_everybody"))] + [
            ft.DropdownOption(key=s["uid"], text=s["callsign"]) for s in rows]
        self.to.value = current if any(o.key == current for o in self.to.options) else ""
        self.chat.controls = [self._bubble(c) for c in eng.tak_chat] or [
            ft.Text(self.t("tak_no_chat"), color=ft.Colors.ON_SURFACE_VARIANT)]

    def _color(self, s: dict) -> str:
        return TEAM_COLORS.get(s.get("team") or "", AFFILIATION_COLORS.get(s["type"].split("-")[1] if
                                                                          s["type"].count("-") else "", "#1E88E5"))

    def _marker(self, lat: float, lon: float, label: str, color: str, stale: bool, me: bool = False) -> fm.Marker:
        dot = ft.Container(width=16 if me else 14, height=16 if me else 14, border_radius=8, bgcolor=color,
                           border=ft.Border.all(2, ft.Colors.WHITE if me else ft.Colors.BLACK),
                           opacity=0.45 if stale else 1.0)
        tag = ft.Container(ft.Text(label, size=10, weight=ft.FontWeight.BOLD, no_wrap=True),
                           bgcolor=ft.Colors.with_opacity(0.9, ft.Colors.SURFACE),
                           border=ft.Border.all(1, ft.Colors.with_opacity(0.55, ft.Colors.BLACK)),
                           padding=ft.Padding.symmetric(horizontal=3), border_radius=4,
                           opacity=0.6 if stale else 1.0)
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
        data = {**self.engine.config.to_dict(), "tak_enabled": on}
        if on:
            data["bbs_enabled"] = False  # one exclusive mode at a time
        await self.app.apply_config(Config.from_dict(data).validate())
