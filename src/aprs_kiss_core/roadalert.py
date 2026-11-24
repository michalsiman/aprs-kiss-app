"""Road incidents ahead: while the tracker runs, a warning for an incident on the way we are going.

Where we will drive is not known (no route), so "ahead" is a corridor along our heading: from here up
to the chosen distance, a kilometre wide on each side near us and widening further out (a road bends,
so something 5 km ahead may well be 2 km off the straight line). Behind us, or far to the side: no
warning. Each incident is announced once; again only after REPEAT_SECONDS, if it is still ahead.
"""

from __future__ import annotations

import math
from typing import Any, Iterable

from .mapfilter import is_road

DISTANCES_KM = (2, 5, 10, 20)
MIN_SPEED_KMH = 5.0  # slower than this the heading from the GPS means nothing
SIDE_NEAR_KM = 1.0  # the corridor's half width right in front of us…
SIDE_WIDENS = 0.25  # …plus this much per km further out
REPEAT_SECONDS = 30 * 60
INCIDENT_MAX_AGE = 3 * 3600  # older reports are not news any more
HEADING_MIN_M = 60  # from our own track: the last two points at least this far apart


def offset_km(lat: float, lon: float, lat2: float, lon2: float) -> tuple[float, float]:
    """(east, north) km from the first point to the second (flat Earth is fine for a few tens of km)."""
    north = (lat2 - lat) * 111.195
    east = (lon2 - lon) * 111.195 * math.cos(math.radians((lat + lat2) / 2))
    return east, north


def ahead(lat: float, lon: float, course: float, lat2: float, lon2: float,
          radius_km: float) -> tuple[float, float] | None:
    """(km ahead, km to the side) when the point is in the corridor, else None."""
    east, north = offset_km(lat, lon, lat2, lon2)
    c = math.radians(course)
    along = east * math.sin(c) + north * math.cos(c)
    side = east * math.cos(c) - north * math.sin(c)  # + right, - left
    if along <= 0 or math.hypot(along, side) > radius_km:
        return None
    if abs(side) > SIDE_NEAR_KM + SIDE_WIDENS * along:
        return None
    return along, side


def heading(fix_course: float | None, fix_speed: float | None, track: list | None) -> float | None:
    """Where we are going: the GPS course when moving, else from the last two places of our own track."""
    if fix_course is not None and fix_speed is not None and fix_speed >= MIN_SPEED_KMH:
        return fix_course % 360
    if track and len(track) >= 2:
        (_t1, lat1, lon1), (_t2, lat2, lon2) = track[-2][:3], track[-1][:3]
        east, north = offset_km(lat1, lon1, lat2, lon2)
        if math.hypot(east, north) * 1000 >= HEADING_MIN_M:
            return math.degrees(math.atan2(east, north)) % 360
    return None


class RoadAlerts:
    def __init__(self) -> None:
        self.told: dict[str, float] = {}  # incident -> when we warned about it

    def check(self, now: float, lat: float, lon: float, course: float | None,
              stations: Iterable[dict[str, Any]], radius_km: float) -> list[tuple[dict[str, Any], float, float]]:
        """New incidents ahead: [(station, km ahead, km to the side)], nearest first."""
        if course is None:
            return []
        found = []
        for e in stations:
            if e.get("latitude") is None or e.get("longitude") is None or not is_road(e):
                continue
            if now - (e.get("last_heard") or 0) > INCIDENT_MAX_AGE:
                continue
            if now - self.told.get(e["call"], -REPEAT_SECONDS) < REPEAT_SECONDS:
                continue
            where = ahead(lat, lon, course, e["latitude"], e["longitude"], radius_km)
            if where:
                found.append((e, *where))
        for e, _a, _s in found:
            self.told[e["call"]] = now
        return sorted(found, key=lambda f: f[1])
