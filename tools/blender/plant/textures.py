"""Painted textures made in code (look `textures[].made_by = "code"`): the foliage
clump atlas and the bark. Grey values only: the model's flat colour (from the
palette) multiplies them, and pietri.dev paints and lights the result (spec §8).

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


def _leaf_cell(
    rng: random.Random, kind: str, density: float, px_per_cm: float, leaf_cm: float
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

    if kind in ("bipinnate", "pinnate"):
        bipinnate = kind == "bipinnate"
        pinna_px = leaf_cm * (0.9 if bipinnate else 1.0) * px_per_cm
        leaflet_px = max(2.0, (0.9 if bipinnate else 2.2) * px_per_cm * LEAF_SCALE)
        area = math.pi * radius**2
        per_leaf = pinna_px * leaflet_px * (4 if bipinnate else 2.5)
        n_leaves = int(area * (0.8 + 2.2 * density) / max(per_leaf, 1.0))
        for _ in range(n_leaves):
            ang0 = rng.uniform(0, math.tau)
            r = edge(ang0) * 0.8 * math.sqrt(rng.uniform(0.0, 1.0))
            base = (c + math.cos(ang0) * r, c + math.sin(ang0) * r)
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
    leaf = foliage.get("leaf_size_cm", [4, 8])
    leaf_cm = (leaf[0] + leaf[1]) / 2 if isinstance(leaf, list) else float(leaf)
    px_per_cm = CELL / (clump_size_m * 100)
    atlas = np.zeros((CELL * ATLAS_CELLS, CELL * ATLAS_CELLS, 4), dtype=np.float32)
    for row in range(ATLAS_CELLS):
        for col in range(ATLAS_CELLS):
            cell = _leaf_cell(rng, kind, density, px_per_cm, leaf_cm)
            atlas[row * CELL : (row + 1) * CELL, col * CELL : (col + 1) * CELL] = cell
    return _quantise(atlas)


def _quantise(img: np.ndarray) -> np.ndarray:
    """Leaf greys to GREYS levels between 0.72 and 1; empty pixels white and clear."""
    out = img.copy()
    lo = 0.72
    grey = np.clip((out[..., 0] - lo) / (1 - lo), 0, 1)
    grey = lo + (1 - lo) * np.round(grey * (GREYS - 1)) / (GREYS - 1)
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


def bark(form: dict[str, Any], seed: int, size: int = 256) -> np.ndarray:
    """A tileable grey bark pattern."""
    rng = random.Random(seed)
    bark_form = form.get("trunk", {}).get("bark", {})
    pattern = bark_form.get("pattern", "fine_fissures")
    depth = float(bark_form.get("depth", 0.5))
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    tau = 2 * math.pi
    wobble = np.zeros_like(xs)
    for k in range(1, 4):
        wobble += rng.uniform(0.01, 0.03) / k * np.sin(tau * (k * ys * 2 + rng.random()))
    value = np.ones_like(xs)
    if pattern in ("deep_fissures", "fine_fissures"):
        n = 6 if pattern == "deep_fissures" else 11
        width = 0.18 if pattern == "deep_fissures" else 0.12
        phase = np.sin(tau * n * (xs + wobble + 0.03 * np.sin(tau * 3 * ys)))
        fissure = np.clip((phase - (1 - 2 * width)) / (2 * width), 0, 1)
        # Fissures break into long plates: modulate along the trunk.
        cut = 0.5 + 0.5 * np.sin(tau * (4 * ys + 2 * xs))
        value -= depth * 0.55 * fissure * (0.6 + 0.4 * cut)
    elif pattern == "plates":
        cells = 0.5 + 0.5 * np.sin(tau * 5 * (xs + wobble)) * np.sin(tau * 3 * (ys + wobble))
        value -= depth * 0.45 * (np.abs(cells - 0.5) < 0.08)
    elif pattern == "peeling":
        patch = np.sin(tau * 3 * (xs + wobble)) * np.sin(tau * 2 * ys + 1.3)
        value -= depth * 0.3 * (patch > 0.4)
    grain = np.zeros_like(xs)
    for k in (8, 16, 32):
        grain += (
            np.sin(tau * (k * xs + rng.random())) * np.sin(tau * (k / 2 * ys + rng.random())) / k
        )
    value += grain * 0.8 * (0.3 + depth)
    value = np.clip(value, 0.35, 1.0)
    out = np.ones((size, size, 4), dtype=np.float32)
    out[..., 0] = value
    out[..., 1] = value
    out[..., 2] = value
    return out


def half_bark(img: np.ndarray) -> np.ndarray:
    """The bark at half size (a plain 2 x 2 mean; it tiles the same)."""
    h, w = img.shape[:2]
    out: np.ndarray = img.reshape(h // 2, 2, w // 2, 2, 4).mean(axis=(1, 3))
    return out
