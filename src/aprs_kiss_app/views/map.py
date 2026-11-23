"""Map of heard stations (OpenStreetMap tiles)."""

from __future__ import annotations

import time

import flet as ft
import flet_map as fm

from ..legend import COLOR_ME, show_legend, station_color, visible
from ..offline_map import MIN_ZOOM, BaseMap
from ..symbols import emoji
from .base import View

DEFAULT_CENTER = (49.8, 15.5)  # Czechia
REBUILD_SECONDS = 2.0
MAX_MARKERS = 400
MUTED_OPACITY = 0.45  # muted map: tiles faded over a neutral background, so the colours recede


class MapView(View):
    key = "map"
    lazy = True
    icon = ft.Icons.MAP_OUTLINED
    selected_icon = ft.Icons.MAP

    def build(self) -> ft.Control:
        self._signature = None
        self._last_build = 0.0
        conf = self.engine.config
        here = self.engine.my_position()
        center = here or DEFAULT_CENTER
        self.markers = fm.MarkerLayer(markers=[])
        self._zoom = 10 if here else 7
        self.base = BaseMap(self.markers, self._zoom, MUTED_OPACITY if conf.map_muted else 1.0)
        self.tiles = self.base.tiles
        self.map = fm.Map(
            expand=True,
            bgcolor=ft.Colors.SURFACE,
            initial_center=fm.MapLatitudeLongitude(*center),
            initial_zoom=self._zoom,
            min_zoom=MIN_ZOOM,
            layers=self.base.layers(self.app.offline_map()),
            # Right click (long press on touch screens): "set as my position".
            on_secondary_tap=self._menu,
            on_long_press=self._menu,
            on_position_change=self._moved,
        )
        self._picked: tuple[float, float] | None = None
        self.menu = ft.ContextMenu(
            self.map, primary_trigger=None, secondary_trigger=None, tertiary_trigger=None,
            on_select=self._menu_select, expand=True,
        )
        # The filters are icons that light up when on, like the map buttons: they take little of the map.
        self.only_recent = toggle(ft.Icons.HISTORY_TOGGLE_OFF, ft.Icons.HISTORY, False, self.t("last_2h"),
                                  self._toggle_recent)
        self.internet = toggle(ft.Icons.PUBLIC_OFF, ft.Icons.PUBLIC, conf.show_internet, self.t("show_internet"),
                               lambda _e: self.app.set_show_internet(not self.engine.config.show_internet))
        bar = ft.Row([
            ft.IconButton(ft.Icons.MY_LOCATION, tooltip=self.t("centre_me"), on_click=self._centre_me),
            self.internet, self.only_recent, self._muted_btn(), self._offline_btn(),
            ft.IconButton(ft.Icons.HELP_OUTLINE, tooltip=self.t("legend"), on_click=lambda _e: show_legend(self.app)),
        ], tight=True, spacing=0, wrap=True, run_spacing=0)
        overlay = ft.Container(
            bar,
            bgcolor=ft.Colors.with_opacity(0.85, ft.Colors.SURFACE),
            border_radius=8, padding=ft.Padding.symmetric(horizontal=2), left=8, top=8,
        )
        return ft.Stack([self.menu, overlay, self.base.credit], expand=True)

    def _toggle_recent(self, _e) -> None:
        self.only_recent.selected = not self.only_recent.selected
        self.force()
        self.app.page.update()

    def _muted_btn(self) -> ft.IconButton:
        self.muted = toggle(ft.Icons.FILTER_B_AND_W_OUTLINED, ft.Icons.FILTER_B_AND_W, self.engine.config.map_muted,
                            self.t("map_muted"), self._toggle_muted)
        self.muted.disabled = self.app.offline_map()
        return self.muted

    def _toggle_muted(self, _e) -> None:
        """Saved like the other view choices; only the tiles change, the markers keep their colours."""
        conf = self.engine.config
        conf.map_muted = not conf.map_muted
        self.muted.selected = conf.map_muted
        self.tiles.opacity = MUTED_OPACITY if conf.map_muted else 1.0
        self.app.save_config_soon()
        self.app.page.update()

    # ─── base map: OpenStreetMap tiles, or the bundled offline map ─────

    def base_map_changed(self) -> None:
        """Called by the app when the internet goes away or returns."""
        if hasattr(self, "map"):
            self.map.layers = self.base.layers(self.app.offline_map())
            self.offline_btn.selected = self.muted.disabled = self.app.offline_map()

    def _offline_btn(self) -> ft.IconButton:
        self.offline_btn = toggle(ft.Icons.CLOUD_OFF_OUTLINED, ft.Icons.CLOUD_OFF, self.app.offline_map(),
                                  self.t("map_offline"), self._toggle_offline)
        return self.offline_btn

    def _toggle_offline(self, _e) -> None:
        conf = self.engine.config
        conf.map_offline = not conf.map_offline
        self.base_map_changed()
        self.app.save_config_soon()
        self.app.page.update()

    def _moved(self, e) -> None:
        zoom = getattr(getattr(e, "camera", None), "zoom", None)
        if zoom is not None and self.base.zoomed(zoom, self.app.offline_map()):
            self.base.offline.cities.update()

    def _centre_on_first_fix(self) -> None:
        """The first GPS fix moves the map to where we are, once, while the map is on screen."""
        if getattr(self, "_gps_centred", False) or self.app.current_key != self.key:
            return
        here = self.engine.gps_fix()
        if here:
            self._gps_centred = True
            self.app.page.run_task(self.centre, here.latitude, here.longitude, 11)

    def force(self) -> None:
        self.internet.selected = self.engine.config.show_internet
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
        self._centre_on_first_fix()
        now = time.time()
        heard = self.engine.station.heard
        signature = (len(heard), next(reversed(heard), None),
                     heard[next(reversed(heard))]["count"] if heard else 0, self.engine.my_position())
        if signature == self._signature or now - self._last_build < REBUILD_SECONDS:
            return
        self._signature = signature
        self._last_build = now
        markers = []
        conf = self.engine.config
        recent = 7200 if self.only_recent.selected else None
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
        here = self.engine.my_position()
        if here:
            markers.append(self._marker(*here, self.engine.status()["callsign"] or self.t("my_position"),
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
        here = self.engine.my_position()
        if here:
            await self.centre(*here, max(self.base.zoom, 11))
        else:
            self.app.toast(self.t("no_position"))


def toggle(icon: str, selected_icon: str, selected: bool, tooltip: str, on_click) -> ft.IconButton:
    """An on/off icon: the plain (or crossed-out) icon when off, the filled one on a tinted background when on."""
    return ft.IconButton(icon, selected_icon=selected_icon, selected=selected, tooltip=tooltip, on_click=on_click,
                         style=ft.ButtonStyle(bgcolor={ft.ControlState.SELECTED:
                                                       ft.Colors.with_opacity(0.18, ft.Colors.PRIMARY)}))
