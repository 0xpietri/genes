"""Meshes from the skeleton: bark tubes, foliage cards, flowers, fruit and thorns.

Every part is a `Part`: plain lists of positions, normals, UVs, triangles and the
per-vertex `_ORDER` (spec §6.3). Y up, metres (spec §8).
"""

from __future__ import annotations

import itertools
import math
import random
from dataclasses import dataclass, field

from plant import vec
from plant.skeleton import BOLE, LEADER, Branch
from plant.vec import UP, Vec

DOWN: Vec = (0.0, -1.0, 0.0)


@dataclass
class Part:
    name: str
    positions: list[Vec] = field(default_factory=list)
    normals: list[Vec] = field(default_factory=list)
    uvs: list[tuple[float, float]] = field(default_factory=list)
    triangles: list[tuple[int, int, int]] = field(default_factory=list)
    order: list[float] | None = None

    @property
    def triangle_count(self) -> int:
        return len(self.triangles)

    def vertex(
        self, p: Vec, n: Vec, uv: tuple[float, float] = (0.0, 0.0), order: float = 0.0
    ) -> int:
        self.positions.append(p)
        self.normals.append(n)
        self.uvs.append(uv)
        if self.order is not None:
            self.order.append(order)
        return len(self.positions) - 1

    def extend(self, other: Part) -> None:
        base = len(self.positions)
        self.positions += other.positions
        self.normals += other.normals
        self.uvs += other.uvs
        if self.order is not None:
            self.order += other.order or [0.0] * len(other.positions)
        self.triangles += [(a + base, b + base, c + base) for a, b, c in other.triangles]


def _noise(*parts: float) -> float:
    """Cheap deterministic value in [-1, 1] from numbers (no global state)."""
    h = 0
    for p in parts:
        h = (h * 1000003) ^ int(p * 1000.0)
        h &= 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0x5BD1E995) & 0xFFFFFFFF
    h ^= h >> 15
    return (h / 0xFFFFFFFF) * 2 - 1


def sides_for(radius: float, coarse: bool) -> int:
    if coarse:
        return max(3, min(6, round(3 + radius * 25)))
    return max(3, min(10, round(3 + radius * 32)))


def tube(
    part: Part,
    branch: Branch,
    sides: int,
    tile: float,
    gnarl: float,
    flare: float,
    height: float,
    seed: float,
    step: int = 1,
    fluting: float = 0.0,
) -> None:
    """A tube along the branch with parallel-transport frames, closed at the tip. The
    trunk and the leaders can be fluted: ribs that spiral up them like fused stems."""
    pts = branch.points[::step]
    radii = branch.radii[::step]
    if pts[-1] != branch.points[-1]:
        pts.append(branch.points[-1])
        radii.append(branch.radii[-1])
    if len(pts) < 2:
        return
    tangents: list[Vec] = []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        tangents.append(vec.norm(vec.sub(b, a)))
    normal = vec.perpendicular(tangents[0])
    around = max(1, round(2 * math.pi * radii[0] / tile))
    v_run = 0.0
    rings: list[int] = []
    trunkish = branch.level in (BOLE, LEADER)
    for i, (p, t, r) in enumerate(zip(pts, tangents, radii, strict=True)):
        if i > 0:
            # Parallel transport: turn the frame by the rotation between tangents.
            prev = tangents[i - 1]
            axis = vec.cross(prev, t)
            if vec.length(axis) > 1e-6:
                ang = math.atan2(vec.length(axis), vec.dot(prev, t))
                normal = vec.norm(vec.rotate(normal, vec.norm(axis), ang))
            v_run += vec.length(vec.sub(p, pts[i - 1]))
        binormal = vec.cross(t, normal)
        start = len(part.positions)
        rings.append(start)
        for j in range(sides + 1):
            theta = 2 * math.pi * (j % sides) / sides
            radial = vec.add(vec.mul(normal, math.cos(theta)), vec.mul(binormal, math.sin(theta)))
            rr = r
            if trunkish and gnarl > 0:
                rr *= (
                    1
                    + gnarl * 0.12 * _noise(seed, j % sides, i)
                    + gnarl * 0.08 * math.sin(3 * theta + seed)
                )
            if trunkish and fluting > 0:
                spiral = 0.35 * v_run / max(radii[0], 0.05)  # a quarter turn every few widths
                rr *= 1 + fluting * 0.22 * math.cos(5 * theta + spiral + seed)
            if branch.level == BOLE or (branch.level == LEADER and branch.parent is None):
                low = math.exp(-p[1] / max(height * 0.06, 0.05))
                rr *= 1 + flare * 1.6 * low + flare * 0.35 * low * math.cos(5 * theta + seed)
            pos = vec.add(p, vec.mul(radial, rr))
            if (i == 0 and branch.level in (BOLE, LEADER) and branch.parent is None) or pos[1] < 0:
                pos = (pos[0], 0.0, pos[2])  # wood meets the ground, never goes into it
            part.vertex(pos, radial, (j / sides * around, v_run / tile))
    for i in range(len(rings) - 1):
        a0, b0 = rings[i], rings[i + 1]
        for j in range(sides):
            i0, i1 = a0 + j, a0 + j + 1
            i2, i3 = b0 + j, b0 + j + 1
            part.triangles += [(i0, i1, i2), (i1, i3, i2)]
    # Close the tip (or the broken end) with a fan.
    last = rings[-1]
    tip = part.vertex(
        vec.add(pts[-1], vec.mul(tangents[-1], radii[-1] * (0.2 if branch.broken else 1.0))),
        tangents[-1],
        (0.5 * around, (v_run + radii[-1]) / tile),
    )
    for j in range(sides):
        part.triangles.append((last + j, last + j + 1, tip))


