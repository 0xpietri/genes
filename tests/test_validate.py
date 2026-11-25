from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from genes import example, glb, jsonio
from genes.species import discover, expected_models
from genes.validate import frozen_problems, validate

from .conftest import example_dir


def _messages(root: Path, examples_root: Path | None = None) -> list[str]:
    return [str(p) for p in validate([root], examples_root if examples_root else root)]


def _edit(path: Path, change: Callable[[Any], None]) -> None:
    data = jsonio.load(path)
    change(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _sheet(root: Path) -> Path:
    return example_dir(root) / "sheets" / "1.json"


def _look(root: Path) -> Path:
    return example_dir(root) / "looks" / "1" / "look.json"


def _refs(root: Path) -> Path:
    return example_dir(root) / "references" / "refs.json"


def _has(messages: list[str], fragment: str) -> bool:
    return any(fragment in m for m in messages)


def test_the_repository_species_and_examples_are_valid() -> None:
    from genes.paths import EXAMPLES_DIR, SPECIES_DIR

    assert validate([SPECIES_DIR, EXAMPLES_DIR], EXAMPLES_DIR) == []


def test_the_example_copy_is_valid(examples: Path) -> None:
    assert _messages(examples) == []


def test_a_source_id_must_exist(examples: Path) -> None:
    _edit(_sheet(examples), lambda s: s["plant"]["size"]["adult_height_m"].update(source=["nope"]))
    assert _has(_messages(examples), "source 'nope' is not in sources[]")


def test_min_typical_max_order(examples: Path) -> None:
    _edit(_sheet(examples), lambda s: s["plant"]["size"]["adult_height_m"].update(typical=20))
    assert _has(_messages(examples), "needs min ≤ typical ≤ max")


def test_example_sources_only_for_example_species(examples: Path, species_root: Path) -> None:
    # The example species moved among real species is refused, for its id, source and status.
    shutil.copytree(example_dir(examples), species_root / "plants" / "example-tree")
    msgs = [str(p) for p in validate([species_root], examples)]
    assert _has(msgs, "example- species live only under examples/")
    # A real id with an example source is refused too.
    folder = species_root / "plants" / "example-tree"
    folder.rename(species_root / "plants" / "fake-tree")
    for path in (species_root / "plants" / "fake-tree").rglob("*.json"):
        _edit(path, lambda d: d.update(id="fake-tree"))
    msgs = [str(p) for p in validate([species_root], examples)]
    assert _has(msgs, "sources of kind 'example' are valid only for example species")
    assert _has(msgs, "status 'example' is valid only for example species")


def test_folder_and_id_agree(examples: Path) -> None:
    _edit(_sheet(examples), lambda s: s.update(id="other-tree"))
    assert _has(_messages(examples), "differs from its folder")


def test_version_matches_file_name(examples: Path) -> None:
    _edit(_sheet(examples), lambda s: s.update(version=2))
    assert _has(_messages(examples), "differs from its file name")


def test_versions_have_no_gaps(examples: Path) -> None:
    shutil.copy(_sheet(examples), _sheet(examples).with_name("3.json"))
    assert _has(_messages(examples), "sheet versions must be 1..n")


def test_relations_name_known_or_planned_species(examples: Path) -> None:
    rel = {"type": "eats", "species": "neltuma-alba", "part": "fruit", "source": ["ex"]}
    _edit(_sheet(examples), lambda s: s.update(relations=[rel]))
    assert _has(_messages(examples), "species 'neltuma-alba' is not in genes")
    _edit(_sheet(examples), lambda s: s["relations"][0].update(planned=True))
    assert _messages(examples) == []


def test_look_for_sheet_must_exist(examples: Path) -> None:
    _edit(_look(examples), lambda look: look.update(for_sheet=4))
    assert _has(_messages(examples), "for_sheet 4 does not exist")


def test_adult_ref_height_within_the_sheet(examples: Path) -> None:
    _edit(_look(examples), lambda look: look["stages"]["adult"].update(ref_height_m=12))
    assert _has(_messages(examples), "outside the sheet's 5.0–9.0 m")


def test_look_references_exist(examples: Path) -> None:
    _edit(_look(examples), lambda look: look.update(references=["r1", "r9"]))
    assert _has(_messages(examples), "reference 'r9' is not in refs.json")


def test_a_missing_model(examples: Path) -> None:
    (example_dir(examples) / "looks" / "1" / "adult-b.lod1.glb").unlink()
    assert _has(_messages(examples), "adult-b.lod1.glb: model is missing")


def test_a_stray_model(examples: Path) -> None:
    folder = example_dir(examples) / "looks" / "1"
    shutil.copy(folder / "adult-a.lod0.glb", folder / "adult-d.lod0.glb")
    assert _has(_messages(examples), "not listed by the look's stages")


def test_changing_the_form_invalidates_the_models(examples: Path) -> None:
    _edit(_look(examples), lambda look: look["form"].update(clumps=30))
    assert _has(_messages(examples), "extras.genes.params_hash")


def _rewrite_model(
    root: Path, name: str, meshes: list[glb.MeshData], extras: dict[str, Any]
) -> None:
    glb.write(example_dir(root) / "looks" / "1" / name, meshes, extras)


def _extras(root: Path, name: str) -> dict[str, Any]:
    return glb.inspect(example_dir(root) / "looks" / "1" / name).extras


def _box(name: str, height: float, lift: float = 0.0, tris: int = 12) -> glb.MeshData:
    pos = [(x, y * height + lift, z) for x in (-0.5, 0.5) for y in (0.0, 1.0) for z in (-0.5, 0.5)]
    idx = [0, 1, 3] * tris
    return glb.MeshData(name, pos, [(0.0, 1.0, 0.0)] * 8, idx, (0.5, 0.5, 0.5))


def test_model_checks(examples: Path) -> None:
    name = "young-a.lod1.glb"
    extras = _extras(examples, name)
    # Over budget (1000 triangles for a young tree far away), a foreign part, no _ORDER on foliage.
    _rewrite_model(
        examples,
        name,
        [_box("bark", 3.0, tris=1200), _box("foliage", 3.0), _box("leaves", 3.0)],
        extras,
    )
    msgs = _messages(examples)
    assert _has(msgs, "1224 triangles, budget 1000")
    assert _has(msgs, "part 'leaves' is not one of")
    assert _has(msgs, "foliage has no _ORDER")


def test_model_must_stand_on_the_ground_at_its_height(examples: Path) -> None:
    name = "young-a.lod1.glb"
    extras = _extras(examples, name)
    _rewrite_model(examples, name, [_box("bark", 4.5, lift=0.3)], extras)
    msgs = _messages(examples)
    assert _has(msgs, "base at y = 0.300 m")
    assert _has(msgs, "height 4.50 m, its stage says 3")


def test_model_extras_must_match(examples: Path) -> None:
    name = "young-a.lod1.glb"
    extras = _extras(examples, name)
    extras["genes"]["variant"] = "b"
    del extras["genes"]["generator"]
    _rewrite_model(examples, name, [_box("bark", 3.0)], extras)
    msgs = _messages(examples)
    assert _has(msgs, "extras.genes.variant is 'b', expected 'a'")
    assert _has(msgs, "extras.genes.generator is missing")


def test_stored_photos_need_a_shareable_licence(examples: Path) -> None:
    def store(refs: dict[str, Any]) -> None:
        refs["photos"][0].update(file="r1.jpg", licence="cc-by-nc")

    _edit(_refs(examples), store)
    msgs = _messages(examples)
    assert _has(msgs, "licence cc-by-nc cannot be stored")
    assert _has(msgs, "file r1.jpg is missing")


def test_repeated_photo_ids(examples: Path) -> None:
    _edit(_refs(examples), lambda r: r["photos"].append(dict(r["photos"][0])))
    assert _has(_messages(examples), "photo id 'r1' is repeated")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_merged_versions_are_frozen(tmp_path: Path, examples: Path) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(examples, repo / "examples")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "species")
    species = discover([repo / "examples"])
    assert frozen_problems(species, "main", repo) == []

    _edit(_sheet(repo / "examples"), lambda s: s.update(range_note="changed"))
    look_dir = example_dir(repo / "examples") / "looks" / "1"
    (look_dir / "adult-a.lod1.glb").write_bytes(b"different")
    # A new version is a draft and may change freely.
    shutil.copy(_sheet(repo / "examples"), _sheet(repo / "examples").with_name("2.json"))
    species = discover([repo / "examples"])
    msgs = [str(p) for p in frozen_problems(species, "main", repo)]
    assert len(msgs) == 2
    assert _has(msgs, "sheets/1.json: changed after it was merged into main")
    assert _has(msgs, "adult-a.lod1.glb: changed after it was merged")
    # An unknown base (no git history yet) checks nothing.
    assert frozen_problems(species, "no-such-branch", repo) == []


