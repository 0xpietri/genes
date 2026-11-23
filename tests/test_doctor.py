from __future__ import annotations

import importlib.util
from typing import Any

import pytest

from genes import doctor


def test_report_names_each_missing_piece_and_its_fix() -> None:
    checks = [
        doctor.Check("Python 3.13", True, "3.13.1"),
        doctor.Check(
            "Blender as a Python module (bpy)", False, "missing", "uv sync --group blender"
        ),
    ]
    text = doctor.report(checks)
    assert "ok      Python 3.13: 3.13.1" in text
    assert "MISSING Blender as a Python module (bpy): missing" in text
    assert "fix: uv sync --group blender" in text
    assert "1 missing." in text


def test_all_ok_says_ready() -> None:
    assert doctor.report([doctor.Check("git", True, "on branch main")]).endswith(
        "Ready to add a species.\n"
    )


def test_bpy_missing_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    real = importlib.util.find_spec

    def fake(name: str, *args: Any) -> Any:
        return None if name == "bpy" else real(name, *args)

    monkeypatch.setattr(importlib.util, "find_spec", fake)
    check = doctor._bpy()
    assert not check.ok
    assert check.fix == "uv sync --group blender"


def test_compressor_missing_is_reported(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    monkeypatch.setattr(doctor, "COMPRESS", tmp_path)
    check = doctor._compress()
    assert not check.ok
    assert check.fix == "npm ci --prefix tools/compress"


def test_the_form_reference_is_up_to_date() -> None:
    """docs/PLANT_FORM_PARAMETERS.md is written from the schema: run
    `uv run genes form-reference` after changing schemas/plant-form.v1.json."""
    from genes import formdoc

    assert formdoc.DOC.read_text(encoding="utf-8") == formdoc.render()


def test_the_form_reference_lists_every_parameter() -> None:
    from genes import formdoc, jsonio

    text = formdoc.render()
    schema = jsonio.load(formdoc.SCHEMA)
    for name in schema["properties"]["trunk"]["properties"]:
        if name != "bark":
            assert f"`trunk.{name}`" in text
    assert "`trunk.bark.pattern`" in text
    assert "`branching[].tortuosity`" in text
