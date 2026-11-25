"""The species page's drawings: cartoon icons and illustrated charts, as inline SVG.

Written at build time like the rest of the page, so every number is in the HTML. Icons are
small cartoon drawings with a dark outline; the charts draw the sheet's sourced ranges with
them. When marcos's painted icons exist (`site/static/art/`), the page can swap them in.
"""

from __future__ import annotations

import json
import math
from functools import cache
from html import escape
from pathlib import Path
from typing import Any

from genes import site_static as static
from genes.site_i18n import T, num

INK = "#1d2a26"
ART_DIR = Path(__file__).resolve().parents[2] / "site" / "static" / "art"
ART_URL = static.url("art")
# Painted icons (marcos's sheet) that stand in for the drawn ones.
PAINTED = {
    "wood": "i-wood",
    "frost": "i-frost",
    "rain": "i-rain",
    "drought": "i-sun",
    "shade_need": "i-sun",
    "life": "i-seedling",
    "fruit": "i-pod",
    "nectar": "i-flower",
    "pollen": "i-bee",
    "browse": "i-goat",
    "shade": "i-shade",
    "nitrogen_fixing": "i-roots",
    "firewood": "i-fire",
    "nest_sites": "i-nest",
    "person": "i-person",
    "leaf": "i-leaf",
    "map": "i-compass",
    "people": "i-bread",
    "thermometer": "i-thermometer",
    "gauge": "i-gauge",
    "cow": "i-cow",
}


def _e(value: Any) -> str:
    return escape(str(value), quote=True)


def _n(x: float) -> str:
    return num(x)


def _minus(text: str) -> str:
    return text.replace("-", "−")


# ---------------------------------------------------------------- icons (viewBox 0 0 48 48)

_O = f'stroke="{INK}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"'

