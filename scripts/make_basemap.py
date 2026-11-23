"""Write site/static/geo/basemap.json from Natural Earth (public domain), once, by hand.

    curl -o a0.json https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson
    curl -o a1.json https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson
    uv run python scripts/make_basemap.py a0.json a1.json

South America's countries, and the provinces of the countries where the Chaco's species live,
projected (equirectangular, scaled by cos 25° S) to SVG units, 10 per degree of longitude, and
simplified to about 3 km. The species pages draw the map from this file at build time.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

OUT = Path(__file__).resolve().parents[1] / "site" / "static" / "geo" / "basemap.json"
BOX = (-82.0, -56.0, -34.0, 13.0)  # lon min, lat min, lon max, lat max
UNIT = 10.0  # SVG units per degree of longitude
COS = math.cos(math.radians(25))
PROVINCES_OF = {"ARG", "BOL", "PRY", "URY"}
TOLERANCE = 0.03  # degrees


def project(lon: float, lat: float) -> tuple[float, float]:
    return ((lon - BOX[0]) * UNIT * COS, (BOX[3] - lat) * UNIT)


def _simplify(pts: list[tuple[float, float]], tol: float) -> list[tuple[float, float]]:
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (ax, ay), (bx, by) = pts[a], pts[b]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy) or 1e-12
        best, idx = 0.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            d = abs(dy * px - dx * py + bx * ay - by * ax) / norm
            if d > best:
                best, idx = d, i
        if best > tol and idx > 0:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(pts, keep, strict=True) if k]


def _rings(geom: dict[str, Any]) -> list[list[list[float]]]:
    if geom["type"] == "Polygon":
        return list(geom["coordinates"])
    return [ring for poly in geom["coordinates"] for ring in poly]


def _path(geom: dict[str, Any]) -> str:
    parts = []
    for ring in _rings(geom):
        if not any(BOX[0] <= x <= BOX[2] and BOX[1] <= y <= BOX[3] for x, y in ring):
            continue
        ring_pts = [(x, y) for x, y in ring]
        half = len(ring_pts) // 2  # a closed ring: simplify its two halves on their own
        pts = _simplify(ring_pts[: half + 1], TOLERANCE)[:-1] + _simplify(
            ring_pts[half:], TOLERANCE
        )
        if len(pts) < 4:
            continue
        xy = [project(x, y) for x, y in pts]
        parts.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in xy) + "Z")
    return "".join(parts)


def _centroid(geom: dict[str, Any]) -> list[float]:
    ring = max(_rings(geom), key=len)
    lon = sum(p[0] for p in ring) / len(ring)
    lat = sum(p[1] for p in ring) / len(ring)
    return [round(lon, 3), round(lat, 3)]


def main(a0: str, a1: str) -> None:
    countries = []
    for f in json.loads(Path(a0).read_text(encoding="utf-8"))["features"]:
        p = f["properties"]
        if p.get("CONTINENT") != "South America":
            continue
        d = _path(f["geometry"])
        if d:
            countries.append({"iso": p["ADM0_A3"], "name": p["NAME"], "d": d})
    provinces = []
    for f in json.loads(Path(a1).read_text(encoding="utf-8"))["features"]:
        p = f["properties"]
        if p.get("adm0_a3") not in PROVINCES_OF:
            continue
        d = _path(f["geometry"])
        if d:
            provinces.append(
                {
                    "country": p["adm0_a3"],
                    "name": p["name"],
                    "d": d,
                    "centre": _centroid(f["geometry"]),
                }
            )
    w, h = project(BOX[2], BOX[1])
    out = {
        "about": "Natural Earth 1:50m countries and 1:10m provinces (public domain), "
        "made by scripts/make_basemap.py",
        "box": list(BOX),
        "unit": UNIT,
        "cos": round(COS, 6),
        "width": round(w, 1),
        "height": round(h, 1),
        "countries": sorted(countries, key=lambda c: c["iso"]),
        "provinces": sorted(provinces, key=lambda c: (c["country"], c["name"])),
    }
    OUT.write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {OUT}: {len(countries)} countries, {len(provinces)} provinces, "
        f"{OUT.stat().st_size // 1024} KB"
    )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
