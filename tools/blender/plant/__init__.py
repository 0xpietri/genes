"""The plant generator, plant@1 (spec §7.2).

It grows a tree from a look's form parameters: trunks and branches stepped
Weber–Penn style and pruned to a crown envelope, a bark mesh, foliage as
painted clumps with crown-proxy normals, flowers, fruit and thorns, for every
stage, variant and LOD.

Everything except `blend.py` is plain Python and is tested without Blender;
`blend.py` turns the result into Blender meshes and exports the glb. A new
species is data only: a look.json whose `form` follows
`schemas/plant-form.v1.json`. Nothing in here names a species.
"""

GENERATOR = "plant@1"
