"""The plant generator (tools/blender/plant): everything but the Blender export runs in
plain Python, so the model contract is checked here without bpy (spec §8)."""

from __future__ import annotations

import copy
import math
from typing import Any

import pytest
from plant import GENERATOR
from plant.form import resolve
from plant.model import PARTS, bounds, build

from genes import jsonio
from genes.paths import REPO_ROOT, SPECIES_DIR
from genes.species import expected_models
from genes.validate import BASE_TOLERANCE_M, HEIGHT_TOLERANCE

LOOK = SPECIES_DIR / "plants" / "neltuma-alba" / "looks" / "1" / "look.json"
BUDGETS: dict[str, Any] = jsonio.load(REPO_ROOT / "budgets.json")


@pytest.fixture(scope="module")
def look() -> dict[str, Any]:
    data: dict[str, Any] = jsonio.load(LOOK)
    return data


def _mesh(model: Any) -> dict[str, tuple[list[Any], list[Any]]]:
    return {k: (list(p.positions), list(p.triangles)) for k, p in model.parts.items()}


def test_the_same_look_builds_the_same_model(look: dict[str, Any]) -> None:
    a = build(look, "adult", "a", "lod0", BUDGETS)
    b = build(look, "adult", "a", "lod0", BUDGETS)
    assert _mesh(a) == _mesh(b)
    assert _mesh(a) != _mesh(build(look, "adult", "b", "lod0", BUDGETS))


def test_a_variant_keeps_its_traits_in_every_stage(look: dict[str, Any]) -> None:
    """An individual's draws hang on its variant, not its stage (spec §6.2)."""
    young, adult = resolve(look, "young", "a"), resolve(look, "adult", "a")
    assert young.ind("trunk.lean_deg") == adult.ind("trunk.lean_deg")
    assert adult.ind("trunk.lean_deg") != resolve(look, "adult", "b").ind("trunk.lean_deg")


@pytest.mark.parametrize(
    "stage", ["seedling", "sapling", "young", "adult", "old", "dead_standing", "fallen"]
)
def test_every_model_keeps_the_contract(look: dict[str, Any], stage: str) -> None:
    for st, variant, lod in expected_models(look):
        if st != stage:
            continue
        model = build(look, st, variant, lod, BUDGETS)
        assert model.triangles <= BUDGETS["triangles"][lod][st], (variant, lod)
        assert set(model.parts) <= set(PARTS)
        lo, hi = bounds(model.parts)
        assert abs(lo[1]) <= BASE_TOLERANCE_M, (variant, lod, lo)
        ref = float(look["stages"][st]["ref_height_m"])
        if st != "fallen":
            assert abs((hi[1] - lo[1]) - ref) <= HEIGHT_TOLERANCE * ref, (variant, lod)
        for name, part in model.parts.items():
            if name == "bark" or part.order is None:
                continue
            assert all(0.0 <= o <= 1.0 for o in part.order), name
        assert model.extras["generator"] == GENERATOR
        assert model.extras["params_hash"] == jsonio.params_hash(look["form"])
        assert (model.extras["stage"], model.extras["variant"], model.extras["lod"]) == (
            st,
            variant,
            lod,
        )
        if st in ("dead_standing", "fallen"):
            assert set(model.parts) <= {"bark", "thorns"}


def test_a_look_with_only_defaults_builds(look: dict[str, Any]) -> None:
    """Every form parameter has a default (schemas/plant-form.v1.json): an empty form is a
    plain tree, the starting point of a new species."""
    bare = copy.deepcopy(look)
    bare["form"] = {}
    for stage in bare["stages"]:
        model = build(bare, stage, "a", "lod0", BUDGETS)
        assert model.triangles > 0
        assert model.triangles <= BUDGETS["triangles"]["lod0"][stage]


def test_defaults_come_from_the_schema() -> None:
    schema = jsonio.load(REPO_ROOT / "schemas" / "plant-form.v1.json")
    flare = schema["properties"]["trunk"]["properties"]["flare"]["default"]
    look = {"id": "x", "look": 1, "form": {}, "stages": {"adult": {"ref_height_m": 5}}}
    assert resolve(look, "adult", "a").get("trunk.flare") == flare


def test_flowers_at_the_tips_sit_further_out(look: dict[str, Any]) -> None:
    def spread(where: str) -> float:
        changed = copy.deepcopy(look)
        changed["form"]["flowers"]["where"] = where
        part = build(changed, "adult", "a", "lod0", BUDGETS).parts["flowers"]
        return sum(math.hypot(p[0], p[2]) for p in part.positions) / len(part.positions)

    assert spread("tips") > spread("axils")
