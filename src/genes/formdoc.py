"""The plant form's parameters as a Markdown reference, written from the schema.

`docs/PLANT_FORM_PARAMETERS.md` is this module's output; a test keeps the two in step,
so the reference never drifts from what the generator accepts.
"""

from __future__ import annotations

import json
from typing import Any

from genes import jsonio
from genes.paths import REPO_ROOT

SCHEMA = REPO_ROOT / "schemas" / "plant-form.v1.json"
DOC = REPO_ROOT / "docs" / "PLANT_FORM_PARAMETERS.md"

# What each group is for, in the order an agent should read the photos.
GROUPS = {
    "crown": "The crown's outline: how wide, how high it starts, flat or round, airy or full.",
    "trunk": "The trunk and the leaders above the fork: count, fork, lean, crookedness, girth.",
    "branching": "Levels of branches below the leaders (1 = main limbs, 2 = branches, "
    "3 = twigs), one entry per level.",
    "foliage": "The leaves: clumps of painted cards along the twigs.",
    "tips": "The fine crooked twiglets at every branch end (what shows on a bare crown).",
    "flowers": "Flowers, shown in the sheet's flowering months.",
    "fruit": "Fruit, shown in the sheet's fruiting months.",
    "thorns": "Thorns on twigs, branches or trunk.",
    "old": "What changes when the tree is old.",
    "dead": "What changes when the tree is dead.",
    "stages": "Overrides for one stage.",
}

KIND = {
    "range": "number or [min, max]",
    "fraction": "0–1",
    "fraction_range": "0–1, or [min, max]",
    "signed_range": "-1–1, or [min, max]",
    "int_range": "integer or [min, max]",
    "interval": "[min, max]",
}


def _kind(node: dict[str, Any]) -> str:
    if "$ref" in node:
        return KIND.get(node["$ref"].rsplit("/", 1)[-1], "")
    if "enum" in node:
        return " | ".join(f"`{v}`" for v in node["enum"])
    t = node.get("type", "")
    if t == "array" and "items" in node and "enum" in node["items"]:
        return "list of " + " | ".join(f"`{v}`" for v in node["items"]["enum"])
    return str(t)


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _rows(props: dict[str, Any], prefix: str) -> list[str]:
    rows: list[str] = []
    for name, node in props.items():
        path = f"{prefix}{name}"
        if node.get("type") == "object" and "properties" in node:
            rows += _rows(node["properties"], path + ".")
            continue
        default = json.dumps(node["default"], ensure_ascii=False) if "default" in node else ""
        rows.append(
            f"| `{path}` | {_cell(_kind(node))} | {_cell(default)} | "
            f"{_cell(node.get('description', ''))} |"
        )
    return rows


def render() -> str:
    schema = jsonio.load(SCHEMA)
    out = [
        "# Plant form parameters (generator `plant@1`)",
        "",
        "Every parameter a look's `form` can set, written from "
        "`schemas/plant-form.v1.json` by `uv run genes form-reference`. Do not edit by hand.",
        "",
        "A look writes only what makes its species different; everything else takes the "
        "default. Ranges: their middle is what is drawn, except `trunk.tortuosity`, "
        "`trunk.twist`, `trunk.gnarl` and `trunk.fluting`, which each variant draws from "
        "its range (variants differ only in crookedness). How to choose them from photos: "
        "`docs/HOW_TO_ADD_A_SPECIES.md`.",
        "",
    ]
    props = schema["properties"]
    for group in [g for g in GROUPS if g in props] + [g for g in props if g not in GROUPS]:
        node = props[group]
        out += [f"## `{group}`", "", GROUPS.get(group, "")]
        if node.get("description"):
            out += ["", _cell(node["description"])]
        out += ["", "| Parameter | Value | Default | What it does |", "| --- | --- | --- | --- |"]
        if node.get("type") == "array":
            out += _rows(node["items"]["properties"], f"{group}[].")
        elif "properties" in node:
            out += _rows(node["properties"], f"{group}.")
        else:
            out = out[:-2]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write() -> None:
    DOC.write_text(render(), encoding="utf-8")
