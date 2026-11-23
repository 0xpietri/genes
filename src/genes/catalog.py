"""Building the static site genes.pietri.dev serves (spec §12).

    dist/index.html, dist/static/...                     the viewer
    dist/species/<id>/index.html                         a species page (same viewer)
    dist/v1/catalog.json                                 every species, versions, hashes
    dist/v1/budgets.json                                 the model budgets
    dist/v1/species/<id>/sheets/<n>.json                 copied byte for byte
    dist/v1/species/<id>/looks/<n>/look.json and models  copied byte for byte
    dist/v1/species/<id>/references.json and photos      the reference set

Same species files, same dist/: byte-identical (sorted keys, no timestamps).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from genes import jsonio
from genes.paths import BUDGETS_FILE, VIEWER_DIR
from genes.species import Species, discover


class CatalogError(RuntimeError):
    """The species do not pass validation; nothing was built."""


def _copy(src: Path, dst: Path) -> dict[str, Any]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    dst.write_bytes(data)
    return {"bytes": len(data), "sha256": jsonio.sha256_bytes(data)}


def _species_entry(sp: Species, out: Path) -> dict[str, Any]:
    base = out / "v1" / "species" / sp.id
    url = f"/v1/species/{sp.id}"
    sheets = []
    for v in sp.sheets:
        meta = _copy(v.path, base / "sheets" / f"{v.number}.json")
        sheets.append(
            {"version": v.number, "path": f"{url}/sheets/{v.number}.json", "sha256": meta["sha256"]}
        )
    looks = []
    for v in sp.looks:
        folder = v.path.parent
        meta = _copy(v.path, base / "looks" / str(v.number) / "look.json")
        files = []
        for model in sorted(folder.glob("*.glb")):
            m = _copy(model, base / "looks" / str(v.number) / model.name)
            files.append({"path": f"{url}/looks/{v.number}/{model.name}", **m})
        looks.append(
            {
                "version": v.number,
                "path": f"{url}/looks/{v.number}/look.json",
                "sha256": meta["sha256"],
                "files": files,
            }
        )

    sheet = sp.latest_sheet.data if sp.latest_sheet else {}
    entry: dict[str, Any] = {
        "id": sp.id,
        "kind": sp.kind,
        "scientific_name": sheet.get("scientific_name", ""),
        "names": sheet.get("names", {}),
        "status_in_sierras_chicas": sheet.get("status_in_sierras_chicas", ""),
        "sheets": sheets,
        "looks": looks,
    }
    if sp.kind == "plant":
        entry["growth_form"] = sheet.get("plant", {}).get("growth_form", "")
    else:
        entry["class"] = sheet.get("animal", {}).get("class", "")

    if sp.refs is not None and isinstance(sp.refs.data, dict):
        refs = sp.refs.data
        for photo in refs.get("photos", []):
            if "file" in photo:
                _copy(sp.refs.path.parent / photo["file"], base / "references" / photo["file"])
        text = jsonio.dumps(refs)
        (base / "references.json").write_text(text, encoding="utf-8")
        entry["references"] = {
            "path": f"{url}/references.json",
            "sha256": jsonio.sha256_bytes(text.encode("utf-8")),
            "bytes": len(text.encode("utf-8")),
        }
    return entry


def _add_reverse_relations(entries: list[dict[str, Any]], species: list[Species]) -> None:
    by_id = {e["id"]: e for e in entries}
    for sp in species:
        sheet = sp.latest_sheet.data if sp.latest_sheet else None
        if not isinstance(sheet, dict):
            continue
        for rel in sheet.get("relations", []):
            target = by_id.get(rel.get("species"))
            if target is None:
                continue
            item = {"type": rel["type"], "from": sp.id}
            for key in ("part", "months"):
                if key in rel:
                    item[key] = rel[key]
            target.setdefault("related", []).append(item)
    for e in entries:
        if "related" in e:
            e["related"].sort(key=lambda r: (r["from"], r["type"], r.get("part", "")))


def build_catalog(species: list[Species], out: Path) -> dict[str, Any]:
    entries = [_species_entry(sp, out) for sp in species]
    _add_reverse_relations(entries, species)
    count = sum(len(e["sheets"]) + len(e["looks"]) for e in entries)
    catalog = {"format": "genes.catalog.v1", "catalog": count, "species": entries}
    (out / "v1").mkdir(parents=True, exist_ok=True)
    (out / "v1" / "catalog.json").write_text(jsonio.dumps(catalog), encoding="utf-8")
    shutil.copyfile(BUDGETS_FILE, out / "v1" / "budgets.json")
    return catalog


def build_viewer(species: list[Species], out: Path) -> None:
    shutil.copytree(VIEWER_DIR / "static", out / "static", dirs_exist_ok=True)
    page = (VIEWER_DIR / "index.html").read_bytes()
    (out / "index.html").write_bytes(page)
    for sp in species:
        target = out / "species" / sp.id / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(page)


def build(roots: list[Path], out: Path) -> dict[str, Any]:
    """Write the whole site into `out` (emptied first). Validation is the caller's job."""
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    species = discover(roots)
    catalog = build_catalog(species, out)
    build_viewer(species, out)
    return catalog
