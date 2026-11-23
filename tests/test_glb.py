from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from genes import glb


def _cube(name: str = "bark", lift: float = 0.0) -> glb.MeshData:
    pos = [(x, y + lift, z) for x in (-0.5, 0.5) for y in (0.0, 1.0) for z in (-0.5, 0.5)]
    normals = [(0.0, 1.0, 0.0)] * 8
    idx = [
        0,
        1,
        3,
        0,
        3,
        2,
        4,
        6,
        7,
        4,
        7,
        5,
        0,
        4,
        5,
        0,
        5,
        1,
        2,
        3,
        7,
        2,
        7,
        6,
        0,
        2,
        6,
        0,
        6,
        4,
        1,
        5,
        7,
        1,
        7,
        3,
    ]
    return glb.MeshData(name, pos, normals, idx, (0.5, 0.4, 0.3), {"_ORDER": [0.1] * 8})


def test_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "m.glb"
    glb.write(path, [_cube()], {"genes": {"id": "x"}})
    info = glb.inspect(path)
    assert info.triangles == 12
    assert info.meshes == ["bark"] and info.materials == ["bark"]
    assert info.bbox_min == (-0.5, 0.0, -0.5) and info.bbox_max == (0.5, 1.0, 0.5)
    assert info.height == 1.0
    assert info.extras == {"genes": {"id": "x"}}
    assert "_ORDER" in info.primitives[0].attributes
    assert not info.has_cameras and not info.has_lights
    assert info.bytes == path.stat().st_size


def test_build_is_deterministic() -> None:
    assert glb.build([_cube()], {"a": 1}) == glb.build([_cube()], {"a": 1})


def _with_doc(data: bytes, change: dict[str, object]) -> bytes:
    """Rewrite a glb's JSON chunk (for node transforms the writer never makes)."""
    doc = glb.read_json(data)
    doc.update(change)
    json_len = struct.unpack_from("<I", data, 12)[0]
    bin_part = data[20 + json_len :]
    chunk = json.dumps(doc).encode()
    chunk += b" " * ((4 - len(chunk) % 4) % 4)
    total = 12 + 8 + len(chunk) + len(bin_part)
    return (
        struct.pack("<III", glb.GLB_MAGIC, 2, total)
        + struct.pack("<II", len(chunk), glb.CHUNK_JSON)
        + chunk
        + bin_part
    )


def test_bbox_follows_node_transforms(tmp_path: Path) -> None:
    data = glb.build([_cube()], {})
    path = tmp_path / "t.glb"
    path.write_bytes(
        _with_doc(data, {"nodes": [{"mesh": 0, "translation": [2, 0.5, 0], "scale": [1, 3, 1]}]})
    )
    info = glb.inspect(path)
    assert info.bbox_min == pytest.approx((1.5, 0.5, -0.5))
    assert info.bbox_max == pytest.approx((2.5, 3.5, 0.5))


def test_lights_and_cameras_are_seen(tmp_path: Path) -> None:
    data = glb.build([_cube()], {})
    path = tmp_path / "l.glb"
    path.write_bytes(
        _with_doc(
            data,
            {
                "cameras": [{"type": "perspective", "perspective": {"yfov": 1, "znear": 0.1}}],
                "extensionsUsed": ["KHR_lights_punctual"],
            },
        )
    )
    info = glb.inspect(path)
    assert info.has_cameras and info.has_lights


def test_not_a_glb(tmp_path: Path) -> None:
    path = tmp_path / "x.glb"
    path.write_bytes(b"hello world, this is not a model at all")
    with pytest.raises(glb.GlbError):
        glb.inspect(path)
