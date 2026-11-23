"""Code-made test models for the example species (phase 1, no Blender).

They follow the model contract (spec §8) so the viewer, the checks and pietri.dev have
something real to load: a cylinder trunk, foliage as clumps of small balls with a per-vertex
_ORDER, flower and fruit dots. The real plant generator (phase 2) replaces this for real species.
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any

from genes import glb, jsonio
from genes.species import expected_models, model_name

GENERATOR = "example@1"


def _srgb_to_linear(hex_colour: str) -> tuple[float, float, float]:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    h = hex_colour.lstrip("#")
    return (
        round(channel(int(h[0:2], 16)), 6),
        round(channel(int(h[2:4], 16)), 6),
        round(channel(int(h[4:6], 16)), 6),
    )


def _lit(palette: dict[str, Any], part: str) -> tuple[float, float, float]:
    tones = palette[part]
    if "lit" not in tones:
        tones = tones.get("mature") or next(iter(tones.values()))
    return _srgb_to_linear(tones["lit"])


class _Builder:
    def __init__(self) -> None:
        self.positions: list[glb.Vec3] = []
        self.normals: list[glb.Vec3] = []
        self.indices: list[int] = []
        self.order: list[float] = []

    def cylinder(
        self,
        base: glb.Vec3,
        top: glb.Vec3,
        r0: float,
        r1: float,
        segments: int,
        horizontal: bool = False,
    ) -> None:
        """A tube from base to top. `horizontal` keeps both rings level (a leaning trunk that
        still stands flat on the ground)."""
        bx, by, bz = base
        tx, ty, tz = top
        ax, ay, az = tx - bx, ty - by, tz - bz
        length = math.sqrt(ax * ax + ay * ay + az * az)
        ax, ay, az = ax / length, ay / length, az / length
        # Two vectors perpendicular to the axis.
        ux, uy, uz = (1.0, 0.0, 0.0) if abs(ay) > 0.9 else (0.0, 1.0, 0.0)
        px, py, pz = ay * uz - az * uy, az * ux - ax * uz, ax * uy - ay * ux
        n = math.sqrt(px * px + py * py + pz * pz)
        px, py, pz = px / n, py / n, pz / n
        qx, qy, qz = ay * pz - az * py, az * px - ax * pz, ax * py - ay * px
        if horizontal:
            px, py, pz, qx, qy, qz = 1.0, 0.0, 0.0, 0.0, 0.0, 1.0
        start = len(self.positions)
        for ring, (cx, cy, cz, r) in enumerate(((bx, by, bz, r0), (tx, ty, tz, r1))):
            del ring
            for i in range(segments):
                a = 2 * math.pi * i / segments
                dx = math.cos(a) * px + math.sin(a) * qx
                dy = math.cos(a) * py + math.sin(a) * qy
                dz = math.cos(a) * pz + math.sin(a) * qz
                self.positions.append((cx + r * dx, cy + r * dy, cz + r * dz))
                self.normals.append((dx, dy, dz))
                self.order.append(0.0)
        for i in range(segments):
            j = (i + 1) % segments
            a, b, c, d = start + i, start + j, start + segments + i, start + segments + j
            self.indices += [a, b, d, a, d, c]

    def ball(self, centre: glb.Vec3, radius: float, order: float, squash: float = 1.0) -> None:
        """An octahedron subdivided once: 32 triangles, smooth normals."""
        cx, cy, cz = centre
        corners = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
        faces = [
            (0, 2, 4),
            (4, 2, 1),
            (1, 2, 5),
            (5, 2, 0),
            (4, 3, 0),
            (1, 3, 4),
            (5, 3, 1),
            (0, 3, 5),
        ]
        tris: list[tuple[glb.Vec3, glb.Vec3, glb.Vec3]] = []

        def unit(v: tuple[float, float, float]) -> glb.Vec3:
            n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
            return (v[0] / n, v[1] / n, v[2] / n)

        def mid(a: glb.Vec3, b: glb.Vec3) -> glb.Vec3:
            return unit(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2))

        for f in faces:
            a, b, c = (unit(tuple(float(x) for x in corners[i])) for i in f)  # type: ignore[arg-type]
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            tris += [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]
        shared: dict[tuple[float, float, float], int] = {}
        for tri in tris:
            for v in tri:
                key = (round(v[0], 6), round(v[1], 6), round(v[2], 6))
                if key not in shared:
                    shared[key] = len(self.positions)
                    self.positions.append(
                        (cx + radius * v[0], cy + radius * v[1] * squash, cz + radius * v[2])
                    )
                    self.normals.append(v)
                    self.order.append(order)
                self.indices.append(shared[key])

    def mesh(self, name: str, colour: tuple[float, float, float], with_order: bool) -> glb.MeshData:
        custom = {"_ORDER": [round(o, 4) for o in self.order]} if with_order else {}
        rounded = [(round(x, 5), round(y, 5), round(z, 5)) for x, y, z in self.positions]
        normals = [(round(x, 5), round(y, 5), round(z, 5)) for x, y, z in self.normals]
        return glb.MeshData(name, rounded, normals, self.indices, colour, custom)


def build_model(look: dict[str, Any], stage: str, variant: str, lod: str) -> bytes:
    """One example model, deterministic for (look form, stage, variant, lod)."""
    form = look["form"]
    stage_info = look["stages"][stage]
    height = float(stage_info["ref_height_m"])
    crown_w = float(stage_info.get("ref_crown_m", height * 0.8))
    seed = f"{look['id']}|{stage}|{variant}"
    rng = random.Random(seed)
    detailed = lod == "lod0"
    segments = 10 if detailed else 5
    clumps = int(form["clumps"] if detailed else max(4, form["clumps"] // 4))

    trunk_h = height * float(form["trunk_fraction"])
    lean = math.radians(rng.uniform(-form["lean_deg"], form["lean_deg"]))
    top = (math.sin(lean) * trunk_h, trunk_h, 0.0)
    trunk_r = max(0.02, height * float(form["trunk_radius_per_height"]))

    bark = _Builder()
    bark.cylinder((0.0, 0.0, 0.0), top, trunk_r, trunk_r * 0.6, segments, horizontal=True)
    meshes = []
    dead = stage == "dead_standing"
    limbs = 3 if dead else 0
    for i in range(limbs):
        a = 2 * math.pi * (i + rng.random() * 0.5) / limbs
        reach = crown_w * 0.35
        end_y = height if i == 0 else height * rng.uniform(0.8, 0.97)
        end = (top[0] + math.cos(a) * reach, end_y, math.sin(a) * reach)
        bark.cylinder(top, end, trunk_r * 0.5, trunk_r * 0.2, max(4, segments // 2))
    meshes.append(bark.mesh("bark", _lit(look["palette"], "bark"), with_order=False))

    if not dead:
        foliage, flowers, fruit = _Builder(), _Builder(), _Builder()
        crown_h = height - trunk_h
        clump_r = crown_w * float(form["clump_size"]) / 2
        squash = float(form["clump_squash"])
        rv = clump_r * squash  # a clump's vertical radius
        for k in range(clumps):
            u = rng.random() * 2 * math.pi
            r = 0.0 if k == 0 else math.sqrt(rng.random()) * (crown_w / 2 - clump_r)
            y = height - rv if k == 0 else trunk_h + rv + rng.random() * max(0.0, crown_h - 2 * rv)
            centre = (top[0] + math.cos(u) * r, y, math.sin(u) * r)
            order = rng.random()
            foliage.ball(centre, clump_r, order, squash=squash)
            if detailed:
                side = rng.random() * 2 * math.pi
                out = (math.cos(side) * clump_r * 0.95, math.sin(side) * clump_r * 0.95)
                tip = (centre[0] + out[0], centre[1] + rv * 0.3, centre[2] + out[1])
                flowers.ball(tip, clump_r * 0.2, rng.random())
                hang = (centre[0] - out[0], centre[1] - rv * 0.5, centre[2] - out[1])
                fruit.ball(hang, clump_r * 0.12, rng.random(), squash=2.5)
        meshes.append(foliage.mesh("foliage", _lit(look["palette"], "foliage"), with_order=True))
        if detailed:
            meshes.append(
                flowers.mesh("flowers", _lit(look["palette"], "flowers"), with_order=True)
            )
            meshes.append(fruit.mesh("fruit", _lit(look["palette"], "fruit"), with_order=True))

    extras = {
        "genes": {
            "id": look["id"],
            "look": look["look"],
            "stage": stage,
            "variant": variant,
            "lod": lod,
            "ref_height_m": height,
            "ref_crown_m": crown_w,
            "scale_range": stage_info.get("scale_range", [0.75, 1.3]),
            "generator": GENERATOR,
            "params_hash": jsonio.params_hash(form),
        }
    }
    return glb.build(meshes, extras)


def build_look(look_dir: Path) -> list[Path]:
    """Write every model of an example look next to its look.json."""
    look = jsonio.load(look_dir / "look.json")
    if look.get("generator") != GENERATOR:
        raise ValueError(f"{look_dir}: generator is {look.get('generator')}, not {GENERATOR}")
    written = []
    for stage, variant, lod in expected_models(look):
        path = look_dir / model_name(stage, variant, lod)
        path.write_bytes(build_model(look, stage, variant, lod))
        written.append(path)
    return written