@dataclass
class Clump:
    centre: Vec
    size: float
    order: float
    outward: Vec
    branch: int = -1  # the branch it grows on


def ellipsoid_normal(p: Vec, centre: Vec, radii: Vec) -> Vec:
    q = (
        (p[0] - centre[0]) / radii[0] ** 2,
        (p[1] - centre[1]) / radii[1] ** 2,
        (p[2] - centre[2]) / radii[2] ** 2,
    )
    n = vec.norm(q)
    return vec.norm(vec.add(n, (0.0, 0.25, 0.0)))


def foliage_cards(
    part: Part,
    clumps: list[Clump],
    cards: int,
    rng: random.Random,
    proxy: tuple[Vec, Vec],
    atlas: int = 2,
) -> None:
    """Crossed alpha cards per clump; normals from the crown's proxy (spec §7.2)."""
    centre, radii = proxy
    cell = 1.0 / atlas
    for c in clumps:
        spin0 = rng.uniform(0, 2 * math.pi)
        for k in range(cards):
            offset = (k - (cards - 1) / 2) * (math.pi / max(cards, 1))
            facing = vec.rotate(c.outward, UP, offset + rng.uniform(-0.25, 0.25))
            facing = vec.norm(vec.add(facing, (0.0, rng.uniform(0.1, 0.6), 0.0)))
            if k == cards - 1 and cards >= 3:
                facing = vec.norm(vec.add((0.0, 1.0, 0.0), vec.mul(c.outward, 0.4)))
            side = vec.perpendicular(facing)
            side = vec.rotate(side, facing, spin0 + k * 1.1)
            upv = vec.cross(facing, side)
            half = c.size * rng.uniform(0.85, 1.15) / 2
            cu = rng.randrange(atlas) * cell
            cv = rng.randrange(atlas) * cell
            corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
            pts = [
                vec.add(c.centre, vec.add(vec.mul(side, sx * half), vec.mul(upv, sy * half)))
                for sx, sy in corners
            ]
            lift = max(0.0, 0.01 - min(p[1] for p in pts))  # never below the ground
            idx = []
            for (sx, sy), p0 in zip(corners, pts, strict=True):
                p = (p0[0], p0[1] + lift, p0[2])
                uv = (cu + (sx + 1) / 2 * cell, cv + (sy + 1) / 2 * cell)
                idx.append(part.vertex(p, ellipsoid_normal(p, centre, radii), uv, c.order))
            part.triangles += [(idx[0], idx[1], idx[2]), (idx[0], idx[2], idx[3])]


