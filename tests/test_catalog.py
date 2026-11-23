from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from genes import catalog, jsonio
from genes.validate import schema_validator

from .conftest import example_dir


def _tree(path: Path) -> dict[str, bytes]:
    return {
        p.relative_to(path).as_posix(): p.read_bytes()
        for p in sorted(path.rglob("*"))
        if p.is_file()
    }


def test_build_is_byte_identical(tmp_path: Path, examples: Path) -> None:
    catalog.build([examples], tmp_path / "a")
    catalog.build([examples], tmp_path / "b")
    assert _tree(tmp_path / "a") == _tree(tmp_path / "b")


def test_catalog_content(tmp_path: Path, examples: Path) -> None:
    out = tmp_path / "dist"
    cat = catalog.build([examples], out)
    assert list(schema_validator("catalog.v1").iter_errors(cat)) == []
    assert json.loads((out / "v1" / "catalog.json").read_text(encoding="utf-8")) == cat
    assert cat["catalog"] == 2  # one sheet + one look
    (entry,) = cat["species"]
    assert entry["id"] == "example-tree" and entry["growth_form"] == "tree"
    # Every listed file exists in dist with the listed hash.
    files: list[dict[str, Any]] = [*entry["sheets"], *entry["looks"], entry["references"]]
    files += entry["looks"][0]["files"]
    for f in files:
        on_disk = out / f["path"].lstrip("/")
        assert jsonio.sha256_file(on_disk) == f["sha256"]
    assert len(entry["looks"][0]["files"]) == 12
    # Sheets and looks are copied byte for byte.
    src = example_dir(examples) / "sheets" / "1.json"
    assert (out / "v1/species/example-tree/sheets/1.json").read_bytes() == src.read_bytes()
    # The viewer, a page per species, the budgets.
    assert (out / "index.html").exists() and (out / "static" / "viewer.js").exists()
    assert (out / "species" / "example-tree" / "index.html").read_bytes() == (
        out / "index.html"
    ).read_bytes()
    assert (out / "v1" / "budgets.json").exists()


def test_reverse_relations(tmp_path: Path, examples: Path) -> None:
    # A second species that eats the example tree's fruit.
    import shutil

    other = examples / "plants" / "example-vine"
    shutil.copytree(example_dir(examples), other)
    shutil.rmtree(other / "looks")
    shutil.rmtree(other / "references")
    sheet = jsonio.load(other / "sheets" / "1.json")
    sheet["id"] = "example-vine"
    sheet["relations"] = [
        {
            "type": "eats",
            "species": "example-tree",
            "part": "fruit",
            "months": [1],
            "source": ["ex"],
        }
    ]
    (other / "sheets" / "1.json").write_text(json.dumps(sheet), encoding="utf-8")
    cat = catalog.build([examples], tmp_path / "dist")
    tree = next(s for s in cat["species"] if s["id"] == "example-tree")
    assert tree["related"] == [
        {"type": "eats", "from": "example-vine", "part": "fruit", "months": [1]}
    ]
    vine = next(s for s in cat["species"] if s["id"] == "example-vine")
    assert vine["looks"] == [] and "references" not in vine
