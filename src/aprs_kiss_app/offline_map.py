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

DATA = pathlib.Path(__file__).with_name("offline") / "world.json"
ATTRIBUTION = "Natural Earth"
BORDER = "#7B5EA7"
COAST = "#4A7FB0"
WATER_HINT = "#DCE9F5"


@functools.lru_cache(maxsize=1)
def data() -> dict:
    try:
        return json.loads(DATA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"borders": [], "coast": [], "cities": []}


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
    def around(cls, lat: float, lon: float, zoom: float) -> Region:
        per_pixel = 360 / (256 * 2 ** zoom)
        half = max(MIN_HALF, per_pixel * SCREENS)
        half_lon = min(180.0, half / max(math.cos(math.radians(min(abs(lat), 80))), 0.2))
        if half >= 90:
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
                             bgcolor=ft.Colors.ON_SURFACE),
                ft.Text(name, size=11 if capital else 10, weight=ft.FontWeight.BOLD if capital else None,
                        color=ft.Colors.ON_SURFACE_VARIANT, no_wrap=True),
            ], spacing=0, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        ))
    return out


class OfflineLayers:
    """The offline map around the middle of the screen, not the whole world.

    Only the borders, coasts and cities in a box around what is on screen go to the map, thinned
    out to what the zoom can show; when the map is moved far enough or zoomed, the box is refilled.
    """

    def __init__(self, lat: float, lon: float, zoom: float) -> None:
        self.coast = fm.PolylineLayer(polylines=[])
        self.borders = fm.PolylineLayer(polylines=[])
        self.cities = fm.MarkerLayer(markers=[])
        self.region: Region | None = None
        self.moved(lat, lon, zoom)

    @property
    def layers(self) -> list:
        return [self.coast, self.borders, self.cities]

    def moved(self, lat: float, lon: float, zoom: float) -> bool:
        """The map moved: refill the layers when the box no longer covers it; True when they changed."""
        if self.region and self.region.covers(lat, lon, zoom):
            return False
        d = data()
        self.region = region = Region.around(lat, lon, zoom)
        self.coast.polylines = _polylines(clip(d["coast"], region), COAST, 1.0)
        self.borders.polylines = _polylines(clip(d["borders"], region), BORDER, 1.4)
        self.cities.markers = city_markers(tier(zoom), region)
        return True


TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
# OpenStreetMap's tile usage policy asks for an identifying User-Agent.
USER_AGENT = "io.github.michalsiman.aprs_kiss_app"
OSM_CREDIT = "© OpenStreetMap"


class BaseMap:
    """What lies under the markers: OpenStreetMap tiles or the offline map, and a small credit line.

    Switching between the two only shows and hides layers. The offline map (tens of thousands of
    points) goes to the screen once, the first time it is wanted, and not again on every switch,
    which made switching slow, above all on phones.
    """

    def __init__(self, markers: fm.MarkerLayer, center: tuple[float, float], zoom: float,
                 tile_opacity: float = 1.0) -> None:
        self.markers, self.center, self.zoom = markers, center, zoom
        self.tiles = fm.TileLayer(url_template=TILES, user_agent_package_name=USER_AGENT, max_zoom=19,
                                  opacity=tile_opacity)
        self.offline: OfflineLayers | None = None
        self.credit_text = ft.Text(size=8, color=ft.Colors.ON_SURFACE_VARIANT)
        # Small and see-through, in the corner: the credit OpenStreetMap asks for, without covering the map.
        self.credit = ft.Container(self.credit_text, right=0, bottom=0, padding=ft.Padding.symmetric(horizontal=3),
                                   bgcolor=ft.Colors.with_opacity(0.55, ft.Colors.SURFACE),
                                   border_radius=ft.BorderRadius.only(top_left=4))

    def layers(self, offline: bool) -> list:
        if offline and self.offline is None:
            self.offline = OfflineLayers(*self.center, self.zoom)
        self.tiles.visible = not offline
        extra = self.offline.layers if self.offline else []
        for layer in extra:
            layer.visible = offline
        self.credit_text.value = f"{ATTRIBUTION} (offline)" if offline else OSM_CREDIT
        return [self.tiles, *extra, self.markers]

    def moved(self, lat: float, lon: float, zoom: float, offline: bool) -> bool:
        """Remember where the map is; True when the offline layers were refilled and need an update."""
        self.center, self.zoom = (lat, lon), zoom
        return bool(self.offline and offline and self.offline.moved(lat, lon, zoom))
