"""The offline base map: country borders, coastlines and bigger cities from Natural Earth (public domain).

Bundled with the app (offline/world.json, built by tools/build_offline_map.py), so the map works
with no internet at all, for APRS as well as TAK. Cities appear by size as you zoom in.
"""

from __future__ import annotations

import functools
import json
import pathlib

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


def _lines(lines: list, color: str, width: float) -> fm.PolylineLayer:
    return fm.PolylineLayer(polylines=[
        fm.PolylineMarker(coordinates=[fm.MapLatitudeLongitude(lat, lon) for lat, lon in line], color=color,
                          stroke_width=width)
        for line in lines])


def city_markers(level: int) -> list[fm.Marker]:
    out = []
    keep = TIERS[level][1]
    for name, lat, lon, pop, capital in data()["cities"]:
        if not keep(pop, bool(capital)):
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
    """The layers of the offline map; `cities` is refilled when the zoom crosses a tier."""

    def __init__(self, zoom: float) -> None:
        d = data()
        self.level = tier(zoom)
        self.coast = _lines(d["coast"], COAST, 1.0)
        self.borders = _lines(d["borders"], BORDER, 1.4)
        self.cities = fm.MarkerLayer(markers=city_markers(self.level))

    @property
    def layers(self) -> list:
        return [self.coast, self.borders, self.cities]

    def zoomed(self, zoom: float) -> bool:
        """Update the cities for a new zoom; True when they changed."""
        level = tier(zoom)
        if level == self.level:
            return False
        self.level = level
        self.cities.markers = city_markers(level)
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

    def __init__(self, markers: fm.MarkerLayer, zoom: float, tile_opacity: float = 1.0) -> None:
        self.markers, self.zoom = markers, zoom
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
            self.offline = OfflineLayers(self.zoom)
        self.tiles.visible = not offline
        extra = self.offline.layers if self.offline else []
        for layer in extra:
            layer.visible = offline
        self.credit_text.value = f"{ATTRIBUTION} (offline)" if offline else OSM_CREDIT
        return [self.tiles, *extra, self.markers]

    def zoomed(self, zoom: float, offline: bool) -> bool:
        """Remember the zoom; True when the offline cities changed and need an update."""
        self.zoom = zoom
        return bool(self.offline and offline and self.offline.zoomed(zoom))
