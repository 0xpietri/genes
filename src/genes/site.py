"""The public catalog genes.pietri.dev shows: pages written once at build time (spec §12).

    dist/index.html                       the catalog: one card per species
    dist/species/<id>/index.html          a species page, every fact already in the HTML
    dist/species/<id>/index.md            the same page as Markdown, for language models
    dist/sitemap.xml  robots.txt  llms.txt  llms-full.txt
    dist/static/site/...                  the pages' CSS and JS (3D, simulator, map, leaf)

Everything a reader or a search engine needs is in the HTML; JavaScript only adds the 3D
tree, the simulator, the animated leaf and the map's pan and zoom. Nothing is computed per
request and nobody logs in (spec §1); `account.js` keeps a place for a later login.
"""

from __future__ import annotations

import json
import math
import os
import shutil
from html import escape
from pathlib import Path
from typing import Any

from genes import jsonio
from genes import site_art as art
from genes.paths import REPO_ROOT
from genes.species import Species

SITE_DIR = REPO_ROOT / "site"
BASE_URL = os.environ.get("GENES_BASE_URL", "https://genes.pietri.dev").rstrip("/")
MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
MONTH_LETTERS = "JFMAMJJASOND"
STAGE_LABEL = {
    "seedling": "Seedling",
    "sapling": "Sapling",
    "young": "Young",
    "adult": "Adult",
    "old": "Old",
    "dead_standing": "Dead, standing",
    "fallen": "Fallen",
}
STATUS_LABEL = {
    "native": "Native to the Sierras Chicas",
    "exotic": "Exotic",
    "invasive": "Invasive",
    "domestic": "Domestic",
}
HABIT_LABEL = {
    "evergreen": "Evergreen",
    "semi_deciduous": "Semi-deciduous",
    "deciduous": "Deciduous",
}
GIVES_LABEL = {
    "fruit": "Fruit",
    "nectar": "Nectar",
    "pollen": "Pollen",
    "browse": "Browse",
    "shade": "Shade",
    "nitrogen_fixing": "Fixes nitrogen",
    "firewood": "Firewood",
    "nest_sites": "Nest sites",
}
# iNaturalist place guesses use these codes for provinces.
PLACE_CODES = {
    "AR-SE": "Santiago del Estero",
    "AR-SF": "Santa Fe",
    "AR-CB": "Córdoba",
    "AR-CC": "Chaco",
    "AR-SA": "Salta",
    "AR-FO": "Formosa",
    "AR-BA": "Buenos Aires",
}
COUNTRY_CODES = {"AR": "ARG", "PY": "PRY", "BO": "BOL", "UY": "URY"}
# The pietri.dev world stands over Unquillo, Córdoba.
WORLD_PLACE = {"name": "Unquillo, Córdoba: the pietri.dev world", "lon": -64.32, "lat": -31.23}


def e(value: Any) -> str:
    return escape(str(value), quote=True)


def dig(obj: Any, *keys: str) -> Any:
    for k in keys:
        obj = obj.get(k) if isinstance(obj, dict) else None
    return obj


def fmt_num(x: float) -> str:
    return f"{x:g}" if abs(x) < 1000 else f"{x:,.0f}"


def fmt_range(r: Any, unit: str = "") -> str:
    if not isinstance(r, dict):
        return ""
    if "value" in r:
        return str(r["value"])
    u = f" {unit}" if unit else ""
    lo, hi = r["min"], r["max"]
    if lo < 0 or hi < 0:  # "−11 to −5", not "-11–-5"
        return f"{fmt_num(lo).replace('-', '−')} to {fmt_num(hi).replace('-', '−')}{u}"
    return f"{fmt_num(lo)}–{fmt_num(hi)}{u}"


def months_text(months: list[int] | None) -> str:
    if not months:
        return ""
    return ", ".join(MONTHS[m - 1] for m in months)


def json_attr(value: Any) -> str:
    return e(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True))


# ---------------------------------------------------------------- shared page parts