ICONS: dict[str, str] = {
    "height": (
        f'<rect x="21" y="26" width="6" height="16" rx="2" fill="#8a5a3b" {_O}/>'
        f'<path d="M10 27c-4-1-4-8 1-9 0-6 7-9 12-6 4-4 12-1 12 4 5 0 7 7 2 10-2 3-25 3-27 1Z" fill="#9cc47a" {_O}/>'
        f'<path d="M41 6v36M37 10l4-4 4 4M37 38l4 4 4-4" fill="none" {_O}/>'
    ),
    "crown": (
        f'<rect x="21.5" y="24" width="5" height="17" rx="2" fill="#8a5a3b" {_O}/>'
        f'<path d="M5 24c0-6 8-11 19-11s19 5 19 11c-6 2-32 2-38 0Z" fill="#a9c98c" {_O}/>'
        f'<path d="M6 7h36M10 4 6 7l4 3M38 4l4 3-4 3" fill="none" {_O}/>'
    ),
    "trunk": (
        f'<circle cx="24" cy="25" r="17" fill="#7a4f33" {_O}/>'
        '<circle cx="24" cy="25" r="13.5" fill="#e3b77c"/>'
        '<circle cx="24" cy="25" r="10" fill="none" stroke="#b9854f" stroke-width="1.6"/>'
        '<circle cx="24" cy="25" r="6.5" fill="none" stroke="#b9854f" stroke-width="1.6"/>'
        '<circle cx="24" cy="25" r="3" fill="none" stroke="#b9854f" stroke-width="1.6"/>'
    ),
    "wood": (
        f'<path d="M8 18h28v16H8z" fill="#8a5a3b" {_O}/>'
        f'<ellipse cx="36" cy="26" rx="5" ry="8" fill="#e3b77c" {_O}/>'
        '<ellipse cx="36" cy="26" rx="2.4" ry="4.2" fill="none" stroke="#b9854f" stroke-width="1.5"/>'
        f'<ellipse cx="8" cy="26" rx="5" ry="8" fill="#6f4529" {_O}/>'
        '<path d="M14 22h14M16 30h10" stroke="#5d3b24" stroke-width="1.6" stroke-linecap="round"/>'
    ),
    "frost": (
        f'<path d="M24 5v38M7.5 14.5l33 19M7.5 33.5l33-19" fill="none" stroke="#bfe3ff" stroke-width="5" stroke-linecap="round"/>'
        f'<path d="M24 5v38M7.5 14.5l33 19M7.5 33.5l33-19M19 8l5 5 5-5M19 40l5-5 5 5" fill="none" {_O}/>'
        f'<circle cx="24" cy="24" r="4" fill="#e9f6ff" {_O}/>'
    ),
    "rain": (
        f'<path d="M24 5s13 14 13 23a13 13 0 0 1-26 0C11 19 24 5 24 5Z" fill="#7cc3ee" {_O}/>'
        '<path d="M17 28a7 7 0 0 0 5 7" fill="none" stroke="#e8f6ff" stroke-width="2.6" stroke-linecap="round"/>'
    ),
    "drought": (
        f'<circle cx="24" cy="20" r="8" fill="#ffd166" {_O}/>'
        f'<path d="M24 5v3M24 32v3M9 20h3M36 20h3M13.4 9.4l2.1 2.1M32.5 28.5l2.1 2.1M13.4 30.6l2.1-2.1M32.5 11.5l2.1-2.1" {_O}/>'
        f'<path d="M6 42c6-3 12 2 18-1s12-2 18 1" fill="none" {_O}/>'
    ),
    "shade_need": (
        f'<circle cx="16" cy="16" r="7" fill="#ffd166" {_O}/>'
        f'<path d="M29 40V28" {_O}/>'
        f'<path d="M20 29c-3-5 2-10 9-10s12 5 9 10c-3 1-15 1-18 0Z" fill="#9cc47a" {_O}/>'
        f'<path d="M6 42h36" {_O}/>'
    ),
    "life": (
        f'<path d="M24 42V24" {_O}/>'
        f'<path d="M24 26c-9 1-14-4-14-11 8-1 14 3 14 11Z" fill="#a9d68b" {_O}/>'
        f'<path d="M24 22c1-8 7-12 15-11 0 8-6 12-15 11Z" fill="#7fbf6a" {_O}/>'
        f'<path d="M12 42h24" {_O}/>'
    ),
    "fruit": (
        f'<path d="M8 12c10 2 26 10 30 27 1 3-3 4-4 1-5-13-15-19-27-23-3-1-2-6 1-5Z" fill="#f0c75e" {_O}/>'
        '<path d="M14 17c2 1 3 2 4 3M21 21c2 1 3 3 4 4M27 27c1 1 2 3 3 5" stroke="#c99a35" stroke-width="2" stroke-linecap="round"/>'
    ),
    "nectar": (
        f'<path d="M24 44V28" {_O}/>'
        f'<rect x="17" y="5" width="14" height="27" rx="7" fill="#f6e27a" {_O}/>'
        '<g fill="#e0bd3d"><circle cx="21" cy="11" r="1.6"/><circle cx="27" cy="13" r="1.6"/><circle cx="22" cy="18" r="1.6"/><circle cx="27" cy="21" r="1.6"/><circle cx="21" cy="25" r="1.6"/></g>'
    ),
    "pollen": (
        f'<ellipse cx="18" cy="16" rx="7" ry="5" fill="#e9f6ff" {_O} transform="rotate(-25 18 16)"/>'
        f'<ellipse cx="30" cy="16" rx="7" ry="5" fill="#e9f6ff" {_O} transform="rotate(25 30 16)"/>'
        f'<ellipse cx="24" cy="29" rx="11" ry="9" fill="#ffcf4a" {_O}/>'
        f'<path d="M19 21.5v15M24 20v18M29 21.5v15" stroke="{INK}" stroke-width="2.6"/>'
        f'<path d="M35 29l6 0" {_O}/>'
    ),
    "browse": (
        f'<path d="M8 40C8 22 18 10 40 8c-1 20-12 32-32 32Z" fill="#9cc47a" {_O}/>'
        f'<path d="M8 40 30 18" fill="none" {_O}/>'
        f'<path d="M40 8c-6 2-7 7-3 9 3 1 5-3 3-9Z" fill="#14201f"/>'
    ),
    "shade": (
        f'<ellipse cx="24" cy="40" rx="18" ry="4" fill="#2b4a3a" {_O}/>'
        f'<rect x="21.5" y="22" width="5" height="18" rx="2" fill="#8a5a3b" {_O}/>'
        f'<path d="M5 23c0-7 8-13 19-13s19 6 19 13c-6 2-32 2-38 0Z" fill="#a9c98c" {_O}/>'
    ),
    "nitrogen_fixing": (
        f'<path d="M4 14h40" {_O}/>'
        f'<path d="M24 6v8M24 14v12M24 22l-9 9M24 22l9 9M24 26v14M15 31l-4 9M33 31l4 9" fill="none" stroke="#a87b4f" stroke-width="2.6" stroke-linecap="round"/>'
        '<g fill="#f2a6a0" stroke="#1d2a26" stroke-width="1.8"><circle cx="15" cy="31" r="3"/><circle cx="33" cy="31" r="3"/><circle cx="24" cy="40" r="3"/><circle cx="11" cy="40" r="2.5"/></g>'
        f'<path d="M24 6c-5-3-9 0-9 0M24 6c5-3 9 0 9 0" fill="none" stroke="#7fbf6a" stroke-width="2.6" stroke-linecap="round"/>'
    ),
    "firewood": (
        f'<path d="M24 4c6 7 12 11 12 20a12 12 0 0 1-24 0c0-5 3-7 5-12 2 3 4 5 6 5-1-4-1-8 1-13Z" fill="#ff9f43" {_O}/>'
        f'<path d="M24 22c3 4 6 6 6 10a6 6 0 0 1-12 0c0-3 3-5 6-10Z" fill="#ffd166" {_O}/>'
        f'<path d="M8 44l32-6M8 38l32 6" stroke="#8a5a3b" stroke-width="4" stroke-linecap="round"/>'
    ),
    "nest_sites": (
        f'<path d="M6 26c2 10 10 14 18 14s16-4 18-14Z" fill="#b48452" {_O}/>'
        '<path d="M9 30c8 3 22 3 30 0M12 35c6 2 18 2 24 0" stroke="#7a5532" stroke-width="1.8" fill="none"/>'
        f'<ellipse cx="18" cy="24" rx="5" ry="6" fill="#dff3ff" {_O}/>'
        f'<ellipse cx="29" cy="23" rx="5" ry="6" fill="#dff3ff" {_O}/>'
    ),
    "person": (
        f'<circle cx="24" cy="9" r="5" fill="#f2c9a0" {_O}/>'
        f'<path d="M16 26c0-6 3-10 8-10s8 4 8 10v4h-16Z" fill="#5fa874" {_O}/>'
        f'<path d="M19 30v13M29 30v13" stroke="#3a4f6b" stroke-width="5" stroke-linecap="round"/>'
    ),
    "year": (
        f'<circle cx="24" cy="24" r="18" fill="#a9c98c" {_O}/>'
        '<path d="M24 6a18 18 0 0 1 18 18H24Z" fill="#f6e27a"/>'
        '<path d="M42 24a18 18 0 0 1-18 18V24Z" fill="#f0c75e"/>'
        f'<circle cx="24" cy="24" r="18" fill="none" {_O}/>'
        f'<path d="M24 24 24 11" {_O}/><circle cx="24" cy="24" r="2.5" fill="{INK}"/>'
    ),
    "leaf": (
        f'<path d="M24 44V6" fill="none" {_O}/>'
        + "".join(
            f'<ellipse cx="{24 + s * 6:.0f}" cy="{y}" rx="5" ry="2.4" fill="#9cc47a" {_O} '
            f'transform="rotate({s * -25} {24 + s * 6:.0f} {y})"/>'
            for y in (10, 17, 24, 31)
            for s in (-1, 1)
        )
    ),
    "map": (
        f'<path d="M6 12l11-4 14 4 11-4v28l-11 4-14-4-11 4Z" fill="#cfe6b4" {_O}/>'
        f'<path d="M17 8v28M31 12v28" fill="none" {_O}/>'
        f'<path d="M24 14c-4 0-6 3-6 6 0 4 6 10 6 10s6-6 6-10c0-3-2-6-6-6Z" fill="#f28b6c" {_O}/>'
        '<circle cx="24" cy="20" r="2" fill="#fff"/>'
    ),
    "people": (
        f'<path d="M8 36c4-10 28-10 32 0l-2 6H10Z" fill="#e3b77c" {_O}/>'
        f'<path d="M14 30c2-6 18-6 20 0" fill="#c9893f" {_O}/>'
        f'<path d="M24 8v12M18 12l6 6 6-6" fill="none" {_O}/>'
    ),
    "photo": (
        f'<rect x="5" y="12" width="38" height="28" rx="5" fill="#cfe6b4" {_O}/>'
        f'<path d="M16 12l3-5h10l3 5" fill="#cfe6b4" {_O}/>'
        f'<circle cx="24" cy="26" r="8" fill="#7cc3ee" {_O}/>'
        '<circle cx="21" cy="23" r="2" fill="#fff"/>'
    ),
    "book": (
        f'<path d="M6 10c6-2 12-2 18 2v28c-6-4-12-4-18-2Z" fill="#e9f0dc" {_O}/>'
        f'<path d="M42 10c-6-2-12-2-18 2v28c6-4 12-4 18-2Z" fill="#cfe6b4" {_O}/>'
    ),
    "conservation": (
        f'<path d="M24 5l15 6v11c0 10-6 17-15 21C15 39 9 32 9 22V11Z" fill="#f0c75e" {_O}/>'
        f'<path d="M17 29c0-8 6-13 14-13 0 8-5 14-14 13Z" fill="#74c27f" {_O}/>'
        f'<path d="M17 29l8-8" fill="none" {_O}/>'
    ),
}


