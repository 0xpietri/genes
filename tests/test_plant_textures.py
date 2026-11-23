"""Painted textures made in code, and the Blender export (both need Blender's packages:
`uv sync --group blender`; skipped without them)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from genes import glb, jsonio
from genes.paths import REPO_ROOT, SPECIES_DIR

np = pytest.importorskip("numpy")

from plant import textures  # noqa: E402
from plant.form import resolve  # noqa: E402

LOOK = SPECIES_DIR / "plants" / "neltuma-alba" / "looks" / "1" / "look.json"


@pytest.fixture(scope="module")
def look() -> dict[str, Any]:
    data: dict[str, Any] = jsonio.load(LOOK)
    return data


@pytest.fixture(scope="module")
def atlas(look: dict[str, Any]) -> Any:
    return textures.foliage_atlas(resolve(look, "adult", "a").data, 0.85, seed=7)


def test_the_atlas_is_grey_cut_outs(atlas: Any) -> None:
    side = textures.CELL * textures.ATLAS_CELLS
    assert atlas.shape == (side, side, 4)
    assert set(np.unique(atlas[..., 3]).tolist()) == {0.0, 1.0}
    leaf = atlas[..., 3] == 1
    assert 0.15 < leaf.mean() < 0.8  # a clump, not a square and not empty
    assert len(np.unique(atlas[leaf][:, 0])) <= textures.GREYS
    assert (atlas[..., 0] == atlas[..., 1]).all() and (atlas[..., 1] == atlas[..., 2]).all()
    assert (atlas[~leaf][:, :3] == 1).all()  # clear pixels white: they compress to nothing


def test_the_atlas_is_deterministic(look: dict[str, Any], atlas: Any) -> None:
    again = textures.foliage_atlas(resolve(look, "adult", "a").data, 0.85, seed=7)
    assert (again == atlas).all()


def test_the_half_atlas_keeps_thin_leaflets(atlas: Any) -> None:
    small = textures.half(atlas)
    assert small.shape[0] == atlas.shape[0] // 2
    assert small[..., 3].mean() >= atlas[..., 3].mean()


def test_bark_is_grey_and_opaque(look: dict[str, Any]) -> None:
    bark = textures.bark(resolve(look, "adult", "a").data, seed=3)
    assert bark.shape == (256, 256, 4)
    assert (bark[..., 3] == 1).all()
    assert bark[..., 0].min() >= 0.35 and bark[..., 0].max() <= 1.0
    assert textures.half_bark(bark).shape == (128, 128, 4)


def test_blender_exports_the_contract(tmp_path: Path, look: dict[str, Any], atlas: Any) -> None:
    pytest.importorskip("bpy")
    from plant import blend
    from plant.model import build

    budgets = jsonio.load(REPO_ROOT / "budgets.json")
    model = build(look, "young", "a", "lod1", budgets)
    tex = {"foliage": textures.half(atlas), "bark": textures.half_bark(textures.bark({}, 1))}
    out = tmp_path / "young-a.lod1.glb"
    blend.export(model, tex, out)
    info = glb.inspect(out)
    assert info.triangles == model.triangles
    assert set(info.meshes) == set(model.parts)
    assert abs(info.bbox_min[1]) < 0.01
    assert info.extras["genes"]["params_hash"] == jsonio.params_hash(look["form"])
    for prim in info.primitives:
        if prim.mesh != "bark":
            assert "_ORDER" in prim.attributes, prim.mesh
    assert not info.has_cameras and not info.has_lights
