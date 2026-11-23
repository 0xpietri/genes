"""`genes doctor`: is this computer ready to add a species?

Checks, without the network and without installing anything, what the recipe
(docs/HOW_TO_ADD_A_SPECIES.md, step 0) needs, and prints the one command that fixes each
missing piece.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from genes.paths import REPO_ROOT

COMPRESS = REPO_ROOT / "tools" / "compress"


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    fix: str = ""


def _python() -> Check:
    v = sys.version_info
    ok = (v.major, v.minor) == (3, 13)
    return Check("Python 3.13", ok, f"{v.major}.{v.minor}.{v.micro}", "uv python install 3.13")


def _bpy() -> Check:
    ok = importlib.util.find_spec("bpy") is not None
    return Check(
        "Blender as a Python module (bpy)",
        ok,
        "installed" if ok else "missing: models cannot be built",
        "uv sync --group blender",
    )


def _node() -> Check:
    node = shutil.which("node")
    if node is None:
        return Check("Node.js 18 or newer", False, "missing", "install Node.js 18+ (nodejs.org)")
    out = subprocess.run([node, "--version"], capture_output=True, text=True, check=False)
    match = re.match(r"v(\d+)", out.stdout.strip())
    major = int(match.group(1)) if match else 0
    return Check(
        "Node.js 18 or newer", major >= 18, out.stdout.strip() or "unknown", "install Node.js 18+"
    )


def _compress() -> Check:
    ok = (COMPRESS / "node_modules").is_dir()
    return Check(
        "Model compressor (tools/compress)",
        ok,
        "installed" if ok else "missing: models cannot be compressed",
        "npm ci --prefix tools/compress",
    )


def _chromium() -> Check:
    fix = "uv run playwright install chromium"
    if importlib.util.find_spec("playwright") is None:
        return Check("Chromium for contact sheets", False, "playwright missing", "uv sync")
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            path = Path(p.chromium.executable_path)
    except Exception as e:  # any failure means it cannot render
        return Check("Chromium for contact sheets", False, str(e).splitlines()[0], fix)
    from genes.contact import CHROMIUM_FALLBACK

    ok = path.exists() or Path(CHROMIUM_FALLBACK).exists()
    return Check("Chromium for contact sheets", ok, "installed" if ok else "missing", fix)


def _git() -> Check:
    git = shutil.which("git")
    if git is None:
        return Check("git", False, "missing", "install git")
    out = subprocess.run(
        [git, "-C", str(REPO_ROOT), "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=False,
    )
    return Check("git", True, f"on branch {out.stdout.strip() or '(detached)'}")


CHECKS = (_python, _bpy, _node, _compress, _chromium, _git)


def run() -> list[Check]:
    return [check() for check in CHECKS]


def report(checks: list[Check]) -> str:
    lines = []
    for c in checks:
        mark = "ok     " if c.ok else "MISSING"
        lines.append(f"{mark} {c.name}: {c.detail}")
        if not c.ok and c.fix:
            lines.append(f"        fix: {c.fix}")
    missing = [c for c in checks if not c.ok]
    lines.append(
        "Ready to add a species."
        if not missing
        else f"{len(missing)} missing. Run the fixes above, then `uv run genes doctor` again."
    )
    return "\n".join(lines) + "\n"
