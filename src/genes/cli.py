"""The `genes` command.

genes validate [--examples] [--base main]   check species (spec §15)
genes build [--examples] [--out dist]       write the static site (spec §12)
genes serve [--examples] [--port 8810]      build into a temporary folder and serve it
genes make-example                          rebuild the example species's code-made models
genes refs candidates <id> --taxon N         shareable iNaturalist photos to choose from
genes refs add <id> <n> --shows .. --angle ..  store a chosen photo (spec §9)
genes build-models <id> [--stage S] ...      build a look's models (needs `uv sync --group blender`)
genes contact-sheet <id>                     models beside the reference photos (spec §7.1)
genes doctor                                 is this computer ready to add a species?
genes form-reference                         rewrite docs/PLANT_FORM_PARAMETERS.md from the schema
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from genes import catalog, example, serve, validate
from genes.paths import EXAMPLES_DIR, REPO_ROOT, SPECIES_DIR


def _roots(with_examples: bool) -> list[Path]:
    return [SPECIES_DIR, *([EXAMPLES_DIR] if with_examples else [])]


def _species_dir(species_id: str) -> Path:
    for kind in ("plants", "animals"):
        folder = SPECIES_DIR / kind / species_id
        if folder.is_dir():
            return folder
    raise SystemExit(f"no species folder for {species_id} under species/")


PLANT_GENERATOR = REPO_ROOT / "tools" / "blender" / "plant" / "main.py"


def build_models(
    species_id: str,
    look: int | None = None,
    stages: list[str] | None = None,
    variants: list[str] | None = None,
    lods: list[str] | None = None,
) -> int:
    """Run the plant generator on a look folder with this Python, which must have bpy."""
    import importlib.util
    import subprocess

    folder = _species_dir(species_id) / "looks"
    numbers = sorted(int(p.name) for p in folder.iterdir() if p.name.isdigit())
    if not numbers:
        raise SystemExit(f"{species_id} has no look")
    number = look if look is not None else numbers[-1]
    if look is None and len(numbers) > 1:
        print(f"building look {number}", file=sys.stderr)
    if importlib.util.find_spec("bpy") is None:
        raise SystemExit("Blender's bpy is not installed: run `uv sync --group blender` once")
    cmd = [sys.executable, str(PLANT_GENERATOR), str(folder / str(number))]
    for flag, values in (("--stage", stages), ("--variant", variants), ("--lod", lods)):
        for value in values or []:
            cmd += [flag, value]
    return subprocess.run(cmd, check=False).returncode


def _check(with_examples: bool, base: str | None) -> bool:
    problems = validate.validate(_roots(with_examples), EXAMPLES_DIR, base)
    for p in problems:
        print(p, file=sys.stderr)
    return not problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="genes", description="Species of the pietri.dev world.")
    sub = parser.add_subparsers(dest="command", required=True)

    def with_examples(p: argparse.ArgumentParser) -> None:
        p.add_argument("--examples", action="store_true", help="include the example species")

    p_val = sub.add_parser("validate", help="check every species")
    with_examples(p_val)
    p_val.add_argument(
        "--base", default="main", help="git ref whose versions are frozen (default main)"
    )

    p_build = sub.add_parser("build", help="write the static site")
    with_examples(p_build)
    p_build.add_argument("--out", type=Path, default=REPO_ROOT / "dist")

    p_serve = sub.add_parser("serve", help="serve the site on 127.0.0.1")
    with_examples(p_serve)
    p_serve.add_argument("--port", type=int, default=8810)

    sub.add_parser("make-example", help="rebuild the example species's models")

    p_refs = sub.add_parser("refs", help="reference photos from iNaturalist")
    refs_sub = p_refs.add_subparsers(dest="refs_command", required=True)
    p_cand = refs_sub.add_parser("candidates", help="download shareable candidates to look at")
    p_cand.add_argument("species")
    p_cand.add_argument("--taxon", type=int, required=True, help="iNaturalist taxon id")
    p_add = refs_sub.add_parser("add", help="store a candidate in references/")
    p_add.add_argument("species")
    p_add.add_argument("number", type=int)
    p_add.add_argument("--shows", required=True, help="comma list: whole,summer,trunk,...")
    p_add.add_argument("--angle", required=True, choices=["side", "below", "above", "detail"])
    p_add.add_argument("--box", help="tree box l,t,r,b as fractions, for whole-tree photos")
    p_add.add_argument("--used-for", action="append")

    p_models = sub.add_parser("build-models", help="build a look's models (needs Blender's bpy)")
    p_models.add_argument("species")
    p_models.add_argument("--look", type=int, help="look version (default: the latest)")
    for flag in ("--stage", "--variant", "--lod"):
        p_models.add_argument(flag, action="append")

    p_sheet = sub.add_parser("contact-sheet", help="render models beside the reference photos")
    p_sheet.add_argument("species")
    p_sheet.add_argument("--out", type=Path, help="default: looks/<n>/sheet.png")

    sub.add_parser("doctor", help="check this computer is ready to add a species")
    sub.add_parser("form-reference", help="rewrite docs/PLANT_FORM_PARAMETERS.md")

    args = parser.parse_args(argv)

    if args.command == "form-reference":
        from genes import formdoc

        formdoc.write()
        print(formdoc.DOC.relative_to(REPO_ROOT))
        return 0

    if args.command == "doctor":
        from genes import doctor

        checks = doctor.run()
        print(doctor.report(checks), end="")
        return 0 if all(c.ok for c in checks) else 1

    if args.command == "validate":
        ok = _check(args.examples, args.base)
        print("ok" if ok else "problems found", file=sys.stderr)
        return 0 if ok else 1

    if args.command == "build":
        if not _check(args.examples, None):
            return 1
        cat = catalog.build(_roots(args.examples), args.out)
        print(f"catalog {cat['catalog']}: {len(cat['species'])} species → {args.out}")
        return 0

    if args.command == "serve":
        if not _check(args.examples, None):
            print("serving anyway, so the problems can be looked at", file=sys.stderr)
        with tempfile.TemporaryDirectory(prefix="genes-") as tmp:
            out = Path(tmp)
            cat = catalog.build(_roots(args.examples), out)
            server = serve.make_server(out, port=args.port)
            print(
                f"{len(cat['species'])} species. Open http://127.0.0.1:{args.port}/  (Ctrl+C stops)"
            )
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        return 0

    if args.command == "make-example":
        for look_dir in sorted((EXAMPLES_DIR / "plants").glob("*/looks/*")):
            for path in example.build_look(look_dir):
                print(path.relative_to(REPO_ROOT))
        return 0

    if args.command == "refs":
        from genes import refs

        if args.refs_command == "candidates":
            refs.candidates(args.species, args.taxon)
            return 0
        folder = _species_dir(args.species)
        box = [float(x) for x in args.box.split(",")] if args.box else None
        entry = refs.add(folder, args.number, args.shows.split(","), args.angle, box, args.used_for)
        print(f"{entry['id']}: {entry['url']} ({entry['licence']}, {entry['author']})")
        return 0

    if args.command == "build-models":
        return build_models(args.species, args.look, args.stage, args.variant, args.lod)

    if args.command == "contact-sheet":
        from genes import contact

        path, matches = contact.contact_sheet(_roots(True), args.species, args.out)
        print(contact.scores_json(matches), end="")
        print(f"sheet: {path}", file=sys.stderr)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
