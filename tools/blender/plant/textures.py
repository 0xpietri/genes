"""Painted textures made in code (look `textures[].made_by = "code"`): the foliage
clump atlas, the bark, and the fruit's accent marks. Near white: the model's flat
colour (from the palette) multiplies them, and pietri.dev paints and lights the result
(spec §8). The foliage is grey only; the bark has gentle colour patches (warm wood,
lichen, weathered).

Arrays are rows from the top, RGBA floats 0–1. numpy comes with Blender's
`bpy`, so this module is only imported by `blend.py`.
"""

from __future__ import annotations

import math
import random
from typing import Any

import numpy as np

ATLAS_CELLS = 2  # 2 x 2 clump variations per atlas
CELL = 512  # the atlas is 1024 px (spec §8.1)
LEAF_SCALE = 1.8  # painted exaggeration: real leaflets would be sub-pixel
TWIG = 0.3  # value of the twigs painted under the leaves (the palette darkens it further)
GREYS = 4  # leaf values are quantised: the alpha carries the shape, and few greys keep
# the lossless WebP small (every model embeds its atlas, spec §8.2 budgets)


def _ellipse(
    img: np.ndarray, cx: float, cy: float, a: float, b: float, angle: float, value: float
) -> None:
    """Paint a filled ellipse (centre, half-axes a along `angle`, b across)."""
    h, w = img.shape[:2]
    r = math.ceil(max(a, b)) + 1
    x0, x1 = max(int(cx) - r, 0), min(int(cx) + r + 1, w)
    y0, y1 = max(int(cy) - r, 0), min(int(cy) + r + 1, h)
    if x0 >= x1 or y0 >= y1:
        return
    ys, xs = np.mgrid[y0:y1, x0:x1]
    dx, dy = xs + 0.5 - cx, ys + 0.5 - cy
    c, s = math.cos(angle), math.sin(angle)
    u = (dx * c + dy * s) / max(a, 0.5)
    v = (-dx * s + dy * c) / max(b, 0.5)
    inside = (u * u + v * v) <= 1.0
    region = img[y0:y1, x0:x1]
    region[inside, 0:3] = value
    region[inside, 3] = 1.0


def _compound_leaf(
    xs: list[int],
    ys: list[int],
    rng: random.Random,
    base: tuple[float, float],
    angle: float,
    pinna_px: float,
    leaflet_px: float,
    pairs: int,
    bipinnate: bool,
) -> None:
    """One compound leaf as pixel coordinates: a short petiole, then pinnae (bipinnate)
    or one rachis (pinnate), each fringed with leaflets on both sides."""
    bx, by = base
    petiole = pinna_px * (0.18 if bipinnate else 0.05)
    bx += math.cos(angle) * petiole
    by += math.sin(angle) * petiole
    rachises = []
    if bipinnate:
        for k in range(pairs):
            spread = rng.uniform(0.25, 0.55) + k * 0.12
            for side in (-1, 1):
                rachises.append((angle + side * spread, pinna_px * rng.uniform(0.75, 1.1)))
    else:
        rachises.append((angle, pinna_px * rng.uniform(0.9, 1.2)))
    for ang, length in rachises:
        x, y = bx, by
        bend = rng.uniform(-0.012, 0.012)
        steps = int(length)
        for i in range(steps):
            ang += bend
            ca, sa = math.cos(ang), math.sin(ang)
            x += ca
            y += sa
            xs.append(int(x))
            ys.append(int(y))
            if i % 2:
                continue
            ll = leaflet_px * (1.0 - 0.45 * i / max(steps, 1))
            for side in (-1, 1):
                la = ang + side * rng.uniform(1.0, 1.35)
                cl, sl = math.cos(la), math.sin(la)
                for j in range(1, int(ll) + 1):
                    px, py = x + cl * j, y + sl * j
                    xs.append(int(px))
                    ys.append(int(py))
                    if not bipinnate:
                        xs.append(int(px + sa))
                        ys.append(int(py - ca))


