"""The offline base map: country borders, coastlines and bigger cities from Natural Earth (public domain).

Bundled with the app (offline/world.json, built by tools/build_offline_map.py), so the map works
with no internet at all, for APRS as well as TAK. Cities appear by size as you zoom in.
"""

from __future__ import annotations

import functools
import json
import math
import pathlib
from dataclasses import dataclass

import flet as ft
import flet_map as fm

from aprs_kiss_core import tilemaps, units

DATA = pathlib.Path(__file__).with_name("offline") / "world.json"
ATTRIBUTION = "Natural Earth, GeoNames"
BORDER = "#7B5EA7"
COAST = "#4A7FB0"
WATER_HINT = "#DCE9F5"
# The map is light in the dark mode too, like the OSM and imported tiles: land, names and dots in fixed colours
LAND = "#F2EFE9"  # OpenStreetMap's land colour, also under tiles still loading
CITY_COLOR = "#2B2B2B"
TOWN_COLOR = "#555555"


@functools.lru_cache(maxsize=1)
def data() -> dict:
    try:
        return json.loads(DATA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"borders": [], "coast": [], "cities": [], "towns": [], "peaks": [], "motorways": [], "roads": []}


MIN_ZOOM = 3  # further out the world repeats side by side
TIERS = (  # (up to zoom, which cities)
    (4.0, lambda pop, capital: capital and pop >= 2_000_000),
    (6.0, lambda pop, capital: capital or pop >= 1_000_000),
    (7.5, lambda pop, capital: capital or pop >= 300_000),
    (99, lambda pop, capital: True),
)


def tier(zoom: float) -> int:
    """Which cities to show: more of them, smaller ones, as you zoom in."""
    return next(i for i, (limit, _) in enumerate(TIERS) if zoom < limit)


MIN_HALF = 3.0  # degrees of latitude: at least ~330 km around the middle of the map is kept
PLACE_SCREENS = 500  # pixels each way for the names
SCREENS = 900  # pixels each way from the middle: a screen and a half, so a short pan needs nothing new


@dataclass(frozen=True)
class Region:
    """The part of the world sent to the screen: a box around the middle of the map, and how finely."""

    south: float
    north: float
    west: float
    east: float
    step: float  # points closer than this (degrees) are left out: under ~2.5 pixels at this zoom
    zoom_key: int

    @classmethod
    def around(cls, lat: float, lon: float, zoom: float, screens: float = SCREENS,
               min_half: float = MIN_HALF) -> Region:
        per_pixel = 360 / (256 * 2 ** zoom)
        half = max(min_half, per_pixel * screens)
        half_lon = min(180.0, half / max(math.cos(math.radians(min(abs(lat), 80))), 0.2))
        if half >= 60:  # most of the world in view: all of it, no box to leave
            return cls(-90, 90, -180, 180, per_pixel * 2.5, round(zoom))
        return cls(max(-90.0, lat - half), min(90.0, lat + half), max(-180.0, lon - half_lon),
                   min(180.0, lon + half_lon), per_pixel * 2.5, round(zoom))

    def contains(self, lat: float, lon: float) -> bool:
        return self.south <= lat <= self.north and self.west <= lon <= self.east

    def covers(self, lat: float, lon: float, zoom: float) -> bool:
        """Still good for this view: the same zoom, and the middle not near the edge of the box."""
        if round(zoom) != self.zoom_key:
            return False
        if self.west <= -180 and self.east >= 180 and self.south <= -90 and self.north >= 90:
            return True
        quarter_lat, quarter_lon = (self.north - self.south) / 4, (self.east - self.west) / 4
        return (self.south + quarter_lat <= lat <= self.north - quarter_lat
                and self.west + quarter_lon <= lon <= self.east - quarter_lon)


def clip(lines: list, region: Region) -> list[list]:
    """The pieces of the lines inside the region, thinned out to what the zoom can show."""
    out = []
    step = region.step
    for line in lines:
        piece: list = []
        prev = None
        for point in line:
            lat, lon = point
            if region.contains(lat, lon):
                if not piece and prev is not None:
                    piece.append(prev)  # from just outside, so the line reaches the edge
                if not piece or abs(lat - piece[-1][0]) + abs(lon - piece[-1][1]) >= step:
                    piece.append(point)
            elif piece:
                piece.append(point)
                _keep(out, piece, step)
                piece = []
            prev = point
        if piece:
            if piece[-1] is not line[-1]:
                piece.append(line[-1])
            _keep(out, piece, step)
    return out


