"""`genes serve`: the built site on 127.0.0.1, for trying species on marcos's PC (spec §14).

Plain standard-library HTTP. Production is Caddy serving the same dist/ (phase 5).
"""

from __future__ import annotations

import functools
import http.server
from pathlib import Path
from typing import Any

# Same rule as origen and micelio: scripts and styles only from files (inline style=""
# attributes allowed); 'wasm-unsafe-eval' for the meshopt decoder.
CSP = (
    "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; "
    "style-src-attr 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' data: blob:; "
    "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
)


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {  # noqa: RUF012 - the base class declares it as an instance dict
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".json": "application/json",
        ".glb": "model/gltf-binary",
        ".wasm": "application/wasm",
    }

    def end_headers(self) -> None:
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        pass  # quiet: marcos only needs the URL


def make_server(
    root: Path, host: str = "127.0.0.1", port: int = 8810
) -> http.server.ThreadingHTTPServer:
    handler = functools.partial(Handler, directory=str(root))
    return http.server.ThreadingHTTPServer((host, port), handler)
