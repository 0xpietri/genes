"""The checks of spec §15 on species files and their models."""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from genes import glb, jsonio
from genes.paths import BUDGETS_FILE, REPO_ROOT, SCHEMAS_DIR
from genes.species import Species, Version, discover, expected_models, model_name

SHAREABLE_LICENCES = {"cc0", "cc-by", "cc-by-sa"}
ALLOWED_PARTS = {"bark", "foliage", "flowers", "fruit", "thorns"}
PHENOLOGY_PARTS = {"foliage", "flowers", "fruit"}  # carry _ORDER (spec §6.3)
BASE_TOLERANCE_M = 0.01
HEIGHT_TOLERANCE = 0.10  # a model's height may differ from its stage's ref_height_m by 10 %
EXAMPLE_PREFIX = "example-"


@dataclass(frozen=True)
class Problem:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------- schemas


def _registry() -> Registry[Any]:
    resources = []
    for path in sorted(SCHEMAS_DIR.glob("*.json")):
        schema = jsonio.load(path)
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


_VALIDATORS: dict[str, Draft202012Validator] = {}


def schema_validator(name: str) -> Draft202012Validator:
    """Validator for schemas/<name>.json, resolving references between the schemas."""
    if name not in _VALIDATORS:
        schema = jsonio.load(SCHEMAS_DIR / f"{name}.json")
        _VALIDATORS[name] = Draft202012Validator(schema, registry=_registry())
    return _VALIDATORS[name]


def _schema_problems(name: str, data: Any, path: Path, prefix: str = "") -> list[Problem]:
    out = []
    for err in sorted(schema_validator(name).iter_errors(data), key=lambda e: list(e.path)):
        where = (
            "/".join([prefix, *map(str, err.path)] if prefix else map(str, err.path)) or "(root)"
        )
        out.append(Problem(_rel(path), f"{where}: {err.message}"))
    return out


# ---------------------------------------------------------------- walking facts


def _walk(value: Any, where: str = "") -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        yield where, value
        for key, item in value.items():
            yield from _walk(item, f"{where}/{key}" if where else str(key))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from _walk(item, f"{where}/{i}")


def _sheet_problems(
    sp: Species, v: Version, known_ids: set[str], is_example: bool
) -> list[Problem]:
    sheet = v.data
    path = _rel(v.path)
    out = _schema_problems("sheet.v1", sheet, v.path)
    if not isinstance(sheet, dict):
        return out
    if sheet.get("id") != sp.id:
        out.append(Problem(path, f"id {sheet.get('id')!r} differs from its folder {sp.id!r}"))
    if sheet.get("version") != v.number:
        out.append(Problem(path, f"version {sheet.get('version')} differs from its file name"))
    if sheet.get("kind") != sp.kind:
        out.append(Problem(path, f"kind {sheet.get('kind')!r} but it lives under {sp.kind}s/"))

    sources = {s.get("id") for s in sheet.get("sources", []) if isinstance(s, dict)}
    example_sources = [
        s.get("id")
        for s in sheet.get("sources", [])
        if isinstance(s, dict) and s.get("kind") == "example"
    ]
    if example_sources and not is_example:
        out.append(Problem(path, "sources of kind 'example' are valid only for example species"))
    if sheet.get("status_in_sierras_chicas") == "example" and not is_example:
        out.append(Problem(path, "status 'example' is valid only for example species"))

    for where, node in _walk(sheet):
        if where.startswith("sources"):
            continue
        src = node.get("source")
        if isinstance(src, list):
            for sid in src:
                if sid not in sources:
                    out.append(Problem(path, f"{where}: source {sid!r} is not in sources[]"))
        if "min" in node and "max" in node:
            lo, hi, typ = node.get("min"), node.get("max"), node.get("typical", node.get("min"))
            numbers = [x for x in (lo, hi, typ) if isinstance(x, int | float)]
            if len(numbers) == 3 and not numbers[0] <= numbers[2] <= numbers[1]:
                out.append(Problem(path, f"{where}: needs min ≤ typical ≤ max"))

    out += _tone_problems(sheet, path)

    for i, rel in enumerate(sheet.get("relations", [])):
        if not isinstance(rel, dict):
            continue
        other = rel.get("species")
        if other == sp.id:
            out.append(Problem(path, f"relations/{i}: a species cannot relate to itself"))
        elif other not in known_ids and not rel.get("planned"):
            out.append(
                Problem(path, f"relations/{i}: species {other!r} is not in genes (mark it planned)")
            )
    return out