def head(
    title: str,
    description: str,
    path: str,
    *,
    image: str | None = None,
    ld: list[dict[str, Any]] | None = None,
    preload: list[str] | None = None,
    scripts: list[str] | None = None,
) -> str:
    url = BASE_URL + path
    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{e(title)}</title>",
        f'<meta name="description" content="{e(description)}">',
        f'<link rel="canonical" href="{e(url)}">',
        '<meta name="color-scheme" content="dark">',
        '<meta name="theme-color" content="#11181a">',
        '<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">',
        '<link rel="alternate" type="text/plain" title="llms.txt" href="/llms.txt">',
        f'<meta property="og:title" content="{e(title)}">',
        f'<meta property="og:description" content="{e(description)}">',
        f'<meta property="og:url" content="{e(url)}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="genes · pietri.dev">',
        '<meta name="twitter:card" content="summary_large_image">',
    ]
    if image:
        parts.append(f'<meta property="og:image" content="{e(BASE_URL + image)}">')
    for font in ("fredoka", "nunito"):
        parts.append(
            f'<link rel="preload" href="/static/site/fonts/{font}.woff2" as="font" '
            'type="font/woff2" crossorigin>'
        )
    parts.append('<link rel="stylesheet" href="/static/site/site.css">')
    for href in preload or []:
        parts.append(f'<link rel="modulepreload" href="{e(href)}">')
    for src in scripts or []:
        parts.append(f'<script type="module" src="{e(src)}"></script>')
    for block in ld or []:
        # JSON-LD is data, not script: CSP's script-src does not apply to it.
        text = json.dumps(block, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
        parts.append(f'<script type="application/ld+json">{text}</script>')
    parts.append("</head>")
    return "\n".join(parts)


def header(active: str = "") -> str:
    plants = ' aria-current="page"' if active == "plants" else ""
    return f"""<header class="top">
  <a class="brand" href="/"><svg class="brand-mark" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 22V11M12 11c0-4 3-7 8-7 0 5-3 8-8 7Zm0 3c0-3-2.5-5.5-7-5.5 0 4 2.5 6 7 5.5Z"/></svg><span>genes</span></a>
  <nav class="nav" aria-label="Sections">
    <a href="/#plants"{plants}>Plants</a>
    <span class="soon" title="Coming later">Animals</span>
    <a href="/#about">About</a>
  </nav>
  <div class="account" data-account-slot></div>
</header>"""


FOOTER = """<footer class="foot">
  <p><strong>genes</strong> is the catalog of living things of <a href="https://pietri.dev">pietri.dev</a>'s world over Unquillo, Córdoba. Facts carry their sources; models are made by a procedural generator to resemble the real species.</p>
  <p>Sheets and looks: CC BY 4.0 · code: MIT · photos keep their own licence. <a href="/v1/catalog.json">Data (JSON)</a> · <a href="/llms.txt">llms.txt</a> · <a href="/sitemap.xml">Sitemap</a> · <a href="https://github.com/0xpietri/genes">Source</a></p>
</footer>"""


# ---------------------------------------------------------------- species data


def lifecycle_of(sp: Species) -> tuple[Path, dict[str, Any]] | None:
    folder = sp.folder / "lifecycle"
    files = sorted(folder.glob("*.json"), key=lambda p: int(p.stem)) if folder.is_dir() else []
    return (files[-1], jsonio.load(files[-1])) if files else None


def media_of(sp: Species) -> Path | None:
    for name in ("card.webp", "card.png"):
        p = sp.folder / "media" / name
        if p.exists():
            return p
    return None


def stage_art_of(sp: Species) -> dict[str, tuple[str, int, int]]:
    """Painted pictures of the tree at each stage: stage -> (URL, width, height)."""
    p = sp.folder / "media" / "stages" / "sizes.json"
    if not p.exists():
        return {}
    sizes = jsonio.load(p)["sizes"]
    return {
        k: (f"/v1/species/{sp.id}/media/stages/{k}.webp", int(w), int(h))
        for k, (w, h) in sorted(sizes.items())
        if (p.parent / f"{k}.webp").exists()
    }


def occurrences_of(sp: Species) -> dict[str, Any] | None:
    p = sp.folder / "occurrences.json"
    return jsonio.load(p) if p.exists() else None


def place_points(refs: dict[str, Any] | None, basemap: dict[str, Any]) -> list[dict[str, Any]]:
    """Reference photos placed at the centre of the province their place names."""
    if not refs:
        return []
    provinces = basemap["provinces"]
    by_place: dict[tuple[str, str], dict[str, Any]] = {}
    for photo in refs.get("photos", []):
        tokens = [t.strip() for t in str(photo.get("place", "")).split(",")]
        country = COUNTRY_CODES.get(tokens[-1]) if tokens else None
        names = [PLACE_CODES.get(t, t) for t in tokens]
        match = None
        for name in names:
            match = next(
                (
                    p
                    for p in provinces
                    if p["name"] == name and (country is None or p["country"] == country)
                ),
                None,
            )
            if match:
                break
        if match is None:
            continue
        key = (match["country"], match["name"])
        pt = by_place.setdefault(
            key,
            {
                "name": match["name"],
                "lon": match["centre"][0],
                "lat": match["centre"][1],
                "photos": [],
            },
        )
        pt["photos"].append(photo["id"])
    return sorted(by_place.values(), key=lambda p: p["name"])


# ---------------------------------------------------------------- infographics (inline SVG)


def phenology_wheel(sheet: dict[str, Any], palette: dict[str, Any]) -> str:
    ph = dig(sheet, "plant", "phenology") or {}
    cx = cy = 160
    foliage = palette.get("foliage", {})
    tone_colour = {k: v.get("lit") for k, v in foliage.items() if isinstance(v, dict)}

    def arc(
        r0: float,
        r1: float,
        m: int,
        fill: str,
        cls: str,
        title: str,
        share: tuple[float, float] = (0, 1),
    ) -> str:
        a0 = (m - 1 + share[0]) / 12 * 2 * math.pi - math.pi / 2
        a1 = (m - 1 + share[1]) / 12 * 2 * math.pi - math.pi / 2
        gap = 0.012
        a0 += gap
        a1 -= gap
        p = [
            (cx + r * math.cos(a), cy + r * math.sin(a))
            for r, a in ((r1, a0), (r1, a1), (r0, a1), (r0, a0))
        ]
        large = 1 if a1 - a0 > math.pi else 0
        d = (
            f"M{p[0][0]:.1f} {p[0][1]:.1f}A{r1} {r1} 0 {large} 1 {p[1][0]:.1f} {p[1][1]:.1f}"
            f"L{p[2][0]:.1f} {p[2][1]:.1f}A{r0} {r0} 0 {large} 0 {p[3][0]:.1f} {p[3][1]:.1f}Z"
        )
        return f'<path class="{cls}" d="{d}" fill="{e(fill)}"><title>{e(title)}</title></path>'

    out = []
    # Leaves: tones by month (two tones share a month: split the cell).
    tones = ph.get("leaf_tones") or []
    for m in range(1, 13):
        here = [t for t in tones if m in t.get("months", [])]
        if not here:
            out.append(arc(118, 146, m, "#2a3335", "ring-empty", f"{MONTHS[m - 1]}: no leaves"))
        for i, t in enumerate(here):
            share = (i / len(here), (i + 1) / len(here))
            out.append(
                arc(
                    118,
                    146,
                    m,
                    tone_colour.get(t["tone"]) or "#8fa155",
                    "ring",
                    f"{MONTHS[m - 1]}: {t['tone']} leaves",
                    share,
                )
            )
    for key, r0, r1, colour, label in (
        ("flowering", 92, 112, dig(palette, "flowers", "lit") or "#e6dc8a", "flowers"),
        ("fruiting", 66, 86, dig(palette, "fruit", "accent") or "#c79a4a", "pods"),
        ("leaf_fall", 40, 60, dig(palette, "foliage", "dry", "lit") or "#b9a35c", "leaf fall"),
    ):
        months = dig(ph, key, "months") or []
        for m in range(1, 13):
            on = m in months
            out.append(
                arc(
                    r0,
                    r1,
                    m,
                    colour if on else "#232c2e",
                    "ring" if on else "ring-empty",
                    f"{MONTHS[m - 1]}: {label if on else 'no ' + label}",
                )
            )
    labels = []
    for m in range(1, 13):
        a = (m - 0.5) / 12 * 2 * math.pi - math.pi / 2
        x, y = cx + 156 * math.cos(a), cy + 156 * math.sin(a)
        labels.append(
            f'<text x="{x:.1f}" y="{y:.1f}" class="wheel-month">{MONTH_LETTERS[m - 1]}</text>'
        )
    return (
        '<svg class="wheel" viewBox="-8 -8 336 336" role="img" '
        'aria-labelledby="wheel-title"><title id="wheel-title">The year of the tree: leaves, '
        "flowers, pods and leaf fall by month</title>"
        + "".join(out)
        + "".join(labels)
        + f'<g class="wheel-needle" data-wheel-needle transform="rotate(0 {cx} {cy})">'
        f'<line x1="{cx}" y1="{cy - 36}" x2="{cx}" y2="{cy - 152}"/><circle cx="{cx}" cy="{cy - 152}" r="4"/></g>'
        f'<text x="{cx}" y="{cy + 5}" class="wheel-centre" data-wheel-month></text>'
        "</svg>"
    )


def life_chart(life: dict[str, Any] | None) -> str:
    if not life:
        return ""
    s = life["samples"]
    n = len(s["date"])
    end_years = s["age_days"][-1] / 365.25
    top = max(s["h_mm"]) / 1000
    W, H, L, B, T = 1000, 250, 44, 216, 12
    sx = (W - L - 12) / end_years
    sy = (B - T) / (math.ceil(top) or 1)
    statuses = life["statuses"]
    step = max(1, n // 400)
    pts = [
        f"{L + s['age_days'][i] / 365.25 * sx:.1f} {B - s['h_mm'][i] / 1000 * sy:.1f}"
        for i in range(0, n, step)
    ] + [f"{L + s['age_days'][-1] / 365.25 * sx:.1f} {B - s['h_mm'][-1] / 1000 * sy:.1f}"]
    bands = []
    prev = 0
    for i in range(1, n + 1):
        if (
            i == n
            or (s["status"][i] >= 3 and s["status"][prev] < 3)
            or (s["status"][i] == 4 and s["status"][prev] == 3)
        ):
            kind = statuses[s["status"][prev]]
            cls = {"standing_dead": "band-dead", "fallen": "band-fallen"}.get(kind, "band-alive")
            x0 = L + s["age_days"][prev] / 365.25 * sx
            x1 = L + s["age_days"][i - 1] / 365.25 * sx
            bands.append(
                f'<rect class="{cls}" x="{x0:.1f}" y="{T}" width="{max(1, x1 - x0):.1f}" '
                f'height="{B - T}"/>'
            )
            prev = i
    ticks = []
    for y in range(0, int(end_years) + 1, 50):
        x = L + y * sx
        ticks.append(
            f'<line class="gl" x1="{x:.1f}" x2="{x:.1f}" y1="{T}" y2="{B}"/>'
            f'<text class="axis axis-x" x="{x:.1f}" y="{B + 18}">{y} y</text>'
        )
    for m in range(0, math.ceil(top) + 1, 2):
        ym = B - m * sy
        ticks.append(f'<text class="axis" x="{L - 6}" y="{ym + 4:.1f}">{m} m</text>')
    area = f"M{L} {B}L" + "L".join(pts) + f"L{pts[-1].split()[0]} {B}Z"
    return (
        f'<svg class="lifechart" viewBox="0 0 {W} {H}" role="img" data-lifechart '
        f'data-x0="{L}" data-sx="{sx:.5f}" data-y0="{B}" data-sy="{sy:.5f}" '
        f'aria-label="Height over the life of one simulated tree">'
        + '<defs><linearGradient id="lc-area" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#9fdc8f" stop-opacity=".55"/>'
        '<stop offset="1" stop-color="#9fdc8f" stop-opacity="0"/></linearGradient></defs>'
        + "".join(bands)
        + "".join(ticks)
        + f'<path class="lifearea" d="{area}"/>'
        + f'<polyline class="lifeline" points="{" ".join(pts)}"/>'
        + f'<line class="life-cursor" data-life-cursor x1="{L}" x2="{L}" y1="{T}" y2="{B}"/>'
        + f'<circle class="life-dot" data-life-dot cx="{L}" cy="{B}" r="5"/></svg>'
    )


def stage_spans(life: dict[str, Any]) -> list[tuple[str, int, float, float]]:
    """The stages one recorded life goes through: (stage, first sample, from year, to year).

    The same rule as `life.js` stageAt (spec §6.2), so the strip and the 3D model agree.
    """
    s = life["samples"]
    ind = life["individual"]
    own = ind["max_height_mm"] / 1000
    spans: list[tuple[str, int, float, float]] = []
    for i in range(len(s["date"])):
        status = life["statuses"][s["status"][i]]
        h = s["h_mm"][i] / 1000
        age = s["age_days"][i] / 365.25
        if status == "fallen":
            st = "fallen"
        elif status == "standing_dead":
            st = "dead_standing"
        elif h < 0.5:
            st = "seedling"
        elif h < 2:
            st = "sapling"
        elif h < 0.6 * own:
            st = "young"
        elif age >= 0.7 * ind["max_age_years"]:
            st = "old"
        else:
            st = "adult"
        if not spans or spans[-1][0] != st:
            if st in {x[0] for x in spans}:
                continue  # a stage seen before (a dip in height): keep the first span
            spans.append((st, i, age, age))
        else:
            spans[-1] = (st, spans[-1][1], spans[-1][2], age)
    return spans


def stage_strip(life: dict[str, Any] | None, art: dict[str, tuple[str, int, int]]) -> str:
    if not life:
        return ""
    items = []
    for st, i, y0, y1 in stage_spans(life):
        pic = art.get(st)
        img = (
            f'<img src="{e(pic[0])}" alt="" width="{pic[1]}" height="{pic[2]}" loading="lazy" decoding="async">'
            if pic
            else ""
        )
        items.append(
            f'<li><button type="button" data-jump="{i}" data-stage-pic="{e(st)}">'
            f'<span class="pic">{img}</span><strong>{e(STAGE_LABEL.get(st, st))}</strong>'
            f"<small>years {math.floor(y0)}–{math.ceil(y1)}</small></button></li>"
        )
    return (
        '<ol class="life-stages" aria-label="Its stages: jump to one">' + "".join(items) + "</ol>"
    )


def gives_tiles(sheet: dict[str, Any]) -> str:
    tiles = []
    for g in dig(sheet, "plant", "gives") or []:
        what = g["what"]
        months = g.get("months")
        cells = ""
        if months:
            cells = (
                '<div class="mini-year" aria-hidden="true">'
                + "".join(
                    f'<span class="{"on" if m in months else ""}">{MONTH_LETTERS[m - 1]}</span>'
                    for m in range(1, 13)
                )
                + "</div>"
            )
        to = ", ".join(g.get("to", []))
        when = months_text(months)
        tiles.append(
            f'<li class="give">{art.icon(what, "ico give-ico")}'
            f"<div><strong>{e(GIVES_LABEL.get(what, what.replace('_', ' ').capitalize()))}</strong>"
            f"{f'<span> to {e(to)}</span>' if to else ''}"
            f"{f'<small>{e(when)}</small>' if when else ''}{cells}"
            f'<small class="src">[{e(", ".join(g.get("source", [])))}]</small></div></li>'
        )
    return '<ul class="gives">' + "".join(tiles) + "</ul>" if tiles else ""


# ---------------------------------------------------------------- pages


def species_ld(sheet: dict[str, Any], path: str, image: str | None) -> list[dict[str, Any]]:
    names = sheet["names"]
    taxon: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Taxon",
        "name": sheet["scientific_name"],
        "taxonRank": "species",
        "alternateName": [*names.get("es", []), *names.get("en", []), *sheet.get("synonyms", [])],
        "description": dig(sheet, "summary", "en"),
        "url": BASE_URL + path,
        "parentTaxon": {"@type": "Taxon", "name": sheet.get("family"), "taxonRank": "family"},
        "sameAs": [
            s
            for s in (
                f"https://www.gbif.org/species/{dig(sheet, 'external', 'gbif')}"
                if dig(sheet, "external", "gbif")
                else None,
                f"https://www.inaturalist.org/taxa/{dig(sheet, 'external', 'inaturalist')}"
                if dig(sheet, "external", "inaturalist")
                else None,
            )
            if s
        ],
    }
    if image:
        taxon["image"] = BASE_URL + image
    crumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "genes", "item": BASE_URL + "/"},
            {
                "@type": "ListItem",
                "position": 2,
                "name": names["es"][0].capitalize(),
                "item": BASE_URL + path,
            },
        ],
    }
    return [taxon, crumbs]


