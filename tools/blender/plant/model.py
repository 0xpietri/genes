"""One model: a stage of a variant at one LOD, as plain meshes and metadata.

`build(look, stage, variant, lod, budgets)` is the whole generator except the
Blender export. Stages (spec §6.2): seedling, sapling, young and adult grow
from the form; old adds broken limbs and a thinner crown; dead_standing loses
its leaves, most twigs and the tops of its leaders; fallen is a dead tree on
the ground. LODs: lod0 is the walk view; lod1 reuses the same skeleton and
clumps, coarser.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any

from genes import jsonio
from plant import GENERATOR, vec
from plant.form import Form, as_range, draw, draw_int, resolve, seed
from plant.geometry import (
    DOWN,
    Clump,
    Part,
    berry,
    cone,
    foliage_cards,
    ribbon,
    sides_for,
    spike,
    tube,
)
from plant.skeleton import BOLE, LEADER, Branch, Growth, Tree, fill_crown, grow, grow_tree
from plant.vec import UP, Vec

PARTS = ("bark", "foliage", "flowers", "fruit", "thorns")
LEAFLESS = ("dead_standing", "fallen")


@dataclass
class Model:
    parts: dict[str, Part]
    colours: dict[str, str]
    extras: dict[str, Any]
    notes: list[str] = field(default_factory=list)

    @property
    def triangles(self) -> int:
        return sum(p.triangle_count for p in self.parts.values())


def lit_colour(palette: dict[str, Any], part: str) -> str:
    tones = palette.get(part) or palette.get("bark") or {"lit": "#808080"}
    if "lit" in tones:
        return str(tones["lit"])
    for phase in ("mature", "summer", "new"):
        if phase in tones:
            return str(tones[phase]["lit"])
    return str(next(iter(tones.values()))["lit"])


def _value_noise(p: Vec, cell: float, key: str) -> float:
    """Smooth 3D value noise in [0, 1]: big gaps in the crown, not speckle."""
    from plant.form import unit

    x, y, z = p[0] / cell, p[1] / cell, p[2] / cell
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz

    def s(t: float) -> float:
        return t * t * (3 - 2 * t)

    total = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (
                    (s(fx) if dx else 1 - s(fx))
                    * (s(fy) if dy else 1 - s(fy))
                    * (s(fz) if dz else 1 - s(fz))
                )
                total += w * unit(key, ix + dx, iy + dy, iz + dz)
    return total


def _stage_height(look: dict[str, Any], stage: str) -> tuple[float, float]:
    stages = look["stages"]
    h = float(stages[stage]["ref_height_m"])
    adult = float(stages.get("adult", stages.get("old", stages[stage]))["ref_height_m"])
    return h, adult


def _old_and_dead(tree: Tree, form: Form, rng: random.Random) -> None:
    stage = form.stage
    if stage == "old":
        # A broken main limb, never a whole stem: the crown keeps its round outline.
        pool = [i for i, b in enumerate(tree.branches) if b.level == 1 and not b.free]
        pool = sorted(pool, key=lambda i: -tree.branches[i].radii[0])[:6]
        for i in rng.sample(pool, min(len(pool), draw_int(rng, form.get("old.broken_limbs")))):
            tree.cut(i, rng.uniform(0.3, 0.6))
    if stage in LEAFLESS:
        lost = float(form.get("dead.lost_twigs"))
        deepest = max(b.level for b in tree.branches)
        for i, b in enumerate(tree.branches):
            if b.removed:
                continue
            if (b.level == deepest and b.level >= 1 and rng.random() < lost) or (
                b.level == deepest - 1 and b.level >= 1 and rng.random() < lost * 0.5
            ):
                tree.remove(i)
        for i, b in enumerate(tree.branches):
            if b.level == LEADER and not b.removed:
                tree.cut(i, draw(rng, form.get("dead.broken_top")))
    if stage == "fallen":
        for i, b in enumerate(tree.branches):
            if b.removed:
                continue
            if b.level >= 2 or (b.level == 1 and rng.random() < 0.6):
                tree.remove(i)
            elif b.level == 1:
                tree.cut(i, rng.uniform(0.3, 0.5))
            elif b.level == LEADER:
                tree.cut(i, rng.uniform(0.5, 0.85))


def _lay_down(tree: Tree, form: Form, max_height: float) -> None:
    """Fallen: the dead tree on the ground, the way it leaned."""
    az = 2 * math.pi * form.unit("lean_azimuth")
    fall = (math.cos(az), 0.0, math.sin(az))
    axis = vec.norm(vec.cross(UP, fall))
    angle = math.radians(87)
    base_r = tree.branches[0].radii[0]
    for b in tree.alive():
        b.points = [vec.rotate(p, axis, angle) for p in b.points]
        b.points = [(p[0], p[1] + base_r * 0.85, p[2]) for p in b.points]
    # The trunk and the leaders lie along the ground, snaking sideways as they grew;
    # their limbs move with them.
    shift: dict[int, list[Vec]] = {}
    for i, b in enumerate(tree.branches):
        if b.removed:
            continue
        if b.level in (BOLE, LEADER):
            flat = [(p[0], r * 0.85, p[2]) for p, r in zip(b.points, b.radii, strict=True)]
            shift[i] = [vec.sub(f, p) for f, p in zip(flat, b.points, strict=True)]
            b.points = flat
        elif b.parent is not None and b.parent in shift:
            moves = shift[b.parent]
            d = moves[min(len(moves) - 1, round(b.at * (len(moves) - 1)))]
            b.points = [vec.add(p, d) for p in b.points]
    for i, b in enumerate(tree.branches):
        if b.removed or b.level == BOLE:
            continue
        total = b.length
        run = 0.0
        # Limbs that reach the ground lie on it; limbs that rise too high are broken off.
        b.points = [
            (p[0], max(p[1], r * 0.8), p[2]) for p, r in zip(b.points, b.radii, strict=True)
        ]
        for k in range(1, len(b.points)):
            a, p = b.points[k - 1], b.points[k]
            seg = vec.length(vec.sub(p, a))
            if p[1] > max_height:
                # Cut where the limb crosses the limit: a stub, not a missing limb.
                limit = max_height
                f = (limit - a[1]) / (p[1] - a[1]) if p[1] != a[1] else 0.0
                t = (run + seg * min(max(f, 0.0), 1.0)) / total if total > 0 else 0.0
                if t < 0.04:
                    tree.remove(i)
                else:
                    tree.cut(i, t)
                break
            run += seg


def _branch_clumps(
    tree: Tree, index: int, t0: float, spacing: float, size: float, rng: random.Random
) -> list[Clump]:
    """Clumps along one branch from t0 to its tip, facing out from the crown's axis."""
    b = tree.branches[index]
    env = tree.envelope
    c_axis = (env.centre[0], (env.base + env.top) / 2, env.centre[1])
    length = b.length
    if length <= 0:
        return []
    out: list[Clump] = []
    steps = max(2 if b.level <= LEADER else 1, int((1 - t0) * length / spacing))
    for k in range(steps + 1):
        t = t0 + (1 - t0) * (k / steps if steps else 1)
        p, tangent, _ = b.point_at(t)
        side = vec.rotate(vec.perpendicular(tangent), tangent, rng.uniform(0, 2 * math.pi))
        centre = vec.add(p, vec.mul(side, size * rng.uniform(0.05, 0.4)))
        if k == steps:
            centre = vec.add(centre, vec.mul(tangent, size * 0.3))
        out_dir = vec.horizontal(vec.sub(centre, c_axis))
        outward = vec.norm(out_dir) if vec.length(out_dir) > 1e-3 else vec.perpendicular(UP)
        out.append(Clump(centre, size, rng.random(), outward, index))
    return out