@cache
def art_sizes() -> dict[str, list[int]]:
    p = ART_DIR / "sizes.json"
    if not p.exists():
        return {}
    sizes: dict[str, list[int]] = json.loads(p.read_text(encoding="utf-8"))["sizes"]
    return sizes


def icon(name: str, cls: str = "ico") -> str:
    painted = PAINTED.get(name)
    if painted and painted in art_sizes():
        w, h = art_sizes()[painted]
        return (
            f'<img class="{cls} painted" src="{ART_URL}/{painted}.webp" alt="" width="{w}" '
            f'height="{h}" loading="lazy" decoding="async">'
        )
    body = ICONS.get(name)
    if not body:
        return ""
    return f'<svg class="{cls}" viewBox="0 0 48 48" aria-hidden="true">{body}</svg>'


# ---------------------------------------------------------------- charts


def _tree_glyph(x: float, base: float, h: float, crown_w: float) -> str:
    """A cartoon umbrella tree, when there is no card picture."""
    trunk_w = max(3.0, h * 0.06)
    crown_h = h * 0.42
    top = base - h
    return (
        f'<g class="glyph-tree"><path d="M{x - trunk_w / 2:.1f} {base}L{x - trunk_w / 3:.1f} {top + crown_h * 0.7:.1f}'
        f'L{x + trunk_w / 3:.1f} {top + crown_h * 0.7:.1f}L{x + trunk_w / 2:.1f} {base}Z" fill="#8a5a3b" {_O}/>'
        f'<path d="M{x - crown_w / 2:.1f} {top + crown_h * 0.8:.1f}c0-{crown_h * 0.9:.1f} {crown_w * 0.2:.1f}-{crown_h * 0.8:.1f} {crown_w / 2:.1f}-{crown_h * 0.8:.1f}'
        f's{crown_w / 2:.1f} 0 {crown_w / 2:.1f} {crown_h * 0.8:.1f}c-{crown_w * 0.3:.1f} {crown_h * 0.25:.1f}-{crown_w * 0.7:.1f} {crown_h * 0.25:.1f}-{crown_w:.1f} 0Z" '
        f'fill="#a9c98c" {_O}/></g>'
    )


