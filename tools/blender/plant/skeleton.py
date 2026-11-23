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
OLD_STAGES = ("old", "dead_standing", "fallen")
SECTORS = 8


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
    free: bool = False  # grows outside the crown on purpose (sagging limbs, gap fillers)

    @property
    def length(self) -> float:
        return sum(
            vec.length(vec.sub(b, a)) for a, b in zip(self.points, self.points[1:], strict=False)
        )

    def fraction(self, k: int) -> float:
        """Where point k sits along the branch, 0–1 of its length."""
        total = self.length
        if total <= 0:
            return 0.0
        run = sum(
            vec.length(vec.sub(self.points[i + 1], self.points[i]))
            for i in range(min(k, len(self.points) - 1))
        )
        return run / total

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
    adult_height: float = 0.0
    # How much limb has gone each way so far (8 compass sectors), to keep the crown even.
    sectors: list[float] = field(default_factory=lambda: [0.0] * SECTORS)
    rest_sectors: list[float] = field(default_factory=lambda: [0.0] * SECTORS)

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
    bend: float = 0.0  # tortuosity: big slow S-bends, not the small zig-zag of wander
    bend_fade: float = 0.0  # how much the bends calm down towards the tip (0–1)
    bend_waves: tuple[float, float] = (0.8, 1.6)  # bends along the branch
    elbows: bool = False  # angular kinks instead of smooth S-curves
    rest: bool = False  # sags to the ground, lies along it and rises again
    full: float = 1.0  # >1 keeps the branch thick for longer before it thins


def _bends(g: Growth, rng: random.Random) -> tuple[float, ...] | None:
    """The shape of a branch's slow bends, drawn once: two waves along it, and how the
    plane they bend in turns, so the trunk snakes in three dimensions."""
    if g.bend <= 0:
        return None
    return (
        rng.uniform(*g.bend_waves),  # waves along the branch
        rng.uniform(0, 2 * math.pi),
        rng.uniform(0, 2 * math.pi),
        rng.uniform(0, 2 * math.pi),  # first bending plane
        rng.uniform(-0.6, 0.6),  # turns of that plane along the branch
    )


def _bend_angle(g: Growth, shape: tuple[float, ...], s: float) -> float:
    waves, ph1, ph2 = shape[0], shape[1], shape[2]

    def f(x: float) -> float:
        return math.sin(2 * math.pi * waves * x + ph1) + 0.45 * math.sin(
            2 * math.pi * 2.3 * waves * x + ph2
        )

    # At most about 35 degrees off the branch's course: crooked, never folded over.
    if g.elbows:
        # Straight runs between kinks: the course jumps at each elbow.
        step = 1 / max(2 * waves, 1.0)
        s = math.floor(s / step) * step + step * 0.5
    wave = max(-1.0, min(1.0, (f(s) - f(0.0)) / 1.8))
    return g.bend * 0.62 * wave * (1 - g.bend_fade * s)


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
    shape = _bends(g, rng)
    droop = g.droop
    ground_left = -1  # steps still to lie on the ground; -1 = not reached it yet
    floor = r0 * 0.95  # the limb lies on the ground, not in it
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
        if droop > 0:
            weight = 2.0 * (i + 1) / n
            d = vec.rotate_towards(d, (0.0, -1.0, 0.0), droop * (math.pi / 2.2) * weight / n)
        step = d
        if shape is not None:
            s = (i + 0.5) / n
            ref = vec.cross(d, UP)
            ref = vec.norm(ref) if vec.length(ref) > 1e-3 else vec.perpendicular(d)
            axis = vec.rotate(ref, d, shape[3] + 2 * math.pi * shape[4] * s)
            step = vec.norm(vec.rotate(d, axis, _bend_angle(g, shape, s)))
        nxt = vec.add(p, vec.mul(step, dl))
        if g.rest and (nxt[1] < floor or ground_left > 0):
            # On the ground: run along it a while, then turn up again.
            flat = vec.horizontal(d)
            d = vec.norm(flat) if vec.length(flat) > 1e-3 else vec.perpendicular(UP)
            if ground_left < 0:
                ground_left = max(1, round(n * rng.uniform(0.12, 0.25)))
            nxt = vec.add(p, vec.mul(d, dl))
            nxt = (nxt[0], floor, nxt[2])
            ground_left -= 1
            if ground_left == 0:
                d = vec.norm(vec.rotate_towards(d, UP, rng.uniform(0.5, 0.9)))
                droop = 0.0
                ground_left = -2  # done: rises and never comes down again
        elif not g.rest and env is not None and nxt[1] < env.top * 0.06:
            break  # drooping limbs stop above the ground
        if g.rest:
            pass  # a resting limb leaves the crown on purpose
        elif env is not None and env.inside(nxt):
            entered = True
        elif env is not None and entered:
            if len(pts) == 1:
                pts.append(vec.add(p, vec.mul(step, dl * 0.5)))
            break
        pts.append(nxt)
        p = nxt
    count = len(pts)
    if count == 1:
        return pts, [r0]
    radii = [r0 + (r1 - r0) * (i / (count - 1)) ** g.full for i in range(count)]
    return pts, radii


