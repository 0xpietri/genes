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
    assert 0.08 < leaf.mean() < 0.8  # a clump, not a square and not empty
    values = set(np.unique(atlas[leaf][:, 0]).tolist())
    assert textures.TWIG in {round(v, 6) for v in values} or min(values) >= 0.72
    assert len(values) <= textures.GREYS + 1  # the leaf greys and the twigs
    assert (atlas[..., 0] == atlas[..., 1]).all() and (atlas[..., 1] == atlas[..., 2]).all()
    assert (atlas[~leaf][:, :3] == 1).all()  # clear pixels white: they compress to nothing


def test_the_atlas_is_deterministic(look: dict[str, Any], atlas: Any) -> None:
    again = textures.foliage_atlas(resolve(look, "adult", "a").data, 0.85, seed=7)
    assert (again == atlas).all()


def test_twigs_are_painted_under_the_leaves(look: dict[str, Any]) -> None:
    form = resolve(look, "adult", "a").data
    bare = {"foliage": {**form["foliage"], "twigs": 0}}
    twiggy = {"foliage": {**form["foliage"], "twigs": 1}}
    dark = lambda a: ((a[..., 3] == 1) & (a[..., 0] < 0.5)).mean()  # noqa: E731
    assert dark(textures.foliage_atlas(bare, 0.85, seed=7)) == 0
    assert dark(textures.foliage_atlas(twiggy, 0.85, seed=7)) > 0.005


def test_the_half_atlas_keeps_thin_leaflets(atlas: Any) -> None:
    small = textures.half(atlas)
    assert small.shape[0] == atlas.shape[0] // 2
    assert small[..., 3].mean() >= atlas[..., 3].mean()


def test_bark_tiles_with_gentle_colour(look: dict[str, Any]) -> None:
    bark = textures.bark(resolve(look, "adult", "a").data, seed=3)
    assert bark.shape == (256, 256, 4)
    assert (bark[..., 3] == 1).all()
    rgb = bark[..., :3]
    assert rgb.min() >= 0.0 and rgb.max() <= 1.0
    assert 0.7 < rgb.mean() < 0.95  # near white: the palette's colour carries the tone
    tint = np.abs(rgb - rgb.mean(axis=2, keepdims=True)).max()
    assert 0.01 < tint < 0.12  # patches of colour, never a different colour
    # It tiles: the jump across each edge is like the jump between neighbouring pixels.
    inner_x = np.abs(np.diff(rgb, axis=1)).mean()
    inner_y = np.abs(np.diff(rgb, axis=0)).mean()
    assert np.abs(rgb[:, 0] - rgb[:, -1]).mean() < 3 * inner_x
    assert np.abs(rgb[0] - rgb[-1]).mean() < 3 * inner_y
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


def test_fruit_accents_paint_the_accent_over_the_lit_colour() -> None:
    lit, accent = "#d6b874", "#5e3852"
    assert textures.fruit("none", lit, accent, 1) is None
    for pattern in ("spots", "streaks", "tip", "blush"):
        tex = textures.fruit(pattern, lit, accent, 1)
        assert tex is not None and tex.shape == (128, 64, 4)
        assert (tex[..., 3] == 1).all()
        rgb = tex[..., :3]
        assert rgb.max() == pytest.approx(1.0)  # the lit colour shows as itself
        darkest = rgb.reshape(-1, 3)[rgb.sum(axis=2).argmin()]
        # lit x darkest (in linear light) is the accent colour.
        want = textures._linear(accent) / textures._linear(lit)
        assert textures._linear_of(darkest) == pytest.approx(want, abs=0.06)
    assert (
        textures.fruit("streaks", lit, accent, 1) == textures.fruit("streaks", lit, accent, 1)
    ).all()
