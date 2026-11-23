"""Where the species has been seen: GBIF occurrences, counted on a grid (the species page's map).

    genes occurrences <id> [--taxon <GBIF key>] [--max 3000]

Downloads georeferenced GBIF occurrences without geospatial issues (preserved specimens,
human observations: iNaturalist research grade among them), counts them in half-degree cells
and writes `species/<kind>/<id>/occurrences.json`. Only counts per cell are stored: no record,
person or exact place. Network only here; the parsing is tested on a recorded answer.
"""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from collections import Counter
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from genes import jsonio

API = "https://api.gbif.org/v1/occurrence/search"
PAGE = 300
CELL_DEG = 0.5
USER_AGENT = "genes-species-tool/0.1"

Fetch = Callable[[str], bytes]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as res:
        data: bytes = res.read()
        return data


def page_url(taxon: int, offset: int) -> str:
    q = {
        "taxonKey": taxon,
        "hasCoordinate": "true",
        "hasGeospatialIssue": "false",
        "occurrenceStatus": "PRESENT",
        "limit": PAGE,
        "offset": offset,
    }
    return f"{API}?{urllib.parse.urlencode(q)}"


def _cell(value: float) -> float:
    """The centre of the half-degree cell holding `value`."""
    return round(math.floor(value / CELL_DEG) * CELL_DEG + CELL_DEG / 2, 2)


def licence_of(url: str) -> str:
    u = url.lower()
    if "publicdomain" in u or "cc0" in u:
        return "cc0"
    if "by-nc" in u:
        return "cc-by-nc"
    if "/by/" in u or "cc_by_4" in u or u.endswith("cc_by"):
        return "cc-by"
    return "other"


def count(pages: list[dict[str, Any]]) -> dict[str, Any]:
    cells: Counter[tuple[float, float]] = Counter()
    basis: Counter[str] = Counter()
    licences: Counter[str] = Counter()
    years: list[int] = []
    for page in pages:
        for r in page.get("results", []):
            lat, lon = r.get("decimalLatitude"), r.get("decimalLongitude")
            if not isinstance(lat, int | float) or not isinstance(lon, int | float):
                continue
            cells[(_cell(lon), _cell(lat))] += 1
            basis[str(r.get("basisOfRecord", "UNKNOWN"))] += 1
            licences[licence_of(str(r.get("license", "")))] += 1
            if isinstance(r.get("year"), int):
                years.append(r["year"])
    return {
        "cell_deg": CELL_DEG,
        "cells": [[lon, lat, n] for (lon, lat), n in sorted(cells.items())],
        "total": sum(cells.values()),
        "basis": dict(sorted(basis.items())),
        "licences": dict(sorted(licences.items())),
        "years": [min(years), max(years)] if years else None,
    }


def download(taxon: int, limit: int, get: Fetch = fetch) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    offset = 0
    while offset < limit:
        page = json.loads(get(page_url(taxon, offset)))
        pages.append(page)
        offset += PAGE
        if page.get("endOfRecords", True):
            break
    return pages


def write(
    folder: Path, taxon: int, limit: int = 3000, get: Fetch = fetch, today: date | None = None
) -> dict[str, Any]:
    counted = count(download(taxon, limit, get))
    out = {
        "format": "genes.occurrences.v1",
        "id": folder.name,
        "source": {
            "title": f"GBIF.org occurrence search, taxon {taxon}: georeferenced, "
            "no geospatial issues; counted per cell",
            "url": f"https://www.gbif.org/occurrence/search?taxon_key={taxon}&has_coordinate=true",
            "accessed": (today or date.today()).isoformat(),
        },
        **counted,
    }
    (folder / "occurrences.json").write_text(jsonio.dumps(out), encoding="utf-8")
    return out
