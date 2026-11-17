"""Map of heard stations (OpenStreetMap tiles)."""

from __future__ import annotations

import time

import flet as ft
import flet_map as fm

from ..symbols import emoji
from .base import View

TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
# OpenStreetMap's tile usage policy asks for an identifying User-Agent.
USER_AGENT = "io.github.michalsiman.aprs_kiss_app"
DEFAULT_CENTER = (49.8, 15.5)  # Czechia
REBUILD_SECONDS = 2.0
MAX_MARKERS = 400


class MapView(View):
    key = "map"
    icon = ft.Icons.MAP_OUTLINED
    selected_icon = ft.Icons.MAP

    def build(self) -> ft.Control:
        self._signature = None
        self._last_build = 0.0
        conf = self.engine.config
        center = (conf.latitude, conf.longitude) if conf.has_position else DEFAULT_CENTER
        self.markers = fm.MarkerLayer(markers=[])
        self.map = fm.Map(
            expand=True,
            initial_center=fm.MapLatitudeLongitude(*center),
            initial_zoom=10 if conf.has_position else 7,
            layers=[
                fm.TileLayer(url_template=TILES, user_agent_package_name=USER_AGENT, max_zoom=19),
                self.markers,
                fm.SimpleAttribution(text="© OpenStreetMap contributors", alignment=ft.Alignment.BOTTOM_RIGHT),
            ],
        )
        self.only_recent = ft.Checkbox(label="< 2 h", value=False, on_change=lambda _e: self._force())
        overlay = ft.Container(
            ft.Row([
                ft.IconButton(ft.Icons.MY_LOCATION, tooltip=self.t("centre_me"), on_click=self._centre_me),
                self.only_recent,
            ], tight=True),
            bgcolor=ft.Colors.with_opacity(0.85, ft.Colors.SURFACE),
            border_radius=8, padding=ft.Padding.symmetric(horizontal=4), left=8, top=8,
        )
        return ft.Stack([self.map, overlay], expand=True)

    def _force(self) -> None:
        self._signature = None
        self._last_build = 0
        self.refresh()

    def _marker(self, lat: float, lon: float, label: str, icon: str, color, on_click=None, bold=False) -> fm.Marker:
        return fm.Marker(
            coordinates=fm.MapLatitudeLongitude(lat, lon),
            width=110, height=50,
            content=ft.Container(
                ft.Column(
                    [
                        ft.Text(icon, size=20),
                        ft.Container(
                            ft.Text(label, size=10, weight=ft.FontWeight.BOLD if bold else None, color=color,
                                    no_wrap=True),
                            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.SURFACE),
                            padding=ft.Padding.symmetric(horizontal=3), border_radius=4,
                        ),
                    ],
                    spacing=0, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                on_click=on_click,
            ),
        )

    def refresh(self) -> None:
        now = time.time()
        heard = self.engine.station.heard
        signature = (len(heard), next(reversed(heard), None),
                     heard[next(reversed(heard))]["count"] if heard else 0, self.engine.config.latitude,
                     self.engine.config.longitude)
        if signature == self._signature or now - self._last_build < REBUILD_SECONDS:
            return
        self._signature = signature
        self._last_build = now
        tracked = self.app.tracked()
        markers = []
        conf = self.engine.config
        recent = 7200 if self.only_recent.value else None
        for e in list(reversed(heard.values()))[:MAX_MARKERS]:
            if e.get("latitude") is None or e.get("longitude") is None:
                continue
            if recent and now - e["last_heard"] > recent:
                continue
            call = e["call"]
            color = ft.Colors.ORANGE if call.upper() in tracked else (
                ft.Colors.BLUE if e.get("last_rf") else ft.Colors.BLUE_GREY)
            markers.append(self._marker(e["latitude"], e["longitude"], call,
                                        emoji(e.get("symbol_table"), e.get("symbol")), color,
                                        on_click=lambda _e, c=call: self.app.show_station(c),
                                        bold=bool(e.get("last_rf"))))
        if conf.has_position:
            markers.append(self._marker(conf.latitude, conf.longitude, self.engine.status()["callsign"] or self.t("my_position"),
                                        emoji(conf.symbol[:1], conf.symbol[1:]), ft.Colors.RED, bold=True))
        self.markers.markers = markers

    async def centre(self, lat: float, lon: float, zoom: float = 12) -> None:
        await self.map.center_on(fm.MapLatitudeLongitude(lat, lon), zoom)

    async def _centre_me(self, _e) -> None:
        conf = self.engine.config
        if conf.has_position:
            await self.centre(conf.latitude, conf.longitude, 11)