def _keep(out: list, piece: list, step: float) -> None:
    """A piece worth drawing: not a speck (an islet smaller than a few pixels at this zoom)."""
    if len(piece) < 2:
        return
    lats, lons = [p[0] for p in piece], [p[1] for p in piece]
    if max(lats) - min(lats) + max(lons) - min(lons) >= step * 2:
        out.append(piece)


def _polylines(lines: list, color: str, width: float) -> list[fm.PolylineMarker]:
    return [fm.PolylineMarker(coordinates=[fm.MapLatitudeLongitude(lat, lon) for lat, lon in line], color=color,
                              stroke_width=width)
            for line in lines]


def city_markers(level: int, region: Region | None = None) -> list[fm.Marker]:
    out = []
    keep = TIERS[level][1]
    for name, lat, lon, pop, capital in data()["cities"]:
        if not keep(pop, bool(capital)) or (region and not region.contains(lat, lon)):
            continue
        out.append(fm.Marker(
            coordinates=fm.MapLatitudeLongitude(lat, lon), width=140, height=30,
            content=ft.Column([
                ft.Container(width=7 if capital else 5, height=7 if capital else 5, border_radius=4,
                             bgcolor=CITY_COLOR),
                ft.Text(name, size=11 if capital else 10, weight=ft.FontWeight.BOLD if capital else None,
                        color=CITY_COLOR, no_wrap=True),
            ], spacing=0, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        ))
    return out


TOWN_TIERS = ((8.5, None), (9.5, 20000), (10.5, 10000), (11.5, 5000), (12.5, 2000), (99, 0))  # (up to zoom, smallest)
PEAK_TIERS = ((7.0, None), (8.5, 1), (10.0, 5), (11.0, 15), (99, 99))  # (up to zoom, each country's N highest)
ROAD_TIERS = ((5.0, False, False), (7.5, True, False), (99, True, True))  # (up to zoom, motorways, main roads)
MOTORWAY = "#E57373"
MAIN_ROAD = "#FFB74D"
PEAK_COLOR = "#8D6E63"


def _limit(tiers, zoom):
    return next(value for upto, value in tiers if zoom < upto)


def town_markers(zoom: float, region: Region | None = None) -> list[fm.Marker]:
    """Smaller towns (GeoNames, Europe): the bigger ones first as you zoom in, all of 5000+ people close up."""
    least = _limit(TOWN_TIERS, zoom)
    if least is None:
        return []
    return [fm.Marker(
        coordinates=fm.MapLatitudeLongitude(lat, lon), width=120, height=26,
        content=ft.Column([
            ft.Container(width=4, height=4, border_radius=2, bgcolor=TOWN_COLOR),
            ft.Text(name, size=9, color=TOWN_COLOR, no_wrap=True),
        ], spacing=0, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
    ) for name, lat, lon, pop in data().get("towns", [])
        if pop >= least and (region is None or region.contains(lat, lon))]


def peak_markers(zoom: float, region: Region | None = None) -> list[fm.Marker]:
    """Each country's highest peaks: the very highest first, the others as you zoom in."""
    ranks = _limit(PEAK_TIERS, zoom)
    if ranks is None:
        return []
    return [fm.Marker(
        coordinates=fm.MapLatitudeLongitude(lat, lon), width=130, height=30,
        content=ft.Column([
            ft.Text("▲", size=10, color=PEAK_COLOR),
            ft.Text(f"{name} {metres} m", size=9, color=PEAK_COLOR, weight=ft.FontWeight.BOLD, no_wrap=True),
        ], spacing=0, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
    ) for name, lat, lon, metres, rank in data().get("peaks", [])
        if rank < ranks and (region is None or region.contains(lat, lon))]


class OfflineLayers:
    """The offline map around the middle of the screen, not the whole world.

    Only the borders, coasts and cities in a box around what is on screen go to the map, thinned
    out to what the zoom can show; when the map is moved far enough or zoomed, the box is refilled.
    """

    def __init__(self, lat: float, lon: float, zoom: float) -> None:
        self.coast = fm.PolylineLayer(polylines=[])
        self.roads = fm.PolylineLayer(polylines=[])  # under the borders: motorways, closer up main roads too
        self.borders = fm.PolylineLayer(polylines=[])
        self.cities = fm.MarkerLayer(markers=[])
        self.region: Region | None = None
        self.places: Region | None = None  # the names (cities, towns, peaks) cover a smaller box
        self.moved(lat, lon, zoom)

    @property
    def layers(self) -> list:
        return [self.coast, self.roads, self.borders, self.cities]

    def moved(self, lat: float, lon: float, zoom: float) -> bool:
        """The map moved: refill the layers when the box no longer covers it; True when they changed."""
        changed = False
        if not (self.region and self.region.covers(lat, lon, zoom)):
            d = data()
            self.region = region = Region.around(lat, lon, zoom)
            self.coast.polylines = _polylines(clip(d["coast"], region), COAST, 1.0)
            self.borders.polylines = _polylines(clip(d["borders"], region), BORDER, 1.4)
            _, motorways, main = next(t for t in ROAD_TIERS if zoom < t[0])
            self.roads.polylines = (
                (_polylines(clip(d.get("roads", []), region), MAIN_ROAD, 1.2) if main else [])
                + (_polylines(clip(d.get("motorways", []), region), MOTORWAY, 2.0) if motorways else []))
            changed = True
        if not (self.places and self.places.covers(lat, lon, zoom)):
            # names only around what is on screen (about a screen and a half each way): close up there
            # are thousands of towns within the lines' box, too many labels for a phone
            self.places = places = Region.around(lat, lon, zoom, screens=PLACE_SCREENS, min_half=0.2)
            self.cities.markers = (peak_markers(zoom, places) + town_markers(zoom, places)
                                   + city_markers(tier(zoom), places))  # the big cities drawn on top
            changed = True
        return changed


# ─── maps the user imported (MBTiles, PMTiles, …), shown over the bundled map when offline ───

_server: tilemaps.TileServer | None = None
_custom: list[tuple[str, tilemaps.TileSource]] = []


def set_custom_maps(paths: list[str]) -> list[tuple[str, tilemaps.MapError]]:
    """Open the imported maps (slow for big folders: call from a thread); the ones that failed."""
    global _server
    if _server is None:
        if not paths:
            return []
        _server = tilemaps.TileServer()
    opened, failed = _server.set_maps(paths)
    _custom[:] = opened
    return failed


def custom_maps() -> list[tuple[str, tilemaps.TileSource]]:
    return list(_custom)


def _custom_layer(url: str, source: tilemaps.TileSource) -> fm.TileLayer:
    bounds = None
    if source.bounds:
        w, s, e, n = source.bounds
        bounds = fm.MapLatitudeLongitudeBounds(fm.MapLatitudeLongitude(n, w), fm.MapLatitudeLongitude(s, e))
    # past its most detailed zoom the map's own tiles are enlarged; where it has none the bundled map shows
    return fm.TileLayer(url_template=url, user_agent_package_name="aprs_kiss_app", tile_bounds=bounds,
                        min_native_zoom=source.min_zoom, max_native_zoom=source.max_zoom, max_zoom=20,
                        min_zoom=max(0, source.min_zoom - 1), keep_buffer=1, pan_buffer=0)


TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
# OpenTopoMap: contour lines and hill shading on OpenStreetMap data, to zoom 17 (its servers have no more)
TOPO_TILES = "https://tile.opentopomap.org/{z}/{x}/{y}.png"
TOPO_CREDIT = "© OpenStreetMap, SRTM · © OpenTopoMap (CC-BY-SA)"
# OpenStreetMap's tile usage policy asks for an identifying User-Agent.
USER_AGENT = "io.github.michalsiman.aprs_kiss_app"
OSM_CREDIT = "© OpenStreetMap"


def gestures() -> fm.InteractionConfiguration:
    """Two fingers either zoom or turn the map, not both at once, and turning needs a clear twist
    (60° instead of 20°): zooming and panning no longer turn the map by accident."""
    return fm.InteractionConfiguration(enable_multi_finger_gesture_race=True, rotation_threshold=60)


class BaseMap:
    """What lies under the markers: OpenStreetMap tiles or the offline map, and a small credit line.

    Switching between the two only shows and hides layers. The offline map (tens of thousands of
    points) goes to the screen once, the first time it is wanted, and not again on every switch,
    which made switching slow, above all on phones.
    """

    def __init__(self, markers: fm.MarkerLayer, center: tuple[float, float], zoom: float,
                 tile_opacity: float = 1.0, trails: fm.PolylineLayer | None = None, overlays: tuple = ()) -> None:
        self.markers, self.center, self.zoom, self.trails = markers, center, zoom, trails
        self.overlays = list(overlays)  # drawn over the stations (the distance measurement)
        self.tiles = fm.TileLayer(url_template=TILES, user_agent_package_name=USER_AGENT, max_zoom=19,
                                  opacity=tile_opacity)
        self.offline: OfflineLayers | None = None
        self._custom: dict[str, fm.TileLayer] = {}
        self.credit_text = ft.Text(size=8, color=ft.Colors.ON_SURFACE_VARIANT)
        # Small and see-through, in the corner: the credit OpenStreetMap asks for, without covering the map.
        self.credit = ft.Container(self.credit_text, right=0, bottom=0, padding=ft.Padding.symmetric(horizontal=3),
                                   bgcolor=ft.Colors.with_opacity(0.55, ft.Colors.SURFACE),
                                   border_radius=ft.BorderRadius.only(top_left=4))

    def layers(self, offline: bool, imported: bool = False, online: str = "osm") -> list:
        """online: "osm" OpenStreetMap, "otm" OpenTopoMap (when not offline)."""
        topo = online == "otm"
        self.tiles.url_template = TOPO_TILES if topo else TILES
        self.tiles.max_zoom = 17 if topo else 19
        if offline and self.offline is None:
            self.offline = OfflineLayers(*self.center, self.zoom)
        self.tiles.visible = not offline
        custom = custom_maps() if offline and imported else []
        self._custom = {url: self._custom.get(url) or _custom_layer(url, source) for url, source in custom}
        extra = (self.offline.layers if self.offline else []) + list(self._custom.values())
        for layer in extra:
            layer.visible = offline
        credits = list(dict.fromkeys(source.attribution or source.name for _, source in custom))  # once each
        self.credit_text.value = ((" · ".join([*credits, ATTRIBUTION]) + " (offline)") if offline
                                  else TOPO_CREDIT if topo else OSM_CREDIT)
        return [self.tiles, *extra, *([self.trails] if self.trails else []), self.markers, *self.overlays]

    def moved(self, lat: float, lon: float, zoom: float, offline: bool) -> bool:
        """Remember where the map is; True when the offline layers were refilled and need an update."""
        self.center, self.zoom = (lat, lon), zoom
        return bool(self.offline and offline and self.offline.moved(lat, lon, zoom))


class ScaleBar:
    """The map's scale: a short bar with its length ("500 m", "10 km") in the lower left corner.

    The map library has none, so it is drawn here from the zoom and the latitude (Web Mercator: a
    pixel is 156543 m × cos(latitude) / 2^zoom), and redrawn whenever the app learns where the map is.
    """

    MAX_PX = 90  # the bar is at most this long; its length is a round 1, 2 or 5 × 10^n

    def __init__(self) -> None:
        self.label = ft.Text(size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE)
        self.bar = ft.Container(height=4, border=ft.Border.only(
            left=ft.BorderSide(1.5, ft.Colors.ON_SURFACE), right=ft.BorderSide(1.5, ft.Colors.ON_SURFACE),
            bottom=ft.BorderSide(1.5, ft.Colors.ON_SURFACE)))
        self.control = ft.Container(
            ft.Column([self.label, self.bar], spacing=1, tight=True,
                      horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            left=8, bottom=6, padding=ft.Padding.symmetric(horizontal=4, vertical=1), border_radius=4,
            bgcolor=ft.Colors.with_opacity(0.6, ft.Colors.SURFACE),
        )

    @staticmethod
    def pick(metres_per_px: float, max_px: float) -> tuple[float, float]:
        """(metres, pixels): the longest round distance that fits in max_px."""
        most = metres_per_px * max_px
        step = 10 ** math.floor(math.log10(most))
        metres = max(m for m in (step, 2 * step, 5 * step) if m <= most)
        return metres, metres / metres_per_px

    def show(self, lat: float, zoom: float) -> None:
        per_px = 156543.03392 * math.cos(math.radians(max(-85.0, min(85.0, lat)))) / 2 ** zoom
        if units.current.miles:  # "500 ft", "2 mi"
            mi_per_px = per_px / 1000 / units.KM_PER_MI
            if mi_per_px * self.MAX_PX >= 1:
                miles, px = self.pick(mi_per_px, self.MAX_PX)
                self.label.value = f"{miles:g} mi"
            else:
                feet, px = self.pick(per_px * units.FT_PER_M, self.MAX_PX)
                self.label.value = f"{feet:g} ft"
            self.bar.width = px
            return
        metres, px = self.pick(per_px, self.MAX_PX)
        self.bar.width = px
        self.label.value = f"{metres / 1000:g} km" if metres >= 1000 else f"{metres:g} m"