def _t0(tree: Tree, index: int, deepest: int, leafy_from: float) -> float | None:
    """Where foliage starts on a branch, or None if it carries none of its own."""
    b = tree.branches[index]
    if b.level == BOLE:
        return None
    if b.level == deepest:
        return leafy_from if b.level >= 1 else max(0.4, tree.envelope.base / tree.height)
    if b.level == deepest - 1 and b.level >= LEADER:
        return 0.75
    return None


def _clumps(tree: Tree, form: Form, size: float, rng: random.Random) -> list[Clump]:
    alive = tree.alive()
    deepest = max(b.level for b in alive)
    leafy_from = float(form.get("foliage.leafy_from"))
    spacing = size * float(form.get("crown.clump_spacing"))
    env = tree.envelope
    out: list[Clump] = []
    for i, b in enumerate(tree.branches):
        if b.removed:
            continue
        t0 = _t0(tree, i, deepest, leafy_from)
        if t0 is not None:
            out += _branch_clumps(tree, i, t0, spacing, size, rng)
    openness = form.ind("crown.openness")
    small = tree.height < 2.5  # seedlings and saplings keep every leaf they have
    cell = max(tree.height * 0.13, size * 2.5)
    kept: list[Clump] = []
    for c in out:
        if c.centre[1] - size / 2 < 0.02:
            continue
        free = tree.branches[c.branch].free
        if not small and not free and not env.inside(c.centre, margin=size * 0.35):
            continue
        if not small and _value_noise(c.centre, cell, form.key + "/gaps") < openness * 0.55:
            continue
        if rng.random() < openness * (0.1 if small else 0.25):
            continue
        kept.append(c)
    if form.stage == "old":
        thin = float(form.get("old.crown_thinning"))
        kept = [c for c in kept if rng.random() >= thin]
    return kept