def stat_tiles(sheet: dict[str, Any], life: dict[str, Any] | None) -> str:
    size = dig(sheet, "plant", "size") or {}
    items = [
        ("Height", size.get("adult_height_m"), "m", "height"),
        ("Crown", size.get("crown_width_m"), "m", "crown"),
        ("Trunk", size.get("trunk_dbh_m"), "m", "trunk"),
        ("Wood", dig(sheet, "plant", "wood", "density_kg_m3"), "kg/m³", "wood"),
        ("Frost", dig(sheet, "plant", "climate", "frost_kill_c_adult"), "°C", "frost"),
        ("Rain", dig(sheet, "plant", "water", "rainfall_mm_year"), "mm/yr", "rain"),
    ]
    out = []
    for label, r, unit, ico in items:
        if not r:
            continue
        typ = (
            f"<small>usually {fmt_num(r['typical']).replace('-', '−')} {e(unit)}</small>"
            if "typical" in r
            else ""
        )
        out.append(
            f'<div class="tile">{art.icon(ico, "ico tile-ico")}<span class="tile-k">{e(label)}</span>'
            f'<span class="tile-v">{e(fmt_range(r))}<em>{e(unit)}</em></span>{typ}'
            f'<small class="src">[{e(", ".join(r.get("source", [])))}]</small></div>'
        )
    if life:
        dead = next((c for c in life["changes"] if c["to"] == "standing_dead"), None)
        if dead:
            years = int(dead["date"][:4]) - int(life["born"][:4])
            out.append(
                f'<div class="tile tile-sim">{art.icon("life", "ico tile-ico")}<span class="tile-k">Simulated life</span>'
                f'<span class="tile-v">{years}<em>years</em></span>'
                f"<small>one tree in pietri.dev's simulator</small></div>"
            )
    return '<div class="tiles">' + "".join(out) + "</div>"


