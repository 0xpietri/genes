"""Vendor three.js into viewer/static/vendor/three/ (run by hand when the pin changes).

Downloads the pinned npm tarball, checks its SHA-256, copies the few files the viewer uses and
rewrites their bare `three` imports into relative paths, so the browser needs no import map
(an import map would be an inline script, which the CSP forbids).

    uv run python scripts/vendor_three.py
"""

from __future__ import annotations

import hashlib
import io
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

VERSION = "0.187.0"  # the same three.js as pietri.dev
SHA256 = "ff540832ded0cfe919764d24a3d88f3e2a05f23303f876423e4f893841e90728"
URL = f"https://registry.npmjs.org/three/-/three-{VERSION}.tgz"

# tarball path -> vendored path (relative to the vendor folder)
FILES = {
    "package/LICENSE": "LICENSE",
    "package/build/three.core.js": "three.core.js",
    "package/build/three.module.js": "three.module.js",
    "package/examples/jsm/loaders/GLTFLoader.js": "addons/loaders/GLTFLoader.js",
    "package/examples/jsm/controls/OrbitControls.js": "addons/controls/OrbitControls.js",
    "package/examples/jsm/utils/BufferGeometryUtils.js": "addons/utils/BufferGeometryUtils.js",
    "package/examples/jsm/utils/SkeletonUtils.js": "addons/utils/SkeletonUtils.js",
    "package/examples/jsm/libs/meshopt_decoder.module.js": "addons/libs/meshopt_decoder.module.js",
}

OUT = Path(__file__).resolve().parents[1] / "viewer" / "static" / "vendor" / "three"


def main() -> int:
    data = urllib.request.urlopen(URL, timeout=60).read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        print(f"sha256 mismatch: {digest}", file=sys.stderr)
        return 1
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for src, dst in FILES.items():
            member = tar.extractfile(src)
            if member is None:
                print(f"missing in tarball: {src}", file=sys.stderr)
                return 1
            text = member.read().decode("utf-8")
            target = OUT / dst
            depth = len(Path(dst).parts) - 1
            to_root = "../" * depth if depth else "./"
            text = re.sub(r"from 'three'", f"from '{to_root}three.module.js'", text)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
    (OUT / "VERSION").write_text(f"three {VERSION}\nsha256 {SHA256}\n", encoding="utf-8")
    print(f"three {VERSION} vendored into {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
