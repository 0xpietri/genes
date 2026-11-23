from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from genes.paths import EXAMPLES_DIR

EXAMPLE = "example-tree"


@pytest.fixture
def examples(tmp_path: Path) -> Path:
    """A writable copy of examples/species (an examples root)."""
    root = tmp_path / "examples"
    shutil.copytree(EXAMPLES_DIR, root)
    return root


@pytest.fixture
def species_root(tmp_path: Path) -> Path:
    """An empty real-species root."""
    root = tmp_path / "species"
    root.mkdir()
    return root


def example_dir(root: Path) -> Path:
    return root / "plants" / EXAMPLE