def facts_table(sheet: dict[str, Any]) -> str:
    rows: list[tuple[str, str, list[str], str]] = []
    p = sheet.get("plant", {})
    for path, label, unit in (
        (("size", "adult_height_m"), "Adult height", "m"),
        (("size", "crown_width_m"), "Crown width", "m"),
        (("size", "trunk_dbh_m"), "Trunk diameter (breast height)", "m"),
        (("size", "trunks"), "Trunks", ""),
        (("water", "rainfall_mm_year"), "Rainfall it lives with", "mm a year"),
        (("water", "drought_tolerance"), "Drought tolerance", ""),
        (("light", "shade_tolerance_seedling"), "Shade tolerance, seedling", ""),
        (("light", "shade_tolerance_adult"), "Shade tolerance, adult", ""),
        (("climate", "frost_kill_c_adult"), "Frost that kills an adult", "°C"),
        (("wood", "density_kg_m3"), "Wood density", "kg/m³"),
    ):
        r = dig(p, *path)
        if isinstance(r, dict):
            rows.append((label, fmt_range(r, unit), r.get("source", []), r.get("note", "")))
    ph = p.get("phenology", {})
    if ph.get("leaf_habit"):
        rows.append(
            (
                "Leaves",
                f"{HABIT_LABEL.get(ph['leaf_habit'], ph['leaf_habit'])}, {ph.get('leaf_type', '')}",
                [],
                "",
            )
        )
    for key, label in (
        ("leaf_out", "New leaves"),
        ("flowering", "Flowers"),
        ("fruiting", "Pods"),
        ("leaf_fall", "Leaf fall"),
    ):
        r = ph.get(key)
        if r:
            trig = f" (after the {r['trigger'].replace('_', ' ')})" if r.get("trigger") else ""
            rows.append(
                (label, months_text(r["months"]) + trig, r.get("source", []), r.get("note", ""))
            )
    if ph.get("spread_days"):
        r = ph["spread_days"]
        rows.append(
            ("Trees differ by", fmt_range(r, "days"), r.get("source", []), r.get("note", ""))
        )
    if dig(p, "reproduction", "fruit"):
        rows.append(("Fruit", p["reproduction"]["fruit"], [], ""))
    body = "".join(
        f'<tr><th scope="row">{e(k)}</th><td>{e(v)}'
        f"{f'<p class=note>{e(note)}</p>' if note else ''}</td>"
        f'<td class="src">{e(", ".join(src))}</td></tr>'
        for k, v, src, note in rows
    )
    return (
        '<table class="facts"><thead><tr><th>Fact</th><th>Value</th><th>Sources</th></tr>'
        f"</thead><tbody>{body}</tbody></table>"
    )


