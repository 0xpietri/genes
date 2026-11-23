"""Where things live in the repository."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO_ROOT / "schemas"
VIEWER_DIR = REPO_ROOT / "viewer"
BUDGETS_FILE = REPO_ROOT / "budgets.json"
SPECIES_DIR = REPO_ROOT / "species"
EXAMPLES_DIR = REPO_ROOT / "examples" / "species"
