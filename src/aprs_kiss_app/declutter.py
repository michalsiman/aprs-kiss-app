"""Markers that would cover each other on screen are spread out in a small circle ("spiderfy").

Stations at the same place (a digipeater and an iGate on one mast, OK0BR-10 and OK0BR-1) or a few metres
apart would otherwise be one unreadable heap. At the map's zoom each station gets a screen position
(Web Mercator pixels); stations whose markers would overlap are grouped, and each group is laid out on a
circle around its middle. A thin line on the map joins each moved marker to where the station really is.
Zooming in, the group falls apart by itself: then the markers no longer overlap and stay where they are.
"""

from __future__ import annotations

import math

TILE = 256
CLOSE_X = 56  # pixels: markers nearer than this side by side…
CLOSE_Y = 30  # …and this one above the other cover each other's label
SLOT = 70  # pixels of circle per marker, so the labels do not touch
MIN_RADIUS = 44
MIN_RADIUS_AROUND = 64  # around a marker that stays: clear of it whatever the angle (√(56² + 30²))
MAX_GROUP = 14  # a bigger heap (a whole city zoomed out) stays as it is: zoom in to see it


def to_px(lat: float, lon: float, zoom: float) -> tuple[float, float]:
    scale = TILE * 2 ** zoom
    lat = max(-85.0, min(85.0, lat))
    x = (lon + 180.0) / 360.0 * scale
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * scale
    return x, y


def from_px(x: float, y: float, zoom: float) -> tuple[float, float]:
    scale = TILE * 2 ** zoom
    lon = x / scale * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / scale))))
    return lat, lon


def groups(points: list[tuple[float, float]], zoom: float) -> list[list[int]]:
    """Indexes of the points whose markers overlap, grouped (each group sorted; single points left out)."""
    px = [to_px(lat, lon, zoom) for lat, lon in points]
    parent = list(range(len(px)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    grid: dict[tuple[int, int], list[int]] = {}
    for i, (x, y) in enumerate(px):
        cx, cy = int(x // CLOSE_X), int(y // CLOSE_Y)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((cx + dx, cy + dy), ()):
                    if abs(px[j][0] - x) < CLOSE_X and abs(px[j][1] - y) < CLOSE_Y:
                        parent[find(i)] = find(j)
        grid.setdefault((cx, cy), []).append(i)
    out: dict[int, list[int]] = {}
    for i in range(len(px)):
        out.setdefault(find(i), []).append(i)
    return [sorted(g) for g in out.values() if len(g) > 1]


def spread(points: list[tuple[float, float]], zoom: float, fixed: int | None = None) -> list[tuple[float, float]]:
    """Where to draw each point: its own place, or a place on its group's circle.

    fixed: a point that stays where it is (our own station); the others of its group circle around it."""
    shown = list(points)
    for group in groups(points, zoom):
        if len(group) > MAX_GROUP:
            continue
        if fixed in group:
            cx, cy = to_px(*points[fixed], zoom)
            ring = [i for i in group if i != fixed]
        else:
            px = [to_px(*points[i], zoom) for i in group]
            cx = sum(p[0] for p in px) / len(px)
            cy = sum(p[1] for p in px) / len(px)
            ring = group
        radius = max(MIN_RADIUS_AROUND if ring is not group else MIN_RADIUS, len(ring) * SLOT / (2 * math.pi))
        for k, i in enumerate(ring):
            angle = -math.pi / 2 + 2 * math.pi * k / len(ring)  # the first one straight above
            shown[i] = from_px(cx + radius * math.cos(angle), cy + radius * math.sin(angle), zoom)
    return shown