def species_page(
    sp: Species, entry: dict[str, Any], catalog_no: int, basemap: dict[str, Any]
) -> tuple[str, str]:
    sheet = sp.latest_sheet.data if sp.latest_sheet else {}
    look = sp.latest_look.data if sp.latest_look else None
    refs = sp.refs.data if sp.refs else None
    life_pair = lifecycle_of(sp)
    life = life_pair[1] if life_pair else None
    occ = occurrences_of(sp)
    palette = (look or {}).get("palette", {})
    path = f"/species/{sp.id}/"
    es = sheet["names"]["es"]
    en = sheet["names"].get("en", [])
    title = f"{es[0].capitalize()} ({sheet['scientific_name']}) · genes"
    desc = dig(sheet, "summary", "en") or ""
    image = entry.get("media", {}).get("path")
    places = place_points(refs, basemap)
    points = {
        "places": places,
        "cells": occ["cells"] if occ else [],
        "world": WORLD_PLACE,
    }
    ph = dig(sheet, "plant", "phenology") or {}
    badges = [STATUS_LABEL.get(sheet.get("status_in_sierras_chicas", ""), "")]
    if ph.get("leaf_habit"):
        badges.append(HABIT_LABEL.get(ph["leaf_habit"], ""))
    badges.append(sheet.get("plant", {}).get("growth_form", "").capitalize())
    if sheet.get("conservation"):
        badges.append(sheet["conservation"].split(" (")[0])
    badges_html = "".join(f"<li>{e(b)}</li>" for b in badges if b)

    look_v = sp.latest_look.number if sp.latest_look else None
    data_attrs = {
        "data-species": sp.id,
        "data-sheet": entry["sheets"][-1]["path"],
        "data-look": entry["looks"][-1]["path"] if entry["looks"] else "",
        "data-models": f"/v1/species/{sp.id}/looks/{look_v}/" if look_v else "",
        "data-lifecycle": entry.get("lifecycle", {}).get("path", ""),
    }
    attrs = " ".join(f'{k}="{e(v)}"' for k, v in data_attrs.items())

    stages = sorted(
        (look or {}).get("stages", {}),
        key=lambda s: list(STAGE_LABEL).index(s) if s in STAGE_LABEL else 99,
    )
    recognisable = "".join(
        f"<li>{e(r['trait'])}</li>" for r in (look or {}).get("recognisable", [])
    )
    uses = dig(sheet, "plant", "people", "uses") or []
    uses_src = ", ".join(dig(sheet, "plant", "people", "source") or [])
    photos = "".join(
        f'<figure class="photo"><a href="{e(p["url"])}" rel="noopener" target="_blank">'
        f'<img src="/v1/species/{e(sp.id)}/references/{e(p["file"])}" loading="lazy" decoding="async" '
        f'alt="{e(es[0])}: {e(", ".join(p["shows"]))}, {e(p["place"])}" width="320" height="240"></a>'
        f"<figcaption>{e(', '.join(p['shows']))} · {e(p['place'])}<br><small>{e(p['author'])}</small></figcaption></figure>"
        for p in (refs or {}).get("photos", [])
        if p.get("file")
    )
    sources = "".join(
        f'<li id="src-{e(s["id"])}"><span class="src-id">{e(s["id"])}</span> '
        + (
            f'<a href="{e(s["url"])}" rel="noopener" target="_blank">{e(s["title"])}</a>'
            if s.get("url")
            else e(s["title"])
        )
        + f" <small>accessed {e(s.get('accessed', ''))}</small></li>"
        for s in sheet.get("sources", [])
    )
    occ_note = (
        f"Each little tree marks a half-degree area with GBIF sightings: {occ['total']:,} "
        f"in {len(occ['cells'])} areas (accessed {occ['source']['accessed']})."
        if occ
        else "For now each little tree marks a province where a reference photo was taken; "
        "the GBIF sightings layer replaces them once `genes occurrences` has been run."
    )
    dead = next((c for c in (life or {}).get("changes", []) if c["to"] == "standing_dead"), None)
    life_text = ""
    if life:
        ind = life["individual"]
        life_text = (
            f'<p>One algarrobo grown alone by <a href="https://pietri.dev">pietri.dev</a>\'s '
            f"simulator, day by day with Unquillo's real weather since {life['born'][:4]}: its "
            f"own limit is {ind['max_height_mm'] / 1000:.1f} m. "
            + (
                f"It dies of {e(dead['cause'])} in {dead['date'][:4]}, "
                f"{int(dead['date'][:4]) - int(life['born'][:4])} years old, stands dead and then "
                f"falls and rots until {life['end']['date'][:4]}. "
                if dead
                else ""
            )
            + "Every page shows the same tree.</p>"
        )

    size = dig(sheet, "plant", "size") or {}
    stage_art = stage_art_of(sp)
    size_pills = "".join(
        f'<span class="pill">{art.icon(ico, "ico ico-sm")}<span>{label}</span>'
        f"<strong>{e(fmt_range(r, 'm'))}</strong>"
        + (f"<small>usually {fmt_num(r['typical'])} m</small>" if "typical" in r else "")
        + "</span>"
        for label, r, ico in (
            ("Height", size.get("adult_height_m"), "height"),
            ("Crown width", size.get("crown_width_m"), "crown"),
            ("Trunk", size.get("trunk_dbh_m"), "trunk"),
        )
        if isinstance(r, dict) and "min" in r
    )
    life_kpis = ""
    if life:
        ind = life["individual"]
        kpis = [
            (f"{ind['max_height_mm'] / 1000:.1f} m", "its tallest", "height"),
        ]
        if dead:
            kpis.insert(
                0, (f"{int(dead['date'][:4]) - int(life['born'][:4])} years", "lived", "life")
            )
            cause = {"age": "Old age"}.get(dead["cause"], str(dead["cause"]).capitalize())
            kpis.append((e(cause), "is what it dies of", "leaf"))
        kpis.append((life["end"]["date"][:4], "gone into the soil", "trunk"))
        life_kpis = (
            '<div class="kpis">'
            + "".join(
                f'<div class="kpi">{art.icon(ico, "ico kpi-ico")}<strong>{v}</strong><span>{k}</span></div>'
                for v, k, ico in kpis
            )
            + "</div>"
        )

    sim = ""
    if look and life:
        stage_opts = "".join(
            f'<li data-stage-chip="{e(s)}">{e(STAGE_LABEL.get(s, s))}</li>' for s in stages
        )
        sim = f"""
      <div class="sim" data-sim>
        <div class="sim-row">
          <button type="button" class="play" data-play aria-label="Play the tree's life"><svg viewBox="0 0 24 24" aria-hidden="true"><path class="i-play" d="M8 5v14l11-7z"/><path class="i-pause" d="M7 5h4v14H7zM13 5h4v14h-4z"/></svg></button>
          <label class="age"><span class="sr">Age</span><input type="range" min="0" max="{len(life["samples"]["date"]) - 1}" value="0" step="1" data-age></label>
          <div class="speed" role="group" aria-label="Speed"><button type="button" data-speed="1">1×</button><button type="button" data-speed="4" aria-pressed="true">4×</button><button type="button" data-speed="16">16×</button></div>
        </div>
        <div class="sim-row">
          <output class="readout" data-readout>Year 0</output>
          <div class="seasons" role="group" aria-label="Season">
            <button type="button" data-season="1">Summer</button><button type="button" data-season="4">Autumn</button><button type="button" data-season="7">Winter</button><button type="button" data-season="10">Spring</button>
          </div>
        </div>
        <ol class="stages" aria-label="Stages">{stage_opts}</ol>
      </div>"""

    html = f"""{
        head(
            title,
            desc,
            path,
            image=image,
            ld=species_ld(sheet, path, image),
            preload=["/static/vendor/three/three.module.js", "/static/vendor/three/three.core.js"],
            scripts=["/static/site/js/species.js"],
        )
    }
<body class="page-species" {attrs}>
{header("plants")}
<main>
  <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Catalog</a> <span>/</span> <span>{
        e(es[0].capitalize())
    }</span></nav>
  <section class="hero">
    <div class="stage" data-stage>
      <div class="stage-sky" aria-hidden="true"></div>
      <canvas class="stage-canvas" data-canvas aria-label="3D model of the {
        e(es[0])
    }: drag to turn, scroll or pinch to zoom"></canvas>
      <noscript><p class="stage-note">The 3D model needs JavaScript.</p></noscript>
      <div class="stage-loading" data-loading>Growing the tree…</div>
      <div class="stage-tools">
        <button type="button" class="daynight" data-daynight aria-pressed="false" title="Day or night"><svg viewBox="0 0 24 24" aria-hidden="true"><circle class="i-sun" cx="12" cy="12" r="4"/><path class="i-sun" d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/><path class="i-moon" d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/></svg><span data-daynight-label>Night</span></button>
        <button type="button" class="tool" data-recentre title="Back to the whole tree"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg></button>
      </div>
      {sim}
    </div>
    <div class="intro">
      <p class="kicker">{e(sheet.get("family", ""))} · {
        e(sheet.get("plant", {}).get("growth_form", ""))
    }</p>
      <h1>{e(es[0].capitalize())}</h1>
      <p class="sci"><i>{e(sheet["scientific_name"])}</i>{
        (" · " + e(", ".join(sheet.get("synonyms", [])))) if sheet.get("synonyms") else ""
    }</p>
      <p class="aka">{e(", ".join([*es[1:], *en]))}</p>
      <ul class="badges">{badges_html}</ul>
      <p class="summary" lang="es">{e(dig(sheet, "summary", "es"))}</p>
      <p class="summary en">{e(desc)}</p>
      {stat_tiles(sheet, life)}
    </div>
  </section>

  <section class="panel span-2" id="life">
    <header>{
        art.icon("life", "ico head-ico")
    }<div><h2>Its life</h2><p>Age, height and death of one tree, simulated once and replayed.</p></div></header>
    {life_kpis}
    {life_text}
    {stage_strip(life, stage_art)}
    {life_chart(life)}
    <ul class="legend"><li><i class="sw alive"></i>Alive</li><li><i class="sw dead"></i>Dead, standing</li><li><i class="sw fallen"></i>Fallen, rotting</li></ul>
  </section>

  <div class="grid grid-wide">
    <section class="panel" id="size">
      <header>{
        art.icon("height", "ico head-ico")
    }<div><h2>How big</h2><p>Adult trees to scale, next to a person.</p></div></header>
      {art.height_scene(size, image, stage_art)}
      <div class="pills">{size_pills}</div>
    </section>
    <section class="panel" id="wood">
      <header>{
        art.icon("wood", "ico head-ico")
    }<div><h2>Wood and trunk</h2><p>How heavy the wood is, and how thick the trunk grows.</p></div></header>
      {art.wood_gauge(dig(sheet, "plant", "wood", "density_kg_m3"))}
      {art.trunk_rings(size.get("trunk_dbh_m"))}
    </section>
  </div>

  <div class="grid">
    <section class="panel" id="climate">
      <header>{
        art.icon("rain", "ico head-ico")
    }<div><h2>Water and cold</h2><p>The ranges the sources give.</p></div></header>
      <div class="tubes">
        <figure><figcaption>{art.icon("gauge", "ico ico-sm")}Rain it lives with</figcaption>{
        art.rain_tube(dig(sheet, "plant", "water", "rainfall_mm_year"))
    }</figure>
        <figure><figcaption>{
        art.icon("thermometer", "ico ico-sm")
    }Frost that kills an adult</figcaption>{
        art.thermometer(dig(sheet, "plant", "climate", "frost_kill_c_adult"))
    }</figure>
      </div>
      <div class="levels">
        {
        art.level_meter(
            "Drought tolerance", dig(sheet, "plant", "water", "drought_tolerance"), "drought"
        )
    }
        {
        art.level_meter(
            "Shade, seedling",
            dig(sheet, "plant", "light", "shade_tolerance_seedling"),
            "shade_need",
        )
    }
        {
        art.level_meter(
            "Shade, adult", dig(sheet, "plant", "light", "shade_tolerance_adult"), "shade_need"
        )
    }
      </div>
    </section>
    <section class="panel" id="year">
      <header>{
        art.icon("year", "ico head-ico")
    }<div><h2>The year</h2><p>In the Sierras Chicas of Córdoba (southern hemisphere).</p></div></header>
      {phenology_wheel(sheet, palette)}
      <ul class="legend"><li><i class="sw leaves"></i>Leaves (outer ring: new, mature, dry)</li><li><i class="sw flowers"></i>Flowers</li><li><i class="sw pods"></i>Pods</li><li><i class="sw fall"></i>Leaf fall</li></ul>
    </section>
  </div>

  <div class="grid">
    <section class="panel" id="map">
      <header>{art.icon("map", "ico head-ico")}<div><h2>Where it lives</h2><p>{
        e(sheet.get("range_note", ""))
    }</p></div></header>
      <figure class="map" data-map data-basemap="/static/site/geo/basemap.json" data-points="{
        json_attr(points)
    }">
        <div class="map-tools"><button type="button" data-zoom="1" aria-label="Zoom in">+</button><button type="button" data-zoom="-1" aria-label="Zoom out">−</button><button type="button" data-zoom="0" aria-label="Whole range">⤢</button></div>
        <div class="map-canvas" data-map-canvas><p class="map-wait">Loading the map…</p></div>
        <figcaption>{
        e(occ_note)
    } The house is Unquillo, where the pietri.dev world stands. Map: Natural Earth.</figcaption>
      </figure>
    </section>
    <section class="panel" id="leaf">
      <header>{art.icon("leaf", "ico head-ico")}<div><h2>The leaf</h2><p>{
        e(HABIT_LABEL.get(ph.get("leaf_habit", ""), ""))
    }, {
        e(ph.get("leaf_type", ""))
    }: each leaf splits into pinnae lined with small leaflets. Drag to turn it.</p></div></header>
      <div class="leafbox" data-leaf><canvas data-leaf-canvas aria-label="Animated 3D leaf"></canvas></div>
    </section>
  </div>

  <div class="grid">
    <section class="panel" id="gives">
      <header>{
        art.icon("shade", "ico head-ico")
    }<div><h2>What it gives</h2><p>To animals, people and the soil.</p></div></header>
      {gives_tiles(sheet)}
    </section>
    <section class="panel" id="people">
      <header>{
        art.icon("people", "ico head-ico")
    }<div><h2>People and the algarrobo</h2><p>Uses the sources record <small class="src">[{
        e(uses_src)
    }]</small>.</p></div></header>
      <ul class="uses">{"".join(f"<li>{e(u)}</li>" for u in uses)}</ul>
      <h3>How to recognise it</h3>
      <ul class="traits">{recognisable}</ul>
      {f'<p class="note">{e(sheet["names"]["note"])}</p>' if sheet["names"].get("note") else ""}
    </section>
  </div>

  <section class="panel span-2" id="photos">
    <header>{
        art.icon("photo", "ico head-ico")
    }<div><h2>Reference photos</h2><p>Real trees the model was checked against, with where each was taken. Each keeps its author and licence.</p></div></header>
    <div class="photos">{photos}</div>
  </section>

  <section class="panel span-2" id="details">
    <header>{
        art.icon("book", "ico head-ico")
    }<div><h2>Technical details</h2><p>Every number is a sourced range in real units.</p></div></header>
    {facts_table(sheet)}
    <dl class="ids">
      <div><dt>Scientific name</dt><dd><i>{e(sheet["scientific_name"])}</i> {
        e(sheet.get("authority", ""))
    }</dd></div>
      <div><dt>Family</dt><dd>{e(sheet.get("family", ""))}</dd></div>
      <div><dt>GBIF</dt><dd><a href="https://www.gbif.org/species/{
        e(dig(sheet, "external", "gbif"))
    }" rel="noopener">{e(dig(sheet, "external", "gbif"))}</a></dd></div>
      <div><dt>iNaturalist</dt><dd><a href="https://www.inaturalist.org/taxa/{
        e(dig(sheet, "external", "inaturalist"))
    }" rel="noopener">{e(dig(sheet, "external", "inaturalist"))}</a></dd></div>
      <div><dt>Conservation</dt><dd>{e(sheet.get("conservation", "—"))}</dd></div>
      <div><dt>Versions</dt><dd>sheet {sp.latest_sheet.number if sp.latest_sheet else "—"} · look {
        look_v or "—"
    } · catalog {catalog_no}</dd></div>
      <div><dt>3D models</dt><dd>{len(stages)} stages × variants, generator {
        e((look or {}).get("generator", ""))
    }</dd></div>
      <div><dt>Data</dt><dd><a href="{e(entry["sheets"][-1]["path"])}">sheet JSON</a>{
        f' · <a href="{e(entry["looks"][-1]["path"])}">look JSON</a>' if entry["looks"] else ""
    }{
        f' · <a href="{e(entry["lifecycle"]["path"])}">simulated life JSON</a>'
        if entry.get("lifecycle")
        else ""
    } · <a href="/species/{e(sp.id)}/index.md">Markdown</a> · <a href="/review/species/{
        e(sp.id)
    }/">model review</a></dd></div>
    </dl>
    <h3>Sources</h3>
    <ol class="sources">{sources}</ol>
  </section>
</main>
{FOOTER}
</body>
</html>
"""
    return html, species_markdown(sp, sheet, look, life, places, occ)


