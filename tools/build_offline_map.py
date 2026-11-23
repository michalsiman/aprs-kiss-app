"""Build src/aprs_kiss_app/offline/world.json from Natural Earth (public domain) and GeoNames (CC BY 4.0).

    python3 tools/build_offline_map.py <folder with the Natural Earth .geojson files> [<GeoNames folder>]

The Natural Earth folder may also hold ne_10m_roads.geojson (Europe's motorways and main roads).
The GeoNames folder (optional) holds countryInfo.txt, cities1000.txt and the per-country dumps
<CC>.zip of the European countries, from https://download.geonames.org/export/dump/ : the places of
1000 people and more, and the highest peaks of each country.

Needs ne_50m_admin_0_boundary_lines_land, ne_50m_coastline and ne_10m_populated_places_simple
from https://github.com/nvkelso/natural-earth-vector/tree/master/geojson.
"""

import io
import json
import math
import pathlib
import sys
import zipfile

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


PLACE_CODES = {"PPL", "PPLA", "PPLA2", "PPLA3", "PPLA4", "PPLC", "PPLG", "PPLS", "PPLF", "PPLR"}
PEAKS_PER_COUNTRY = 30
PEAK_SPACING_KM = 12  # spread over the ranges, not thirty around the highest one


def _km(a, b):
    return math.hypot((a[0] - b[0]) * 111, (a[1] - b[1]) * 111 * math.cos(math.radians(a[0])))


def _europe_codes(folder):
    return {line.split("\t")[0] for line in (folder / "countryInfo.txt").read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#") and line.split("\t")[8] == "EU"}


def towns(folder, cities_already):
    """European places of 1000 people and more; parts of cities and places already among the cities dropped."""
    eu = _europe_codes(folder)
    rows = []
    for line in (folder / "cities1000.txt").read_text(encoding="utf-8").splitlines():
        f = line.split("\t")
        if f[8] in eu and f[7] in PLACE_CODES:
            rows.append([f[1], round(float(f[4]), 3), round(float(f[5]), 3), int(f[14] or 0)])
    rows.sort(key=lambda r: -r[3])
    big = [(c[1], c[2]) for c in cities_already]
    out = []
    grid: dict = {}
    for name, lat, lon, pop in rows:
        cell = (round(lat * 20), round(lon * 12))  # ~5 km cells, to look for a bigger place nearby fast
        near = [p for dx in (-1, 0, 1) for dy in (-1, 0, 1) for p in grid.get((cell[0] + dx, cell[1] + dy), [])]
        # a bigger place within 1.5 km: this one is a part of it (villages are often 2-3 km apart)
        if any(_km((lat, lon), p) < 1.5 for p in near) or any(_km((lat, lon), p) < 1.5 for p in big if
                                                                abs(p[0] - lat) < 0.1):
            continue  # a district of a bigger town, or a town the cities list has already
        grid.setdefault(cell, []).append((lat, lon))
        out.append([name, lat, lon, pop])
    return out


def peaks(folder):
    """Each European country's highest peaks, at least PEAK_SPACING_KM apart; [name, lat, lon, m, rank]."""
    out = []
    for code in sorted(_europe_codes(folder)):
        path = folder / f"{code}.zip"
        if not path.exists():
            continue
        rows = []
        with zipfile.ZipFile(path) as zf, zf.open(f"{code}.txt") as fh:
            for line in io.TextIOWrapper(fh, encoding="utf-8"):
                f = line.rstrip("\n").split("\t")
                if f[6] != "T" or f[7] not in ("PK", "MT", "VLC") or f[8] != code or "[" in f[1]:
                    continue
                try:
                    metres = int(float(f[15] or f[16]))
                except ValueError:
                    continue
                if metres > 0:
                    rows.append([f[1], round(float(f[4]), 3), round(float(f[5]), 3), metres])
        rows.sort(key=lambda r: -r[3])
        mine = []
        for r in rows:
            if all(_km((r[1], r[2]), (m[1], m[2])) >= PEAK_SPACING_KM for m in mine):
                mine.append(r)
            if len(mine) >= PEAKS_PER_COUNTRY:
                break
        out += [[*m, rank] for rank, m in enumerate(mine)]
    # a peak on a border is in both countries' lists (Sněžka / Śnieżka): keep it once
    out.sort(key=lambda p: (p[4], -p[3]))
    kept = []
    for p in out:
        if all(_km((p[1], p[2]), (k[1], k[2])) >= 2 for k in kept):
            kept.append(p)
    return kept


MOTORWAYS = ("Major Highway", "Beltway")
MAIN_ROADS = ("Secondary Highway",)


def roads(path):
    """Europe's motorways and main roads from Natural Earth: (motorways, main roads) as lists of lines."""
    motorways, main = [], []
    for f in json.loads(path.read_text())["features"]:
        p = f["properties"]
        if p.get("continent") != "Europe":
            continue
        kind = motorways if p.get("type") in MOTORWAYS or p.get("expressway") == 1 else main if p.get(
            "type") in MAIN_ROADS else None
        if kind is None:
            continue
        g = f["geometry"]
        for part in g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]:
            line = [[round(lat, 3), round(lon, 3)] for lat, lon in simplify([[c[1], c[0]] for c in part], 0.005)]
            if len(line) > 1:
                kind.append(line)
    return motorways, main


def main(folder, geonames=None):
    d = pathlib.Path(folder)
    data = {
        "source": "Natural Earth (public domain), naturalearthdata.com",
        "borders": lines(d / "ne_50m_admin_0_boundary_lines_land.geojson", 0.01),
        "coast": lines(d / "ne_50m_coastline.geojson", 0.02),
        "cities": cities(d / "ne_10m_populated_places_simple.geojson"),
    }
    if (d / "ne_10m_roads.geojson").exists():
        data["motorways"], data["roads"] = roads(d / "ne_10m_roads.geojson")
    if geonames:
        g = pathlib.Path(geonames)
        data["source"] += "; GeoNames (CC BY 4.0), geonames.org"
        data["towns"] = towns(g, data["cities"])
        data["peaks"] = peaks(g)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    pts = {k: sum(len(x) for x in data[k]) for k in ("borders", "coast")}
    print(OUT, OUT.stat().st_size // 1024, "kB", pts, len(data["cities"]), "cities",
          len(data.get("towns", [])), "towns", len(data.get("peaks", [])), "peaks",
          len(data.get("motorways", [])), "motorways", len(data.get("roads", [])), "roads")


if __name__ == "__main__":
    main(*sys.argv[1:3])
