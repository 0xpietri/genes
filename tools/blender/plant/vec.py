"""Tiny 3D vector helpers on tuples (Y up, metres). Plain Python so the generator is
deterministic and testable without Blender or numpy."""

from __future__ import annotations

import math

Vec = tuple[float, float, float]

UP: Vec = (0.0, 1.0, 0.0)


def add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(a: Vec, s: float) -> Vec:
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def length(a: Vec) -> float:
    return math.sqrt(dot(a, a))


def norm(a: Vec) -> Vec:
    n = length(a)
    if n < 1e-12:
        return UP
    return (a[0] / n, a[1] / n, a[2] / n)


def lerp(a: Vec, b: Vec, t: float) -> Vec:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def horizontal(a: Vec) -> Vec:
    return (a[0], 0.0, a[2])


def perpendicular(d: Vec) -> Vec:
    """Any unit vector perpendicular to d."""
    other: Vec = (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 else (0.0, 0.0, 1.0)
    return norm(cross(d, other))


def rotate(v: Vec, axis: Vec, angle: float) -> Vec:
    """Rodrigues rotation of v about a unit axis by angle (radians)."""
    c, s = math.cos(angle), math.sin(angle)
    k = axis
    kv = cross(k, v)
    kd = dot(k, v) * (1 - c)
    return (
        v[0] * c + kv[0] * s + k[0] * kd,
        v[1] * c + kv[1] * s + k[1] * kd,
        v[2] * c + kv[2] * s + k[2] * kd,
    )


def rotate_towards(v: Vec, target: Vec, angle: float) -> Vec:
    """Turn unit v towards unit target by at most angle (radians)."""
    axis = cross(v, target)
    n = length(axis)
    if n < 1e-9:
        return v
    between = math.atan2(n, dot(v, target))
    return norm(rotate(v, mul(axis, 1 / n), min(angle, between)))


def from_spherical(azimuth: float, tilt: float) -> Vec:
    """Unit vector tilted `tilt` radians from up, towards `azimuth` (0 = +X, π/2 = +Z)."""
    st = math.sin(tilt)
    return (st * math.cos(azimuth), math.cos(tilt), st * math.sin(azimuth))