def species_markdown(
    sp: Species,
    sheet: dict[str, Any],
    look: dict[str, Any] | None,
    life: dict[str, Any] | None,
    places: list[dict[str, Any]],
    occ: dict[str, Any] | None,
) -> str:
    names = sheet["names"]
    lines = [
        f"# {names['es'][0].capitalize()} ({sheet['scientific_name']})",
        "",
        f"> {dig(sheet, 'summary', 'en')}",
        "",
        f"- Spanish names: {', '.join(names['es'])}",
        f"- English names: {', '.join(names.get('en', []))}",
        f"- Synonyms: {', '.join(sheet.get('synonyms', [])) or '—'}",
        f"- Family: {sheet.get('family', '')}",
        f"- Status in the Sierras Chicas (Córdoba, Argentina): {sheet.get('status_in_sierras_chicas', '')}",
        f"- Conservation: {sheet.get('conservation', '—')}",
        f"- Range: {sheet.get('range_note', '')}",
        f"- Page: {BASE_URL}/species/{sp.id}/",
        "",
        "## Resumen (es)",
        "",
        dig(sheet, "summary", "es") or "",
        "",
        "## Facts",
        "",
        "Ranges are min–max as the sources give them; sources by id at the end.",
        "",
    ]
    p = sheet.get("plant", {})

    def walk(obj: Any, prefix: str) -> None:
        if not isinstance(obj, dict):
            return
        if "source" in obj and ("min" in obj or "value" in obj or "months" in obj):
            if "months" in obj:
                val = months_text(obj["months"])
                if obj.get("trigger"):
                    val += f" (trigger: {obj['trigger']})"
            else:
                val = fmt_range(obj)
                if "typical" in obj:
                    val += f", usually {fmt_num(obj['typical'])}"
            note = f" {obj['note']}" if obj.get("note") else ""
            lines.append(f"- {prefix}: {val} [{', '.join(obj['source'])}].{note}")
            return
        for k, v in obj.items():
            if k in ("leaf_tones", "gives", "people"):
                continue
            walk(v, f"{prefix}.{k}" if prefix else k)

    walk(p, "")
    for t in dig(p, "phenology", "leaf_tones") or []:
        lines.append(
            f"- leaf tone {t['tone']}: {months_text(t['months'])} [{', '.join(t['source'])}]"
        )
    for g in p.get("gives", []):
        when = f" in {months_text(g['months'])}" if g.get("months") else ""
        to = f" to {', '.join(g['to'])}" if g.get("to") else ""
        lines.append(
            f"- gives {g['what'].replace('_', ' ')}{to}{when} [{', '.join(g.get('source', []))}]"
        )
    if dig(p, "people", "uses"):
        lines += ["", "## Uses", ""] + [f"- {u}" for u in p["people"]["uses"]]
    if look:
        lines += ["", "## How to recognise it", ""] + [
            f"- {r['trait']}" for r in look.get("recognisable", [])
        ]
    if life:
        s = life["samples"]
        dead = next((c for c in life["changes"] if c["to"] == "standing_dead"), None)
        lines += [
            "",
            "## One simulated life",
            "",
            f"pietri.dev's simulator grew one tree alone with Unquillo's weather from {life['born']}"
            f" (own maximum height {life['individual']['max_height_mm'] / 1000:.1f} m).",
        ]
        for y in (5, 20, 50, 100):
            i = min(range(len(s["age_days"])), key=lambda k: abs(s["age_days"][k] - y * 365.25))
            lines.append(
                f"- at {y} years: {s['h_mm'][i] / 1000:.1f} m tall, crown {2 * s['crown_radius_mm'][i] / 1000:.1f} m wide"
            )
        if dead:
            lines.append(
                f"- died of {dead['cause']} on {dead['date']}; gone by {life['end']['date']}"
            )
    if places or occ:
        lines += ["", "## Where", ""]
        lines += [f"- reference photos from {pl['name']} ({len(pl['photos'])})" for pl in places]
        if occ:
            lines.append(
                f"- {occ['total']} GBIF sightings in {len(occ['cells'])} half-degree cells"
            )
    lines += ["", "## Sources", ""]
    lines += [
        f"- {s['id']}: {s['title']}. {s.get('url', '')} (accessed {s.get('accessed', '')})"
        for s in sheet.get("sources", [])
    ]
    lines += ["", "Licence: CC BY 4.0, genes (pietri.dev).", ""]
    return "\n".join(lines)


