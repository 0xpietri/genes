"""The crown envelope: the shape branches are pruned to (spec §6.1, crown.*)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from plant.vec import Vec

BOTTOM = {"umbrella": 0.55, "weeping": 0.6, "columnar": 0.6, "globose": 0.15, "irregular": 0.25}


@dataclass
class Envelope:
    kind: str
    top: float  # metres, the tree's height
    base: float  # metres, where the crown starts
    radius: float  # metres, half the crown width at its widest
    widest: float  # 0–1 of the crown's depth
    flat_top: float
    irregular: float
    centre: tuple[float, float] = (0.0, 0.0)  # x, z of the crown's axis
    lobes: list[tuple[int, float, float]] = field(default_factory=list)  # (k, amplitude, phase)

    def profile(self, u: float) -> float:
        """Radius as a fraction of the widest radius, u = 0 at the crown's base, 1 at the top."""
        if u < 0 or u > 1:
            return 0.0
        up = min(max(self.widest, 0.02), 0.98)
        sharp = 6.0 if self.kind == "columnar" else 2.0
        if self.kind == "conical":
            if u < up:
                return 0.6 + 0.4 * u / up
            return float(max(0.0, 1.0 - (u - up) / (1.0 - up)) ** 1.1)
        if u < up:
            # The underside: spreading crowns are a shallow bowl, round ones close to a point.
            s = u / up
            low = 1.6 if self.kind in ("umbrella", "weeping") else sharp
            f0 = BOTTOM.get(self.kind, 0.15)
            return f0 + (1.0 - f0) * float((1.0 - (1.0 - s) ** low) ** (1.0 / low))
        t = (u - up) / (1.0 - up)
        p = sharp + 10.0 * self.flat_top**2
        return float((1.0 - min(t, 1.0) ** p) ** (1.0 / p))

    def radius_at(self, y: float, azimuth: float) -> float:
        depth = self.top - self.base
        u = (y - self.base) / depth if depth > 0 else 1.0
        if u < 0 and self.kind in ("umbrella", "weeping"):
            # Drooping limbs of spreading crowns hang below the crown's base at its edge.
            drop = 0.35 if self.kind == "weeping" else 0.2
            if u < -drop * self.top / max(depth, 1e-6):
                return 0.0
            f = 1.0
        else:
            f = self.profile(u)
        wobble = 1.0
        for k, amp, phase in self.lobes:
            wobble += self.irregular * amp * math.sin(k * azimuth + phase)
        return self.radius * f * max(wobble, 0.3)

    def inside(self, p: Vec, margin: float = 0.0) -> bool:
        if p[1] > self.top + margin:
            return False
        dx, dz = p[0] - self.centre[0], p[2] - self.centre[1]
        r = math.hypot(dx, dz)
        return r <= self.radius_at(p[1], math.atan2(dz, dx)) + margin

    def distance(self, start: Vec, direction: Vec, limit: float) -> float:
        """How far a ray from `start` runs before leaving the envelope (at most `limit`). A ray
        that starts below the crown (a leader from a low fork) counts from where it enters."""
        step = max(self.top * 0.01, 0.02)
        travelled = 0.0
        entered = self.inside(start)
        while travelled < limit:
            nxt = travelled + step
            p = (
                start[0] + direction[0] * nxt,
                start[1] + direction[1] * nxt,
                start[2] + direction[2] * nxt,
            )
            if self.inside(p):
                entered = True
            elif entered:
                return travelled
            travelled = nxt
        return limit