def height_scene(
    sheet_size: dict[str, Any],
    picture: str | None,
    stage_art: dict[str, tuple[str, int, int]] | None = None,
) -> str:
    """Small, usual and tallest adults drawn to scale next to a 1.75 m person."""
    h = sheet_size.get("adult_height_m")
    if not h:
        return ""
    c = sheet_size.get("crown_width_m") or {}
    top = max(20.0, math.ceil(h["max"] / 5) * 5)
    W, H, base, left = 600, 330, 280, 40
    sy = (base - 26) / top
    aspect = 0.917  # the card picture's width over height
    parts = [
        '<defs><linearGradient id="hs-sky" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#9fd3f0" stop-opacity=".0"/>'
        '<stop offset="1" stop-color="#9fd3f0" stop-opacity=".10"/></linearGradient>'
        '<linearGradient id="hs-ground" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#b7c77a"/><stop offset="1" stop-color="#8a9a52"/>'
        "</linearGradient></defs>",
        f'<rect x="{left}" y="10" width="{W - left - 6}" height="{base - 10}" rx="14" fill="url(#hs-sky)"/>',
    ]
    for m in range(0, int(top) + 1, 5):
        y = base - m * sy
        parts.append(
            f'<line class="gl" x1="{left}" x2="{W - 6}" y1="{y:.1f}" y2="{y:.1f}"/>'
            f'<text class="axis" x="{left - 8}" y="{y + 4:.1f}">{m} m</text>'
        )
    parts.append(
        f'<path d="M{left} {base}H{W - 6}v4c0 4-3 6-7 6H{left + 7}c-4 0-7-2-7-6Z" fill="url(#hs-ground)" stroke="{INK}" stroke-width="2"/>'
    )
    p = 1.75 * sy
    person = art_sizes().get("i-person")
    if person:
        pw = p * person[0] / person[1]
        parts.append(
            f'<image href="{ART_URL}/i-person.webp" x="{82 - pw / 2:.1f}" y="{base - p:.1f}" '
            f'width="{pw:.1f}" height="{p:.1f}"/>'
        )
    else:
        parts.append(
            f'<svg x="{82 - p * 0.55:.1f}" y="{base - p:.1f}" width="{p * 1.1:.1f}" height="{p:.1f}" viewBox="6 2 36 42" preserveAspectRatio="xMidYMax meet">'
            f"{ICONS['person']}</svg>"
        )
    parts.append(f'<text class="scale-sub" x="82" y="{base + 30}">{T("you, 1.75 m")}</text>')
    which = {"min": "young", "typical": "adult", "max": "adult"}
    xs = {"min": 150, "typical": 262, "max": 462}
    for key, label in (("max", "tallest"), ("typical", "usually"), ("min", "small")):
        hh = float(h.get(key) or 0)
        if not hh:
            continue
        x = xs[key]
        th = hh * sy
        drawn = (stage_art or {}).get(which[key])
        if drawn:
            url, iw, ih = drawn
            tw = th * iw / ih
            parts.append(
                f'<image class="scale-pic" href="{_e(url)}" x="{x - tw / 2:.1f}" y="{base - th + 3:.1f}" '
                f'width="{tw:.1f}" height="{th:.1f}"/>'
            )
        elif picture:
            tw = th * aspect
            parts.append(
                f'<ellipse cx="{x}" cy="{base}" rx="{tw * 0.3:.1f}" ry="{max(2.5, tw * 0.03):.1f}" fill="#1d2a26" opacity=".3"/>'
                f'<image class="scale-pic" href="{_e(picture)}" x="{x - tw / 2:.1f}" y="{base - th:.1f}" '
                f'width="{tw:.1f}" height="{th:.1f}" preserveAspectRatio="xMidYMax meet"/>'
            )
        else:
            cw = float(c.get(key) or hh * 0.8) * sy
            parts.append(_tree_glyph(x, base, th, cw))
        parts.append(
            f'<g class="chip"><rect x="{x - 26}" y="{base - th - 30:.1f}" width="52" height="22" rx="11"/>'
            f'<text x="{x}" y="{base - th - 15:.1f}">{_n(hh)} m</text></g>'
            f'<text class="scale-sub" x="{x}" y="{base + 30}">{T(label)}</text>'
        )
    return (
        f'<svg class="scene" viewBox="0 0 {W} {H}" role="img" aria-label="{T("Adult height")} '
        f"{_n(h['min'])}–{_n(h['max'])} m, {T('usually')} {_n(h.get('typical', h['max']))} m, "
        f'{T("next to a 1.75 m person")}">' + "".join(parts) + "</svg>"
    )