def _twigs(
    img: np.ndarray, rng: random.Random, c: float, radius: float, amount: float
) -> list[tuple[float, float]]:
    """Dark crooked twigs from the clump's middle outwards, kinked at every few
    centimetres and forking, under the leaves: the branch net seen through the foliage."""
    stack = [
        (
            c + rng.uniform(-0.15, 0.15) * radius,
            c + rng.uniform(-0.15, 0.15) * radius,
            rng.uniform(0, math.tau),
            radius * rng.uniform(0.55, 1.0),
            2.2,
        )
        for _ in range(round(2 + 9 * amount))
    ]
    along: list[tuple[float, float]] = []
    while stack:
        x, y, ang, left, width = stack.pop()
        while left > 0:
            run = rng.uniform(radius * 0.08, radius * 0.2)
            ang += rng.uniform(-0.65, 0.65)  # an elbow
            ca, sa = math.cos(ang), math.sin(ang)
            for _ in range(int(min(run, left))):
                x, y = x + ca, y + sa
                _ellipse(img, x, y, width / 2, width / 2, 0.0, TWIG)
            along.append((x, y))
            left -= run
            width = max(1.0, width * 0.85)
            if rng.random() < 0.3 * amount + 0.1 and left > radius * 0.15:
                stack.append(
                    (x, y, ang + rng.choice((-1, 1)) * rng.uniform(0.5, 1.0), left * 0.6, width)
                )
    return along


def _leaf_cell(
    rng: random.Random,
    kind: str,
    density: float,
    px_per_cm: float,
    leaf_cm: float,
    twigs: float = 0.0,
) -> np.ndarray:
    img = np.zeros((CELL, CELL, 4), dtype=np.float32)
    c = CELL / 2
    radius = CELL * 0.46
    # Leaves sit inside a ragged round blob, so each card reads as a clump.
    lobes = [(k, rng.uniform(0.05, 0.12), rng.uniform(0, 6.28)) for k in (3, 5, 7)]

    def edge(ang: float) -> float:
        return radius * (1 + sum(a * math.sin(k * ang + p) for k, a, p in lobes))

    def blob(x: float, y: float) -> bool:
        return math.hypot(x - c, y - c) < edge(math.atan2(y - c, x - c))

    # Leaves grow on the twigs, when there are twigs.
    on_twigs = _twigs(img, rng, c, radius * 0.9, twigs) if twigs > 0 else []

    if kind in ("bipinnate", "pinnate"):
        bipinnate = kind == "bipinnate"
        pinna_px = leaf_cm * (0.9 if bipinnate else 1.0) * px_per_cm
        leaflet_px = max(2.0, (0.9 if bipinnate else 2.2) * px_per_cm * LEAF_SCALE)
        area = math.pi * radius**2
        per_leaf = pinna_px * leaflet_px * (4 if bipinnate else 2.5)
        n_leaves = int(area * (0.2 + 2.4 * density) / max(per_leaf, 1.0))
        for _ in range(n_leaves):
            ang0 = rng.uniform(0, math.tau)
            r = edge(ang0) * 0.8 * math.sqrt(rng.uniform(0.0, 1.0))
            base = (c + math.cos(ang0) * r, c + math.sin(ang0) * r)
            if on_twigs and rng.random() < twigs:
                base = on_twigs[rng.randrange(len(on_twigs))]
                ang0 = math.atan2(base[1] - c, base[0] - c)
            # Leaves point outwards and sag (image y grows downwards).
            ang = ang0 + rng.gauss(0, 0.9)
            ang = math.atan2(math.sin(ang) + 0.35, math.cos(ang))
            xs: list[int] = []
            ys: list[int] = []
            _compound_leaf(
                xs, ys, rng, base, ang, pinna_px, leaflet_px, rng.randint(1, 3), bipinnate
            )
            pts = [
                (x, y)
                for x, y in zip(xs, ys, strict=True)
                if 2 <= x < CELL - 2 and 2 <= y < CELL - 2
            ]
            if not pts:
                continue
            px_arr = np.array(pts, dtype=np.int64)
            value = rng.uniform(0.72, 1.0)
            img[px_arr[:, 1], px_arr[:, 0], 0:3] = value
            img[px_arr[:, 1], px_arr[:, 0], 3] = 1.0
    elif kind == "needle":
        for _ in range(int(600 + 1400 * density)):
            x, y = rng.uniform(0, CELL), rng.uniform(0, CELL)
            if blob(x, y):
                length = px_per_cm * LEAF_SCALE * rng.uniform(1.5, 3)
                _ellipse(img, x, y, length, 1.0, rng.uniform(0, math.tau), rng.uniform(0.7, 1))
    else:  # broad and scale
        size = px_per_cm * LEAF_SCALE * leaf_cm * (0.35 if kind == "broad" else 0.15)
        for _ in range(int((240 + 1000 * density) * (8 / max(size, 4)))):
            x, y = rng.uniform(0, CELL), rng.uniform(0, CELL)
            if blob(x, y):
                _ellipse(
                    img,
                    x,
                    y,
                    size * rng.uniform(0.35, 0.55),
                    size * rng.uniform(0.2, 0.32),
                    rng.uniform(0, math.tau),
                    rng.uniform(0.72, 1.0),
                )
    return img


