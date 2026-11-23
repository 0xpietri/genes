"""Growing the branch skeleton (spec §7.2): a trunk, its leaders and up to three
branching levels, stepped Weber–Penn style and pruned to the crown envelope.

Levels: -1 is the bole (the trunk below the fork), 0 the leaders (or the single
main axis), 1..3 the branching levels of the look.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from plant import vec
from plant.envelope import Envelope
from plant.form import Form, draw, draw_int
from plant.vec import UP, Vec

BOLE = -1
LEADER = 0


@dataclass
class Branch:
    level: int
    points: list[Vec]
    radii: list[float]
    parent: int | None = None
    at: float = 0.0  # where on the parent, 0–1 of its length
    children: list[int] = field(default_factory=list)
    removed: bool = False
    broken: bool = False  # ends in a break, not a tip

    @property
    def length(self) -> float:
        return sum(
            vec.length(vec.sub(b, a)) for a, b in zip(self.points, self.points[1:], strict=False)
        )

    def point_at(self, t: float) -> tuple[Vec, Vec, float]:
        """Position, tangent and radius at fraction t of the length."""
        total = self.length
        if total <= 0 or len(self.points) < 2:
            return self.points[0], UP, self.radii[0]
        want = min(max(t, 0.0), 1.0) * total
        run = 0.0
        for i in range(len(self.points) - 1):
            a, b = self.points[i], self.points[i + 1]
            seg = vec.length(vec.sub(b, a))
            if run + seg >= want or i == len(self.points) - 2:
                f = 0.0 if seg <= 0 else min(max((want - run) / seg, 0.0), 1.0)
                r = self.radii[i] + (self.radii[i + 1] - self.radii[i]) * f
                return vec.lerp(a, b, f), vec.norm(vec.sub(b, a)), r
            run += seg
        return self.points[-1], UP, self.radii[-1]

    def cut(self, t: float) -> None:
        """Keep only the first fraction t of the branch."""
        p, _, r = self.point_at(t)
        total = self.length
        want = t * total
        run = 0.0
        keep_p: list[Vec] = [self.points[0]]
        keep_r: list[float] = [self.radii[0]]
        for i in range(len(self.points) - 1):
            seg = vec.length(vec.sub(self.points[i + 1], self.points[i]))
            if run + seg >= want:
                break
            run += seg
            keep_p.append(self.points[i + 1])
            keep_r.append(self.radii[i + 1])
        keep_p.append(p)
        keep_r.append(r)
        self.points, self.radii = keep_p, keep_r
        self.broken = True


@dataclass
class Tree:
    height: float
    envelope: Envelope
    branches: list[Branch]
    twig_radius: float

    def alive(self) -> list[Branch]:
        return [b for b in self.branches if not b.removed]

    def remove(self, index: int) -> None:
        self.branches[index].removed = True
        for c in self.branches[index].children:
            self.remove(c)

    def cut(self, index: int, t: float) -> None:
        """Break branch `index` at t; its children beyond the break go with it."""
        b = self.branches[index]
        b.cut(t)
        for c in b.children:
            if self.branches[c].at > t:
                self.remove(c)
            else:
                self.branches[c].at = self.branches[c].at / t if t > 0 else 0.0


@dataclass
class Growth:
    curve: float
    droop: float
    wander: float


def grow(
    start: Vec,
    direction: Vec,
    length: float,
    r0: float,
    r1: float,
    g: Growth,
    rng: random.Random,
    env: Envelope | None,
    segments: int,
) -> tuple[list[Vec], list[float]]:
    """Step a branch from `start`: wander, curve and droop at every step, and stop where it
    leaves the envelope."""
    n = max(2, segments)
    dl = length / n
    d = vec.norm(direction)
    pts: list[Vec] = [start]
    p = start
    entered = env is None or env.inside(start)
    for i in range(n):
        if g.wander > 0:
            axis = vec.rotate(vec.perpendicular(d), d, rng.uniform(0, 2 * math.pi))
            d = vec.norm(vec.rotate(d, axis, rng.gauss(0, g.wander * 0.3)))
        if g.curve > 0:
            d = vec.rotate_towards(d, UP, g.curve * (math.pi / 3) / n)
        elif g.curve < 0:
            out = vec.horizontal(d)
            target = (
                vec.norm(vec.sub(vec.norm(out), vec.mul(UP, 0.35))) if vec.length(out) > 1e-3 else d
            )
            d = vec.rotate_towards(d, target, -g.curve * (math.pi / 3) / n)
        if g.droop > 0:
            weight = 2.0 * (i + 1) / n
            d = vec.rotate_towards(d, (0.0, -1.0, 0.0), g.droop * (math.pi / 2.2) * weight / n)
        nxt = vec.add(p, vec.mul(d, dl))
        if env is not None and nxt[1] < env.top * 0.06:
            break  # drooping limbs stop above the ground
        if env is not None and env.inside(nxt):
            entered = True
        elif env is not None and entered:
            if len(pts) == 1:
                pts.append(vec.add(p, vec.mul(d, dl * 0.5)))
            break
        pts.append(nxt)
        p = nxt
    count = len(pts)
    if count == 1:
        return pts, [r0]
    radii = [r0 + (r1 - r0) * (i / (count - 1)) for i in range(count)]
    return pts, radii


def _segments(level: int, length: float, height: float) -> int:
    most = {BOLE: 8, LEADER: 10, 1: 7, 2: 5, 3: 3}[level]
    return max(2, min(most, round(length / max(height * 0.035, 0.05))))


def make_envelope(form: Form, height: float, centre: tuple[float, float]) -> Envelope:
    width = form.ind("crown.width_to_height") * height
    lobes = [(k, 0.35 / k**0.3, 2 * math.pi * form.unit(f"lobe{k}")) for k in (2, 3, 5)]
    return Envelope(
        kind=form.get("crown.envelope"),
        top=height,
        base=form.ind("crown.base") * height,
        radius=width / 2,
        widest=form.ind("crown.widest"),
        flat_top=form.ind("crown.flat_top"),
        irregular=form.ind("crown.irregular"),
        centre=centre,
        lobes=lobes,
    )


def grow_tree(form: Form, height: float, adult_height: float, rng: random.Random) -> Tree:
    """The whole skeleton for one stage of one variant, `height` metres tall."""
    lean = math.radians(form.ind("trunk.lean_deg"))
    if form.stage in ("old", "dead_standing", "fallen"):
        lean += math.radians(form.ind("old.extra_lean_deg"))
    lean_az = 2 * math.pi * form.unit("lean_azimuth")
    trunk_dir = vec.from_spherical(lean_az, lean)
    count = max(1, form.ind_int("trunk.count"))
    split = form.ind("trunk.split_height")
    twist = form.ind("trunk.twist")
    taper = form.ind("trunk.taper")
    # Radius grows faster than height (allometry), so small stages are slender.
    rph = form.ind("trunk.radius_per_height")
    trunk_r = rph * adult_height * (height / adult_height) ** 1.35
    trunk_r = max(trunk_r, 0.003)
    twig_r = max(0.0035 * math.sqrt(height / max(adult_height, 1e-6)), 0.0015)

    branches: list[Branch] = []
    fork_h = split * height if count > 1 else 0.0
    # The crown's axis passes over the leaning trunk.
    drift = math.tan(lean) * height * 0.6
    centre = (math.cos(lean_az) * drift, math.sin(lean_az) * drift)
    env = make_envelope(form, height, centre)

    bole_growth = Growth(curve=0.12, droop=0.0, wander=twist * 0.5)
    if fork_h > 0.02 * height:
        length = fork_h / max(math.cos(lean), 0.3)
        pts, radii = grow(
            (0.0, 0.0, 0.0),
            trunk_dir,
            length,
            trunk_r,
            trunk_r * (1 - 0.25 * taper),
            bole_growth,
            rng,
            None,
            _segments(BOLE, length, height),
        )
        branches.append(Branch(BOLE, pts, radii))
        fork, fork_r = pts[-1], radii[-1]
        top_dir = vec.norm(vec.sub(pts[-1], pts[-2]))
    else:
        fork, fork_r, top_dir = (0.0, 0.0, 0.0), trunk_r, trunk_dir

    leader_growth = Growth(curve=form.ind("trunk.leader_curve"), droop=0.0, wander=twist * 0.45)
    reach = form.ind("trunk.leader_reach")
    az0 = 2 * math.pi * form.unit("leader_azimuth")
    leader_r = fork_r * count ** (-1 / 2.3)
    bole = 0 if branches else None
    for i in range(count):
        if count == 1:
            d = top_dir
            length = (height - fork[1]) * 0.97 / max(d[1], 0.3)
        else:
            az = az0 + 2 * math.pi * i / count + rng.uniform(-0.35, 0.35) * math.pi / count
            tilt = math.radians(draw(rng, form.get("trunk.fork_angle_deg")))
            d = vec.norm(vec.add(vec.from_spherical(az, tilt), vec.mul(vec.sub(top_dir, UP), 0.8)))
            to_edge = env.distance(fork, d, height * 2)
            length = max(reach * to_edge, height * 0.2)
        r0 = leader_r * rng.uniform(0.85, 1.1) if count > 1 else fork_r
        r1 = max(twig_r * 2, r0 * (1 - taper) * 0.5)
        pts, radii = grow(
            fork,
            d,
            length,
            r0,
            r1,
            leader_growth,
            rng,
            env if count > 1 else None,
            _segments(LEADER, length, height),
        )
        if len(pts) < 2:
            pts.append(vec.add(fork, vec.mul(d, height * 0.05)))
            radii = [r0, r1]
        if bole is None and fork_h <= 0.02 * height and count == 1:
            # One axis from the ground: it is the bole and the leader at once.
            pts[0] = (0.0, 0.0, 0.0)
        branches.append(Branch(LEADER, pts, radii, parent=bole, at=1.0))
        if bole is not None:
            branches[bole].children.append(len(branches) - 1)

    tree = Tree(height, env, branches, twig_r)
    parents = [i for i, b in enumerate(branches) if b.level == LEADER]
    for lv in form.levels:
        parents = _grow_level(tree, parents, lv, form, rng)
    return tree


def _grow_level(
    tree: Tree, parents: list[int], lv: dict[str, object], form: Form, rng: random.Random
) -> list[int]:
    level = int(lv["level"])  # type: ignore[call-overload]
    lengths = [tree.branches[i].length for i in parents]
    mean = sum(lengths) / len(lengths) if lengths else 1.0
    s0, s1 = (float(x) for x in lv["start"])  # type: ignore[attr-defined]
    taper = form.ind("trunk.taper")
    env = tree.envelope
    made: list[int] = []
    roll_kind = lv["roll"]
    for pi in parents:
        parent = tree.branches[pi]
        plen = parent.length
        if plen <= 0:
            continue
        n = round(draw_int(rng, lv["count"]) * min(max(plen / mean, 0.3), 1.8))
        roll = rng.uniform(0, 2 * math.pi)
        for j in range(n):
            t = s0 + (s1 - s0) * (j + rng.uniform(0.15, 0.85)) / max(n, 1)
            p, tangent, pr = parent.point_at(t)
            if p[1] < env.base - 0.05 * tree.height and level == 1:
                continue
            if roll_kind == "opposite":
                roll_j = roll + (j % 2) * math.pi + (j // 2) * math.pi / 2
            elif roll_kind == "alternate":
                roll_j = roll + (j % 2) * math.pi + rng.uniform(-0.3, 0.3)
            else:
                roll_j = roll + j * 2.39996 + rng.uniform(-0.3, 0.3)
            ref = vec.cross(tangent, UP)
            ref = vec.norm(ref) if vec.length(ref) > 1e-3 else vec.perpendicular(tangent)
            axis = vec.norm(vec.rotate(ref, tangent, roll_j))
            angle = math.radians(draw(rng, lv["angle_deg"]))
            d = vec.norm(vec.rotate(tangent, axis, angle))
            near_tip = max(0.0, (t - 0.5) / 0.5)
            length = draw(rng, lv["length"]) * plen * (1 - 0.5 * near_tip)
            length = max(length, tree.height * 0.03)
            r0 = min(pr * draw(rng, lv["radius_ratio"]), pr * 0.9)
            r0 = max(r0, tree.twig_radius)
            r1 = max(tree.twig_radius, r0 * (1 - taper) * 0.5)
            g = Growth(
                curve=draw(rng, lv["curve"]),
                droop=draw(rng, lv["droop"]),
                wander=draw(rng, lv["wander"]),
            )
            pts, radii = grow(
                p, d, length, r0, r1, g, rng, env, _segments(level, length, tree.height)
            )
            if len(pts) < 2:
                continue
            tree.branches.append(Branch(level, pts, radii, parent=pi, at=t))
            idx = len(tree.branches) - 1
            parent.children.append(idx)
            made.append(idx)
    return made