def _arc(cx: float, cy: float, r: float, a0: float, a1: float) -> str:
    """An arc from angle a0 to a1 (radians, 0 = left, pi = right, over the top)."""
    x0, y0 = cx - r * math.cos(a0), cy - r * math.sin(a0)
    x1, y1 = cx - r * math.cos(a1), cy - r * math.sin(a1)
    large = 1 if a1 - a0 > math.pi else 0
    return f"M{x0:.1f} {y0:.1f}A{r} {r} 0 {large} 1 {x1:.1f} {y1:.1f}"


def wood_gauge(density: dict[str, Any] | None) -> str:
    """Wood density on a dial from 0 to 1,200 kg/m³, with water's 1,000 marked."""
    if not density or "min" not in density:
        return ""
    lo, hi = 0.0, 1200.0
    cx, cy, r = 150.0, 150.0, 108.0

    def ang(v: float) -> float:
        return (min(hi, max(lo, v)) - lo) / (hi - lo) * math.pi

    typ = float(density.get("typical", (density["min"] + density["max"]) / 2))
    parts = [
        '<defs><linearGradient id="wg" x1="0" x2="1"><stop offset="0" stop-color="#e3b77c"/>'
        '<stop offset="1" stop-color="#8a5a3b"/></linearGradient></defs>',
        f'<path d="{_arc(cx, cy, r, 0, math.pi)}" class="dial-track"/>',
        f'<path d="{_arc(cx, cy, r, ang(density["min"]), ang(density["max"]))}" class="dial-fill" stroke="url(#wg)"/>',
    ]
    for v in (0, 300, 600, 900, 1200):
        a = ang(v)
        x0, y0 = cx - (r - 22) * math.cos(a), cy - (r - 22) * math.sin(a)
        parts.append(
            f'<text class="axis dial-tick" x="{x0:.1f}" y="{y0 + 4:.1f}">{num(v, ",")}</text>'
        )
    a = ang(1000)
    wx, wy = cx - (r + 24) * math.cos(a), cy - (r + 24) * math.sin(a)
    tx0, ty0 = cx - (r - 14) * math.cos(a), cy - (r - 14) * math.sin(a)
    tx1, ty1 = cx - (r + 12) * math.cos(a), cy - (r + 12) * math.sin(a)
    parts.append(
        f'<line x1="{tx0:.1f}" y1="{ty0:.1f}" x2="{tx1:.1f}" y2="{ty1:.1f}" class="water-tick"/>'
        f'<svg x="{wx - 11:.1f}" y="{wy - 12:.1f}" width="22" height="22" viewBox="0 0 48 48">{ICONS["rain"]}</svg>'
    )
    a = ang(typ)
    nx, ny = cx - (r - 30) * math.cos(a), cy - (r - 30) * math.sin(a)
    parts.append(
        f'<line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" class="dial-needle"/>'
        f'<circle cx="{cx}" cy="{cy}" r="9" class="dial-hub"/>'
    )
    floats = T("Lighter than water" if density["max"] < 1000 else "Heavier than water")
    return (
        f'<svg class="dial" viewBox="0 0 300 200" role="img" aria-label="{T("Wood density")} '
        f"{_n(density['min'])}–{_n(density['max'])} kg/m³, {T('usually')} {_n(typ)}; "
        f'{T("water is 1,000")}">' + "".join(parts) + "</svg>"
        f'<p class="dial-read"><strong>{_n(typ)}</strong> kg/m³ {T("usually")} · {floats} '
        f"<small>({T('water: 1,000')})</small></p>"
    )


