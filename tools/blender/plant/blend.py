"""Blender side of the generator: meshes, materials and the glTF export.

The only module that imports `bpy` (AGENTS.md). Coordinates: the generator works
in glTF's frame (Y up); Blender is Z up, and its exporter turns it back.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import bpy
import numpy as np

from plant.geometry import Part
from plant.model import Model

ALPHA_PARTS = ("foliage",)
DOUBLE_SIDED = ("foliage", "fruit", "flowers")


def srgb_to_linear(hex_colour: str) -> tuple[float, float, float, float]:
    def channel(c: int) -> float:
        v = c / 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    h = hex_colour.lstrip("#")
    return (channel(int(h[0:2], 16)), channel(int(h[2:4], 16)), channel(int(h[4:6], 16)), 1.0)


def reset() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def image(name: str, pixels: np.ndarray) -> Any:
    """A packed Blender image from rows-from-the-top RGBA floats."""
    h, w = pixels.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.flipud(pixels).astype(np.float32).ravel())
    img.pack()
    return img


def material(name: str, colour: str, tex: Any | None, alpha: bool, double: bool) -> Any:
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Metallic"].default_value = 0.0
    rgba = srgb_to_linear(colour)
    if tex is None:
        bsdf.inputs["Base Color"].default_value = rgba
    else:
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = tex
        node.interpolation = "Linear"
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(node.outputs["Color"], mix.inputs["A"])
        mix.inputs["B"].default_value = rgba
        nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
        if alpha:
            cut = nt.nodes.new("ShaderNodeMath")
            cut.operation = "GREATER_THAN"
            cut.inputs[1].default_value = 0.5
            nt.links.new(node.outputs["Alpha"], cut.inputs[0])
            nt.links.new(cut.outputs[0], bsdf.inputs["Alpha"])
    mat.use_backface_culling = not double
    return mat


def mesh_object(part: Part, mat: Any) -> Any:
    verts = [(p[0], -p[2], p[1]) for p in part.positions]
    mesh = bpy.data.meshes.new(part.name)
    mesh.from_pydata(verts, [], part.triangles)
    uv = mesh.uv_layers.new(name="UVMap")
    loop_uvs = []
    for loop in mesh.loops:
        u, v = part.uvs[loop.vertex_index]
        loop_uvs += [u, 1.0 - v]
    uv.data.foreach_set("uv", loop_uvs)
    if part.order is not None:
        attr = mesh.attributes.new("_ORDER", "FLOAT", "POINT")
        attr.data.foreach_set("value", part.order)
    mesh.normals_split_custom_set_from_vertices([(n[0], -n[2], n[1]) for n in part.normals])
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(part.name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def export(model: Model, textures: dict[str, Any], path: Path) -> None:
    """One model to an uncompressed glb (meshopt comes after, in tools/compress)."""
    reset()
    scene = bpy.context.scene
    for name, part in model.parts.items():
        pixels = textures.get(name)
        tex = image(f"{name}_texture", pixels) if pixels is not None else None
        mat = material(name, model.colours[name], tex, name in ALPHA_PARTS, name in DOUBLE_SIDED)
        mesh_object(part, mat)
    scene["genes"] = model.extras
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        export_yup=True,
        export_apply=True,
        export_attributes=True,
        export_extras=True,
        export_cameras=False,
        export_lights=False,
        export_image_format="WEBP",
        export_image_quality=100,  # 100 is lossless WebP: crisp cut-outs, few greys
        export_tangents=False,
        export_skins=False,
        export_animations=False,
        export_morph=False,
    )
