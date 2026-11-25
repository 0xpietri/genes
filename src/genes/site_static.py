"""The site's own CSS, JS, fonts and art, published under a folder named by their content.

A page links `/static/site/<version>/site.css`, where `<version>` is a hash of every file
in `site/static/`. Any change to any of them gives a new folder, so a browser or Cloudflare
can never mix a new page with an old script or stylesheet, and the files can be cached for
a year. Only the HTML pages must be fetched fresh (Caddy sends them with `no-cache`).
"""

from __future__ import annotations

import hashlib
from functools import cache
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parents[2] / "site" / "static"


@cache
def version() -> str:
    """Ten hex characters that change whenever any static file changes."""
    h = hashlib.sha256()
    for p in sorted(STATIC_DIR.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(STATIC_DIR).as_posix().encode())
            h.update(b"\0")
            h.update(p.read_bytes())
    return h.hexdigest()[:10]


def url(path: str = "") -> str:
    """The public URL of a static file, e.g. url("js/species.js")."""
    base = f"/static/site/{version()}"
    return f"{base}/{path.lstrip('/')}" if path else base