def foliage_atlas(form: dict[str, Any], clump_size_m: float, seed: int) -> np.ndarray:
    """A 2 x 2 atlas of painted leaf-mass cards for the foliage clumps."""
    rng = random.Random(seed)
    foliage = form.get("foliage", {})
    kind = foliage.get("leaf_type", "broad")
    density = float(foliage.get("density", 0.6))
    twigs = float(foliage.get("twigs", 0.0))
    leaf = foliage.get("leaf_size_cm", [4, 8])
    leaf_cm = (leaf[0] + leaf[1]) / 2 if isinstance(leaf, list) else float(leaf)
    px_per_cm = CELL / (clump_size_m * 100)
    atlas = np.zeros((CELL * ATLAS_CELLS, CELL * ATLAS_CELLS, 4), dtype=np.float32)
    for row in range(ATLAS_CELLS):
        for col in range(ATLAS_CELLS):
            cell = _leaf_cell(rng, kind, density, px_per_cm, leaf_cm, twigs)
            atlas[row * CELL : (row + 1) * CELL, col * CELL : (col + 1) * CELL] = cell
    return _quantise(atlas)


def _quantise(img: np.ndarray) -> np.ndarray:
    """Leaf greys to GREYS levels between 0.72 and 1, twigs to TWIG; empty pixels white
    and clear."""
    out = img.copy()
    lo = 0.72
    grey = np.clip((out[..., 0] - lo) / (1 - lo), 0, 1)
    grey = lo + (1 - lo) * np.round(grey * (GREYS - 1)) / (GREYS - 1)
    grey = np.where(out[..., 0] < 0.55, TWIG, grey)
    for ch in range(3):
        out[..., ch] = np.where(out[..., 3] > 0.5, grey, 1.0)
    out[..., 3] = (out[..., 3] > 0.5).astype(np.float32)
    return out


