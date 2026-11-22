"""Build src/aprs_kiss_app/offline/world.json from Natural Earth (public domain) GeoJSON.

    python3 tools/build_offline_map.py <folder with the Natural Earth .geojson files>

Needs ne_50m_admin_0_boundary_lines_land, ne_50m_coastline and ne_10m_populated_places_simple
from https://github.com/nvkelso/natural-earth-vector/tree/master/geojson.
"""

import json
import math
import pathlib
import sys

OUT = pathlib.Path(__file__).resolve().parents[1] / "src/aprs_kiss_app/offline/world.json"


def simplify(points, tolerance):
    """Douglas-Peucker on [lat, lon] in degrees."""
    if len(points) < 3:
        return points
    (ay, ax), (by, bx) = points[0], points[-1]
    dx, dy = bx - ax, by - ay
    norm = math.hypot(dx, dy)
    best, index = -1.0, 0
    for i in range(1, len(points) - 1):
        py, px = points[i]
        d = abs(dy * px - dx * py + bx * ay - by * ax) / norm if norm else math.hypot(px - ax, py - ay)
        if d > best:
            best, index = d, i
    if best <= tolerance:
        return [points[0], points[-1]]
    return simplify(points[:index + 1], tolerance)[:-1] + simplify(points[index:], tolerance)


def lines(path, tolerance):
    out = []
    for f in json.loads(path.read_text())["features"]:
        g = f["geometry"]
        for part in g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]:
            line = simplify([[lat, lon] for lon, lat, *_ in part], tolerance)
            line = [[round(lat, 3), round(lon, 3)] for lat, lon in line]
            if len(line) > 1:
                out.append(line)
    return out


FIXES = {"Pizen": "Plzeň"}  # typos in Natural Earth


def cities(path):
    europe = lambda lat, lon: 34 <= lat <= 72 and -25 <= lon <= 45  # noqa: E731
    out = []
    for f in json.loads(path.read_text())["features"]:
        p = f["properties"]
        pop, lat, lon = int(p.get("pop_max") or 0), p["latitude"], p["longitude"]
        capital = p.get("featurecla") == "Admin-0 capital"
        regional = p.get("featurecla") == "Admin-1 capital"
        if (europe(lat, lon) and (pop >= 100000 or (regional and pop >= 50000))) or capital or pop >= 3000000:
            out.append([FIXES.get(p["name"], p["name"]), round(lat, 4), round(lon, 4), pop, 1 if capital else 0])
    return sorted(out, key=lambda c: -c[3])


def main(folder):
    d = pathlib.Path(folder)
    data = {
        "source": "Natural Earth (public domain), naturalearthdata.com",
        "borders": lines(d / "ne_50m_admin_0_boundary_lines_land.geojson", 0.01),
        "coast": lines(d / "ne_50m_coastline.geojson", 0.02),
        "cities": cities(d / "ne_10m_populated_places_simple.geojson"),
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    pts = {k: sum(len(x) for x in data[k]) for k in ("borders", "coast")}
    print(OUT, OUT.stat().st_size // 1024, "kB", pts, len(data["cities"]), "cities")


if __name__ == "__main__":
    main(sys.argv[1])
