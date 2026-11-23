"""Reading and writing glTF binary (.glb) files without Blender.

The reader measures what the checks need (spec §8, §15): triangles, mesh and material names,
the bounding box in the model's own frame, custom attributes and `extras.genes`. It reads
accessor counts and bounds only, so it also works on meshopt-compressed files.

The writer builds small models from code: the example species and test fixtures.
"""

from __future__ import annotations

import json
import math
import struct
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

GLB_MAGIC = 0x46546C67  # "glTF"
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942
TRIANGLES = 4
FLOAT = 5126
UNSIGNED_SHORT = 5123
UNSIGNED_INT = 5125

Vec3 = tuple[float, float, float]
Mat4 = list[float]  # column-major, as glTF


class GlbError(ValueError):
    """The file is not a glTF binary this module can read."""


# ---------------------------------------------------------------- reading


@dataclass
class PrimitiveInfo:
    mesh: str
    material: str | None
    triangles: int
    attributes: list[str]


@dataclass
class GlbInfo:
    """What the checks look at in one model."""

    triangles: int
    meshes: list[str]
    materials: list[str]
    primitives: list[PrimitiveInfo]
    bbox_min: Vec3
    bbox_max: Vec3
    extras: dict[str, Any]
    has_cameras: bool
    has_lights: bool
    extensions_used: list[str]
    bytes: int

    @property
    def height(self) -> float:
        return self.bbox_max[1] - self.bbox_min[1]


def read_json(data: bytes) -> dict[str, Any]:
    """The JSON chunk of a .glb."""
    if len(data) < 20:
        raise GlbError("too short for a glb")
    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != GLB_MAGIC:
        raise GlbError("not a glb (bad magic)")
    if version != 2:
        raise GlbError(f"glTF version {version}, expected 2")
    if length != len(data):
        raise GlbError("length in the header does not match the file")
    chunk_len, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != CHUNK_JSON:
        raise GlbError("first chunk is not JSON")
    doc: dict[str, Any] = json.loads(data[20 : 20 + chunk_len].decode("utf-8"))
    return doc


def _identity() -> Mat4:
    return [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]


def _mul(a: Mat4, b: Mat4) -> Mat4:
    out = [0.0] * 16
    for col in range(4):
        for row in range(4):
            out[col * 4 + row] = sum(a[k * 4 + row] * b[col * 4 + k] for k in range(4))
    return out


def _node_matrix(node: dict[str, Any]) -> Mat4:
    if "matrix" in node:
        return [float(v) for v in node["matrix"]]
    tx, ty, tz = node.get("translation", [0.0, 0.0, 0.0])
    qx, qy, qz, qw = node.get("rotation", [0.0, 0.0, 0.0, 1.0])
    sx, sy, sz = node.get("scale", [1.0, 1.0, 1.0])
    r = [
        1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy + qz * qw), 2 * (qx * qz - qy * qw), 0.0,
        2 * (qx * qy - qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz + qx * qw), 0.0,
        2 * (qx * qz + qy * qw), 2 * (qy * qz - qx * qw), 1 - 2 * (qx * qx + qy * qy), 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]  # fmt: skip
    for i in range(3):
        r[i] *= sx
        r[4 + i] *= sy
        r[8 + i] *= sz
    r[12], r[13], r[14] = tx, ty, tz
    return r


def _apply(m: Mat4, p: Vec3) -> Vec3:
    x, y, z = p
    return (
        m[0] * x + m[4] * y + m[8] * z + m[12],
        m[1] * x + m[5] * y + m[9] * z + m[13],
        m[2] * x + m[6] * y + m[10] * z + m[14],
    )


# Largest value of each integer component type, for normalized accessors (KHR_mesh_quantization).
_NORMALIZED_MAX = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0}


def _dequantize(acc: dict[str, Any], values: list[float]) -> list[float]:
    """Accessor min/max are stored in the component type: a normalized accessor's values are
    integers that stand for -1..1 or 0..1 (glTF 2.0 §3.11, meshopt's quantization)."""
    if acc.get("normalized"):
        top = _NORMALIZED_MAX.get(int(acc.get("componentType", 5126)), 1.0)
        return [max(v / top, -1.0) for v in values]
    return [float(v) for v in values]