def half(img: np.ndarray) -> np.ndarray:
    """The atlas at half size for lod1: a pixel is leaf if any of its four was (thin
    leaflets survive), with the mean grey of the leaf pixels."""
    h, w = img.shape[:2]
    blocks = img.reshape(h // 2, 2, w // 2, 2, 4)
    alpha = blocks[..., 3]
    covered = alpha.sum(axis=(1, 3))
    out = np.ones((h // 2, w // 2, 4), dtype=np.float32)
    grey = (blocks[..., 0] * alpha).sum(axis=(1, 3)) / np.maximum(covered, 1)
    out[..., 3] = (covered > 0).astype(np.float32)
    for ch in range(3):
        out[..., ch] = grey
    return _quantise(out)


def _noise(size: int, cells: int, rng: random.Random, rows: int | None = None) -> np.ndarray:
    """Tileable smooth value noise in 0–1: a random grid (`rows` x `cells`, square by
    default) that wraps, smoothly interpolated to `size` pixels. Few rows and many
    columns make fibres running along the trunk."""
    ny = rows or cells
    grid = np.array([[rng.random() for _ in range(cells)] for _ in range(ny)], np.float32)

    def axis(n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        t = np.arange(size, dtype=np.float32) * n / size
        i0 = np.floor(t).astype(np.int64)
        f = t - i0
        return i0 % n, (i0 + 1) % n, f * f * (3 - 2 * f)

    x0, x1, fx = axis(cells)
    y0, y1, fy = axis(ny)
    top = grid[y0][:, x0] * (1 - fx)[None, :] + grid[y0][:, x1] * fx[None, :]
    bottom = grid[y1][:, x0] * (1 - fx)[None, :] + grid[y1][:, x1] * fx[None, :]
    out: np.ndarray = top * (1 - fy)[:, None] + bottom * fy[:, None]
    return out


# Bark tints, as gentle multipliers of the palette's bark colour: warm reddish wood in the
# fissures and fresh plates, grey-green lichen, pale weathered patches.
BARK_TINTS = {
    "warm": (1.05, 0.97, 0.9),
    "lichen": (0.97, 1.02, 0.97),
    "pale": (1.06, 1.06, 1.05),
}


def bark(form: dict[str, Any], seed: int, size: int = 256) -> np.ndarray:
    """A tileable bark pattern: irregular fissures that wander, fork and change width,
    split into plates of slightly different tones, with gentle colour patches. Near
    white on average: the palette's bark colour multiplies it."""
    rng = random.Random(seed)
    bark_form = form.get("trunk", {}).get("bark", {})
    pattern = bark_form.get("pattern", "fine_fissures")
    depth = float(bark_form.get("depth", 0.5))
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    warp = (_noise(size, 3, rng) - 0.5) * 0.22 + (_noise(size, 9, rng) - 0.5) * 0.06
    value = np.ones_like(xs)
    if pattern in ("deep_fissures", "fine_fissures"):
        n = 7 if pattern == "deep_fissures" else 12
        width = 0.3 if pattern == "deep_fissures" else 0.18
        u = n * (xs + warp)
        plate = np.floor(u).astype(np.int64) % n
        c = u - np.floor(u)
        dist = np.minimum(c, 1 - c)
        w_local = width * (0.35 + 1.1 * _noise(size, 6, rng))
        fissure = np.clip(1.25 * (1 - dist / np.maximum(w_local, 1e-3)), 0, 1) ** 0.8
        # Cross-cracks cut the strips into plates, each at its own heights.
        offsets = np.array([rng.random() for _ in range(n)], np.float32)
        m = 3 if pattern == "deep_fissures" else 5
        v = m * (ys + offsets[plate] + 0.08 * (_noise(size, 5, rng) - 0.5))
        cv = v - np.floor(v)
        cross = np.clip(1 - np.minimum(cv, 1 - cv) / 0.05, 0, 1)
        cross *= np.clip((_noise(size, 7, rng) - 0.35) * 4, 0, 1)
        tones = np.array([rng.uniform(0.88, 1.0) for _ in range(n)], np.float32)
        value *= tones[plate]
        # Ridges are lit on one side, so the plates read as raised.
        ridge = np.clip(c * 2, 0, 1) * (1 - fissure)
        value *= 0.9 + 0.1 * ridge
        value -= depth * 0.75 * np.maximum(fissure, cross * 0.6)
    elif pattern == "plates":
        cells = _noise(size, 6, rng)
        edges = np.abs(np.sin(np.pi * 4 * (cells + warp)))
        value -= depth * 0.45 * (edges < 0.15)
    elif pattern == "peeling":
        patch = _noise(size, 4, rng) + warp
        value -= depth * 0.3 * (patch > 0.6)
    # Fibres along the trunk.
    fibre = _noise(size, 48, rng, rows=6) * 0.6 + _noise(size, 96, rng, rows=12) * 0.4
    value += (fibre - 0.5) * 0.4 * (0.3 + depth)
    value = np.clip(value, 0.3, 1.05)
    out = np.ones((size, size, 4), dtype=np.float32)
    rgb = np.repeat(value[..., None], 3, axis=2)
    for name, tint in BARK_TINTS.items():
        lo = {"warm": 0.5, "lichen": 0.62, "pale": 0.6}[name]
        mask = np.clip((_noise(size, 4, rng) - lo) / 0.2, 0, 1)
        if name == "warm":  # wood shows warm in the fissures
            mask = np.maximum(mask, np.clip(0.9 - value, 0, 1))
        rgb *= 1 + (np.array(tint, np.float32)[None, None, :] - 1) * mask[..., None]
    out[..., :3] = np.clip(rgb, 0.0, 1.0)
    return out


def half_bark(img: np.ndarray) -> np.ndarray:
    """The bark at half size (a plain 2 x 2 mean; it tiles the same)."""
    h, w = img.shape[:2]
    out: np.ndarray = img.reshape(h // 2, 2, w // 2, 2, 4).mean(axis=(1, 3))
    return out


def _linear(hex_colour: str) -> np.ndarray:
    h = hex_colour.lstrip("#")
    return _linear_of(np.array([int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32))


def _linear_of(c: np.ndarray) -> np.ndarray:
    out: np.ndarray = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return out


def _srgb(c: np.ndarray) -> np.ndarray:
    out: np.ndarray = np.where(
        c <= 0.0031308, c * 12.92, 1.055 * np.power(np.maximum(c, 0), 1 / 2.4) - 0.055
    )
    return out


def fruit(pattern: str, lit: str, accent: str, seed: int, size: int = 64) -> np.ndarray | None:
    """Where the accent colour shows on a fruit (`fruit.accent`), as a texture the flat lit
    colour multiplies: white keeps the lit colour, and the marks are accent / lit per
    channel (in linear light, the way the material multiplies), so lit x texture paints
    the accent. Accent channels brighter than lit cannot be reached and stay at lit. UV:
    u across the fruit, v along it (pods), or a front view (round fruit). None for
    `none`."""
    if pattern == "none":
        return None
    rng = random.Random(seed)
    w, h = size, size * 2
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = (xs + 0.5) / w, (ys + 0.5) / h
    mark = np.zeros((h, w), dtype=np.float32)
    if pattern == "spots":
        for _ in range(26):
            spot = np.zeros((h, w, 4), dtype=np.float32)
            cx, cy = rng.uniform(0, w), rng.uniform(0, h)
            a, b = rng.uniform(2, 6), rng.uniform(1.5, 4)
            _ellipse(spot, cx, cy, a, b, rng.uniform(0, math.pi), 1.0)
            mark = np.maximum(mark, spot[..., 0] * rng.uniform(0.6, 1.0))
    elif pattern == "streaks":
        for _ in range(7):
            x0 = rng.uniform(0.1, 0.9)
            width = rng.uniform(0.03, 0.08)
            phase = rng.uniform(0, 2 * math.pi)
            centre = x0 + 0.04 * np.sin(2 * math.pi * 1.5 * v + phase)
            line = np.clip(1 - np.abs(u - centre) / width, 0, 1)
            # Each streak runs part of the length and fades at its ends.
            lo, hi = sorted((rng.uniform(0, 1), rng.uniform(0, 1)))
            along = np.clip(np.minimum(v - lo, hi - v) / 0.08 + 0.5, 0, 1)
            mark = np.maximum(mark, line * along * rng.uniform(0.6, 1.0))
    elif pattern == "tip":
        mark = np.clip((v - 0.7) / 0.25, 0, 1)
    elif pattern == "blush":
        d = np.hypot(u - 0.35, (v - 0.4) * 0.5)
        mark = np.clip(1 - d / 0.4, 0, 1) ** 0.8
    else:
        raise ValueError(f"unknown fruit accent {pattern}")
    ratio = np.clip(_linear(accent) / np.maximum(_linear(lit), 1e-4), 0, 1)
    colour = 1 - mark[..., None] * (1 - ratio[None, None, :])
    out = np.ones((h, w, 4), dtype=np.float32)
    out[..., :3] = _srgb(colour)
    return out
