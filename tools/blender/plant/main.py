"""Build a look's models headless: `genes build-models` runs this with Blender's Python.

    python tools/blender/plant/main.py <look_dir> [--stage S] [--variant a] [--lod lod0]

Writes `<stage>-<variant>.<lod>.glb` next to look.json, compressed with meshopt
(tools/compress), and prints one JSON line per model with its numbers.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from plant import blend, textures  # noqa: E402
from plant.form import resolve, seed  # noqa: E402
from plant.model import build  # noqa: E402

REPO = HERE.parents[2]
COMPRESS = REPO / "tools" / "compress" / "compress.mjs"


def compress(src: Path, dst: Path) -> None:
    if not (COMPRESS.parent / "node_modules").is_dir():
        sys.exit("tools/compress has no node_modules: run `npm ci --prefix tools/compress` once")
    subprocess.run(["node", str(COMPRESS), str(src), str(dst)], check=True, capture_output=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("look_dir", type=Path)
    parser.add_argument("--stage", action="append")
    parser.add_argument("--variant", action="append")
    parser.add_argument("--lod", action="append")
    parser.add_argument("--raw", action="store_true", help="skip meshopt (for debugging)")
    args = parser.parse_args(argv)

    look_dir: Path = args.look_dir.resolve()
    look = json.loads((look_dir / "look.json").read_text(encoding="utf-8"))
    budgets = json.loads((REPO / "budgets.json").read_text(encoding="utf-8"))
    adult = resolve(look, "adult" if "adult" in look["stages"] else next(iter(look["stages"])), "a")
    lo, hi = adult.range("crown.clump_size_m")
    atlas = textures.foliage_atlas(adult.data, (lo + hi) / 2, seed(look["id"], "foliage"))
    bark = textures.bark(adult.data, seed(look["id"], "bark"))
    # lod1 is seen from further away: half-size textures keep the look's weight down.
    tex_by_lod = {
        "lod0": {"foliage": atlas, "bark": bark},
        "lod1": {"foliage": textures.half(atlas), "bark": textures.half_bark(bark)},
    }
    from genes.species import variant_letters

    with tempfile.TemporaryDirectory() as tmp:
        for stage in sorted(look["stages"]):
            if args.stage and stage not in args.stage:
                continue
            for variant in variant_letters(int(look["stages"][stage].get("variants", 1))):
                if args.variant and variant not in args.variant:
                    continue
                for lod in look["lods"]:
                    if (args.lod and lod not in args.lod) or lod == "impostor":
                        continue
                    model = build(look, stage, variant, lod, budgets)
                    name = f"{stage}-{variant}.{lod}.glb"
                    raw = Path(tmp) / name
                    blend.export(model, tex_by_lod.get(lod, tex_by_lod["lod0"]), raw)
                    out = look_dir / name
                    if args.raw:
                        out.write_bytes(raw.read_bytes())
                    else:
                        compress(raw, out)
                    print(
                        json.dumps(
                            {
                                "model": name,
                                "triangles": model.triangles,
                                "parts": {k: p.triangle_count for k, p in model.parts.items()},
                                "bytes": out.stat().st_size,
                                "height_m": model.extras["ref_height_m"],
                                "crown_m": model.extras["ref_crown_m"],
                                "notes": model.notes,
                            }
                        ),
                        flush=True,
                    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