def _tone_problems(sheet: dict[str, Any], path: str) -> list[Problem]:
    """Leaf tones (spec §6.4): at most two share a month, and together they cover every
    month a leaf is on: all year unless the tree is deciduous."""
    ph = (sheet.get("plant") or {}).get("phenology") or {}
    tones = ph.get("leaf_tones")
    if not isinstance(tones, list):
        return []
    out: list[Problem] = []
    count = dict.fromkeys(range(1, 13), 0)
    for t in tones:
        for m in t.get("months", []) if isinstance(t, dict) else []:
            if m in count:
                count[m] += 1
    crowded = [m for m, n in count.items() if n > 2]
    if crowded:
        out.append(Problem(path, f"leaf_tones: more than two tones in months {crowded}"))
    if ph.get("leaf_habit") != "deciduous":
        empty = [m for m, n in count.items() if n == 0]
        if empty:
            out.append(Problem(path, f"leaf_tones: no tone in months {empty}"))
    return out


# ---------------------------------------------------------------- looks and models


def _range_of(sheet: Any, *keys: str) -> tuple[float, float] | None:
    node = sheet
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    if isinstance(node, dict) and "min" in node and "max" in node:
        return float(node["min"]), float(node["max"])
    return None


def _model_problems(
    path: Path, look: dict[str, Any], stage: str, variant: str, lod: str, budgets: dict[str, Any]
) -> list[Problem]:
    rel = _rel(path)
    if not path.exists():
        return [Problem(rel, "model is missing")]
    try:
        info = glb.inspect(path)
    except glb.GlbError as exc:
        return [Problem(rel, str(exc))]
    out: list[Problem] = []

    tri_budget = budgets["triangles"].get(lod, {}).get(stage)
    if tri_budget is not None and info.triangles > tri_budget:
        out.append(Problem(rel, f"{info.triangles} triangles, budget {tri_budget}"))
    if lod == "lod0" and info.bytes > budgets["file_bytes_lod0"]:
        out.append(Problem(rel, f"{info.bytes} bytes, budget {budgets['file_bytes_lod0']}"))
    for name in sorted(set(info.meshes) | set(info.materials)):
        if name not in ALLOWED_PARTS:
            out.append(Problem(rel, f"part {name!r} is not one of {sorted(ALLOWED_PARTS)}"))
    for prim in info.primitives:
        if prim.mesh in PHENOLOGY_PARTS and "_ORDER" not in prim.attributes:
            out.append(Problem(rel, f"{prim.mesh} has no _ORDER attribute (spec §6.3)"))
    if info.has_cameras or info.has_lights:
        out.append(Problem(rel, "models carry no cameras or lights (spec §8)"))

    if abs(info.bbox_min[1]) > BASE_TOLERANCE_M:
        out.append(Problem(rel, f"base at y = {info.bbox_min[1]:.3f} m, must be 0"))
    if not (
        info.bbox_min[0] <= 0 <= info.bbox_max[0] and info.bbox_min[2] <= 0 <= info.bbox_max[2]
    ):
        out.append(Problem(rel, "the origin is outside the model's footprint"))
    ref_h = float(look["stages"][stage]["ref_height_m"])
    if stage != "fallen" and abs(info.height - ref_h) > HEIGHT_TOLERANCE * ref_h:
        out.append(Problem(rel, f"height {info.height:.2f} m, its stage says {ref_h} m"))

    extras = info.extras.get("genes")
    if not isinstance(extras, dict):
        out.append(Problem(rel, "extras.genes is missing (spec §8)"))
        return out
    want = {
        "id": look.get("id"),
        "look": look.get("look"),
        "stage": stage,
        "variant": variant,
        "lod": lod,
        "params_hash": jsonio.params_hash(look.get("form")),
    }
    for key, value in want.items():
        if extras.get(key) != value:
            out.append(
                Problem(rel, f"extras.genes.{key} is {extras.get(key)!r}, expected {value!r}")
            )
    for key in ("ref_height_m", "generator"):
        if key not in extras:
            out.append(Problem(rel, f"extras.genes.{key} is missing"))
    return out


# Generators whose `form` has its own schema (the others are free-form).
FORM_SCHEMAS = {"plant@1": "plant-form.v1"}