def trunk_rings(dbh: dict[str, Any] | None) -> str:
    """Trunk diameters drawn to scale as cut logs, inside the biggest."""
    if not dbh or "min" not in dbh:
        return ""
    big = float(dbh["max"])
    R = 74.0
    cx, cy = 90.0, 90.0
    k = R / (big / 2)
    rows = []
    rings = [f'<circle cx="{cx}" cy="{cy}" r="{R}" class="ring-max"/>']
    typ = dbh.get("typical")
    if typ:
        rt = float(typ) / 2 * k
        rings.append(
            f'<circle cx="{cx}" cy="{cy}" r="{rt + 4:.1f}" fill="#7a4f33" stroke="{INK}" stroke-width="2"/>'
        )
        rings.append(f'<circle cx="{cx}" cy="{cy}" r="{rt:.1f}" fill="#e3b77c"/>')
        for f in (0.75, 0.5, 0.25):
            rings.append(
                f'<circle cx="{cx}" cy="{cy}" r="{rt * f:.1f}" fill="none" stroke="#b9854f" stroke-width="1.5"/>'
            )
    rmin = float(dbh["min"]) / 2 * k
    rings.append(f'<circle cx="{cx}" cy="{cy}" r="{rmin:.1f}" class="ring-min"/>')
    for label, v, y in (("biggest", big, 40), ("usually", typ, 90), ("small", dbh["min"], 140)):
        if v:
            rows.append(
                f'<text class="ring-v" x="196" y="{y}">{_n(float(v))} m</text>'
                f'<text class="axis ring-k" x="196" y="{y + 18}">{T(label)}</text>'
            )
    return (
        f'<svg class="rings" viewBox="0 0 300 180" role="img" aria-label="{T("Trunk diameter at breast height")} '
        f'{_n(dbh["min"])}–{_n(big)} m">' + "".join(rings) + "".join(rows) + "</svg>"
    )


