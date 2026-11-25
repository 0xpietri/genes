"""Contact sheet maths: the photo's tree mask, the fitted silhouette and their overlap."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from genes import contact


def _photo() -> Image.Image:
    """Blue sky, a dark-green round crown on a brown trunk, green grass."""
    img = Image.new("RGB", (200, 200), (110, 160, 220))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 180, 200, 200), fill=(80, 140, 50))
    d.rectangle((95, 110, 105, 180), fill=(90, 60, 40))
    d.ellipse((50, 30, 150, 120), fill=(50, 80, 30))
    return img


def _silhouette(box: tuple[int, int, int, int]) -> Image.Image:
    img = Image.new("RGB", (100, 100), (255, 255, 255))
    ImageDraw.Draw(img).ellipse(box, fill=(0, 0, 0))
    return img


def test_sky_is_not_tree() -> None:
    mask = contact.photo_mask(_photo())
    assert mask.getpixel((10, 10)) == 0  # sky
    assert mask.getpixel((100, 70)) == 255  # crown
    assert mask.getpixel((100, 150)) == 255  # trunk


def test_overlap_is_intersection_over_union() -> None:
    a = Image.new("1", (10, 10))
    b = Image.new("1", (10, 10))
    ImageDraw.Draw(a).rectangle((0, 0, 4, 9), fill=1)
    ImageDraw.Draw(b).rectangle((0, 0, 9, 9), fill=1)
    assert contact.overlap(a, b) == 0.5
    assert contact.overlap(a, a) == 1.0
    assert contact.overlap(Image.new("1", (4, 4)), Image.new("1", (4, 4))) == 0.0


def test_fit_keeps_proportions_and_stands_on_the_bottom() -> None:
    mask = contact.model_mask(_silhouette((40, 10, 60, 90)))  # 20 x 80: tall and thin
    fitted = contact._fit(mask, (100, 100))
    box = fitted.getbbox()
    assert box is not None
    left, top, right, bottom = box
    assert top == 0 and bottom == 100
    assert 20 <= right - left <= 30  # not stretched to the box's width


def test_the_best_silhouette_wins() -> None:
    photo = _photo()
    box = [0.2, 0.1, 0.8, 0.95]
    round_tree = _silhouette((10, 5, 90, 95))
    pole = _silhouette((45, 0, 55, 99))
    model, view, score, overlay = contact.match_photo(
        photo, box, {("adult-a.lod0.glb", "side"): pole, ("adult-b.lod0.glb", "side"): round_tree}
    )
    assert model == "adult-b.lod0.glb" and view == "side"
    assert 0.3 < score <= 1
    assert overlay.size == photo.size


def test_the_saved_sheet_is_small(tmp_path: Path) -> None:
    sheet = Image.new("RGB", (300, 300), (255, 255, 255))
    ImageDraw.Draw(sheet).ellipse((50, 50, 250, 250), fill=(60, 110, 40))
    contact.save_sheet(sheet, tmp_path / "sheet.png")
    saved = Image.open(tmp_path / "sheet.png")
    assert saved.size == (200, 200) and saved.mode == "P"


def test_the_barest_month_comes_from_the_leaf_calendar() -> None:
    def sheet(tones: list[tuple[str, list[int]]], fall: list[int] | None = None) -> dict[str, Any]:
        ph: dict[str, Any] = {"leaf_tones": [{"tone": t, "months": m} for t, m in tones]}
        if fall:
            ph["leaf_fall"] = {"months": fall}
        return {"plant": {"phenology": ph}}

    # A deciduous tree bare from April to September: the middle of the bare run.
    assert contact.barest_month(sheet([("mature", [10, 11, 12, 1, 2, 3])])) == 7
    # A bare run over New Year stays whole.
    assert contact.barest_month(sheet([("mature", [3, 4, 5, 6, 7, 8, 9])])) == 12
    # Never bare: the month with only dry leaves.
    assert (
        contact.barest_month(
            sheet([("mature", [1, 2, 3, 4, 5, 6, 7, 10, 11, 12]), ("new", [9]), ("dry", [8, 9])])
        )
        == 8
    )
    # Leaves all year: the middle of leaf fall.
    assert contact.barest_month(sheet([("mature", list(range(1, 13)))], fall=[6, 7, 8])) == 7
