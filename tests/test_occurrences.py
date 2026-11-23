"""GBIF sightings counted per half-degree cell (the species page's map), on a recorded answer."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from genes import jsonio, occurrences

FIXTURE = Path(__file__).parent / "fixtures" / "gbif" / "occurrence_page.json"


def test_counts_cells_without_keeping_records(tmp_path: Path) -> None:
    urls: list[str] = []

    def get(url: str) -> bytes:
        urls.append(url)
        return FIXTURE.read_bytes()

    folder = tmp_path / "neltuma-alba"
    folder.mkdir()
    out = occurrences.write(folder, 5358528, get=get, today=date(2026, 11, 23))
    assert (
        len(urls) == 1 and "taxonKey=5358528" in urls[0] and "hasGeospatialIssue=false" in urls[0]
    )
    assert out["total"] == 3  # the record without coordinates is skipped
    assert out["cells"] == [[-64.25, -31.25, 2], [-58.75, -27.25, 1]]
    assert out["licences"] == {"cc-by": 1, "cc-by-nc": 1, "cc0": 1}
    assert out["years"] == [1951, 2023]
    saved = jsonio.load(folder / "occurrences.json")
    assert saved["source"]["accessed"] == "2026-11-23"
    assert "decimalLatitude" not in (folder / "occurrences.json").read_text(encoding="utf-8")


def test_cells_are_half_degree_centres() -> None:
    assert occurrences._cell(-31.24) == -31.25
    assert occurrences._cell(-64.45) == -64.25
    assert occurrences._cell(-64.51) == -64.75
