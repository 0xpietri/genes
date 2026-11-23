from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator

from genes import jsonio
from genes.paths import EXAMPLES_DIR, SCHEMAS_DIR
from genes.validate import schema_validator

SCHEMAS = sorted(p.stem for p in SCHEMAS_DIR.glob("*.json"))


@pytest.mark.parametrize("name", SCHEMAS)
def test_every_schema_is_valid_draft_2020_12(name: str) -> None:
    schema = jsonio.load(SCHEMAS_DIR / f"{name}.json")
    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == f"https://genes.pietri.dev/schemas/{name}.json"


def test_example_files_match_their_schemas() -> None:
    base = EXAMPLES_DIR / "plants" / "example-tree"
    for name, path in [
        ("sheet.v1", base / "sheets" / "1.json"),
        ("look.v1", base / "looks" / "1" / "look.json"),
        ("refs.v1", base / "references" / "refs.json"),
    ]:
        errors = list(schema_validator(name).iter_errors(jsonio.load(path)))
        assert errors == [], (name, [e.message for e in errors])


def _minimal_sheet(kind: str) -> dict[str, object]:
    sheet: dict[str, object] = {
        "format": "genes.sheet.v1",
        "id": "furnarius-rufus",
        "version": 1,
        "kind": kind,
        "scientific_name": "Furnarius rufus",
        "names": {"es": ["Hornero"], "en": ["Rufous hornero"]},
        "status_in_sierras_chicas": "native",
        "summary": {"es": "Hace nidos de barro.", "en": "Builds mud nests."},
        "sources": [{"id": "s1", "kind": "observations", "title": "iNaturalist"}],
    }
    return sheet


def test_an_animal_sheet_fits_the_reserved_block() -> None:
    sheet = _minimal_sheet("animal")
    sheet["animal"] = {"class": "bird"}
    sheet["relations"] = [
        {"type": "nests_in", "species": "neltuma-alba", "planned": True, "source": ["s1"]}
    ]
    assert list(schema_validator("sheet.v1").iter_errors(sheet)) == []


def test_kind_and_block_must_agree() -> None:
    sheet = _minimal_sheet("animal")
    sheet["plant"] = {"growth_form": "tree"}
    assert list(schema_validator("sheet.v1").iter_errors(sheet))


@pytest.mark.parametrize("bad_id", ["Neltuma-alba", "neltuma_alba", "-x", "neltuma--alba", ""])
def test_ids_are_kebab_slugs(bad_id: str) -> None:
    sheet = _minimal_sheet("animal")
    sheet["id"] = bad_id
    sheet["animal"] = {"class": "bird"}
    assert list(schema_validator("sheet.v1").iter_errors(sheet))
