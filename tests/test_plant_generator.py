"""The plant generator (tools/blender/plant): everything but the Blender export runs in
plain Python, so the model contract is checked here without bpy (spec §8)."""

from __future__ import annotations

import copy
import math
import random
from typing import Any

import pytest
from plant import GENERATOR
from plant.form import resolve, seed
from plant.model import PARTS, _old_and_dead, _stage_height, bounds, build, crown_clumps
from plant.skeleton import grow_tree

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
    assert young.ind("trunk.tortuosity") == adult.ind("trunk.tortuosity")
    assert adult.ind("trunk.tortuosity") != resolve(look, "adult", "b").ind("trunk.tortuosity")


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


def _skeleton(look: dict[str, Any], stage: str, variant: str = "a") -> Any:
    import random

    from plant.form import seed
    from plant.model import _stage_height
    from plant.skeleton import grow_tree

    form = resolve(look, stage, variant)
    height, adult = _stage_height(look, stage)
    return grow_tree(form, height, adult, random.Random(seed(form.key, stage)))


def _crookedness(branch: Any) -> float:
    """How far the branch strays from the straight line between its ends, per metre."""
    a, b = branch.points[0], branch.points[-1]
    ab = [b[i] - a[i] for i in range(3)]
    norm = math.sqrt(sum(x * x for x in ab)) or 1.0
    worst = 0.0
    for p in branch.points:
        ap = [p[i] - a[i] for i in range(3)]
        t = sum(ap[i] * ab[i] for i in range(3)) / norm**2
        off = [ap[i] - t * ab[i] for i in range(3)]
        worst = max(worst, math.sqrt(sum(x * x for x in off)))
    return worst / norm


def test_tortuosity_bends_the_leaders(look: dict[str, Any]) -> None:
    def mean_crook(tortuosity: float) -> float:
        changed = copy.deepcopy(look)
        changed["form"]["trunk"]["tortuosity"] = tortuosity
        changed["form"]["trunk"]["twist"] = 0
        leaders = [b for b in _skeleton(changed, "adult").branches if b.level == 0]
        return sum(_crookedness(b) for b in leaders) / len(leaders)

    assert mean_crook(0.9) > mean_crook(0.0) + 0.03


def test_old_limbs_rest_on_the_ground(look: dict[str, Any]) -> None:
    def resting(sag: float) -> int:
        changed = copy.deepcopy(look)
        changed["form"]["old"].update(limb_sag=sag, sagging_limbs=1.0)
        tree = _skeleton(changed, "old")
        return sum(
            1
            for b in tree.branches
            if b.level == 1 and min(p[1] for p in b.points) <= b.radii[0] * 1.01
        )

    assert resting(1.0) > 0
    assert resting(0.0) == 0


def test_an_old_trunk_opens_at_the_base(look: dict[str, Any]) -> None:
    changed = copy.deepcopy(look)
    changed["form"]["old"]["trunk_split"] = 1.0
    tree = _skeleton(changed, "old")
    stems = [b for b in tree.branches if b.level == 0]
    assert len(stems) >= 2
    assert all(b.points[0][1] < 0.1 * tree.height for b in stems)
    starts = {(round(b.points[0][0], 3), round(b.points[0][2], 3)) for b in stems}
    assert len(starts) == len(stems)  # each stem stands on its own part of the stump


def test_a_fallen_trunk_lies_on_the_ground(look: dict[str, Any]) -> None:
    model = build(look, "fallen", "a", "lod0", BUDGETS)
    lo, hi = bounds(model.parts)
    assert hi[1] - lo[1] <= float(look["stages"]["fallen"]["ref_height_m"]) * 2
    assert max(hi[0] - lo[0], hi[2] - lo[2]) > 3 * (hi[1] - lo[1])


@pytest.mark.parametrize("stage", ["young", "adult", "old"])
def test_every_variant_has_leaves_on_top(look: dict[str, Any], stage: str) -> None:
    for variant in "abc":
        model = build(look, stage, variant, "lod0", BUDGETS)
        lo, hi = bounds(model.parts)
        height = hi[1] - lo[1]
        leaves = model.parts["foliage"].positions
        assert max(p[1] for p in leaves) > 0.9 * height, variant
        # Seen from above, the crown's middle is covered too, not a ring round a hole: most
        # spots of the inner crown have leaves above half the tree's height.
        top = [p for p in leaves if p[1] > 0.5 * height]
        cx = (min(p[0] for p in leaves) + max(p[0] for p in leaves)) / 2
        cz = (min(p[2] for p in leaves) + max(p[2] for p in leaves)) / 2
        reach = max(math.hypot(p[0] - cx, p[2] - cz) for p in leaves)
        step = reach / 5
        spots = [
            (cx + i * step, cz + j * step)
            for i in range(-3, 4)
            for j in range(-3, 4)
            if math.hypot(i, j) <= 3
        ]
        covered = sum(
            1 for x, z in spots if any(math.hypot(p[0] - x, p[2] - z) < step for p in top)
        )
        assert covered >= 0.8 * len(spots), (variant, covered, len(spots))


@pytest.mark.parametrize("stage", ["adult", "old"])
def test_no_limb_is_left_bare(look: dict[str, Any], stage: str) -> None:
    for variant in "abc":
        form = resolve(look, stage, variant)
        height, adult = _stage_height(look, stage)
        rng = random.Random(seed(form.key, stage))
        tree = grow_tree(form, height, adult, rng)
        _old_and_dead(tree, form, rng)
        clumps = crown_clumps(tree, form, 0.8, rng)
        carrying: set[int] = set()
        for c in clumps:
            i: int | None = c.branch
            while i is not None:
                carrying.add(i)
                i = tree.branches[i].parent
        bare = [
            i
            for i, b in enumerate(tree.branches)
            if not b.removed and not b.broken and b.level >= 1 and i not in carrying
        ]
        assert not bare, (variant, bare)


def test_variants_differ_only_in_crookedness(look: dict[str, Any]) -> None:
    forms = [resolve(look, "adult", v) for v in "abc"]
    for path in ("crown.width_to_height", "crown.base", "trunk.split_height", "trunk.lean_deg"):
        assert len({f.ind(path) for f in forms}) == 1, path
    assert len({f.ind_int("trunk.count") for f in forms}) == 1
    assert len({round(f.ind("trunk.tortuosity"), 6) for f in forms}) == 3


@pytest.mark.parametrize("stage", ["young", "adult", "old"])
def test_every_variant_is_even_on_all_sides(look: dict[str, Any], stage: str) -> None:
    widths = []
    for variant in "abc":
        model = build(look, stage, variant, "lod0", BUDGETS)
        pts = model.parts["foliage"].positions + model.parts["bark"].positions
        cx = cz = 0.0  # the trunk stands on the origin
        # How far the tree reaches out from its foot, in four quarters round it.
        reach = [0.0] * 4
        for p in pts:
            q = int(
                ((math.atan2(p[2] - cz, p[0] - cx) + math.pi / 4) % (2 * math.pi)) // (math.pi / 2)
            )
            reach[q % 4] = max(reach[q % 4], math.hypot(p[0] - cx, p[2] - cz))
        assert min(reach) >= 0.55 * max(reach), (variant, [round(r, 1) for r in reach])
        lo, hi = bounds(model.parts)
        widths.append(max(hi[0] - lo[0], hi[2] - lo[2]))
    assert min(widths) >= 0.75 * max(widths), [round(w, 1) for w in widths]