def _sector(tree: Tree, p: Vec) -> int:
    env = tree.envelope
    az = math.atan2(p[2] - env.centre[1], p[0] - env.centre[0]) % (2 * math.pi)
    return int(az / (2 * math.pi / SECTORS)) % SECTORS


def _balanced(
    tree: Tree,
    start: Vec,
    d: Vec,
    length: float,
    rest: bool,
    balance: float,
    rng: random.Random,
) -> Vec:
    """Turn a main limb so that it ends on the side of the crown that has the least so far:
    the tree spreads the same on every side, its sagging limbs reach the ground all round.
    A limb never turns back across its own stem (at most about 110 degrees from outwards)."""
    sectors = tree.rest_sectors if rest else tree.sectors
    env = tree.envelope
    flat = math.hypot(d[0], d[2])
    width = 2 * math.pi / SECTORS
    if flat > 1e-3 and rng.random() < balance:
        off = (start[0] - env.centre[0], start[2] - env.centre[1])
        spread = math.hypot(*off)
        out = math.atan2(off[1], off[0])
        order = sorted(range(SECTORS), key=lambda k: (sectors[k], rng.random()))
        for k in order:
            az = (k + rng.uniform(0.2, 0.8)) * width
            reach = max(env.radius * 0.75, spread + flat * length * 0.5)
            target = (env.centre[0] + reach * math.cos(az), env.centre[1] + reach * math.sin(az))
            heading = math.atan2(target[1] - start[2], target[0] - start[0])
            turn = abs((heading - out + math.pi) % (2 * math.pi) - math.pi)
            if spread < env.radius * 0.15 or turn < math.radians(110):
                d = (flat * math.cos(heading), d[1], flat * math.sin(heading))
                break
    tip = vec.add(start, vec.mul(d, length))
    sectors[_sector(tree, tip)] += length * max(flat, 0.2)
    return d


def _bend_style(form: Form) -> tuple[tuple[float, float], bool]:
    return form.range("trunk.bends"), form.get("trunk.bend_style") == "elbows"


