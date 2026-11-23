"""A look's form parameters: defaults, stage changes and each variant's draws.

The defaults live in schemas/plant-form.v1.json (one source for the docs, the
validator and the generator). Draws are hashed from (species, look, variant,
parameter path), so they do not depend on the order they are asked for and an
individual keeps its traits from seedling to fallen.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "plant-form.v1.json"

STAGE_DEFAULTS: dict[str, dict[str, Any]] = {
    "seedling": {
        "levels": 0,
        "flowers": {"cover": 0},
        "fruit": {"cover": 0},
        "trunk": {"count": 1},
    },
    "sapling": {"levels": 1, "flowers": {"cover": 0}, "fruit": {"cover": 0}, "trunk": {"count": 1}},
    "young": {"levels": 2},
}

ENVELOPE_WIDEST = {
    "umbrella": 0.7,
    "globose": 0.5,
    "conical": 0.05,
    "columnar": 0.5,
    "weeping": 0.6,
    "irregular": 0.5,
}


def _defaults_from(schema: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, prop in schema.get("properties", {}).items():
        if "default" in prop:
            out[key] = copy.deepcopy(prop["default"])
        elif prop.get("type") == "object" and "properties" in prop:
            out[key] = _defaults_from(prop)
    return out


def _load_schema() -> dict[str, Any]:
    with SCHEMA.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data


_SCHEMA = _load_schema()
DEFAULTS = _defaults_from(_SCHEMA)
LEVEL_DEFAULTS = _defaults_from(_SCHEMA["properties"]["branching"]["items"])


def merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    """Deep merge: objects merge, everything else is replaced."""
    out = copy.deepcopy(base)
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def unit(*parts: object) -> float:
    """A number in [0, 1) hashed from the parts."""
    digest = hashlib.sha256("/".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def seed(*parts: object) -> int:
    digest = hashlib.sha256("/".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(digest[:8], "big")


def as_range(value: Any) -> tuple[float, float]:
    if isinstance(value, list):
        lo, hi = float(value[0]), float(value[1])
        return (min(lo, hi), max(lo, hi))
    return (float(value), float(value))


@dataclass
class Form:
    """One stage of one variant: the merged parameters and the variant's draws."""

    data: dict[str, Any]
    key: str  # species/look/variant: what individual draws hash from
    stage: str
    levels: list[dict[str, Any]]

    def get(self, path: str) -> Any:
        node: Any = self.data
        for part in path.split("."):
            node = node[part]
        return node

    def range(self, path: str) -> tuple[float, float]:
        return as_range(self.get(path))

    def ind(self, path: str) -> float:
        """The individual's own value of a range: the same in every stage. Rule: variants
        of a species differ only in how crooked they are (VARIES); everything that sets
        the tree's proportions takes the middle of its range, so no variant comes out
        lopsided or out of proportion, whatever a look says."""
        lo, hi = self.range(path)
        if path not in VARIES:
            return (lo + hi) / 2
        return lo + (hi - lo) * unit(self.key, path)

    def ind_int(self, path: str) -> int:
        lo, hi = self.range(path)
        return int((lo + hi) / 2 + 0.5)

    def unit(self, name: str) -> float:
        return unit(self.key, name)


# The only individual traits that change between variants: the shape of the crookedness.
VARIES = frozenset({"trunk.tortuosity", "trunk.twist", "trunk.gnarl", "trunk.fluting"})


def draw(rng: random.Random, value: Any) -> float:
    """A per-branch value from a range."""
    lo, hi = as_range(value)
    return lo if hi == lo else rng.uniform(lo, hi)


def draw_int(rng: random.Random, value: Any) -> int:
    lo, hi = as_range(value)
    return int(lo) if hi == lo else rng.randint(int(lo), int(hi))


def resolve(look: dict[str, Any], stage: str, variant: str) -> Form:
    """The form a stage of a variant is built from."""
    raw = look.get("form", {})
    data = merge(DEFAULTS, {k: v for k, v in raw.items() if k != "stages"})
    over = merge(STAGE_DEFAULTS.get(stage, {}), raw.get("stages", {}).get(stage, {}))
    levels_wanted = over.pop("levels", None)
    data = merge(data, over)  # a stage's `branching` replaces the whole list
    all_levels = sorted(
        (merge(LEVEL_DEFAULTS, lv) for lv in data.get("branching", [])), key=lambda lv: lv["level"]
    )
    if levels_wanted is None:
        levels_wanted = len(all_levels)
    crown = data["crown"]
    if "widest" not in crown:
        crown["widest"] = ENVELOPE_WIDEST[crown["envelope"]]
    key = f"{look['id']}/{look['look']}/{variant}"
    return Form(data, key, stage, all_levels[: int(levels_wanted)])