def _bare_ends(
    tree: Tree, form: Form, clumps: list[Clump], size: float, rng: random.Random
) -> list[Clump]:
    """No limb is left bare: a branch with no foliage on it or beyond it gets leaves at its
    end (a bare limb reads as a sick tree)."""
    carrying: set[int] = set()
    for c in clumps:
        i: int | None = c.branch
        while i is not None and i >= 0 and i not in carrying:
            carrying.add(i)
            i = tree.branches[i].parent
    spacing = size * float(form.get("crown.clump_spacing"))
    out: list[Clump] = []
    for i, b in enumerate(tree.branches):
        if b.removed or b.level < 1 or b.broken:
            continue
        # A limb that sagged to the ground carries leaves where it rises again.
        resting = (
            b.free and b.level == 1 and b.parent is not None and not tree.branches[b.parent].free
        )
        if not resting:
            if i in carrying:
                continue
            if any(not tree.branches[c].removed for c in b.children):
                continue  # its children get theirs
        out += [
            c
            for c in _branch_clumps(tree, i, 0.3 if resting else 0.55, spacing, size, rng)
            if c.centre[1] - size / 2 >= 0.02
        ]
    # A parent whose children all came out bare is covered by them now.
    return out


def crown_clumps(tree: Tree, form: Form, size: float, rng: random.Random) -> list[Clump]:
    """All the foliage of a living tree: on its twigs, over the whole top of the crown, and
    at the end of every limb."""
    clumps = _clumps(tree, form, size, rng)
    filled = fill_crown(tree, form, [c.centre for c in clumps], size, rng)
    spacing = size * float(form.get("crown.clump_spacing"))
    deepest = max(b.level for b in tree.alive())
    leafy_from = float(form.get("foliage.leafy_from"))
    for i in filled:
        t0 = _t0(tree, i, deepest, leafy_from)
        if t0 is not None:
            clumps += _branch_clumps(tree, i, t0, spacing, size, rng)
    clumps += _bare_ends(tree, form, clumps, size, rng)
    return clumps + _bare_runs(tree, clumps, spacing, size, rng)