def test_committed_example_models_are_what_the_code_makes() -> None:
    from genes.paths import EXAMPLES_DIR

    for look_dir in sorted((EXAMPLES_DIR / "plants").glob("*/looks/*")):
        look = jsonio.load(look_dir / "look.json")
        for stage, variant, lod in expected_models(look):
            name = f"{stage}-{variant}.{lod}.glb"
            built = example.build_model(look, stage, variant, lod)
            assert (look_dir / name).read_bytes() == built, (
                f"{name}: run `uv run genes make-example`"
            )


def test_a_plant_form_is_checked_against_its_schema(examples: Path) -> None:
    def plant(look: dict[str, Any]) -> None:
        look["generator"] = "plant@1"
        look["form"] = {"trunk": {"count": "two", "colour": 1}}

    _edit(_look(examples), plant)
    msgs = _messages(examples)
    assert _has(msgs, "form/trunk/count")
    assert _has(msgs, "'colour' was unexpected")


def test_tree_box_order_and_file(examples: Path) -> None:
    def box(refs: dict[str, Any]) -> None:
        refs["photos"][0]["tree_box"] = [0.8, 0.1, 0.2, 0.9]

    _edit(_refs(examples), box)
    msgs = _messages(examples)
    assert _has(msgs, "tree_box needs left < right")
    assert _has(msgs, "a tree_box needs a stored file")