def inspect(path: Path) -> GlbInfo:
    """Measure a .glb file (spec §15, models)."""
    data = path.read_bytes()
    doc = read_json(data)
    accessors = doc.get("accessors", [])
    materials = doc.get("materials", [])
    meshes = doc.get("meshes", [])

    prims: list[PrimitiveInfo] = []
    mesh_tris: list[int] = []
    for mesh in meshes:
        total = 0
        for prim in mesh.get("primitives", []):
            if prim.get("mode", TRIANGLES) != TRIANGLES:
                raise GlbError(f"mesh {mesh.get('name')!r}: only triangle primitives are allowed")
            if "indices" in prim:
                count = int(accessors[prim["indices"]]["count"])
            else:
                count = int(accessors[prim["attributes"]["POSITION"]]["count"])
            tris = count // 3
            total += tris
            mat = prim.get("material")
            prims.append(
                PrimitiveInfo(
                    mesh=str(mesh.get("name", "")),
                    material=None if mat is None else str(materials[mat].get("name", "")),
                    triangles=tris,
                    attributes=sorted(prim.get("attributes", {})),
                )
            )
        mesh_tris.append(total)

    lo = [math.inf, math.inf, math.inf]
    hi = [-math.inf, -math.inf, -math.inf]
    triangles = 0
    nodes = doc.get("nodes", [])
    scene_index = doc.get("scene", 0)
    scenes = doc.get("scenes", [])
    roots = scenes[scene_index].get("nodes", []) if scenes else []
    stack: list[tuple[int, Mat4]] = [(n, _identity()) for n in roots]
    while stack:
        index, parent = stack.pop()
        node = nodes[index]
        world = _mul(parent, _node_matrix(node))
        if "mesh" in node:
            triangles += mesh_tris[node["mesh"]]
            for prim in meshes[node["mesh"]].get("primitives", []):
                acc = accessors[prim["attributes"]["POSITION"]]
                if "min" not in acc or "max" not in acc:
                    raise GlbError("POSITION accessors must have min and max")
                amin, amax = _dequantize(acc, acc["min"]), _dequantize(acc, acc["max"])
                for cx in (amin[0], amax[0]):
                    for cy in (amin[1], amax[1]):
                        for cz in (amin[2], amax[2]):
                            p = _apply(world, (cx, cy, cz))
                            for i in range(3):
                                lo[i] = min(lo[i], p[i])
                                hi[i] = max(hi[i], p[i])
        stack.extend((child, world) for child in node.get("children", []))

    if triangles == 0:
        lo = hi = [0.0, 0.0, 0.0]
    extras: dict[str, Any] = {}
    if scenes:
        extras = dict(scenes[scene_index].get("extras", {}))
    used = list(doc.get("extensionsUsed", []))
    return GlbInfo(
        triangles=triangles,
        meshes=[str(m.get("name", "")) for m in meshes],
        materials=[str(m.get("name", "")) for m in materials],
        primitives=prims,
        bbox_min=(lo[0], lo[1], lo[2]),
        bbox_max=(hi[0], hi[1], hi[2]),
        extras=extras,
        has_cameras=bool(doc.get("cameras")),
        has_lights="KHR_lights_punctual" in used,
        extensions_used=used,
        bytes=len(data),
    )


# ---------------------------------------------------------------- writing


@dataclass
class MeshData:
    """One named mesh with one material: flat colour, optional per-vertex extras."""

    name: str
    positions: list[Vec3]
    normals: list[Vec3]
    indices: list[int]
    colour: tuple[float, float, float]  # linear RGB, 0..1
    custom: dict[str, list[float]] = field(default_factory=dict)  # e.g. {"_ORDER": [...]}
    alpha_cutoff: float | None = None


def _pad(data: bytes, fill: bytes) -> bytes:
    return data + fill * ((4 - len(data) % 4) % 4)


def write(path: Path, meshes: Sequence[MeshData], extras: dict[str, Any]) -> None:
    """Write meshes as one scene, each mesh on its own node at the origin. Deterministic."""
    path.write_bytes(build(meshes, extras))