def _bare_runs(
    tree: Tree, clumps: list[Clump], spacing: float, size: float, rng: random.Random
) -> list[Clump]:
    """No long bare stick in the crown: a branch whose outer part runs far from any leaves
    gets clumps along it (a long twig with a puff only at its tip reads as a broom)."""
    cell = size * 1.5
    grid: set[tuple[int, int, int]] = set()
    for c in clumps:
        grid.add((int(c.centre[0] // cell), int(c.centre[1] // cell), int(c.centre[2] // cell)))

    def covered(p: Vec) -> bool:
        k = (int(p[0] // cell), int(p[1] // cell), int(p[2] // cell))
        return any(
            (k[0] + dx, k[1] + dy, k[2] + dz) in grid
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            for dz in (-1, 0, 1)
        )

    base = tree.envelope.base
    out: list[Clump] = []
    for i, b in enumerate(tree.branches):
        if b.removed or b.level < 1 or b.broken or b.length < size * 2:
            continue
        samples = [b.point_at(0.4 + 0.6 * k / 6)[0] for k in range(7)]
        samples = [p for p in samples if p[1] > base * 0.8]
        bare = [p for p in samples if not covered(p)]
        if len(samples) >= 3 and len(bare) > len(samples) // 2:
            out += [
                c
                for c in _branch_clumps(tree, i, 0.4, spacing, size, rng)
                if c.centre[1] - size / 2 >= 0.02
            ]
    return out


def _fit(clumps: list[Clump], cap: int) -> tuple[list[Clump], float]:
    """At most `cap` clumps, grown so the crown stays as full: a random share, low ones
    first."""
    if cap <= 0:
        return [], 1.0
    if len(clumps) <= cap:
        return clumps, 1.0
    grow = math.sqrt(len(clumps) / cap) ** 0.85
    # The clumps hidden low inside the crown go first; the top, which shades, stays full.
    top = max(c.centre[1] for c in clumps) or 1.0
    kept = sorted(clumps, key=lambda c: c.order - 0.6 * c.centre[1] / top)[:cap]
    # The kept clumps had the lowest orders: spread them over 0–1 again, keeping their
    # ranking, so a season's amount still shows that share of the crown (spec §6.3).
    ranked = {id(c): (i + 0.5) / len(kept) for i, c in enumerate(kept)}
    kept = sorted(kept, key=lambda c: (c.centre[1], c.centre[0], c.centre[2]))
    return [Clump(c.centre, c.size * grow, ranked[id(c)], c.outward, c.branch) for c in kept], grow


def _cluster(clumps: list[Clump], cap: int, base_size: float) -> list[Clump]:
    """lod1: merge nearby clumps into fewer, bigger ones."""
    if len(clumps) <= cap:
        return clumps
    cell = base_size * 1.2
    for _ in range(40):
        cells: dict[tuple[int, int, int], list[Clump]] = {}
        for c in clumps:
            key = (
                math.floor(c.centre[0] / cell),
                math.floor(c.centre[1] / cell),
                math.floor(c.centre[2] / cell),
            )
            cells.setdefault(key, []).append(c)
        if len(cells) <= cap:
            break
        cell *= 1.15
    merged: list[Clump] = []
    for key in sorted(cells):
        group = cells[key]
        n = len(group)
        centre = (
            sum(c.centre[0] for c in group) / n,
            sum(c.centre[1] for c in group) / n,
            sum(c.centre[2] for c in group) / n,
        )
        size = max(group[0].size, cell * 1.15)
        out = vec.norm(vec.add(group[0].outward, (0.0, 0.0, 0.0)))
        merged.append(Clump(centre, size, group[0].order, out))
    return merged


def _proxy(clumps: list[Clump], tree: Tree) -> tuple[Vec, Vec]:
    """A smooth ellipsoid around the crown: its normals light the clumps as one mass."""
    if not clumps:
        env = tree.envelope
        mid = (env.centre[0], (env.base + env.top) / 2, env.centre[1])
        return mid, (env.radius or 1.0, (env.top - env.base) / 2 or 1.0, env.radius or 1.0)
    lo = [min(c.centre[i] - c.size / 2 for c in clumps) for i in range(3)]
    hi = [max(c.centre[i] + c.size / 2 for c in clumps) for i in range(3)]
    centre = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)
    radii = tuple(max((hi[i] - lo[i]) / 2, 0.05) for i in range(3))
    return centre, (radii[0], radii[1], radii[2])


def _twiglets(
    tree: Tree, form: Form, bark: Part, r_min: float, cap: int, rng: random.Random
) -> int:
    """Fine crooked twigs bristling from the end of every drawn branch (spec §7.2), added
    to the bark within `cap` triangles; the highest ends get them first. Returns how
    many were made."""
    lo_n, hi_n = as_range(form.get("tips.twiglets"))
    crook = float(form.get("tips.crookedness"))
    forks = float(form.get("tips.forks"))
    tile = float(form.get("trunk.bark.tile_m"))
    drawn = [b for b in tree.alive() if b.level >= 1 and b.radii[0] >= r_min and len(b.points) > 1]
    ends: list[Branch] = []
    for b in drawn:
        kids = [tree.branches[c] for c in b.children]
        if not any(not k.removed and k.radii[0] >= r_min for k in kids if k.at > 0.6):
            ends.append(b)
    ends.sort(key=lambda b: -b.points[-1][1])
    floor_r = max(tree.twig_radius * 0.6, 0.0015)
    start_tris = bark.triangle_count
    made = 0

    def sprout(p: Vec, d: Vec, length: float, r0: float, level: int) -> Vec | None:
        nonlocal made
        g = Growth(
            curve=0.1,
            droop=0.0,
            wander=0.5 * crook,
            bend=crook,
            bend_waves=(1.2, 2.4),
        )
        pts, radii = grow(p, d, length, r0, floor_r, g, rng, None, 4)
        if len(pts) < 2:
            return None
        tube(bark, Branch(level, pts, radii), 3, tile, 0.0, 0.0, tree.height, 0.0)
        made += 1
        return pts[len(pts) // 2]

    for b in ends:
        if bark.triangle_count - start_tris >= cap - 30:
            break
        count = int(lo_n) if hi_n == lo_n else rng.randint(int(lo_n), int(hi_n))
        for _ in range(count):
            t = rng.uniform(0.75, 1.0)
            p, tangent, r = b.point_at(t)
            axis = vec.rotate(vec.perpendicular(tangent), tangent, rng.uniform(0, 2 * math.pi))
            d = vec.norm(vec.rotate(tangent, axis, math.radians(rng.uniform(15, 55))))
            d = vec.norm(vec.add(d, (0.0, 0.25, 0.0)))  # twigs reach for the light
            length = draw(rng, form.get("tips.length")) * tree.height
            r0 = max(min(r * 0.6, 0.02 * length), floor_r * 1.3)
            mid = sprout(p, d, length, r0, 4)
            if mid is not None and rng.random() < forks:
                axis = vec.rotate(vec.perpendicular(d), d, rng.uniform(0, 2 * math.pi))
                d2 = vec.norm(vec.rotate(d, axis, math.radians(rng.uniform(25, 50))))
                sprout(mid, d2, length * 0.55, floor_r * 1.1, 5)
    return made


def _simple(b: Branch, segments: int | None, upto: int | None = None) -> Branch:
    """The branch cut after point `upto`, with at most `segments` segments."""
    n = len(b.points) if upto is None else max(2, min(upto + 1, len(b.points)))
    pts, radii = b.points[:n], b.radii[:n]
    if segments is not None and n - 1 > segments:
        idx = sorted({round(i * (n - 1) / segments) for i in range(segments + 1)})
        pts, radii = [pts[i] for i in idx], [radii[i] for i in idx]
    return Branch(b.level, pts, radii, parent=b.parent, at=b.at, broken=b.broken and upto is None)


def _segments_for(b: Branch, coarse: bool) -> int | None:
    """Fewer rings on thin wood: its crook still shows, and more of it fits the budget."""
    if coarse:
        return 6 if b.level < 1 else 3
    if b.level < 1 or b.radii[0] >= 0.05:
        return None
    return 3 if b.radii[0] < 0.008 else 5 if b.radii[0] < 0.02 else 8


# The rule (spec §7.2): no foliage without wood. Every clump has drawn wood within this
# share of its size from its centre, inside its leaves.
REACH = 0.45
# Share of the bark budget kept for the fine twigs that carry the foliage (lod0).
CARRY_SHARE = 0.3


def _carrier_sides(b: Branch) -> int:
    return 3 if b.radii[0] < 0.015 else 4


# Thinner wood than this would not show at all: carriers are drawn at least this thick.
CARRIER_MIN_R = 0.006


def _carrier_segments(b: Branch, upto: int) -> int:
    """Two segments, up to four on long twigs, so they stay crooked."""
    run = sum(
        vec.length(vec.sub(b.points[j + 1], b.points[j]))
        for j in range(min(upto, len(b.points) - 1))
    )
    return max(1, min(upto, max(2, min(4, round(run / 0.6)))))


def _carrier_tris(b: Branch, upto: int) -> int:
    return _carrier_segments(b, upto) * 2 * _carrier_sides(b)


def _chains(tree: Tree, clumps: list[Clump]) -> list[list[tuple[int, int]]]:
    """For each clump, highest first: the branches from its own down to the leaders, each
    with the point it must be drawn to so the wood reaches the clump."""
    out: list[list[tuple[int, int]]] = []
    for c in sorted(clumps, key=lambda c: -c.centre[1]):
        chain: list[tuple[int, int]] = []
        i = c.branch if c.branch >= 0 else None
        target = c.centre
        while i is not None and tree.branches[i].level >= 1:
            b = tree.branches[i]
            k = min(range(len(b.points)), key=lambda j: vec.length(vec.sub(b.points[j], target)))
            chain.append((i, max(1, k)))
            target = b.points[0]
            i = b.parent
        out.append(chain)
    return out


def _carry_plan(
    tree: Tree, chains: list[list[tuple[int, int]]], r_min: float, cap: int | None
) -> tuple[dict[int, int], int]:
    """The fine twigs, thinner than r_min, that carry the clumps out from the drawn wood:
    how far each is drawn, and their triangles. With a cap, the highest clumps first."""
    need: dict[int, int] = {}
    cost = 0
    for chain in chains:
        wanted = {
            i: k for i, k in chain if tree.branches[i].radii[0] < r_min and need.get(i, 0) < k
        }
        extra = sum(
            _carrier_tris(tree.branches[i], k)
            - (_carrier_tris(tree.branches[i], need[i]) if i in need else 0)
            for i, k in wanted.items()
        )
        if cap is not None and cost + extra > cap:
            continue
        cost += extra
        need.update(wanted)
    return need, cost


def _anchor(clumps: list[Clump], wood: list[Vec]) -> int:
    """The rule, last: a clump with no drawn wood within REACH of its size moves onto the
    nearest wood. Returns how many moved."""
    if not clumps or not wood:
        return 0
    cell = max(0.05, min(c.size for c in clumps))
    grid: dict[tuple[int, int, int], list[Vec]] = {}
    for p in wood:
        grid.setdefault((int(p[0] // cell), int(p[1] // cell), int(p[2] // cell)), []).append(p)
    span = max(max(p[i] for p in wood) - min(p[i] for p in wood) for i in range(3))
    rings = int(span / cell) + 2
    moved = 0
    for c in clumps:
        k = (int(c.centre[0] // cell), int(c.centre[1] // cell), int(c.centre[2] // cell))
        best: Vec | None = None
        best_d = math.inf
        for r in range(rings):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    for dz in range(-r, r + 1):
                        if max(abs(dx), abs(dy), abs(dz)) != r:
                            continue
                        for p in grid.get((k[0] + dx, k[1] + dy, k[2] + dz), ()):
                            d = vec.length(vec.sub(p, c.centre))
                            if d < best_d:
                                best, best_d = p, d
            if best is not None and best_d <= r * cell:
                break
        limit = c.size * REACH
        if best is not None and best_d > limit:
            c.centre = vec.add(best, vec.mul(vec.sub(c.centre, best), limit / best_d))
            moved += 1
    return moved


def _bark(
    tree: Tree,
    form: Form,
    coarse: bool,
    cap: int,
    seed_value: float,
    clumps: list[Clump] | None = None,
    carry_cap: int = 0,
) -> tuple[Part, float, int]:
    """The bark mesh within `cap` triangles: the thinnest branches are drawn only as fine
    twigs out to the clumps they carry (lod0), or left out (lod1). Returns the bark, the
    radius under which branches became carriers, and how many carriers were drawn."""
    tile = float(form.get("trunk.bark.tile_m"))
    gnarl = form.ind("trunk.gnarl")
    flare = form.ind("trunk.flare")
    fluting = form.ind("trunk.fluting")
    alive = tree.alive()
    thresholds = sorted({0.0} | {b.radii[0] for b in alive if b.level >= 1})
    best = Part("bark")
    used = 0.0
    plan: dict[int, int] = {}
    chains = _chains(tree, clumps) if clumps else []
    lo, hi = 0, len(thresholds) - 1
    # Binary search the smallest radius threshold that fits the cap.
    while lo <= hi:
        mid = (lo + hi) // 2
        part = Part("bark")
        r_min = thresholds[mid]
        for b in alive:
            if b.level >= 1 and b.radii[0] < r_min:
                continue
            sides = sides_for(b.radii[0], coarse)
            if b.level >= 1:
                sides = min(sides, 7)  # limbs read as round with seven sides
            if fluting > 0 and not coarse and b.level in (BOLE, LEADER):
                sides = max(sides, 15)  # enough sides for five ribs
            tube(
                part,
                _simple(b, _segments_for(b, coarse)),
                sides,
                tile,
                gnarl,
                flare,
                tree.height,
                seed_value,
                fluting=fluting,
            )
        if part.triangle_count <= cap:
            best, used = part, r_min
            hi = mid - 1
        else:
            lo = mid + 1
    if chains and best.positions and used > 0:
        # The fine twigs out to the clumps, the highest first, as far as they fit.
        plan, _ = _carry_plan(tree, chains, used, cap + carry_cap - best.triangle_count)
    if not best.positions:
        part = Part("bark")
        for b in alive:
            if b.level <= LEADER:
                tube(part, b, 4, tile, gnarl, flare, tree.height, seed_value, step=2)
        best = part
    for i in sorted(plan):
        b = tree.branches[i]
        twig = _simple(b, _carrier_segments(b, plan[i]), plan[i])
        twig.radii = [
            max(r, CARRIER_MIN_R * (1 - 0.5 * k / len(twig.radii)))
            for k, r in enumerate(twig.radii)
        ]
        tube(best, twig, _carrier_sides(b), tile, 0, 0, 0, 0, closed=False)
    return best, used, len(plan)


# Where on a clump flowers sit, as a share of its size out from its centre.
FLOWER_REACH = {"tips": (0.4, 0.55), "axils": (0.15, 0.45), "along": (0.0, 0.5)}


def _flowers_and_fruit(
    clumps: list[Clump], form: Form, rng: random.Random, coarse: bool, caps: tuple[int, int]
) -> tuple[Part, Part]:
    flowers = Part("flowers", order=[])
    fruit = Part("fruit", order=[])
    # Flowers and fruit go first on the outer, lower clumps, where they are seen.
    if clumps:
        cx = sum(c.centre[0] for c in clumps) / len(clumps)
        cz = sum(c.centre[2] for c in clumps) / len(clumps)
        top = max(c.centre[1] for c in clumps) or 1.0
        reach = max(math.hypot(c.centre[0] - cx, c.centre[2] - cz) for c in clumps) or 1.0

        def shown(c: Clump) -> float:
            out = math.hypot(c.centre[0] - cx, c.centre[2] - cz) / reach
            return out - 0.5 * c.centre[1] / top + rng.uniform(0, 0.6)

        clumps = sorted(clumps, key=shown, reverse=True)
    f_form = form.get("flowers.form")
    f_cover = float(form.get("flowers.cover"))
    if f_form != "none" and f_cover > 0:
        for c in clumps:
            if rng.random() >= f_cover:
                continue
            n = 1 if coarse else draw_int(rng, form.get("flowers.per_clump"))
            for _ in range(n):
                if flowers.triangle_count >= caps[0]:
                    break
                length = draw(rng, form.get("flowers.length_cm")) / 100 * (2.2 if coarse else 1)
                length *= float(form.get("flowers.show_scale"))
                off = vec.rotate(c.outward, UP, rng.uniform(-1.5, 1.5))
                lo, hi = FLOWER_REACH[str(form.get("flowers.where"))]
                base = vec.add(c.centre, vec.mul(off, c.size * rng.uniform(lo, hi)))
                base = vec.add(base, (0.0, rng.uniform(-0.2, 0.2) * c.size, 0.0))
                order = min(0.999, max(0.0, c.order * 0.6 + rng.random() * 0.4))
                if f_form in ("spike", "panicle") and not coarse:
                    d = vec.norm(vec.add(vec.mul(off, 0.7), (0.0, rng.uniform(-0.8, 0.3), 0.0)))
                    spike(flowers, base, d, length, max(length * 0.09, 0.004), order)
                else:
                    berry(flowers, base, max(length * 0.35, 0.01), order)
    r_form = form.get("fruit.form")
    r_cover = float(form.get("fruit.cover"))
    if r_form != "none" and r_cover > 0:
        hanging = bool(form.get("fruit.hanging"))
        for c in clumps:
            if rng.random() >= r_cover:
                continue
            # Bunches hang from the clump's lower outer side, where they show.
            anchor = vec.add(c.centre, (0.0, -c.size * 0.48, 0.0))
            anchor = vec.add(anchor, vec.mul(c.outward, c.size * 0.35))
            n = 1 if coarse else draw_int(rng, form.get("fruit.per_bunch"))
            order = c.order * 0.7 + rng.random() * 0.3
            for _ in range(n):
                if fruit.triangle_count >= caps[1]:
                    break
                show = float(form.get("fruit.show_scale"))
                length = draw(rng, form.get("fruit.length_cm")) / 100 * show
                width = draw(rng, form.get("fruit.width_cm")) / 100 * show
                if hanging and anchor[1] - length < 0.05:
                    continue
                if coarse:
                    width *= 2.5
                az = rng.uniform(0, 2 * math.pi)
                spread = rng.uniform(0.05, 0.45)
                if hanging:
                    d = vec.norm(
                        vec.add(DOWN, vec.mul(vec.from_spherical(az, math.pi / 2), spread))
                    )
                else:
                    d = vec.norm(vec.add(c.outward, (0.0, 0.5, 0.0)))
                bend_axis = vec.norm(vec.cross(d, vec.from_spherical(az + 1.3, math.pi / 2)))
                start = vec.add(
                    anchor, vec.mul(vec.from_spherical(az, math.pi / 2), rng.uniform(0, 0.06))
                )
                o = min(0.999, max(0.0, order + rng.uniform(-0.05, 0.05)))
                if r_form.startswith("pod") or r_form == "samara":
                    bend = {
                        "pod_straight": 0.15,
                        "pod_curved": 1.6,
                        "pod_coiled": 5.5,
                        "samara": 0.3,
                    }[r_form]
                    bend *= rng.uniform(0.7, 1.25)
                    ribbon(fruit, start, d, bend_axis, length, width, bend, o, 2 if coarse else 3)
                else:
                    centre = vec.add(start, vec.mul(d, length * 0.6))
                    stretch = 1.4 if r_form == "capsule" else 1.0
                    berry(fruit, centre, max(length / 2, 0.006) * (2 if coarse else 1), o, stretch)
    return flowers, fruit


def _thorns(tree: Tree, form: Form, rng: random.Random, cap: int) -> Part:
    part = Part("thorns")
    kind = form.get("thorns.kind")
    if kind == "none" or cap <= 0:
        return part
    where = form.get("thorns.where")
    spacing = float(form.get("thorns.spacing_m"))
    alive = tree.alive()
    deepest = max(b.level for b in alive)
    levels = {
        "young_twigs": {deepest, deepest - 1},
        "branches": {1, 2, 3},
        "trunk": {BOLE, LEADER},
        "all": {BOLE, LEADER, 1, 2, 3},
    }[where]
    paired = kind != "single"
    candidates = [b for b in alive if b.level in levels and b.level >= BOLE]
    rng.shuffle(candidates)
    for b in candidates:
        length = b.length
        steps = int(length * 0.85 / spacing)
        for k in range(steps):
            if part.triangle_count + (6 if paired else 3) > cap:
                return part
            t = 0.05 + 0.8 * k / max(steps, 1)
            p, tangent, r = b.point_at(t)
            roll = rng.uniform(0, 2 * math.pi)
            for s in (0, math.pi) if paired else (0,):
                side = vec.rotate(vec.perpendicular(tangent), tangent, roll + s)
                d = vec.norm(vec.add(side, vec.mul(tangent, 0.6)))
                tl = draw(rng, form.get("thorns.length_cm")) / 100
                base = vec.add(p, vec.mul(side, r * 0.9))
                cone(part, base, d, tl, max(tl * 0.13, 0.0015))
    return part


def _scale(parts: dict[str, Part], s: float) -> None:
    for part in parts.values():
        part.positions = [(p[0] * s, p[1] * s, p[2] * s) for p in part.positions]


def bounds(parts: dict[str, Part]) -> tuple[Vec, Vec]:
    pts = [p for part in parts.values() for p in part.positions]
    lo = (min(p[0] for p in pts), min(p[1] for p in pts), min(p[2] for p in pts))
    hi = (max(p[0] for p in pts), max(p[1] for p in pts), max(p[2] for p in pts))
    return lo, hi


def build(
    look: dict[str, Any], stage: str, variant: str, lod: str, budgets: dict[str, Any]
) -> Model:
    form = resolve(look, stage, variant)
    height, adult_height = _stage_height(look, stage)
    grow_height = adult_height if stage == "fallen" else height
    rng = random.Random(seed(form.key, stage))
    tree = grow_tree(form, grow_height, adult_height, rng)
    _old_and_dead(tree, form, rng)
    if stage == "fallen":
        _lay_down(tree, form, height)

    coarse = lod != "lod0"
    budget = int(budgets["triangles"][lod][stage] * 0.92)
    notes: list[str] = []
    leafless = stage in LEAFLESS
    size = 0.0
    clumps: list[Clump] = []
    if not leafless:
        lo, hi = form.range("crown.clump_size_m")
        size = (lo + hi) / 2 * min(1.0, (height / adult_height) ** 0.6)
        size = max(size, 0.06)
        clumps = crown_clumps(tree, form, size, rng)

    mesh_rng = random.Random(seed(form.key, stage, lod))
    cards = int(form.get("foliage.cards_per_clump"))
    if coarse:
        cards = max(1, min(2, cards))
    thorn_cap = 0 if coarse else int(budget * 0.04)
    flower_cap, fruit_cap = int(budget * (0.05 if coarse else 0.07)), int(budget * 0.1)
    fl = fr = Part("none")
    if leafless:
        bark_cap = int(budget * 0.95)
    else:
        # The bark gets what the foliage does not need, so sparse crowns keep their wood.
        shown = clumps if not coarse else _cluster(clumps, max(1, len(clumps) // 6), size)
        # A dry run with the same seed: how much the flowers and fruit will really take.
        fl, fr = _flowers_and_fruit(
            shown, form, random.Random(seed(form.key, stage, lod)), coarse, (flower_cap, fruit_cap)
        )
        need = min(len(shown) * cards * 2, int(budget * 0.6))
        need += fl.triangle_count + fr.triangle_count
        bark_cap = max(int(budget * 0.4), budget - thorn_cap - need)
    tipped = (
        not coarse
        and stage in form.get("tips.stages")
        and as_range(form.get("tips.twiglets"))[1] > 0
    )
    # Twiglets get their full share where nothing hides them; in leaf, a smaller one: the
    # twigs that carry the leaves come first.
    tip_share = float(form.get("tips.share")) * (1.0 if leafless else 0.4) if tipped else 0.0
    parts: dict[str, Part] = {}
    fitted: list[Clump] = []
    thorns = Part("thorns")
    if not leafless:
        thorns = _thorns(tree, form, mesh_rng, thorn_cap)
        if not coarse:
            # The foliage this model affords, fitted first: the bark then carries it.
            left = budget - bark_cap - thorns.triangle_count - fl.triangle_count
            cap = max(1, (left - fr.triangle_count) // (2 * cards))
            fitted, grow = _fit(clumps, cap)
            if grow > 1.05:
                notes.append(
                    f"{stage}-{variant}.{lod}: "
                    f"{len(clumps)} clumps over budget, kept {cap} at ×{grow:.2f} size"
                )
    bark, r_min, carried = _bark(
        tree,
        form,
        coarse,
        int(bark_cap * (1 - tip_share - (CARRY_SHARE if fitted else 0.0))),
        form.unit("bark_seed") * 10,
        fitted or None,
        int(bark_cap * CARRY_SHARE) if fitted else 0,
    )
    if r_min > 0:
        notes.append(
            f"{stage}-{variant}.{lod}: branches thinner than {r_min * 100:.1f} cm "
            + (f"drawn as {carried} fine twigs out to the leaves" if carried else "left out")
        )
    parts["bark"] = bark
    if not leafless and coarse:
        left = budget - bark.triangle_count - thorns.triangle_count
        left -= fl.triangle_count + fr.triangle_count
        fitted = _cluster(clumps, max(1, left // (2 * cards)), size)
    if tipped:
        made = _twiglets(
            tree,
            form,
            bark,
            r_min,
            bark_cap - bark.triangle_count,
            random.Random(seed(form.key, stage, "tips")),
        )
        notes.append(f"{stage}-{variant}.{lod}: {made} twiglets")
    if not leafless:
        moved = _anchor(fitted, bark.positions)
        if moved:
            notes.append(f"{stage}-{variant}.{lod}: {moved} clumps moved onto their wood")
        while True:
            flowers, fruit = _flowers_and_fruit(
                fitted,
                form,
                random.Random(seed(form.key, stage, lod, "bloom")),
                coarse,
                (flower_cap, fruit_cap),
            )
            left = budget - bark.triangle_count - flowers.triangle_count - fruit.triangle_count
            left -= thorns.triangle_count
            cap = max(1, left // (2 * cards))
            if len(fitted) <= cap:
                break
            # Over by a little: the lowest clumps go, and the flowers are placed again.
            top = max(c.centre[1] for c in fitted) or 1.0
            keep = set(
                map(id, sorted(fitted, key=lambda c: c.order - 0.6 * c.centre[1] / top)[:cap])
            )
            fitted = [c for c in fitted if id(c) in keep]
        foliage = Part("foliage", order=[])
        foliage_cards(foliage, fitted, cards, mesh_rng, _proxy(fitted, tree))
        parts.update({"foliage": foliage, "flowers": flowers, "fruit": fruit, "thorns": thorns})
    parts = {k: v for k, v in parts.items() if v.triangles}

    lo_b, hi_b = bounds(parts)
    if stage == "fallen":
        dy = -lo_b[1]
        for part in parts.values():
            part.positions = [(p[0], p[1] + dy, p[2]) for p in part.positions]
    elif hi_b[1] > 0:
        _scale(parts, height / hi_b[1])
    lo_b, hi_b = bounds(parts)
    crown = max(hi_b[0] - lo_b[0], hi_b[2] - lo_b[2])
    info = look["stages"][stage]
    extras = {
        "id": look["id"],
        "look": look["look"],
        "stage": stage,
        "variant": variant,
        "lod": lod,
        "ref_height_m": round(hi_b[1] - lo_b[1], 3),
        "ref_crown_m": round(crown, 3),
        "scale_range": info.get("scale_range", [0.75, 1.3]),
        "generator": GENERATOR,
        "params_hash": jsonio.params_hash(look.get("form")),
    }
    colours = {name: lit_colour(look["palette"], name) for name in parts}
    return Model(parts, colours, extras, notes)