def _look_problems(sp: Species, v: Version, budgets: dict[str, Any]) -> list[Problem]:
    look = v.data
    path = _rel(v.path)
    out = _schema_problems("look.v1", look, v.path)
    if not isinstance(look, dict):
        return out
    form_schema = FORM_SCHEMAS.get(str(look.get("generator")))
    if form_schema and "form" in look:
        out.extend(_schema_problems(form_schema, look["form"], v.path, "form"))
    if look.get("id") != sp.id:
        out.append(Problem(path, f"id {look.get('id')!r} differs from its folder {sp.id!r}"))
    if look.get("look") != v.number:
        out.append(Problem(path, f"look {look.get('look')} differs from its folder name"))
    sheet_numbers = {s.number: s for s in sp.sheets}
    for_sheet = look.get("for_sheet")
    if not isinstance(for_sheet, int) or for_sheet not in sheet_numbers:
        out.append(Problem(path, f"for_sheet {for_sheet} does not exist"))
    if out or not isinstance(for_sheet, int):
        return out

    sheet = sheet_numbers[for_sheet].data
    adult = look["stages"].get("adult")
    height_range = _range_of(sheet, "plant", "size", "adult_height_m")
    if adult and height_range:
        lo, hi = height_range
        if not lo <= adult["ref_height_m"] <= hi:
            out.append(
                Problem(
                    path,
                    f"adult ref_height_m {adult['ref_height_m']} is outside "
                    f"the sheet's {lo}–{hi} m",
                )
            )

    foliage = (look.get("palette") or {}).get("foliage") or {}
    ph = (sheet.get("plant") or {}).get("phenology") or {}
    for t in ph.get("leaf_tones") or []:
        tone = t.get("tone") if isinstance(t, dict) else None
        if tone and "lit" not in foliage and tone not in foliage:
            out.append(
                Problem(path, f"palette.foliage has no {tone!r} tone the sheet's leaf_tones use")
            )

    if sp.refs is not None and isinstance(sp.refs.data, dict):
        photo_ids = {p.get("id") for p in sp.refs.data.get("photos", [])}
        for rid in look.get("references", []):
            if rid not in photo_ids:
                out.append(Problem(path, f"reference {rid!r} is not in refs.json"))

    folder = v.path.parent
    expected = {model_name(*m) for m in expected_models(look)}
    total = 0
    for stage, variant, lod in expected_models(look):
        model = folder / model_name(stage, variant, lod)
        out.extend(_model_problems(model, look, stage, variant, lod, budgets))
        if model.exists():
            total += model.stat().st_size
    for extra in sorted(folder.glob("*.glb")):
        if extra.name not in expected:
            out.append(
                Problem(_rel(extra), "model not listed by the look's stages, variants and lods")
            )
    if total > budgets["look_bytes"]:
        out.append(Problem(path, f"models weigh {total} bytes, budget {budgets['look_bytes']}"))
    return out


# ---------------------------------------------------------------- references


def _refs_problems(sp: Species) -> list[Problem]:
    if sp.refs is None:
        return []
    v = sp.refs
    path = _rel(v.path)
    out = _schema_problems("refs.v1", v.data, v.path)
    if not isinstance(v.data, dict):
        return out
    if v.data.get("id") != sp.id:
        out.append(Problem(path, f"id {v.data.get('id')!r} differs from its folder {sp.id!r}"))
    seen: set[str] = set()
    for photo in v.data.get("photos", []):
        pid = photo.get("id")
        if pid in seen:
            out.append(Problem(path, f"photo id {pid!r} is repeated"))
        seen.add(pid)
        if "file" in photo:
            if photo.get("licence") not in SHAREABLE_LICENCES:
                out.append(
                    Problem(
                        path,
                        f"photo {pid!r}: licence {photo.get('licence')} cannot be stored, "
                        "link only",
                    )
                )
            if not (v.path.parent / photo["file"]).exists():
                out.append(Problem(path, f"photo {pid!r}: file {photo['file']} is missing"))
        box = photo.get("tree_box")
        if isinstance(box, list) and len(box) == 4 and not (box[0] < box[2] and box[1] < box[3]):
            out.append(
                Problem(path, f"photo {pid!r}: tree_box needs left < right and top < bottom")
            )
        if box and "file" not in photo:
            out.append(Problem(path, f"photo {pid!r}: a tree_box needs a stored file"))
    return out


# ---------------------------------------------------------------- frozen versions


LIFECYCLE_COLUMNS = (
    "date",
    "age_days",
    "h_mm",
    "crown_radius_mm",
    "stem_mm",
    "status",
    "health",
    "decay",
)


