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