def index_page(species: list[Species], entries: list[dict[str, Any]], catalog_no: int) -> str:
    by_id = {e_["id"]: e_ for e_ in entries}
    cards = []
    for i, sp in enumerate(species):
        if sp.id.startswith("example-"):
            continue
        sheet = sp.latest_sheet.data if sp.latest_sheet else {}
        entry = by_id[sp.id]
        es = sheet["names"]["es"][0].capitalize()
        h = dig(sheet, "plant", "size", "adult_height_m")
        habit = HABIT_LABEL.get(dig(sheet, "plant", "phenology", "leaf_habit") or "", "")
        img = entry.get("media", {}).get("path")
        picture = (
            f'<img class="card-img" src="{e(img)}" alt="{e(es)}, cut out" width="480" '
            f'height="600" {"fetchpriority=high" if i == 0 else "loading=lazy"} decoding="async">'
            if img
            else '<div class="card-img placeholder" aria-hidden="true"></div>'
        )
        cards.append(f"""<li class="card" data-card>
  <a href="/species/{e(sp.id)}/" class="card-link">
    <div class="card-art">{picture}<span class="pedestal" aria-hidden="true"></span></div>
    <div class="card-text">
      <span class="card-kicker">{e(STATUS_LABEL.get(sheet.get("status_in_sierras_chicas", ""), "").split(" to ")[0])} · {e(sheet.get("plant", {}).get("growth_form", ""))}</span>
      <h2>{e(es)}</h2>
      <p class="card-sci"><i>{e(sheet["scientific_name"])}</i></p>
      <p class="card-meta">{e(fmt_range(h, "m")) if h else ""}{" · " + e(habit) if habit else ""}</p>
    </div>
    <span class="card-go" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg></span>
  </a>
</li>""")
    cards.append("""<li class="card card-soon" aria-label="More species coming">
  <div class="card-art"><div class="card-img placeholder soon-mark" aria-hidden="true"></div><span class="pedestal" aria-hidden="true"></span></div>
  <div class="card-text"><span class="card-kicker">Coming</span><h2>More species</h2><p class="card-sci">Trees, grasses and later animals of the Chaco Serrano, one by one.</p></div>
</li>""")
    n = len([s for s in species if not s.id.startswith("example-")])
    ld: list[dict[str, Any]] = [
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "genes",
            "url": BASE_URL + "/",
            "description": "Catalog of the living things of the pietri.dev world: real biology with "
            "sources and 3D models.",
        },
        {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": k + 1,
                    "url": f"{BASE_URL}/species/{sp.id}/",
                    "name": sp.latest_sheet.data["scientific_name"] if sp.latest_sheet else sp.id,
                }
                for k, sp in enumerate(s for s in species if not s.id.startswith("example-"))
            ],
        },
    ]
    desc = (
        "Species of the pietri.dev world over Unquillo, Córdoba: real biology with sources, "
        "rotatable 3D trees, their simulated life and where they grow."
    )
    return f"""{head("genes · species of the pietri.dev world", desc, "/", ld=ld, scripts=["/static/site/js/catalog.js"])}
<body class="page-index">
{header("plants")}
<main>
  <section class="lead">
    <p class="kicker">Catalog · {n} species · release {catalog_no}</p>
    <h1>Living things of the pietri.dev world</h1>
    <p>Trees, grasses and, later, animals of the Chaco Serrano around Unquillo, Córdoba. Each one with its facts and sources, a 3D model to turn and zoom, its year and one whole simulated life.</p>
  </section>
  <div class="filters" role="group" aria-label="Show"><button type="button" aria-pressed="true">All</button><button type="button" disabled>Trees</button><button type="button" disabled>Grasses</button><button type="button" disabled>Animals</button></div>
  <ul class="cards" id="plants">
{"".join(cards)}
  </ul>
  <section class="about" id="about">
    <h2>About genes</h2>
    <p>genes is where the species of <a href="https://pietri.dev">pietri.dev</a>'s little world are defined: what each one is in reality, with sources (how tall it grows, when it flowers, how much frost it takes), and how it looks, as 3D models for every stage of its life. The world's simulator reads these facts; this site shows them to anyone. Nothing here needs an account.</p>
  </section>
</main>
{FOOTER}
</body>
</html>
"""


