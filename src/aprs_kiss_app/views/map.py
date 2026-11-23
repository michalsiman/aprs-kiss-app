"""Map of heard stations (OpenStreetMap tiles)."""

from __future__ import annotations

import asyncio
import math
import time

import flet as ft
import flet_map as fm

from ..legend import COLOR_ME, map_label, show_legend, station_color, visible
from ..offline_map import MIN_ZOOM, BaseMap, Region, ScaleBar, gestures
from ..symbols import emoji
from ..declutter import spread
from .map_source import MapSourceButton
from .base import View, toggle

DEFAULT_CENTER = (49.8, 15.5)  # Czechia
REBUILD_SECONDS = 2.0
MAX_MARKERS = 400  # the most recently heard stations in the area on screen
MAX_MARKERS_PHONE = 150
CAMERA_SECONDS = 2.0  # while the map is shown, where it is looking is asked for no more often than this
TRAIL_SECONDS = 1800  # the trails show the last half hour
TRAIL_COLOR = "#E53935"  # one red, like aprs.fi
LEADER_COLOR = "#8E8E8E"  # from a spread-out marker to where the station really is
MUTED_OPACITY = 0.45  # muted map: tiles faded over a neutral background, so the colours recede


class MapView(View):
    key = "map"
    lazy = True
    keep_alive = True
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
        self._cache: dict[tuple, fm.Marker] = {}  # unchanged stations keep their marker: nothing to resend
        self._area = Region.around(*center, self._zoom)  # stations outside it are not put on the map
        self._camera_asked = 0.0
        self._camera_busy = False
        self.trails = fm.PolylineLayer(polylines=[])  # where moving stations went in the last hour
        self._trail_cache: dict[tuple, fm.PolylineMarker] = {}
        self.base = BaseMap(self.markers, center, self._zoom, MUTED_OPACITY if conf.map_muted else 1.0, self.trails)
        self.tiles = self.base.tiles
        self.map = fm.Map(
            expand=True,
            bgcolor=ft.Colors.SURFACE,
            initial_center=fm.MapLatitudeLongitude(*center),
            initial_zoom=self._zoom,
            min_zoom=MIN_ZOOM,
            interaction_configuration=gestures(),
            layers=self.base.layers(self.app.offline_map(), self.app.imported_shown()),
            # Right click (long press on touch screens): "set as my position".
            on_secondary_tap=self._menu,
            on_long_press=self._menu,
            # Not on_position_change: that sends an event for every frame of a pan or zoom, which on a
            # phone floods the app. Where the map looks is asked for after a gesture and now and then.
            on_pointer_up=self._gesture_end,
        )
        self._picked: tuple[float, float] | None = None
        self.menu = ft.ContextMenu(
            self.map, primary_trigger=None, secondary_trigger=None, tertiary_trigger=None,
            on_select=self._menu_select, expand=True,
        )
        # The filters are icons that light up when on, like the map buttons: they take little of the map.
        self.trails_btn = toggle(ft.Icons.TIMELINE, ft.Icons.TIMELINE, conf.map_trails, self.t("map_trails"),
                                 self._toggle_trails)
        self.only_recent = toggle(ft.Icons.HISTORY_TOGGLE_OFF, ft.Icons.HISTORY, False, self.t("last_2h"),
                                  self._toggle_recent)
        self.internet = toggle(ft.Icons.PUBLIC_OFF, ft.Icons.PUBLIC, conf.show_internet, self.t("show_internet"),
                               lambda _e: self.app.set_show_internet(not self.engine.config.show_internet))
        self.tools = [
            ft.IconButton(ft.Icons.MY_LOCATION, tooltip=self.t("centre_me"), on_click=self._centre_me),
            self.internet, self.only_recent, self.trails_btn, self._offline_btn(),
        ]  # the muted map and the legend are in the map menu: the bar fits on a phone
        # The bar folds into one gear button (and stays folded next time) for those who want the whole map.
        self.fold_btn = ft.IconButton(on_click=self._toggle_tools)
        bar = ft.Row([self.fold_btn, *self.tools], tight=True, spacing=0, wrap=True, run_spacing=0)
        self._show_tools(not conf.map_tools_hidden)
        overlay = ft.Container(
            bar,
            bgcolor=ft.Colors.with_opacity(0.85, ft.Colors.SURFACE),
            border_radius=8, padding=ft.Padding.symmetric(horizontal=2), left=8, top=8,
        )
        self.controls = MapControls(self.map, self.t, lambda: self.app.page.run_task(self._ask_camera, 0.7))
        self.scale = ScaleBar()
        self.scale.show(center[0], self._zoom)
        return ft.Stack([self.menu, overlay, self.controls.control, self.scale.control, self.base.credit], expand=True)

    def _show_tools(self, shown: bool) -> None:
        for button in self.tools:
            button.visible = shown
        self.fold_btn.icon = ft.Icons.CHEVRON_LEFT if shown else ft.Icons.SETTINGS
        self.fold_btn.tooltip = self.t("map_tools_hide" if shown else "map_tools_show")

    def _toggle_tools(self, _e) -> None:
        conf = self.engine.config
        conf.map_tools_hidden = not conf.map_tools_hidden
        self._show_tools(not conf.map_tools_hidden)
        self.app.save_config_soon()
        self.app.page.update()

    def _toggle_trails(self, _e) -> None:
        conf = self.engine.config
        conf.map_trails = not conf.map_trails
        self.trails_btn.selected = conf.map_trails
        self.app.save_config_soon()
        self.force()
        self.app.page.update()

    def _toggle_recent(self, _e) -> None:
        self.only_recent.selected = not self.only_recent.selected
        self.force()
        self.app.page.update()

    def _toggle_muted(self, _e) -> None:
        """Saved like the other view choices; only the tiles change, the markers keep their colours."""
        conf = self.engine.config
        conf.map_muted = not conf.map_muted
        self.muted.checked = conf.map_muted
        self.tiles.opacity = MUTED_OPACITY if conf.map_muted else 1.0
        self.app.save_config_soon()
        self.app.page.update()

    # ─── base map: OpenStreetMap tiles, or the bundled offline map ─────

    def base_map_changed(self) -> None:
        """Called by the app when the internet goes away or returns."""
        if hasattr(self, "map"):
            self.map.layers = self.base.layers(self.app.offline_map(), self.app.imported_shown())
            self.muted.disabled = self.app.offline_map()
            self.source_btn.refresh()

    def _offline_btn(self) -> ft.Control:
        self.muted = ft.PopupMenuItem(self.t("map_muted"), icon=ft.Icons.FILTER_B_AND_W,
                                      checked=self.engine.config.map_muted, on_click=self._toggle_muted)
        self.muted.disabled = self.app.offline_map()
        legend = ft.PopupMenuItem(self.t("legend"), icon=ft.Icons.HELP_OUTLINE,
                                  on_click=lambda _e: show_legend(self.app))
        self.source_btn = MapSourceButton(self.app, [self.muted, legend])
        return self.source_btn.control

    def _gesture_end(self, _e=None) -> None:
        self.app.page.run_task(self._ask_camera, 0.8)  # after the fling has (mostly) stopped

    async def _ask_camera(self, delay: float = 0) -> None:
        """Where the map looks now: the offline map and the markers follow it."""
        if self._camera_busy:
            return
        self._camera_busy = True
        try:
            await asyncio.sleep(delay)
            self._camera_asked = time.monotonic()
            camera = await self.map.get_camera()
        except Exception:  # noqa: BLE001 - the map is not on screen (yet)
            return
        finally:
            self._camera_busy = False
        lon = (camera.center.longitude + 180) % 360 - 180
        if self.controls.rotated(camera.rotation) and self.app.current_key == self.key:
            self.controls.needle.update()
        self._look(camera.center.latitude, lon, camera.zoom)

    def _look(self, lat: float, lon: float, zoom: float) -> None:
        self.base.moved(lat, lon, zoom, self.app.offline_map())
        self.scale.show(lat, zoom)
        changed = True  # at least the scale follows the zoom (the update sends only what changed)
        self._zoom = zoom
        if abs(zoom - getattr(self, "_layout_zoom", zoom)) >= 0.3:  # the markers' spread depends on the zoom
            self._signature = None
            self._last_build = 0
            self.refresh()
        if not self._area.covers(lat, lon, zoom):
            self._area = Region.around(lat, lon, zoom)
            self._signature = None
            self._last_build = 0
            self.refresh()
            changed = True
        if changed and self.app.current_key == self.key:
            self.app.page.update()

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
                        map_label(label, color, bold),
                    ],
                    spacing=0, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                on_click=on_click,
            ),
        )

    def refresh(self) -> None:
        self._centre_on_first_fix()
        if (self.app.current_key == self.key and not self._camera_busy
                and time.monotonic() - self._camera_asked > CAMERA_SECONDS):
            self._camera_asked = time.monotonic()
            self.app.page.run_task(self._ask_camera)
        now = time.time()
        heard = self.engine.station.heard
        signature = (len(heard), next(reversed(heard), None),
                     heard[next(reversed(heard))]["count"] if heard else 0, self.engine.my_position())
        if signature == self._signature or now - self._last_build < REBUILD_SECONDS:
            return
        self._signature = signature
        self._last_build = now
        conf = self.engine.config
        recent = 7200 if self.only_recent.selected else None
        area = self._area
        limit = MAX_MARKERS_PHONE if self.app.mobile else MAX_MARKERS
        wanted = []
        trails = []
        for e in reversed(heard.values()):
            lat, lon = e.get("latitude"), e.get("longitude")
            if lat is None or lon is None or not area.contains(lat, lon):
                continue
            if recent and now - e["last_heard"] > recent:
                continue
            if not visible(self.app, e):
                continue
            wanted.append((e["call"], lat, lon, emoji(e.get("symbol_table"), e.get("symbol")),
                           station_color(self.app, e), bool(e.get("last_rf"))))
            if conf.map_trails:
                points = tuple((p[1], p[2]) for p in e.get("track", ()) if now - p[0] <= TRAIL_SECONDS)
                if len(points) >= 2:
                    trails.append((e["call"], points))
            if len(wanted) >= limit:
                break
        wanted.sort()  # a steady order: the list changes only where stations come, go or move
        here = self.engine.my_position()
        if here:
            wanted.append((self.engine.status()["callsign"] or self.t("my_position"), *here,
                           emoji(conf.symbol[:1], conf.symbol[1:]), COLOR_ME, True, "me"))
        # stations whose markers would cover each other are spread in a circle, at this zoom
        self._layout_zoom = self._zoom
        me = len(wanted) - 1 if here else None  # our own station stays where it is
        shown = spread([(k[1], k[2]) for k in wanted], self._zoom, fixed=me)
        cache, markers, leaders = {}, [], []
        for key, (slat, slon) in zip(wanted, shown):
            moved = (slat, slon) != (key[1], key[2])
            ckey = (key, round(slat, 7), round(slon, 7))
            marker = self._cache.get(ckey)
            if marker is None:
                call, _lat, _lon, icon, color, bold = key[:6]
                click = None if len(key) > 6 else (lambda _e, c=call: self.app.show_station(c))
                marker = self._marker(slat, slon, call, icon, color, on_click=click, bold=bold)
            cache[ckey] = marker
            markers.append(marker)
            if moved:  # a thin line to where the station really is
                leaders.append(("leader", ((round(slat, 7), round(slon, 7)), (key[1], key[2]))))
        self._cache = cache
        if [id(m) for m in markers] != [id(m) for m in self.markers.markers]:
            self.markers.markers = markers
        self._draw_trails(trails + leaders)

    def _draw_trails(self, trails: list) -> None:
        """A thin red line joining where the station was (the marker shows where it is now); unchanged ones
        are not sent again."""
        cache, lines = {}, []
        for key in sorted(trails):
            line = self._trail_cache.get(key)
            if line is None:
                kind, points = key
                leader = kind == "leader"
                line = fm.PolylineMarker(coordinates=[fm.MapLatitudeLongitude(lat, lon) for lat, lon in points],
                                         color=LEADER_COLOR if leader else TRAIL_COLOR,
                                         stroke_width=1.6 if leader else 2)
            cache[key] = line
            lines.append(line)
        self._trail_cache = cache
        if [id(x) for x in lines] != [id(x) for x in self.trails.polylines]:
            self.trails.polylines = lines

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
        self._look(lat, lon, zoom)  # the offline map and the stations there first, then the move
        await self.map.center_on(fm.MapLatitudeLongitude(lat, lon), zoom)

    async def _centre_me(self, _e) -> None:
        here = self.engine.my_position()
        if here:
            await self.centre(*here, max(self.base.zoom, 11))
        else:
            self.app.toast(self.t("no_position"))