def _lifecycle_problems(sp: Species) -> list[Problem]:
    """A recorded life from pietri.dev's simulator (the species page replays it)."""
    folder = sp.folder / "lifecycle"
    if not folder.is_dir():
        return []
    out: list[Problem] = []
    for path in sorted(folder.iterdir()):
        rel = _rel(path)
        if path.suffix != ".json" or not path.stem.isdigit():
            out.append(Problem(rel, "lifecycle files are <n>.json"))
            continue
        try:
            life = jsonio.load(path)
        except ValueError as exc:
            out.append(Problem(rel, f"cannot read JSON ({exc})"))
            continue
        if life.get("format") != "pietri.lifecycle.v1":
            out.append(Problem(rel, "format must be pietri.lifecycle.v1"))
            continue
        if not isinstance(life.get("recorded"), dict) or "commit" not in life["recorded"]:
            out.append(Problem(rel, "recorded{repository, commit, command} is missing"))
        samples = life.get("samples", {})
        lengths = {k: len(samples.get(k, [])) for k in LIFECYCLE_COLUMNS}
        if len(set(lengths.values())) != 1 or not lengths["date"]:
            out.append(Problem(rel, f"sample columns differ in length or are empty: {lengths}"))
            continue
        statuses = life.get("statuses", [])
        if any(not 0 <= s < len(statuses) for s in samples["status"]):
            out.append(Problem(rel, "a status index is outside statuses[]"))
        if samples["age_days"] != sorted(samples["age_days"]):
            out.append(Problem(rel, "samples are not in time order"))
    return out


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=False)


def frozen_problems(species: list[Species], base: str, repo: Path = REPO_ROOT) -> list[Problem]:
    """A sheet or look version merged into `base` must not change (spec §4)."""
    if _git(["rev-parse", "--verify", "--quiet", base], repo).returncode != 0:
        return []
    out: list[Problem] = []
    for sp in species:
        files: list[Path] = [s.path for s in sp.sheets]
        for look in sp.looks:
            files.extend(sorted(p for p in look.path.parent.iterdir() if p.is_file()))
        for f in files:
            try:
                relpath = f.resolve().relative_to(repo.resolve()).as_posix()
            except ValueError:
                continue
            old = _git(["show", f"{base}:{relpath}"], repo)
            if old.returncode != 0:
                continue  # not merged yet: a draft
            if old.stdout != f.read_bytes():
                out.append(
                    Problem(relpath, f"changed after it was merged into {base}; make a new version")
                )
    return out


# ---------------------------------------------------------------- all together


def validate(
    roots: list[Path], examples_root: Path | None = None, base: str | None = None
) -> list[Problem]:
    """Every problem in the species under `roots`. Species under `examples_root` may (and must)
    be example species; elsewhere example ids, sources and statuses are refused."""
    budgets = jsonio.load(BUDGETS_FILE)
    species = discover(roots)
    known = {sp.id for sp in species}
    out: list[Problem] = []
    ids_seen: set[str] = set()
    for sp in species:
        in_examples = (
            examples_root is not None and examples_root.resolve() in sp.folder.resolve().parents
        )
        rel = _rel(sp.folder)
        if sp.id in ids_seen:
            out.append(Problem(rel, f"species id {sp.id!r} appears twice"))
        ids_seen.add(sp.id)
        is_example = sp.id.startswith(EXAMPLE_PREFIX)
        if is_example != in_examples:
            out.append(
                Problem(rel, "example- species live only under examples/, and only they live there")
            )
        if not sp.sheets:
            out.append(Problem(rel, "no sheets/1.json"))
        numbers = [s.number for s in sp.sheets]
        if numbers != list(range(1, len(numbers) + 1)):
            out.append(Problem(rel, f"sheet versions must be 1..n without gaps, found {numbers}"))
        look_numbers = [v.number for v in sp.looks]
        if look_numbers != list(range(1, len(look_numbers) + 1)):
            out.append(
                Problem(rel, f"look versions must be 1..n without gaps, found {look_numbers}")
            )
        for v in [*sp.sheets, *sp.looks, *([sp.refs] if sp.refs else [])]:
            if v.error:
                out.append(Problem(_rel(v.path), v.error))
        for v in sp.sheets:
            if v.data is not None:
                out.extend(_sheet_problems(sp, v, known, is_example))
        for v in sp.looks:
            if v.data is not None:
                out.extend(_look_problems(sp, v, budgets))
        if sp.refs is not None and sp.refs.data is not None:
            out.extend(_refs_problems(sp))
        out.extend(_lifecycle_problems(sp))
    if base:
        out.extend(frozen_problems(species, base))
    return out