def build(meshes: Sequence[MeshData], extras: dict[str, Any]) -> bytes:
    buffer = bytearray()
    views: list[dict[str, Any]] = []
    accessors: list[dict[str, Any]] = []
    doc_meshes: list[dict[str, Any]] = []
    materials: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []

    def add_view(blob: bytes, target: int) -> int:
        while len(buffer) % 4:
            buffer.append(0)
        views.append(
            {"buffer": 0, "byteOffset": len(buffer), "byteLength": len(blob), "target": target}
        )
        buffer.extend(blob)
        return len(views) - 1

    def add_vec3(values: list[Vec3], with_bounds: bool) -> int:
        blob = b"".join(struct.pack("<fff", *v) for v in values)
        acc: dict[str, Any] = {
            "bufferView": add_view(blob, 34962),
            "componentType": FLOAT,
            "count": len(values),
            "type": "VEC3",
        }
        if with_bounds:
            # Bounds of the float32 values actually stored.
            stored = [struct.unpack("<fff", struct.pack("<fff", *v)) for v in values]
            acc["min"] = [min(v[i] for v in stored) for i in range(3)]
            acc["max"] = [max(v[i] for v in stored) for i in range(3)]
        accessors.append(acc)
        return len(accessors) - 1

    def add_scalar(values: list[float]) -> int:
        blob = struct.pack(f"<{len(values)}f", *values)
        accessors.append(
            {
                "bufferView": add_view(blob, 34962),
                "componentType": FLOAT,
                "count": len(values),
                "type": "SCALAR",
            }
        )
        return len(accessors) - 1

    def add_indices(values: list[int], vertex_count: int) -> int:
        wide = vertex_count > 65535
        blob = struct.pack(f"<{len(values)}{'I' if wide else 'H'}", *values)
        accessors.append(
            {
                "bufferView": add_view(blob, 34963),
                "componentType": UNSIGNED_INT if wide else UNSIGNED_SHORT,
                "count": len(values),
                "type": "SCALAR",
            }
        )
        return len(accessors) - 1

    for mesh in meshes:
        if len(mesh.positions) != len(mesh.normals):
            raise ValueError(f"{mesh.name}: positions and normals differ in length")
        attributes = {
            "POSITION": add_vec3(mesh.positions, with_bounds=True),
            "NORMAL": add_vec3(mesh.normals, with_bounds=False),
        }
        for name in sorted(mesh.custom):
            values = mesh.custom[name]
            if len(values) != len(mesh.positions):
                raise ValueError(f"{mesh.name}: {name} has the wrong length")
            attributes[name] = add_scalar(values)
        material: dict[str, Any] = {
            "name": mesh.name,
            "pbrMetallicRoughness": {
                "baseColorFactor": [*mesh.colour, 1.0],
                "metallicFactor": 0.0,
                "roughnessFactor": 1.0,
            },
        }
        if mesh.alpha_cutoff is not None:
            material["alphaMode"] = "MASK"
            material["alphaCutoff"] = mesh.alpha_cutoff
        materials.append(material)
        doc_meshes.append(
            {
                "name": mesh.name,
                "primitives": [
                    {
                        "attributes": attributes,
                        "indices": add_indices(mesh.indices, len(mesh.positions)),
                        "material": len(materials) - 1,
                        "mode": TRIANGLES,
                    }
                ],
            }
        )
        nodes.append({"name": mesh.name, "mesh": len(doc_meshes) - 1})

    while len(buffer) % 4:
        buffer.append(0)
    doc: dict[str, Any] = {
        "asset": {"version": "2.0", "generator": "genes"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes))), "extras": extras}],
        "nodes": nodes,
        "meshes": doc_meshes,
        "materials": materials,
        "accessors": accessors,
        "bufferViews": views,
        "buffers": [{"byteLength": len(buffer)}],
    }
    json_chunk = _pad(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8"), b" ")
    bin_chunk = bytes(buffer)
    total = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    return b"".join(
        [
            struct.pack("<III", GLB_MAGIC, 2, total),
            struct.pack("<II", len(json_chunk), CHUNK_JSON),
            json_chunk,
            struct.pack("<II", len(bin_chunk), CHUNK_BIN),
            bin_chunk,
        ]
    )