class MapControls:
    """Small buttons in the map's corner: zoom in, zoom out, and a compass that turns the map north up.

    The needle points where north is when the map has been turned (two fingers on a phone); a tap on it
    turns the map back.
    """

    SIZE = 34

    def __init__(self, map_: fm.Map, t, after) -> None:
        self.map, self.after = map_, after
        self.needle = ft.Icon(ft.Icons.NAVIGATION, size=18, color=ft.Colors.RED_400, rotate=ft.Rotate(0))
        column = ft.Column([
            self._button(ft.Icon(ft.Icons.ADD, size=20), t("zoom_in"), self._zoom_in),
            self._button(ft.Icon(ft.Icons.REMOVE, size=20), t("zoom_out"), self._zoom_out),
            self._button(self.needle, t("north_up"), self._north),
        ], spacing=0, tight=True)
        self.control = ft.Container(column, bgcolor=ft.Colors.with_opacity(0.85, ft.Colors.SURFACE),
                                    border_radius=self.SIZE // 2, right=8, bottom=22)

    def _button(self, content: ft.Control, tooltip: str, on_click) -> ft.Container:
        return ft.Container(content, width=self.SIZE, height=self.SIZE, alignment=ft.Alignment.CENTER,
                            border_radius=self.SIZE // 2, tooltip=tooltip, on_click=on_click, ink=True)

    async def _zoom_in(self, _e) -> None:
        await self.map.zoom_in()
        self.after()

    async def _zoom_out(self, _e) -> None:
        await self.map.zoom_out()
        self.after()

    async def _north(self, _e) -> None:
        await self.map.reset_rotation()
        self.rotated(0)
        self.needle.update()
        self.after()

    def rotated(self, degrees: float | None) -> bool:
        """Turn the needle with the map; True when it moved."""
        angle = math.radians(degrees or 0)
        if abs(angle - self.needle.rotate.angle) < 0.01:
            return False
        self.needle.rotate = ft.Rotate(angle)
        return True
