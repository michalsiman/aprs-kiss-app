"""Markers that would cover each other on screen are moved a little apart.

Stations at the same place (a digipeater and an iGate on one mast, OK0BR-10 and OK0BR-1) or a few metres
apart would otherwise be one unreadable heap. At the map's zoom each station gets a screen position (Web
Mercator pixels). The markers are placed one by one: each at its own place when that is free, otherwise at
the nearest free spot on small rings around its own place (never further than MAX_SHIFT pixels, so a
station never wanders off to somebody else's town). A thin line on the map joins a moved marker to where
the station really is; where two lines would cross, the two markers swap places (then up to SWAP_SHIFT). Zooming in, the markers no longer overlap and all stay at their places.
"""

from __future__ import annotations

import math

TILE = 256
CLOSE_X = 66  # pixels: markers nearer than this side by side…
CLOSE_Y = 48  # …and this one above the other cover each other's label
RINGS = (54, 78, 104, 132, 160)  # pixels: the circles tried around a station's own place
DIRECTIONS = 12
MAX_SHIFT = RINGS[-1]
SWAP_SHIFT = MAX_SHIFT * 1.5  # untangling crossed lines may take a marker this far (else crowds stay crossed)
# Closer than this on screen (side by side, one above the other): as good as one place. One of them staying
# would cover the other's dot with its symbol (the disc sits above the point) or the top of its tag, and the
# dot would look like the first station's; so neither stays.
SAME_X = 34
SAME_Y = 32
MIN_ZOOM = 9.0  # further out (a whole region) the markers stay where they are: spreading would be a web of lines


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


def _offsets() -> list[tuple[float, float]]:
    out = [(0.0, 0.0)]
    for ring, r in enumerate(RINGS):
        turn = math.pi / DIRECTIONS * (ring % 2)  # every other ring turned by half a step
        for k in range(DIRECTIONS):
            a = -math.pi / 2 + 2 * math.pi * k / DIRECTIONS + turn  # the first one straight above
            out.append((r * math.cos(a), r * math.sin(a)))
    return out


OFFSETS = _offsets()


def spread(points: list[tuple[float, float]], zoom: float, fixed: int | None = None) -> list[tuple[float, float]]:
    """Where to draw each point: its own place, or a free spot close to it.

    fixed: a point placed first and never moved (our own station)."""
    shown = list(points)
    if zoom < MIN_ZOOM:
        return shown
    grid: dict[tuple[int, int], list[tuple[float, float]]] = {}

    def free(x: float, y: float) -> bool:
        cx, cy = int(x // CLOSE_X), int(y // CLOSE_Y)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for px, py in grid.get((cx + dx, cy + dy), ()):
                    if abs(px - x) < CLOSE_X and abs(py - y) < CLOSE_Y:
                        return False
        return True

    def take(x: float, y: float) -> None:
        grid.setdefault((int(x // CLOSE_X), int(y // CLOSE_Y)), []).append((x, y))

    px = [to_px(*pt, zoom) for pt in points]
    # Several stations at one place (or nearly, see SAME_X / SAME_Y): none of them stays on it. The place itself is kept free for the dot
    # the lines point to, otherwise the first station's marker covered it and nobody could tell where
    # the group really is.
    shared = set()
    cells: dict[tuple[int, int], list[int]] = {}
    for i, (x, y) in enumerate(px):
        cx, cy = int(x // SAME_X), int(y // SAME_Y)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in cells.get((cx + dx, cy + dy), ()):
                    if abs(px[j][0] - x) < SAME_X and abs(px[j][1] - y) < SAME_Y:
                        shared.update((i, j))
        cells.setdefault((cx, cy), []).append(i)
    if fixed in shared:
        shared.discard(fixed)  # our own station stays; the others go round it
    for i in shared:
        take(*px[i])  # the place is taken (by its dot)

    order = list(range(len(points)))
    if fixed is not None and 0 <= fixed < len(points):
        order.remove(fixed)
        order.insert(0, fixed)
    for i in order:
        x, y = to_px(*points[i], zoom)
        if i == fixed:
            take(x, y)
            continue
        for ox, oy in OFFSETS[1:] if i in shared else OFFSETS:  # sharing a place: never on it
            if free(x + ox, y + oy):
                if ox or oy:
                    shown[i] = from_px(x + ox, y + oy, zoom)
                take(x + ox, y + oy)
                break
        else:
            take(x, y)  # no room anywhere near: it stays on its place, under the others
    return untangle(points, shown, zoom, fixed)


DISC_UP = 13  # pixels: a line starts at the symbol's disc, this far above the marker's point


def _crosses(a: tuple, b: tuple, c: tuple, d: tuple) -> bool:
    """Segments a–b and c–d cross (touching at an end, e.g. two lines to one dot, is not crossing)."""
    def side(p, q, r) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    d1, d2, d3, d4 = side(c, d, a), side(c, d, b), side(a, b, c), side(a, b, d)
    return ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4))


def untangle(points: list[tuple[float, float]], shown: list[tuple[float, float]], zoom: float,
             fixed: int | None = None) -> list[tuple[float, float]]:
    """No two lines (from a moved marker to where its station is) cross: when two do, the two markers swap
    their spots. Both spots were free, the lines get shorter in sum, so it ends; a swap that would take a
    marker further than SWAP_SHIFT from its station is not made."""
    shown = list(shown)
    real = [to_px(*pt, zoom) for pt in points]
    at = [to_px(*pt, zoom) for pt in shown]

    def line(i: int):
        return (at[i][0], at[i][1] - DISC_UP), real[i]

    for _ in range(500):
        moved = [i for i in range(len(points)) if i != fixed and shown[i] != points[i]]
        swapped = False
        for n, i in enumerate(moved):
            for j in moved[n + 1:]:
                if not _crosses(*line(i), *line(j)):
                    continue
                if math.dist(at[j], real[i]) > SWAP_SHIFT or math.dist(at[i], real[j]) > SWAP_SHIFT:
                    continue
                at[i], at[j] = at[j], at[i]
                shown[i], shown[j] = shown[j], shown[i]
                swapped = True
                break
            if swapped:
                break
        if not swapped:
            break
    return shown