def test_leaf_tones_cover_the_year_two_at_most(examples: Path) -> None:
    """Spec §6.4: the leaf tones together cover every month a leaf is on; at most two share."""

    def tones(s: Any) -> None:
        s["plant"]["phenology"]["leaf_habit"] = "evergreen"
        s["plant"]["phenology"]["leaf_tones"] = [
            {"tone": "new", "months": [9, 10], "source": [s["sources"][0]["id"]]},
            {"tone": "mature", "months": [10, 11, 12, 1, 2, 3], "source": [s["sources"][0]["id"]]},
            {"tone": "dry", "months": [10], "source": [s["sources"][0]["id"]]},
        ]

    _edit(_sheet(examples), tones)
    messages = _messages(examples)
    assert _has(messages, "more than two tones in months [10]")
    assert _has(messages, "no tone in months [4, 5, 6, 7, 8]")


def test_leaf_tones_need_their_colour_in_the_palette(examples: Path) -> None:
    def tones(s: Any) -> None:
        s["plant"]["phenology"]["leaf_habit"] = "deciduous"
        s["plant"]["phenology"]["leaf_tones"] = [
            {"tone": "autumn", "months": [4], "source": [s["sources"][0]["id"]]}
        ]

    _edit(_sheet(examples), tones)
    _edit(_look(examples), lambda look: look["palette"]["foliage"].pop("autumn", None))
    assert _has(_messages(examples), "palette.foliage has no 'autumn' tone")


def test_a_fruit_accent_needs_its_colour_in_the_palette(examples: Path) -> None:
    def accent(look: Any) -> None:
        look["form"].setdefault("fruit", {})["accent"] = "streaks"
        look["palette"].setdefault("fruit", {"lit": "#d6b874", "shade": "#6b4a5e"}).pop(
            "accent", None
        )

    _edit(_look(examples), accent)
    assert _has(_messages(examples), "palette.fruit has no accent")
