"""The `genes` command's new subcommands, without the network or Blender."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from genes import cli


def test_build_models_runs_the_generator_on_the_latest_look(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[list[str]] = []

    def run(cmd: list[str], check: bool) -> Any:
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr("importlib.util.find_spec", lambda name: object())
    assert cli.main(["build-models", "neltuma-alba", "--stage", "adult", "--lod", "lod0"]) == 0
    cmd = seen[0]
    assert cmd[1].endswith(str(Path("tools", "blender", "plant", "main.py")))
    assert cmd[2].endswith(str(Path("neltuma-alba", "looks", "1")))
    assert cmd[3:] == ["--stage", "adult", "--lod", "lod0"]


def test_build_models_without_blender(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
    with pytest.raises(SystemExit, match="uv sync --group blender"):
        cli.main(["build-models", "neltuma-alba"])


def test_unknown_species() -> None:
    with pytest.raises(SystemExit, match="no species folder"):
        cli.main(["build-models", "nope"])
