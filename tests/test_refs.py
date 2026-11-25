"""Reference photos from iNaturalist, on recorded answers (tests never touch the network)."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from genes import jsonio, refs

FIXTURES = Path(__file__).parent / "fixtures" / "inaturalist"


def _observations() -> dict[str, Any]:
    data: dict[str, Any] = jsonio.load(FIXTURES / "observations.json")
    return data


def _jpeg(w: int = 2000, h: int = 1500) -> bytes:
    out = BytesIO()
    Image.new("RGB", (w, h), (90, 120, 60)).save(out, "JPEG")
    return out.getvalue()


def test_only_shareable_photos_are_candidates() -> None:
    answer = _observations()
    answer["results"][0]["photos"][0]["license_code"] = "cc-by-nc"
    answer["results"][0]["photos"][1]["license_code"] = None
    found = refs.parse_observations(answer, start=10)
    total = sum(len(o["photos"]) for o in answer["results"])
    assert len(found) == total - 2
    assert [c.number for c in found] == list(range(10, 10 + len(found)))
    assert all(c.licence in refs.SHAREABLE for c in found)
    c = found[0]
    assert c.large.endswith(".jpg") or "/large." in c.large
    assert "/square." not in c.medium
    assert c.page == f"https://www.inaturalist.org/photos/{c.photo}"


def test_phenology_histograms() -> None:
    hist = {
        phase: refs.parse_histogram(jsonio.load(FIXTURES / f"hist_{value}.json"))
        for phase, value in refs.PHENOLOGY.items()
    }
    assert all(set(months) == set(range(1, 13)) for months in hist.values())
    lines = refs.phenology_summary(hist)
    assert len(lines) == 3 and lines[0].startswith("flowers: ")
    assert refs.phenology_summary({"fruit": {1: 0}}) == ["fruit: no annotations"]


def test_candidates_and_add(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(refs, "WORK", tmp_path / ".work")

    def get(url: str) -> bytes:
        if "/observations/histogram" in url:
            value = url.split("term_value_id=")[1].split("&")[0]
            return (FIXTURES / f"hist_{value}.json").read_bytes()
        if "/observations?" in url:
            return json.dumps(_observations()).encode()
        return _jpeg()

    folder = refs.candidates("some-tree", taxon=1, get=get)
    assert (folder / "grid-1.jpg").exists() and (folder / "000.jpg").exists()
    assert set(jsonio.load(folder / "phenology.json")) == set(refs.PHENOLOGY)

    species = tmp_path / "species" / "plants" / "some-tree"
    entry = refs.add(species, 1, ["whole", "summer"], "side", box=[0.1, 0.1, 0.9, 0.95], get=get)
    assert entry["id"] == "r01" and entry["tree_box"] == [0.1, 0.1, 0.9, 0.95]
    stored = Image.open(species / "references" / "r01.jpg")
    assert max(stored.size) == refs.MAX_SIDE
    data = jsonio.load(species / "references" / "refs.json")
    assert data["photos"][0]["licence"] in refs.SHAREABLE
    assert refs.add(species, 2, ["trunk"], "detail", get=get)["id"] == "r02"  # same observation
    with pytest.raises(SystemExit):
        refs.add(species, 1, ["whole"], "side", get=get)


def test_grid_marks_coordinates_and_the_box(tmp_path: Path) -> None:
    photo = Image.new("RGB", (400, 300), (40, 120, 200))
    plain = refs.grid_picture(photo)
    boxed = refs.grid_picture(photo, [0.25, 0.2, 0.75, 0.9])
    assert plain.size == photo.size
    # Grid lines every 0.05: the line at x = 0.5 is lighter than the sky beside it.
    assert sum(plain.getpixel((200, 140))) > sum(plain.getpixel((205, 140)))
    # The box is yellow where it runs and nowhere else.
    r, g, b = boxed.getpixel((100, 140))
    assert r > 200 and g > 200 and b < 100
    assert boxed.getpixel((33, 140)) == plain.getpixel((33, 140))
    species = tmp_path / "species" / "plants" / "some-tree"
    (species / "references").mkdir(parents=True)
    photo.save(species / "references" / "r01.jpg")
    out = refs.grid(species, "r01", work=tmp_path / ".work")
    assert out.name == "box-r01.jpg" and out.exists()