def rain_tube(rain: dict[str, Any] | None, top: float = 1000.0) -> str:
    """Yearly rainfall as a rain gauge: the range the species lives with, filled."""
    if not rain or "min" not in rain:
        return ""
    x, y0, y1, w = 46.0, 24.0, 214.0, 46.0
    sy = (y1 - y0) / top

    def yv(v: float) -> float:
        return y1 - min(top, v) * sy

    ticks = "".join(
        f'<line class="gl" x1="{x - 6}" x2="{x}" y1="{yv(v):.1f}" y2="{yv(v):.1f}"/>'
        f'<text class="axis" x="{x - 10}" y="{yv(v) + 4:.1f}">{num(v, ",")}</text>'
        for v in range(0, int(top) + 1, 250)
    )
    return (
        f'<svg class="tube" viewBox="0 0 170 250" role="img" aria-label="{T("Rainfall it lives with")}: '
        f'{_n(rain["min"])}–{_n(rain["max"])} {T("mm a year")}">'
        '<defs><linearGradient id="rt" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9fdcff"/>'
        '<stop offset="1" stop-color="#3f8fc4"/></linearGradient></defs>'
        f'<rect x="{x}" y="{y0 - 6}" width="{w}" height="{y1 - y0 + 12}" rx="14" class="tube-glass"/>'
        f'<rect x="{x + 6}" y="{yv(rain["max"]):.1f}" width="{w - 12}" height="{yv(rain["min"]) - yv(rain["max"]):.1f}" rx="8" fill="url(#rt)" stroke="{INK}" stroke-width="2"/>'
        + ticks
        + f'<text class="tube-v" x="{x + w + 8}" y="{yv(rain["max"]) + 5:.1f}">{_n(rain["max"])}</text>'
        f'<text class="tube-v" x="{x + w + 8}" y="{yv(rain["min"]) + 5:.1f}">{_n(rain["min"])}</text>'
        f'<text class="axis tube-u" x="{x + w / 2}" y="{y1 + 30}">{T("mm a year")}</text>'
        "</svg>"
    )