def _segments(level: int, length: float, height: float, bend: float = 0.0) -> int:
    most = {BOLE: 8, LEADER: 10, 1: 7, 2: 5, 3: 3}[level]
    if bend > 0 and level <= 1:
        most += round(4 * min(bend, 1.0))  # bends need more rings to stay round
    step = height * (0.035 - 0.015 * min(bend, 1.0))
    return max(2, min(most, round(length / max(step, 0.05))))


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
    # Old trees: the trunk opens from near the ground into stems that rise side by side.
    opened = float(form.get("old.trunk_split")) if form.stage in OLD_STAGES else 0.0
    if opened > 0:
        count = max(count, 2)
        split = split * (1 - opened) + 0.03 * opened
    twist = form.ind("trunk.twist")
    # Crookedness comes with age: a sapling is nearly straight.
    bend = form.ind("trunk.tortuosity") * min(1.0, height / adult_height) ** 0.8
    style = _bend_style(form)
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

    bole_growth = Growth(
        curve=0.12, droop=0.0, wander=twist * 0.5, bend=bend, bend_waves=style[0], elbows=style[1]
    )
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
            _segments(BOLE, length, height, bend),
        )
        branches.append(Branch(BOLE, pts, radii))
        fork, fork_r = pts[-1], radii[-1]
        top_dir = vec.norm(vec.sub(pts[-1], pts[-2]))
    else:
        fork, fork_r, top_dir = (0.0, 0.0, 0.0), trunk_r, trunk_dir

    leader_growth = Growth(
        curve=form.ind("trunk.leader_curve"),
        droop=0.0,
        wander=twist * 0.45,
        bend=bend,
        bend_fade=0.7,  # crooked low down, still reaching the crown's edge
        full=1.6,
        bend_waves=style[0],
        elbows=style[1],
    )
    reach = form.ind("trunk.leader_reach")
    az0 = 2 * math.pi * form.unit("leader_azimuth")
    leader_r = fork_r * count ** (-1 / 2.8)  # stems as thick as fused trunks
    bole = 0 if branches else None
    for i in range(count):
        if count == 1:
            d = top_dir
            length = (height - fork[1]) * 0.97 / max(d[1], 0.3)
        else:
            az = az0 + 2 * math.pi * i / count + rng.uniform(-0.35, 0.35) * math.pi / count
            tilt = math.radians(draw(rng, form.get("trunk.fork_angle_deg")))
            tilt *= 1 - 0.75 * opened  # split stems rise close together, then part
            d = vec.norm(vec.add(vec.from_spherical(az, tilt), vec.mul(vec.sub(top_dir, UP), 0.8)))
            to_edge = env.distance(fork, d, height * 2)
            length = max(reach * to_edge, height * 0.2)
        r0 = leader_r * rng.uniform(0.85, 1.1) if count > 1 else fork_r
        r1 = max(twig_r * 2, r0 * (1 - taper) * 0.5)
        start = fork
        if opened > 0 and count > 1:
            # Each stem stands on its own part of the stump, so a crack opens between them.
            side = vec.from_spherical(az, math.pi / 2)
            start = vec.add(fork, vec.mul(side, fork_r * 0.4 * opened))
            r0 = max(r0, fork_r * 0.72)
        pts, radii = grow(
            start,
            d,
            length,
            r0,
            r1,
            leader_growth,
            rng,
            env if count > 1 else None,
            _segments(LEADER, length, height, bend),
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

    tree = Tree(height, env, branches, twig_r, adult_height)
    for b in branches:
        if b.level == LEADER and len(b.points) > 1:
            tree.sectors[_sector(tree, b.points[-1])] += b.length * 0.5
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
    age = min(1.0, tree.height / max(tree.adult_height, 1e-6)) ** 0.8
    bend = form.ind("trunk.tortuosity") * 0.6 * age  # main limbs snake too, a little less
    style = _bend_style(form)
    env = tree.envelope
    made: list[int] = []
    roll_kind = lv["roll"]
    aged = form.stage in ("old", "dead_standing")
    sag = float(form.get("old.limb_sag")) if aged else 0.0
    sagging = float(form.get("old.sagging_limbs")) if aged and sag > 0 else 0.0
    balance = float(form.get("crown.balance"))
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
            # Old trees: some low main limbs sag; at the far end of the scale they reach
            # the ground, lie along it and rise again.
            rest = level == 1 and sagging > 0 and t < 0.5 and rng.random() < sagging
            if p[1] < env.base - 0.05 * tree.height and level == 1 and not rest:
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
            if rest:
                angle = max(angle, math.radians(rng.uniform(65, 85)))
            d = vec.norm(vec.rotate(tangent, axis, angle))
            near_tip = max(0.0, (t - 0.5) / 0.5)
            length = draw(rng, lv["length"]) * plen * (1 - 0.5 * near_tip)
            if rest:
                length = max(length, plen * rng.uniform(0.9, 1.25))
            if level == 1:
                d = _balanced(tree, p, d, length, rest, balance, rng)
            length = max(length, tree.height * 0.03)
            r0 = min(pr * draw(rng, lv["radius_ratio"]), pr * 0.9)
            r0 = max(r0, tree.twig_radius)
            r1 = max(tree.twig_radius, r0 * (1 - taper) * 0.5)
            if "tortuosity" in lv:
                lv_bend = draw(rng, lv["tortuosity"]) * age
            else:
                lv_bend = bend if level == 1 else 0.0
            g = Growth(
                curve=draw(rng, lv["curve"]),
                droop=draw(rng, lv["droop"]),
                wander=draw(rng, lv["wander"]),
                bend=max(lv_bend, bend / 0.6) if rest else lv_bend,
                full=1.4 if level == 1 else 1.0,
                bend_waves=style[0],
                elbows=lv.get("bend_style", "elbows" if style[1] else "smooth") == "elbows",
            )
            if rest:
                g.droop, g.curve = 0.25 + 0.85 * sag, 0.0
                g.rest = sag >= 0.8
                r0 = max(r0, pr * 0.8)  # the big low limbs are nearly trunk-thick
                r1 = max(r1, r0 * 0.6)
            pts, radii = grow(
                p,
                d,
                length,
                r0,
                r1,
                g,
                rng,
                None if rest else env,
                _segments(level, length, tree.height, g.bend) + (5 if rest else 0),
            )
            if len(pts) < 2:
                continue
            free = rest or parent.free
            tree.branches.append(Branch(level, pts, radii, parent=pi, at=t, free=free))
            idx = len(tree.branches) - 1
            parent.children.append(idx)
            made.append(idx)
    return made


def _top_at(env: Envelope, x: float, z: float) -> float | None:
    """The crown's upper surface above (x, z): the highest height still inside it."""
    step = max(env.top * 0.015, 0.02)
    y = env.top
    while y > env.base:
        if env.inside((x, y, z)):
            return y
        y -= step
    return None


def _twig_growth(form: Form, level: int, age: float) -> Growth:
    """The crooked thin growth of the crown's upper twigs."""
    lv = next((x for x in form.levels if int(x["level"]) == level), None)
    if lv is not None and "tortuosity" in lv:
        tort = lv["tortuosity"]
        lo, hi = (tort, tort) if isinstance(tort, (int, float)) else tort
        bend = (float(lo) + float(hi)) / 2 * age
    else:
        bend = form.ind("trunk.tortuosity") * 0.6 * age
    style = lv.get("bend_style") if lv is not None else None
    elbows = (style or form.get("trunk.bend_style")) == "elbows"
    return Growth(
        curve=0.15, droop=0.0, wander=0.25, bend=bend, bend_waves=(1.0, 2.0), elbows=elbows
    )


def fill_crown(
    tree: Tree, form: Form, covered: list[Vec], size: float, rng: random.Random
) -> list[int]:
    """Trees have leaves on top. Where no foliage reaches the crown's upper surface, a thin
    crooked branch rises from the nearest limb below, with twigs at its end; returns the new
    branches. `covered` are the centres of the foliage clumps already there."""
    amount = float(form.get("crown.fill_top"))
    alive = [(i, b) for i, b in enumerate(tree.branches) if not b.removed]
    deepest = max(b.level for _, b in alive)
    if amount <= 0 or deepest < 1 or tree.height < 1.0:
        return []
    env = tree.envelope
    age = min(1.0, tree.height / max(tree.adult_height, 1e-6)) ** 0.8
    spacing = size * 1.05
    reach = env.radius * 1.2
    cells = int(2 * reach / spacing) + 1
    upper = env.base + 0.4 * (env.top - env.base)
    # The top is where the tree's foliage already reaches, not above it.
    roof = max((c[1] for c in covered), default=env.top)
    targets: list[Vec] = []
    for i in range(cells):
        for j in range(cells):
            x = env.centre[0] - reach + (i + rng.uniform(0.2, 0.8)) * spacing
            z = env.centre[1] - reach + (j + rng.uniform(0.2, 0.8)) * spacing
            y = _top_at(env, x, z)
            if y is None or y < upper:
                continue
            top = min(y, roof)
            targets.append((x, top - size * rng.uniform(0.25, 0.6), z))
            # A second layer under it: the crown is a thick dome, not a skin.
            if top - size * 2 > upper:
                targets.append((x, top - size * rng.uniform(1.4, 2.0), z))
    rng.shuffle(targets)
    sources = [
        (i, b)
        for i, b in alive
        if (LEADER <= b.level < deepest or (deepest == 1 and b.level == LEADER)) and not b.free
    ]
    near = size * 0.95
    have = list(covered)
    made: list[int] = []
    for tgt in targets:
        if rng.random() > amount:
            continue
        if any(
            math.hypot(tgt[0] - c[0], tgt[2] - c[2]) < near and c[1] > tgt[1] - size for c in have
        ):
            continue
        best: tuple[float, int, int] | None = None
        for i, b in sources:
            for k, p in enumerate(b.points[:-1]):
                if p[1] > tgt[1] - size * 0.4 or b.radii[k] < tree.twig_radius * 2:
                    continue
                d = vec.length(vec.sub(tgt, p))
                if best is None or d < best[0]:
                    best = (d, i, k)
        if best is None or best[0] > tree.height * 0.9:
            continue
        dist, pi, k = best
        parent = tree.branches[pi]
        start = parent.points[k]
        level = min(parent.level + 1, deepest)
        level = max(level, 1)
        g = _twig_growth(form, level, age)
        r0 = max(tree.twig_radius * 1.5, min(parent.radii[k] * 0.5, 0.035 * best[0]))
        pts, radii = grow(
            start,
            vec.norm(vec.sub(tgt, start)),
            dist,
            r0,
            tree.twig_radius,
            g,
            rng,
            None,
            _segments(max(level, 2), dist, tree.height, g.bend),
        )
        if len(pts) < 2:
            continue
        riser = Branch(level, pts, radii, parent=pi, at=parent.fraction(k), free=True)
        tree.branches.append(riser)
        idx = len(tree.branches) - 1
        parent.children.append(idx)
        made.append(idx)
        have.append(pts[-1])
        if level >= deepest:
            continue
        # A few crooked twigs fan out from its upper half, so the top is a net, not a stick.
        tg = _twig_growth(form, deepest, age)
        for _ in range(rng.randint(2, 4)):
            t = rng.uniform(0.45, 0.95)
            p, tangent, pr = riser.point_at(t)
            axis = vec.rotate(vec.perpendicular(tangent), tangent, rng.uniform(0, 2 * math.pi))
            out = vec.norm(vec.rotate(tangent, axis, math.radians(rng.uniform(30, 60))))
            flat = vec.horizontal(out)
            if vec.length(flat) > 1e-3:  # they spread under the crown's surface, not above it
                out = vec.norm(vec.add(vec.norm(flat), vec.mul(UP, 0.25)))
            length = min(max(dist * rng.uniform(0.3, 0.5), size * 0.6), size * 1.3)
            tp, tr = grow(
                p, out, length, max(pr * 0.7, tree.twig_radius), tree.twig_radius, tg, rng, None, 3
            )
            if len(tp) < 2:
                continue
            tree.branches.append(Branch(deepest, tp, tr, parent=idx, at=t, free=True))
            riser.children.append(len(tree.branches) - 1)
            made.append(len(tree.branches) - 1)
            have.append(tp[-1])
    return made
