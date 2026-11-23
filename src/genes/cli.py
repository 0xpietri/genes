"""The `genes` command.

genes validate [--examples] [--base main]   check species (spec §15)
genes build [--examples] [--out dist]       write the static site (spec §12)
genes serve [--examples] [--port 8810]      build into a temporary folder and serve it
genes make-example                          rebuild the example species's code-made models
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

    args = parser.parse_args(argv)

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

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