def thermometer(
    frost: dict[str, Any] | None,
    lo: float = -15.0,
    hi: float = 5.0,
    label: str = "Frost that kills an adult",
) -> str:
    """A cold limit (the frost that kills an adult, or the coldest where it grows) on a
    thermometer. A range with only one end draws that end."""
    if not frost:
        return ""
    ends = [frost[k] for k in ("min", "typical", "max") if frost.get(k) is not None]
    if not ends:
        return ""
    frost = {**frost, "min": frost.get("min", min(ends)), "max": frost.get("max", max(ends))}
    lo = min(lo, 5 * math.floor(float(frost["min"]) / 5))
    x, y0, y1, w = 50.0, 20.0, 196.0, 22.0
    sy = (y1 - y0) / (hi - lo)

    def yv(v: float) -> float:
        return y0 + (hi - max(lo, min(hi, v))) * sy

    ticks = "".join(
        f'<line class="gl" x1="{x - 6}" x2="{x}" y1="{yv(v):.1f}" y2="{yv(v):.1f}"/>'
        f'<text class="axis" x="{x - 10}" y="{yv(v) + 4:.1f}">{_minus(str(v))}°</text>'
        for v in range(int(lo), int(hi) + 1, 5)
    )
    typ = frost.get("typical")
    mark = (
        f'<line x1="{x - 4}" x2="{x + w + 4}" y1="{yv(typ):.1f}" y2="{yv(typ):.1f}" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>'
        f'<text class="tube-v" x="{x + w + 10}" y="{yv(typ) + 5:.1f}">{_minus(_n(typ))}° {T("usually")}</text>'
        if typ is not None
        else ""
    )
    return (
        f'<svg class="tube" viewBox="0 0 170 250" role="img" aria-label="{T(label)}: '
        f'{_minus(_n(frost["min"]))} – {_minus(_n(frost["max"]))} °C">'
        f'<rect x="{x}" y="{y0 - 8}" width="{w}" height="{y1 - y0 + 16}" rx="{w / 2}" class="tube-glass"/>'
        f'<rect x="{x + 5}" y="{yv(frost["max"]):.1f}" width="{w - 10}" height="{yv(frost["min"]) - yv(frost["max"]):.1f}" rx="5" fill="#9fdcff" stroke="{INK}" stroke-width="2"/>'
        f'<rect x="{x + 7}" y="{yv(frost["min"]):.1f}" width="{w - 14}" height="{y1 + 12 - yv(frost["min"]):.1f}" fill="#3f8fc4"/>'
        f'<circle cx="{x + w / 2}" cy="{y1 + 22}" r="17" fill="#3f8fc4" stroke="{INK}" stroke-width="2.2"/>'
        f'<circle cx="{x + w / 2 - 5}" cy="{y1 + 17}" r="4" fill="#d6f0ff"/>'
        + ticks
        + mark
        + "</svg>"
    )


LEVELS = ("low", "medium", "high")


def level_meter(label: str, r: dict[str, Any] | None, ico: str) -> str:
    """A low, medium or high tolerance as three dots."""
    if not r or "value" not in r:
        return ""
    v = str(r["value"])
    n = LEVELS.index(v) + 1 if v in LEVELS else 0
    dots = "".join(f'<i class="{"on" if i < n else ""}"></i>' for i in range(3))
    return (
        f'<div class="level">{icon(ico, "ico ico-sm")}<span class="level-k">{_e(label)}</span>'
        f'<span class="level-dots" aria-hidden="true">{dots}</span>'
        f'<strong class="level-v">{_e(T(v))}</strong></div>'
    )
