"""Map of heard stations (OpenStreetMap tiles)."""

from __future__ import annotations

import time

import flet as ft
import flet_map as fm

from ..legend import COLOR_ME, internet_checkbox, show_legend, station_color, visible
from ..symbols import emoji
from .base import View

TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
# OpenStreetMap's tile usage policy asks for an identifying User-Agent.
USER_AGENT = "io.github.michalsiman.aprs_kiss_app"
DEFAULT_CENTER = (49.8, 15.5)  # Czechia
REBUILD_SECONDS = 2.0
MAX_MARKERS = 400
MUTED_OPACITY = 0.45  # muted map: tiles faded over a neutral background, so the colours recede


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
        self.tiles = fm.TileLayer(url_template=TILES, user_agent_package_name=USER_AGENT, max_zoom=19,
                                  opacity=MUTED_OPACITY if conf.map_muted else 1.0)
        self.map = fm.Map(
            expand=True,
            bgcolor=ft.Colors.SURFACE,
            initial_center=fm.MapLatitudeLongitude(*center),
            initial_zoom=10 if conf.has_position else 7,
            layers=[
                self.tiles,
                self.markers,
                fm.SimpleAttribution(text="© OpenStreetMap contributors", alignment=ft.Alignment.BOTTOM_RIGHT),
            ],
            # Right click (long press on touch screens): "set as my position".
            on_secondary_tap=self._menu,
            on_long_press=self._menu,
        )
        self._picked: tuple[float, float] | None = None
        self.menu = ft.ContextMenu(
            self.map, primary_trigger=None, secondary_trigger=None, tertiary_trigger=None,
            on_select=self._menu_select, expand=True,
        )
        self.only_recent = ft.Checkbox(label=self.t("last_2h"), value=False, on_change=lambda _e: self.force())
        self.internet = internet_checkbox(self.app)
        overlay = ft.Container(
            ft.Row([
                ft.IconButton(ft.Icons.MY_LOCATION, tooltip=self.t("centre_me"), on_click=self._centre_me),
                self._muted_btn(),
                self.internet,
                self.only_recent,
                ft.TextButton(self.t("legend"), icon=ft.Icons.HELP_OUTLINE,
                              on_click=lambda _e: show_legend(self.app)),
            ], tight=True, wrap=True),
            bgcolor=ft.Colors.with_opacity(0.85, ft.Colors.SURFACE),
            border_radius=8, padding=ft.Padding.symmetric(horizontal=4), left=8, top=8,
        )
        return ft.Stack([self.menu, overlay], expand=True)

    def _muted_btn(self) -> ft.IconButton:
        self.muted = ft.IconButton(ft.Icons.FILTER_B_AND_W_OUTLINED, selected_icon=ft.Icons.FILTER_B_AND_W,
                                   selected=self.engine.config.map_muted, tooltip=self.t("map_muted"),
                                   on_click=self._toggle_muted)
        return self.muted

    def _toggle_muted(self, _e) -> None:
        """Saved like the other view choices; only the tiles change, the markers keep their colours."""
        conf = self.engine.config
        conf.map_muted = not conf.map_muted
        self.muted.selected = conf.map_muted
        self.tiles.opacity = MUTED_OPACITY if conf.map_muted else 1.0
        self.app.save_config_soon()
        self.app.page.update()

    def force(self) -> None:
        self.internet.value = self.engine.config.show_internet
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
                            bgcolor=ft.Colors.with_opacity(0.9, ft.Colors.SURFACE),
                            # A thin dark frame keeps the label readable on a busy, colourful map.
                            border=ft.Border.all(1, ft.Colors.with_opacity(0.55, ft.Colors.BLACK)),
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
        markers = []
        conf = self.engine.config
        recent = 7200 if self.only_recent.value else None
        for e in list(reversed(heard.values()))[:MAX_MARKERS]:
            if e.get("latitude") is None or e.get("longitude") is None:
                continue
            if recent and now - e["last_heard"] > recent:
                continue
            if not visible(self.app, e):
                continue
            call = e["call"]
            markers.append(self._marker(e["latitude"], e["longitude"], call,
                                        emoji(e.get("symbol_table"), e.get("symbol")), station_color(self.app, e),
                                        on_click=lambda _e, c=call: self.app.show_station(c),
                                        bold=bool(e.get("last_rf"))))
        if conf.has_position:
            markers.append(self._marker(conf.latitude, conf.longitude, self.engine.status()["callsign"] or self.t("my_position"),
                                        emoji(conf.symbol[:1], conf.symbol[1:]), COLOR_ME, bold=True))
        self.markers.markers = markers

    async def _menu(self, e) -> None:
        lon = (e.coordinates.longitude + 180) % 360 - 180  # the map wraps around the world
        lat, lon = round(e.coordinates.latitude, 5), round(lon, 5)
        self._picked = (lat, lon)
        self.menu.items = [
            ft.PopupMenuItem(content=self.t("set_my_position"), icon=ft.Icons.MY_LOCATION, data="me"),
            ft.PopupMenuItem(content=self.t("copy_coordinates", lat=f"{lat:.5f}", lon=f"{lon:.5f}"),
                             icon=ft.Icons.CONTENT_COPY, data="copy"),
        ]
        self.menu.update()
        await self.menu.open(global_position=e.global_position, local_position=e.local_position)

    async def _menu_select(self, e) -> None:
        if not self._picked or e.item is None:
            return
        lat, lon = self._picked
        if e.item.data == "me":
            await self.app.set_position(lat, lon)
        elif e.item.data == "copy":
            await ft.Clipboard().set(f"{lat:.5f}, {lon:.5f}")
            self.app.toast(self.t("copied"))

    async def centre(self, lat: float, lon: float, zoom: float = 12) -> None:
        await self.map.center_on(fm.MapLatitudeLongitude(lat, lon), zoom)

    async def _centre_me(self, _e) -> None:
        conf = self.engine.config
        if conf.has_position:
            await self.centre(conf.latitude, conf.longitude, 11)