def ribbon(
    part: Part,
    anchor: Vec,
    direction: Vec,
    bend_axis: Vec,
    length: float,
    width: float,
    bend: float,
    order: float,
    segments: int = 4,
) -> None:
    """A flat curved strip (a pod or a samara), double sided by its material."""
    d = vec.norm(direction)
    p = anchor
    across = vec.norm(vec.cross(d, bend_axis))
    step = length / segments
    rows: list[tuple[int, int]] = []
    for i in range(segments + 1):
        t = i / segments
        w = width * (0.35 + 0.65 * math.sin(math.pi * min(max(t, 0.08), 0.92)))
        n = vec.norm(vec.cross(d, across))
        a = part.vertex(vec.add(p, vec.mul(across, w / 2)), n, (0.0, t), order)
        b = part.vertex(vec.sub(p, vec.mul(across, w / 2)), n, (1.0, t), order)
        rows.append((a, b))
        d = vec.norm(vec.rotate(d, bend_axis, bend / segments))
        across = vec.norm(vec.rotate(across, bend_axis, bend / segments))
        p = vec.add(p, vec.mul(d, step))
    for (a, b), (c, e) in itertools.pairwise(rows):
        part.triangles += [(a, b, c), (b, e, c)]


def spike(
    part: Part, base: Vec, direction: Vec, length: float, radius: float, order: float
) -> None:
    """A tapered three-sided spike (a catkin-like inflorescence or a thorn)."""
    d = vec.norm(direction)
    side = vec.perpendicular(d)
    ring = []
    for j in range(3):
        radial = vec.rotate(side, d, 2 * math.pi * j / 3)
        ring.append(part.vertex(vec.add(base, vec.mul(radial, radius)), radial, (0.0, 0.0), order))
    mid_ring = []
    mid = vec.add(base, vec.mul(d, length * 0.55))
    for j in range(3):
        radial = vec.rotate(side, d, 2 * math.pi * j / 3 + 0.4)
        mid_ring.append(
            part.vertex(vec.add(mid, vec.mul(radial, radius * 1.15)), radial, (0.0, 0.5), order)
        )
    tip = part.vertex(vec.add(base, vec.mul(d, length)), d, (0.0, 1.0), order)
    for j in range(3):
        a, b = ring[j], ring[(j + 1) % 3]
        c, e = mid_ring[j], mid_ring[(j + 1) % 3]
        part.triangles += [(a, b, c), (b, e, c), (c, e, tip)]


def cone(part: Part, base: Vec, direction: Vec, length: float, radius: float) -> None:
    """A three-sided cone without its base: 3 triangles (a thorn)."""
    d = vec.norm(direction)
    side = vec.perpendicular(d)
    ring = []
    for j in range(3):
        radial = vec.rotate(side, d, 2 * math.pi * j / 3)
        ring.append(part.vertex(vec.add(base, vec.mul(radial, radius)), radial))
    tip = part.vertex(vec.add(base, vec.mul(d, length)), d)
    for j in range(3):
        part.triangles.append((ring[j], ring[(j + 1) % 3], tip))


def berry(part: Part, centre: Vec, radius: float, order: float, stretch: float = 1.0) -> None:
    """An octahedron: 8 triangles (berries, drupes, capsules, ball flowers)."""
    axes: list[Vec] = [
        (radius, 0.0, 0.0),
        (-radius, 0.0, 0.0),
        (0.0, radius * stretch, 0.0),
        (0.0, -radius * stretch, 0.0),
        (0.0, 0.0, radius),
        (0.0, 0.0, -radius),
    ]
    idx = [part.vertex(vec.add(centre, a), vec.norm(a), (0.0, 0.0), order) for a in axes]
    faces = [(0, 2, 4), (4, 2, 1), (1, 2, 5), (5, 2, 0), (4, 3, 0), (1, 3, 4), (5, 3, 1), (0, 3, 5)]
    part.triangles += [(idx[a], idx[b], idx[c]) for a, b, c in faces]