def sitemap(urls: list[str]) -> str:
    items = "".join(f"<url><loc>{e(BASE_URL + u)}</loc></url>" for u in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{items}</urlset>\n'
    )


ROBOTS = """User-agent: *
Allow: /
Disallow: /review/

Sitemap: {base}/sitemap.xml
"""


def llms_txt(species: list[Species]) -> str:
    lines = [
        "# genes",
        "",
        "> The catalog of living things of pietri.dev's world over Unquillo, Córdoba, Argentina: "
        "real biology as sourced ranges in real units, 3D models of every life stage, and one "
        "simulated life per species. Static files; nothing is computed per request.",
        "",
        "Facts carry source ids; the sources are listed on each page. Licence: CC BY 4.0.",
        "",
        "## Species",
        "",
    ]
    for sp in species:
        if sp.id.startswith("example-") or not sp.latest_sheet:
            continue
        sh = sp.latest_sheet.data
        lines.append(
            f"- [{sh['names']['es'][0].capitalize()} ({sh['scientific_name']})]"
            f"({BASE_URL}/species/{sp.id}/index.md): {dig(sh, 'summary', 'en')}"
        )
    lines += [
        "",
        "## Data",
        "",
        f"- [Catalog JSON]({BASE_URL}/v1/catalog.json): every species with its versions and file hashes",
        f"- [All species in one file]({BASE_URL}/llms-full.txt)",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- build


def build(
    species: list[Species], entries: list[dict[str, Any]], catalog_no: int, out: Path
) -> None:
    shutil.copytree(SITE_DIR / "static", out / "static" / "site", dirs_exist_ok=True)
    basemap = jsonio.load(SITE_DIR / "static" / "geo" / "basemap.json")
    by_id = {x["id"]: x for x in entries}
    urls = ["/"]
    full = []
    for sp in species:
        if not sp.latest_sheet or sp.latest_sheet.data is None:
            continue
        html, md = species_page(sp, by_id[sp.id], catalog_no, basemap)
        target = out / "species" / sp.id
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.html").write_text(html, encoding="utf-8")
        (target / "index.md").write_text(md, encoding="utf-8")
        if not sp.id.startswith("example-"):
            urls.append(f"/species/{sp.id}/")
            full.append(md)
    (out / "index.html").write_text(index_page(species, entries, catalog_no), encoding="utf-8")
    (out / "sitemap.xml").write_text(sitemap(urls), encoding="utf-8")
    (out / "robots.txt").write_text(ROBOTS.format(base=BASE_URL), encoding="utf-8")
    (out / "llms.txt").write_text(llms_txt(species), encoding="utf-8")
    (out / "llms-full.txt").write_text("\n\n---\n\n".join(full) + "\n", encoding="utf-8")
