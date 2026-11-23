"""Canonical JSON and hashes, so the same repository state gives byte-identical output."""

import hashlib
import json
from pathlib import Path
from typing import Any


def dumps(value: Any) -> str:
    """Sorted keys, two-space indent, UTF-8 kept, one trailing newline."""
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def load(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def params_hash(form: Any) -> str:
    """The hash every model carries of the look's form parameters (spec §8): the first 16 hex
    digits of the SHA-256 of the canonical JSON of `form`."""
    canonical = json.dumps(form, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(canonical.encode("utf-8"))[:16]
