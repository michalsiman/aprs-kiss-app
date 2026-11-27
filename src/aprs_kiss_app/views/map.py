"""Map of heard stations (OpenStreetMap tiles)."""

from __future__ import annotations

import asyncio
import math
import time

import flet as ft
import flet_map as fm
from aprs_kiss_core import localwx, mapfilter, repeater, units

from ..legend import COLOR_ME, map_label, show_legend, station_color, visible
from ..offline_map import LAND, MIN_ZOOM, BaseMap, Region, ScaleBar, gestures
from ..symbols import emoji
from ..declutter import from_px, spread, to_px
from .map_source import MapSourceButton, _label
from .base import (STAY_WIDTH, View, bearing, bearing_deg, check_item, distance_km, distance_text, menu_line, stay_item, toggle,
                   walkie_talkie)

DEFAULT_CENTER = (49.8, 15.5)  # Czechia
REBUILD_SECONDS = 2.0
MAX_MARKERS = 400  # the most recently heard stations in the area on screen
MAX_MARKERS_PHONE = 150
CAMERA_WATCH_SECONDS = 1.0  # while the map is on screen, how often it is asked where it looks
CAMERA_SECONDS = 2.0  # while the map is shown, where it is looking is asked for no more often than this
TRAIL_SECONDS = 1800  # the trails show the last half hour
TRAIL_COLOR = "#E53935"  # one red, like aprs.fi
MEASURE_COLOR = "#6A1B9A"  # the measured line: a colour no station label uses
LEADER_COLOR = "#8E8E8E"  # from a spread-out marker to where the station really is
FOLLOW_ZOOM = 13.0  # while the tracker runs the map follows us at this zoom…
FOLLOW_IDLE_SECONDS = 15.0  # …and comes back to it this long after the map was last moved by hand
FOLLOW_OWN_MOVE_SECONDS = 2.0  # camera changes this soon after the map followed us are ours, not the user's
FOLLOW_SLACK_PX = 12  # closer than this to the middle: no need to move
DISC_ABOVE_PX = 13  # the symbol's disc is this far above the middle of its marker (56 px box, disc 30 px at its top)
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
        self._camera_again = False
        self._camera_seen: tuple | None = None
        self._touched = 0.0  # when the user last moved or zoomed the map (monotonic)
        self._followed = 0.0  # when the map last moved itself to follow us
        self.app.page.run_task(self._watch_camera)
        self.trails = fm.PolylineLayer(polylines=[])  # where moving stations went in the last hour
        self._trail_cache: dict[tuple, fm.PolylineMarker] = {}
        # measuring a distance: a dashed line between two points, a pin at each end
        self.measure_line = fm.PolylineLayer(polylines=[])
        self.measure_pins = fm.MarkerLayer(markers=[])
        self.points = fm.MarkerLayer(markers=[])  # a position from a message or the chat, shown on request
        self._measure: list[tuple[float, float]] = []
        self.base = BaseMap(self.markers, center, self._zoom, MUTED_OPACITY if conf.map_muted else 1.0, self.trails,
                            overlays=(self.measure_line, self.measure_pins, self.points))
        self.tiles = self.base.tiles
        self.map = fm.Map(
            expand=True,
            bgcolor=LAND,  # light in the dark mode too, like all the maps
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
            on_tap=self._tap,
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
        self.me_btn = ft.IconButton(ft.Icons.MY_LOCATION, tooltip=self.t("centre_me"), on_click=self._centre_me)
        self.tools = [
            self.me_btn,
            self.internet, self.only_recent, self._filter_btn(), self.trails_btn, self._offline_btn(),
        ]  # the muted map and the legend are in the map menu: the bar fits on a phone
        # The bar folds into one gear button (and stays folded next time) for those who want the whole map.
        self.fold_btn = ft.IconButton(on_click=self._toggle_tools)
        bar = ft.Row([self.fold_btn, *self.tools], tight=True, spacing=0, wrap=True, run_spacing=0)
        # under the bar, small: how many stations the map shows now
        self.count_text = ft.Text(size=11, color=ft.Colors.ON_SURFACE_VARIANT)
        self._count_points: list[tuple[float, float, str]] = []  # (lat, lon, call) of the stations put on the map
        self._view_at = (*center, self._zoom)
        self._map_size: tuple[float, float] | None = None
        # the weather around us: in the top right corner; under the bar while the bar is open (on a phone
        # the open bar runs across the whole width)
        self.wx_text = ft.Text(size=13, weight=ft.FontWeight.BOLD)
        self.wx_box = ft.Container(
            ft.Row([ft.Icon(ft.Icons.THERMOSTAT, size=16, color=ft.Colors.PRIMARY), self.wx_text],
                   tight=True, spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ft.Colors.with_opacity(0.6, ft.Colors.SURFACE), border_radius=8,
            padding=ft.Padding.symmetric(horizontal=8, vertical=3), visible=False,
            on_click=self._wx_details)  # a tap: which stations, their values, how far and how old
        self._wx_at = 0.0  # when the weather was last worked out (monotonic)
        self._wx: dict | None = None
        self._wx_news: tuple | None = None
        self.wx_corner = ft.Container(right=8, top=8)
        self.count_box = ft.Container(self.count_text, bgcolor=ft.Colors.with_opacity(0.75, ft.Colors.SURFACE),
                                      border_radius=6, padding=ft.Padding.symmetric(horizontal=6, vertical=1),
                                      visible=conf.map_count, on_click=self._count_details)  # a tap: more
        self.overlay = ft.Column([
            ft.Container(bar, bgcolor=ft.Colors.with_opacity(0.85, ft.Colors.SURFACE),
                         border_radius=8, padding=ft.Padding.symmetric(horizontal=2)),
            self.count_box,
        ], spacing=3, tight=True, left=8, top=8)
        self._show_tools(not conf.map_tools_hidden)
        self.controls = MapControls(self.map, self.t, lambda: self.app.page.run_task(self._ask_camera, 0.7))
        self.scale = ScaleBar()
        self.scale.show(center[0], self._zoom)
        self.measure_text = ft.Text(size=14, weight=ft.FontWeight.BOLD)
        self.measure_box = ft.Container(
            ft.Row([ft.Container(
                ft.Row([ft.Icon(ft.Icons.STRAIGHTEN, size=18, color=ft.Colors.PRIMARY), self.measure_text,
                        ft.IconButton(ft.Icons.CLOSE, icon_size=18, tooltip=self.t("measure_close"),
                                      on_click=self._measure_clear)],
                       tight=True, spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=ft.Colors.with_opacity(0.95, ft.Colors.SURFACE), border_radius=20,
                padding=ft.Padding.only(left=12, right=2), shadow=ft.BoxShadow(blur_radius=4, color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK)),
            )], alignment=ft.MainAxisAlignment.CENTER),
            left=70, right=70, bottom=36, visible=False,
        )
        # Following us, the map moved by hand: a button back to us, counting down to when it goes back by itself.
        self.back_text = ft.Text(size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_PRIMARY)
        self.back_btn = ft.Container(
            ft.Row([ft.Icon(ft.Icons.MY_LOCATION, size=20, color=ft.Colors.ON_PRIMARY), self.back_text],
                   tight=True, spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ft.Colors.PRIMARY, border_radius=22, padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.35, ft.Colors.BLACK)),
            left=8, bottom=40, visible=False, tooltip=self.t("follow_back_tip"), on_click=self._centre_me,  # above the scale
        )
        return ft.Stack([self.menu, self.overlay, self.wx_corner, self.controls.control, self.scale.control, self.base.credit,
                         self.measure_box, self.back_btn], expand=True, on_size_change=self._sized)

    def _sized(self, e) -> None:
        self._map_size = (e.width, e.height)
        self._show_count()
        self.app.page.update()

    def _on_screen(self) -> list[tuple[float, float, str]]:
        """The stations inside the part of the map on screen (our own position not counted)."""
        points = self._count_points
        if not self._map_size:
            return list(points)
        lat, lon, zoom = self._view_at
        cx, cy = to_px(lat, lon, zoom)
        half_w, half_h = self._map_size[0] / 2, self._map_size[1] / 2
        shown = []
        for point in points:
            x, y = to_px(point[0], point[1], zoom)
            if abs(x - cx) <= half_w and abs(y - cy) <= half_h:
                shown.append(point)
        return shown

    def _show_count(self) -> None:
        self.count_text.value = self.t("map_count", n=len(self._on_screen()))

    def _count_details(self, _e=None) -> None:
        """What is on the map now: how many points, how many callsigns (with and without the SSID; an object
        counts as its owner's), the nearest and the furthest one from us (a tap opens it)."""
        points = self._on_screen()
        heard = self.engine.station.heard
        calls = set()
        for _lat, _lon, call in points:
            entry = heard.get(call) or {}
            calls.add((entry.get("object_of") or call).upper())
        bases = {c.split("-")[0] for c in calls}
        here = self.engine.my_position()

        def line(label: str, value: str, call: str | None = None) -> ft.Control:
            row = ft.Row([ft.Text(label, expand=True, color=ft.Colors.ON_SURFACE_VARIANT),
                          ft.Text(value, weight=ft.FontWeight.BOLD)], spacing=12)
            if not call:
                return ft.Container(row, padding=ft.Padding.symmetric(horizontal=8, vertical=6))

            def go(_e) -> None:
                self.app.page.pop_dialog()
                self.app.show_station(call)
            return ft.Container(row, padding=ft.Padding.symmetric(horizontal=8, vertical=6), border_radius=8,
                                ink=True, on_click=go)

        rows = [line(self.t("count_points"), str(len(points))),
                line(self.t("count_calls"), f"{len(calls)} ({self.t('count_no_ssid', n=len(bases))})")]
        if here and points:
            far = sorted(((distance_km(*here, p[0], p[1]), p) for p in points), key=lambda d: d[0])

            def where(item) -> str:
                km, (plat, plon, call) = item
                return f"{call} · {distance_text(km)} {bearing(*here, plat, plon)}"

            rows.append(line(self.t("count_nearest"), where(far[0]), far[0][1][2]))
            rows.append(line(self.t("count_farthest"), where(far[-1]), far[-1][1][2]))
        elif points:
            rows.append(ft.Text(self.t("count_no_pos"), size=12, color=ft.Colors.ON_SURFACE_VARIANT))
        self.app.show_dialog(ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.PLACE, color=ft.Colors.PRIMARY), ft.Text(self.t("count_title"))], spacing=8),
            content=ft.Column(rows, tight=True, spacing=2, width=420),
            actions=[ft.TextButton(self.t("close"), on_click=lambda _e: self.app.page.pop_dialog())],
        ))

    def _toggle_count(self, _e) -> None:
        conf = self.engine.config
        conf.map_count = not conf.map_count
        self.count_check.value = conf.map_count
        self.count_box.visible = conf.map_count
        self.app.save_config_soon()
        self.app.page.update()

    def _show_tools(self, shown: bool) -> None:
        for button in self.tools:
            button.visible = shown
        self.fold_btn.icon = ft.Icons.CHEVRON_LEFT if shown else ft.Icons.SETTINGS
        self.fold_btn.tooltip = self.t("map_tools_hide" if shown else "map_tools_show")
        # the weather: under the open bar, in the corner when the bar is folded
        under = self.overlay.controls
        if shown and self.wx_box not in under:
            self.wx_corner.content = None
            under.append(self.wx_box)
        elif not shown and self.wx_corner.content is not self.wx_box:
            if self.wx_box in under:
                under.remove(self.wx_box)
            self.wx_corner.content = self.wx_box

    def _show_weather(self, force: bool = False) -> None:
        """The average of the weather stations within 20 km, worked out every 5 minutes (sooner while there
        is nothing to show yet); hidden when switched off or nothing is known."""
        conf = self.engine.config
        mono = time.monotonic()
        heard = self.engine.station.heard
        # nothing to show yet: again as soon as a station is heard or we learn where we are
        news = (len(heard), next(reversed(heard), None), self.engine.my_position())
        if not force and mono - self._wx_at < localwx.REFRESH_SECONDS and (self._wx or news == self._wx_news):
            return
        self._wx_at, self._wx_news = mono, news
        self._wx = wx = localwx.around(heard, self.engine.my_position(), time.time()) \
            if conf.map_weather else None
        self.wx_box.visible = wx is not None
        if wx is None:
            return
        u = units.current
        self.wx_text.value = self._wx_parts(wx)
        self.wx_box.tooltip = self.t("wx_near_tip", n=wx["stations"], dist=u.whole(localwx.RADIUS_KM),
                                     minutes=max(1, round(wx["oldest"] / 60)))

    def _wx_parts(self, values: dict) -> str:
        u = units.current
        parts = [u.temperature_text(values["temperature"])] if "temperature" in values else []
        if "humidity" in values:
            parts.append(f"{values['humidity']:.0f} %")
        if "pressure" in values:
            parts.append(u.pressure_text(values["pressure"]))
        return " · ".join(parts)

    def _wx_details(self, _e=None) -> None:
        """The weather stations the average is made of: nearest first, each with its values, distance,
        direction and how old its report is; a tap on one opens the station."""
        self._show_weather(force=True)  # as it is now: the ages from this moment, the box the same
        wx = self._wx
        if not wx:
            self.app.page.update()
            return
        heard = self.engine.station.heard
        here = self.engine.my_position()

        def open_station(call: str):
            def go(_e) -> None:
                self.app.page.pop_dialog()
                self.app.show_station(call)
            return go

        rows: list[ft.Control] = [
            ft.Text(self._wx_parts(wx), size=18, weight=ft.FontWeight.BOLD),
            ft.Text(self.t("wx_near_tip", n=wx["stations"], dist=units.current.whole(localwx.RADIUS_KM),
                           minutes=max(1, round(wx["oldest"] / 60))), size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Divider(height=8),
        ]
        for st in wx["list"]:
            entry = heard.get(st["call"]) or {}
            where = distance_text(st["km"])
            if here and entry.get("latitude") is not None:
                where += " " + bearing(*here, entry["latitude"], entry["longitude"])
            rows.append(ft.Container(
                ft.Column([
                    ft.Row([ft.Text(st["call"], weight=ft.FontWeight.BOLD, expand=True),
                            ft.Text(where, color=ft.Colors.ON_SURFACE_VARIANT)]),
                    ft.Row([ft.Text(self._wx_parts(st), expand=True),
                            ft.Text(self.t.age(st["age"]), size=12, color=ft.Colors.ON_SURFACE_VARIANT)]),
                ], spacing=2, tight=True),
                padding=ft.Padding.symmetric(horizontal=8, vertical=6), border_radius=8, ink=True,
                on_click=open_station(st["call"])))
        self.app.show_dialog(ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.THERMOSTAT, color=ft.Colors.PRIMARY), ft.Text(self.t("wx_near"))], spacing=8),
            # as tall as the stations need, scrolling when there are many
            content=ft.Column(rows, spacing=4, width=420, scroll=ft.ScrollMode.AUTO,
                              height=min(110 + 56 * len(wx["list"]), 460)),
            actions=[ft.TextButton(self.t("close"), on_click=lambda _e: self.app.page.pop_dialog())],
        ))

    def _toggle_weather(self, _e) -> None:
        conf = self.engine.config
        conf.map_weather = not conf.map_weather
        self.wx_check.value = conf.map_weather
        self.app.save_config_soon()
        self._show_weather(force=True)
        self.app.page.update()

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

    # ─── filters: only weather stations, moving stations, road incidents (any mix) ─────

    FILTER_ICONS = {"weather": ft.Icons.THUNDERSTORM_OUTLINED, "moving": ft.Icons.DIRECTIONS_CAR_OUTLINED,
                    "repeater": ft.Icons.CELL_TOWER, "road": ft.Icons.CAR_CRASH_OUTLINED}

    def _filter_btn(self) -> ft.Control:
        # one line each (the explanation in brackets does not fit a phone's menu); a box each, the menu stays open
        self.filter_items, self.filter_boxes = {}, {}
        for kind, icon in self.FILTER_ICONS.items():
            self.filter_items[kind], self.filter_boxes[kind] = check_item(
                self.t(f"filter_{kind}").split(" (")[0], icon, False, lambda _e, k=kind: self._toggle_filter(k))
        self.filter_all, _ = stay_item(menu_line(ft.Icons.FILTER_ALT_OFF_OUTLINED, self.t("filter_all")),
                                       lambda _e: self._set_filters(set(), rf_km=0))  # the boxes clear, the menu stays
        # how far: internet stations (the APRS-IS area asked from the server) and radio ones
        self.reach_is, self.reach_is_chips = self._reach_item(
            ft.Icon(ft.Icons.PUBLIC, size=20), self.t("reach_is", unit=units.current.unit),
            units.current.reach_choices(), self._set_is_km)
        self.reach_rf, self.reach_rf_chips = self._reach_item(
            walkie_talkie(ft.Colors.ON_SURFACE, 20), self.t("reach_rf", unit=units.current.unit),
            (*units.current.reach_choices(), (0, "∞")),
            lambda km: self._set_filters(mapfilter.parse(self.engine.config.map_filters), rf_km=km))
        self.filter_icon = ft.Icon(ft.Icons.FILTER_ALT_OUTLINED)
        self.filter_face = ft.Container(self.filter_icon, padding=8, shape=ft.BoxShape.CIRCLE)
        self.filter_btn = ft.PopupMenuButton(content=self.filter_face, tooltip=self.t("filter"),
                                             items=[*self.filter_items.values(), ft.PopupMenuItem(),
                                                    self.reach_is, self.reach_rf, ft.PopupMenuItem(), self.filter_all])
        self._show_filters()
        return self.filter_btn

    def _reach_item(self, icon, label: str, choices: tuple, pick) -> tuple[ft.PopupMenuItem, dict]:
        """A menu line with a label and a chip per distance ((km, label); 0 = no limit); a chip's tap keeps the
        menu open. In miles the chips say 10 / 30 / 60 and keep the kilometres underneath."""
        chips = {}
        for km, text in choices:
            chips[km] = ft.Container(
                ft.Text(text, size=13), border_radius=14, alignment=ft.Alignment.CENTER,
                padding=ft.Padding.symmetric(horizontal=10, vertical=5), width=50,
                tooltip=f"{text} {units.current.unit}" if km else self.t("reach_any"),
                on_click=lambda _e, k=km: pick(k))
        box = ft.Container(
            ft.Column([ft.Row([icon, ft.Text(label, size=13, max_width=STAY_WIDTH - 40)], spacing=10),
                       ft.Row(list(chips.values()), spacing=6)], spacing=6, tight=True),
            width=STAY_WIDTH, padding=ft.Padding.symmetric(vertical=6),
            on_click=lambda _e: None)  # a tap between the chips does not close the menu either
        return ft.PopupMenuItem(content=box), chips

    @staticmethod
    def _mark_chips(chips: dict, chosen: int) -> None:
        if chosen and chosen not in chips:  # e.g. 50 km saved, the chips in miles (16 / 48 / 97 km): the nearest
            chosen = min((km for km in chips if km), key=lambda km: abs(km - chosen), default=chosen)
        for km, chip in chips.items():
            on = km == chosen
            chip.bgcolor = ft.Colors.with_opacity(0.22, ft.Colors.PRIMARY) if on else None
            chip.border = ft.Border.all(1, ft.Colors.PRIMARY if on else ft.Colors.with_opacity(0.4, ft.Colors.OUTLINE))
            chip.content.weight = ft.FontWeight.BOLD if on else None
            chip.content.color = ft.Colors.PRIMARY if on else None

    def _show_filters(self) -> None:
        conf = self.engine.config
        kinds = mapfilter.parse(conf.map_filters)
        for kind, box in self.filter_boxes.items():
            box.value = kind in kinds
        self._mark_chips(self.reach_is_chips, conf.aprsis_radius_km)
        self._mark_chips(self.reach_rf_chips, conf.map_rf_km)
        active = bool(kinds) or bool(conf.map_rf_km)
        self.filter_icon.icon = ft.Icons.FILTER_ALT if active else ft.Icons.FILTER_ALT_OUTLINED
        self.filter_icon.color = ft.Colors.PRIMARY if active else None
        self.filter_face.bgcolor = ft.Colors.with_opacity(0.18, ft.Colors.PRIMARY) if active else None
        names = [self.t(f"filter_{k}_short") for k in mapfilter.KINDS if k in kinds]
        if conf.map_rf_km:
            names.append(f"{self.t('reach_rf', unit=units.current.unit)} {units.current.from_km(conf.map_rf_km):.0f}")
        self.filter_btn.tooltip = self.t("filter_on", what=", ".join(names)) if names else self.t("filter")

    def _toggle_filter(self, kind: str) -> None:
        self._set_filters(mapfilter.parse(self.engine.config.map_filters) ^ {kind})

    def _set_is_km(self, km: int) -> None:
        """The APRS-IS area: the server is asked for it at once; the settings form shows it too."""
        self.engine.set_is_radius(km)
        if self.app.has_view("settings"):
            form = self.app.view("settings")
            if getattr(form, "radius", None) is not None:
                form.radius.value = f"{units.current.from_km(km):.0f}"
        self._set_filters(mapfilter.parse(self.engine.config.map_filters))

    def _set_filters(self, kinds: set[str], rf_km: int | None = None) -> None:
        if rf_km is not None:
            self.engine.config.map_rf_km = rf_km
        self.engine.config.map_filters = mapfilter.join(kinds)
        self._show_filters()
        self.app.save_config_soon()
        self.force()
        self.app.page.update()

    def _toggle_muted(self, _e) -> None:
        """Saved like the other view choices; only the tiles change, the markers keep their colours."""
        conf = self.engine.config
        conf.map_muted = not conf.map_muted
        self.muted_box.value = conf.map_muted
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
        self.muted, self.muted_box = check_item(self.t("map_muted"), ft.Icons.FILTER_B_AND_W,
                                                self.engine.config.map_muted, self._toggle_muted)
        self.muted.disabled = self.app.offline_map()
        weather, self.wx_check = check_item(self.t("wx_near"), ft.Icons.THERMOSTAT, self.engine.config.map_weather,
                                            self._toggle_weather)
        count, self.count_check = check_item(self.t("map_count_show"), ft.Icons.PLACE, self.engine.config.map_count,
                                             self._toggle_count)
        legend = ft.PopupMenuItem(self.t("legend"), icon=ft.Icons.HELP_OUTLINE,
                                  on_click=lambda _e: show_legend(self.app))
        self.source_btn = MapSourceButton(self.app, [self.muted, weather, count, legend])
        return self.source_btn.control

    def _gesture_end(self, _e=None) -> None:
        self.app.page.run_task(self._ask_camera, 0.4)  # soon, and the watch below catches the end of a fling

    async def _watch_camera(self) -> None:
        """While the map is on screen, where it looks is asked for every second. A pinch, a fling or the
        mouse wheel then always ends with the markers, the lines and the scale redrawn for the new zoom
        (asking only when the fingers lift missed zooms that went on after it)."""
        while not self.app._closing and self.built and self in self.app.views:  # a rebuilt app: this view is gone
            await asyncio.sleep(CAMERA_WATCH_SECONDS)
            if self.app.current_key == self.key:
                await self._ask_camera()
                await self._follow()

    async def _ask_camera(self, delay: float = 0) -> None:
        """Where the map looks now: the offline map and the markers follow it."""
        if delay:
            await asyncio.sleep(delay)
        if self._camera_busy:
            self._camera_again = True  # asked while asking: ask once more when this answer is in
            return
        self._camera_busy = True
        try:
            while True:
                self._camera_again = False
                self._camera_asked = time.monotonic()
                try:
                    camera = await self.map.get_camera()
                except Exception:  # noqa: BLE001 - the map is not on screen (yet)
                    return
                lon = (camera.center.longitude + 180) % 360 - 180
                seen = (round(camera.center.latitude, 6), round(lon, 6), round(camera.zoom, 3),
                        round(camera.rotation or 0, 1))
                if seen != self._camera_seen:  # nothing to redraw when the map has not moved
                    if (self._camera_seen is not None
                            and time.monotonic() - self._followed > FOLLOW_OWN_MOVE_SECONDS):
                        self._touched = time.monotonic()  # moved, not by us: the wheel, a fling, the buttons
                    self._camera_seen = seen
                    if self.controls.rotated(camera.rotation) and self.app.current_key == self.key:
                        self.controls.needle.update()
                    self._look(camera.center.latitude, lon, camera.zoom)
                if not self._camera_again:
                    break
        finally:
            self._camera_busy = False

    def _look(self, lat: float, lon: float, zoom: float) -> None:
        self._view_at = (lat, lon, zoom)
        self._show_count()
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

    def _marker(self, lat: float, lon: float, label: str, icon: str, color, on_click=None, bold=False,
                freq: str | None = None) -> fm.Marker:
        extra = 14 if freq else 0  # a repeater's frequency line: the box grows both ways, the symbol stays put
        return fm.Marker(
            coordinates=fm.MapLatitudeLongitude(lat, lon),
            width=110 if not freq else 130, height=56 + 2 * extra,
            content=ft.Container(
                padding=ft.Padding.only(top=extra),
                content=ft.Column(
                    [
                        # the symbol on a small light disc: it no longer melts into a green or brown map
                        ft.Container(ft.Text(icon, size=18), width=30, height=30, alignment=ft.Alignment.CENTER,
                                     border_radius=15, bgcolor=ft.Colors.with_opacity(0.88, ft.Colors.WHITE),
                                     border=ft.Border.all(0.8, ft.Colors.with_opacity(0.18, ft.Colors.BLACK)),
                                     shadow=ft.BoxShadow(blur_radius=3, offset=ft.Offset(0, 1),
                                                         color=ft.Colors.with_opacity(0.25, ft.Colors.BLACK))),
                        map_label(label, color, bold, sub=freq,
                                  band="°C" if freq and freq.endswith(("°C", "°F"))
                                  else freq.split(" · ")[1] if freq and " · " in freq else None),
                    ],
                    spacing=1, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                on_click=on_click,
            ),
        )

    def _temperature(self, entry: dict) -> str | None:
        """A weather station's temperature for the second line of its tag ("4.8 °C"; "4,8 °C" in Czech;
        "40.6 °F" when the settings say Fahrenheit)."""
        wx = entry.get("weather")
        temp = wx.get("temperature") if isinstance(wx, dict) else None
        if not isinstance(temp, (int, float)):
            return None
        return units.current.temperature_text(temp)

    @staticmethod
    def _dot(lat: float, lon: float) -> fm.Marker:
        """Where a moved marker's station really is: a small grey dot at the end of its line."""
        return fm.Marker(coordinates=fm.MapLatitudeLongitude(lat, lon), width=10, height=10,
                         content=ft.Container(width=10, height=10, border_radius=5, bgcolor=LEADER_COLOR,
                                              border=ft.Border.all(1.5, ft.Colors.WHITE)))

    def refresh(self) -> None:
        self._centre_on_first_fix()
        self._show_weather()
        if (self.app.current_key == self.key and not self._camera_busy
                and time.monotonic() - self._camera_asked > CAMERA_SECONDS):
            self._camera_asked = time.monotonic()
            self.app.page.run_task(self._ask_camera)
        now = time.time()
        heard = self.engine.station.heard
        kinds = mapfilter.parse(self.engine.config.map_filters)
        conf = self.engine.config
        signature = (len(heard), next(reversed(heard), None),
                     heard[next(reversed(heard))]["count"] if heard else 0, self.engine.my_position(),
                     int(now // 60) if "moving" in kinds else 0,  # standing stations drop out as time goes
                     conf.aprsis_radius_km, conf.map_rf_km)
        if signature == self._signature or now - self._last_build < REBUILD_SECONDS:
            return
        self._signature = signature
        self._last_build = now
        here = self.engine.my_position()
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
            if not visible(self.app, e) or not mapfilter.shown(e, kinds, now):
                continue
            if not mapfilter.in_reach(e, here, conf.aprsis_radius_km, conf.map_rf_km):
                continue
            wanted.append((e["call"], lat, lon, emoji(e.get("symbol_table"), e.get("symbol")),
                           station_color(self.app, e), bool(e.get("last_rf")),
                           repeater.label(e) or self._temperature(e)))
            if conf.map_trails:
                points = tuple((p[1], p[2]) for p in e.get("track", ()) if now - p[0] <= TRAIL_SECONDS)
                if len(points) >= 2:
                    trails.append((e["call"], points))
            if len(wanted) >= limit:
                break
        wanted.sort()  # a steady order: the list changes only where stations come, go or move
        self._count_points = [(k[1], k[2], k[0]) for k in wanted]
        self._show_count()
        if conf.map_trails:  # our own trail too, from the GPS
            points = tuple((p[1], p[2]) for p in self.engine.my_track.get("track", ()) if now - p[0] <= TRAIL_SECONDS)
            if len(points) >= 2:
                trails.append(("\x00me", points))
        if here:
            wanted.append((self.engine.status()["callsign"] or self.t("my_position"), *here,
                           emoji(conf.symbol[:1], conf.symbol[1:]), COLOR_ME, True, None, "me"))
        # stations whose markers would cover each other are spread in a circle, at this zoom
        self._layout_zoom = self._zoom
        me = len(wanted) - 1 if here else None  # our own station stays where it is
        shown = spread([(k[1], k[2]) for k in wanted], self._zoom, fixed=me)
        cache, markers, leaders, dots = {}, [], [], []
        for key, (slat, slon) in zip(wanted, shown):
            moved = (slat, slon) != (key[1], key[2])
            ckey = (key, round(slat, 7), round(slon, 7))
            marker = self._cache.get(ckey)
            if marker is None:
                call, _lat, _lon, icon, color, bold, freq = key[:7]
                click = None if len(key) > 7 else (lambda _e, c=call: self.app.show_station(c))
                marker = self._marker(slat, slon, call, icon, color, on_click=click, bold=bold, freq=freq)
            if ckey in cache:
                continue  # the same station twice (cannot happen, but one marker twice breaks the map)
            cache[ckey] = marker
            markers.append(marker)
            if moved:  # a thin line to where the station really is, and a dot there
                # from the middle of the symbol's disc, not of the whole marker (disc and tag)
                x, y = to_px(slat, slon, self._zoom)
                dlat, dlon = from_px(x, y - DISC_ABOVE_PX, self._zoom)
                leaders.append(("leader", ((round(dlat, 7), round(dlon, 7)), (key[1], key[2]))))
                dkey = ("dot", key[1], key[2])
                if dkey not in cache:  # two stations at one place share one dot: never one marker twice
                    cache[dkey] = self._cache.get(dkey) or self._dot(key[1], key[2])
                    dots.append(cache[dkey])
        markers = markers + dots  # the dots on top: where a group really is must always show
        self._cache = cache
        if [id(m) for m in markers] != [id(m) for m in self.markers.markers]:
            self.markers.markers = markers
        self._draw_trails(trails + leaders)

    def _draw_trails(self, trails: list) -> None:
        """A thin red line joining where the station was (the marker shows where it is now); unchanged ones
        are not sent again."""
        cache, lines = {}, []
        for key in sorted(set(trails)):  # one line object only once
            line = self._trail_cache.get(key)
            if line is None:
                kind, points = key
                leader = kind == "leader"
                line = fm.PolylineMarker(coordinates=[fm.MapLatitudeLongitude(lat, lon) for lat, lon in points],
                                         color=LEADER_COLOR if leader else TRAIL_COLOR,
                                         stroke_width=1.5 if leader else 2.5)
            cache[key] = line
            lines.append(line)
        self._trail_cache = cache
        if [id(x) for x in lines] != [id(x) for x in self.trails.polylines]:
            self.trails.polylines = lines

    async def _menu(self, e) -> None:
        lon = (e.coordinates.longitude + 180) % 360 - 180  # the map wraps around the world
        lat, lon = round(e.coordinates.latitude, 5), round(lon, 5)
        self._picked = (lat, lon)
        here = self.engine.my_position()
        from aprs_kiss_core.geotext import position_to_locator  # noqa: PLC0415

        loc = position_to_locator(lat, lon)
        self.menu.items = [
            ft.PopupMenuItem(content=ft.Text(self.t("locator_is", loc=loc), weight=ft.FontWeight.BOLD),
                             icon=ft.Icons.GRID_ON, data="copy_loc"),
            ft.PopupMenuItem(),
            ft.PopupMenuItem(content=self.t("measure_from"), icon=ft.Icons.STRAIGHTEN, data="measure"),
            *([ft.PopupMenuItem(content=self.t("measure_from_me"), icon=ft.Icons.NEAR_ME, data="measure_me")]
              if here else []),
            ft.PopupMenuItem(content=self.t("nav_here") if self.app.can_share else self.t("nav_web"),
                             icon=ft.Icons.NAVIGATION, data="navigate"),
            ft.PopupMenuItem(content=self.t("share_place"), icon=ft.Icons.SHARE, data="share"),
            ft.PopupMenuItem(content=self.t("pos_to_chat"), icon=ft.Icons.FORUM_OUTLINED, data="chat"),
            ft.PopupMenuItem(content=self.t("pos_to_message"), icon=ft.Icons.MAIL_OUTLINE, data="message"),
            ft.PopupMenuItem(content=self.t("loc_to_chat", loc=loc), icon=ft.Icons.FORUM_OUTLINED, data="loc_chat"),
            ft.PopupMenuItem(content=self.t("loc_to_message", loc=loc), icon=ft.Icons.MAIL_OUTLINE, data="loc_message"),
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
        if e.item.data == "measure":
            self._measure = [(lat, lon)]  # the next tap on the map is the other end
            self._draw_measure()
        elif e.item.data == "measure_me":
            here = self.engine.my_position()
            if here:
                self._measure = [here, (lat, lon)]
                self._draw_measure()
        elif e.item.data == "me":
            await self.app.set_position(lat, lon)
        elif e.item.data == "navigate":
            await self.app.navigate_to(lat, lon)
        elif e.item.data == "share":
            await self.app.share_place(lat, lon)
        elif e.item.data == "chat":
            await self.app.send_position_text(lat, lon, "chat")
        elif e.item.data in ("loc_chat", "loc_message"):
            await self.app.send_position_text(lat, lon, "chat" if e.item.data == "loc_chat" else "message", locator=True)
        elif e.item.data == "copy_loc":
            from aprs_kiss_core.geotext import position_to_locator  # noqa: PLC0415

            await ft.Clipboard().set(position_to_locator(lat, lon))
            self.app.toast(self.t("copied"))
        elif e.item.data == "message":
            await self.app.send_position_text(lat, lon, "message")
        elif e.item.data == "copy":
            await ft.Clipboard().set(f"{lat:.5f}, {lon:.5f}")
            self.app.toast(self.t("copied"))

    # ─── measuring a distance ─────────────────────────────────────────────

    def _tap(self, e) -> None:
        """While measuring: a tap puts (or moves) the far end there."""
        if not self._measure or getattr(e, "coordinates", None) is None:
            return
        lon = (e.coordinates.longitude + 180) % 360 - 180
        self._measure = [self._measure[0], (e.coordinates.latitude, lon)]
        self._draw_measure()

    def _measure_clear(self, _e=None) -> None:
        self._measure = []
        self._draw_measure()

    async def show_point(self, lat: float, lon: float, label: str = "") -> None:
        """A position from a message or the chat: a red pin there, the map centred on it."""
        self.points.markers = [fm.Marker(
            # above the point: the tip of the pin is where the position is
            coordinates=fm.MapLatitudeLongitude(lat, lon), width=180, height=58, alignment=ft.Alignment.TOP_CENTER,
            content=ft.Column([
                map_label(label, None, True) if label else ft.Container(),
                ft.Icon(ft.Icons.LOCATION_ON, size=36, color="#C62828"),
            ], spacing=0, alignment=ft.MainAxisAlignment.END, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        )]
        await self.centre(lat, lon, max(self.base.zoom, 13))

    @staticmethod
    def _pin(lat: float, lon: float, color) -> fm.Marker:
        return fm.Marker(coordinates=fm.MapLatitudeLongitude(lat, lon), width=14, height=14,
                         content=ft.Container(width=14, height=14, border_radius=7, bgcolor=color,
                                              border=ft.Border.all(2, ft.Colors.WHITE)))

    def _draw_measure(self) -> None:
        points = self._measure
        self.measure_pins.markers = [self._pin(*points[0], MEASURE_COLOR)] if points else []
        self.measure_line.polylines = []
        if len(points) == 2:
            (lat1, lon1), (lat2, lon2) = points
            self.measure_pins.markers.append(self._pin(lat2, lon2, MEASURE_COLOR))
            self.measure_line.polylines = [fm.PolylineMarker(
                coordinates=[fm.MapLatitudeLongitude(lat1, lon1), fm.MapLatitudeLongitude(lat2, lon2)],
                color=MEASURE_COLOR, stroke_width=3,
                stroke_pattern=fm.DashedStrokePattern(segments=[12, 8]))]
            km = distance_km(lat1, lon1, lat2, lon2)
            self.measure_text.value = f"{distance_text(km)} · {bearing_deg(lat1, lon1, lat2, lon2):.0f}°"
        elif points:
            self.measure_text.value = self.t("measure_hint")
        self.measure_box.visible = bool(points)
        self.app.page.update()

    async def centre(self, lat: float, lon: float, zoom: float = 12) -> None:
        self._look(lat, lon, zoom)  # the offline map and the stations there first, then the move
        await self.map.center_on(fm.MapLatitudeLongitude(lat, lon), zoom)

    # ─── following us while the tracker runs, as in a navigation ─────

    def following(self) -> bool:
        return bool(self.engine.config.tracker_on and self.engine.gps_fix())

    async def _follow(self) -> None:
        """While the tracker runs, we stay in the middle of the map at FOLLOW_ZOOM. Moved or zoomed by
        hand, the map stays so for FOLLOW_IDLE_SECONDS after the last touch, then comes back."""
        following = self.following()
        if self.me_btn.icon_color != (ft.Colors.PRIMARY if following else None):
            self.me_btn.icon_color = ft.Colors.PRIMARY if following else None
            self.me_btn.tooltip = self.t("map_following" if following else "centre_me")
            self.me_btn.update()
        now = time.monotonic()
        left = FOLLOW_IDLE_SECONDS - (now - self._touched)
        back = following and left >= 0.5 and self._camera_seen is not None
        text = self.t("follow_back", s=math.ceil(left)) if back else self.back_text.value
        if back != self.back_btn.visible or text != self.back_text.value:
            self.back_btn.visible, self.back_text.value = back, text
            self.back_btn.update()
        if not following or self._camera_seen is None:
            return
        if left > 0 or now - self._followed < FOLLOW_OWN_MOVE_SECONDS:
            return
        fix = self.engine.gps_fix()
        lat, lon, zoom, _rot = self._camera_seen
        mx, my = to_px(fix.latitude, fix.longitude, FOLLOW_ZOOM)
        cx, cy = to_px(lat, lon, FOLLOW_ZOOM)
        if abs(zoom - FOLLOW_ZOOM) < 0.05 and math.hypot(mx - cx, my - cy) < FOLLOW_SLACK_PX:
            return  # already there
        self._followed = time.monotonic()
        await self.centre(fix.latitude, fix.longitude, FOLLOW_ZOOM)

    async def _centre_me(self, _e) -> None:
        here = self.engine.my_position()
        if here and self.following():
            self._touched = 0.0  # following again at once, at the usual zoom
            self._followed = 0.0
            self._camera_seen = self._camera_seen or (*here, -1.0, 0.0)  # not asked yet: move anyway
            await self._follow()
        elif here:
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
