"""Finding species on disk (spec §10).

<root>/<kind>s/<id>/sheets/<n>.json
<root>/<kind>s/<id>/looks/<n>/look.json   and its models <stage>-<variant>.<lod>.glb
<root>/<kind>s/<id>/references/refs.json  and stored photos next to it
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from genes import jsonio

KIND_DIRS = {"plants": "plant", "animals": "animal"}


@dataclass
class Version:
    number: int
    path: Path  # the JSON file
    data: Any  # parsed JSON, or None if it did not parse
    error: str | None = None


@dataclass
class Species:
    id: str
    kind: str  # from the folder: plant or animal
    folder: Path
    sheets: list[Version]
    looks: list[Version]
    refs: Version | None

    @property
    def latest_sheet(self) -> Version | None:
        return self.sheets[-1] if self.sheets else None

    @property
    def latest_look(self) -> Version | None:
        return self.looks[-1] if self.looks else None


def model_name(stage: str, variant: str, lod: str) -> str:
    return f"{stage}-{variant}.{lod}.glb"


def variant_letters(count: int) -> list[str]:
    return [chr(ord("a") + i) for i in range(count)]


def expected_models(look: dict[str, Any]) -> list[tuple[str, str, str]]:
    """(stage, variant, lod) of every model a look must have, in a fixed order."""
    out: list[tuple[str, str, str]] = []
    for stage in sorted(look.get("stages", {})):
        for variant in variant_letters(int(look["stages"][stage].get("variants", 1))):
            for lod in look.get("lods", []):
                out.append((stage, variant, lod))
    return out


def _load(path: Path, number: int) -> Version:
    try:
        return Version(number, path, jsonio.load(path))
    except (OSError, ValueError) as exc:
        return Version(number, path, None, f"{path}: cannot read JSON ({exc})")


def _numbered(folder: Path, pattern: str) -> list[tuple[int, Path]]:
    found: list[tuple[int, Path]] = []
    if not folder.is_dir():
        return found
    for entry in folder.iterdir():
        stem = entry.stem if pattern == "file" else entry.name
        wanted = (pattern == "file" and entry.suffix == ".json") or (
            pattern == "dir" and entry.is_dir()
        )
        if wanted and stem.isdigit():
            found.append((int(stem), entry))
    return sorted(found)


def load_species(folder: Path, kind: str) -> Species:
    sheets = [_load(p, n) for n, p in _numbered(folder / "sheets", "file")]
    looks = [_load(p / "look.json", n) for n, p in _numbered(folder / "looks", "dir")]
    refs_path = folder / "references" / "refs.json"
    refs = _load(refs_path, 1) if refs_path.exists() else None
    return Species(folder.name, kind, folder, sheets, looks, refs)


def discover(roots: list[Path]) -> list[Species]:
    """Every species under the given roots, sorted by id."""
    found: list[Species] = []
    for root in roots:
        for kind_dir, kind in KIND_DIRS.items():
            base = root / kind_dir
            if not base.is_dir():
                continue
            for folder in sorted(base.iterdir()):
                if folder.is_dir() and not folder.name.startswith("."):
                    found.append(load_species(folder, kind))
    return sorted(found, key=lambda s: s.id)
