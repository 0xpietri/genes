from __future__ import annotations

import threading
import urllib.request
from collections.abc import Iterator
from email.message import Message
from pathlib import Path

import pytest

from genes import catalog, serve


@pytest.fixture
def server(tmp_path: Path, examples: Path) -> Iterator[str]:
    out = tmp_path / "dist"
    catalog.build([examples], out)
    srv = serve.make_server(out, port=0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _get(url: str) -> tuple[int, Message, bytes]:
    with urllib.request.urlopen(url) as res:
        return res.status, res.headers, res.read()


def test_serves_the_site_with_the_csp(server: str) -> None:
    status, headers, body = _get(f"{server}/review/species/example-tree/")
    assert status == 200 and b'src="/static/viewer.js"' in body
    status, headers, body = _get(f"{server}/species/example-tree/")
    assert status == 200 and b'src="/static/site/js/species.js"' in body
    assert "script-src 'self'" in headers["Content-Security-Policy"]
    status, headers, _ = _get(f"{server}/v1/species/example-tree/looks/1/adult-a.lod0.glb")
    assert headers["Content-Type"] == "model/gltf-binary"
    status, headers, _ = _get(f"{server}/static/viewer.js")
    assert headers["Content-Type"].startswith("text/javascript")
    status, headers, _ = _get(f"{server}/v1/catalog.json")
    assert headers["Content-Type"] == "application/json"
