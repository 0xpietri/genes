# Phase 2 report: the plant generator and algarrobo blanco

Date: 2026-11-23. Spec: `docs/spec/GENES_SPEC_v0.1.md` §17 phase 2.

## Try it (on marcos's PC, in the genes folder)

The models are already built and committed, so looking at them needs nothing new:

```
uv sync
uv run genes serve
```

Then open <http://127.0.0.1:8810/species/neltuma-alba>. To rebuild the models and the
contact sheet yourself (one time setup first, then the two commands):

```
uv sync --group blender
npm ci --prefix tools/compress
uv run playwright install chromium
uv run genes build-models neltuma-alba
uv run genes contact-sheet neltuma-alba
```

The sheet is `species/plants/neltuma-alba/looks/1/sheet.png`. Checks:

```
uv run genes validate
uv run pytest
```

## What was built

- **The plant generator** (`tools/blender/plant/`, generator `plant@1`). Everything but
  the export is plain Python, so it is tested without Blender:
  - `form.py` reads a look's `form`, fills the defaults from
    `schemas/plant-form.v1.json`, applies the stage's changes, and draws each variant's
    traits (hashed on id, look and variant, so variant b leans the same way as a sapling
    and as an old tree).
  - `envelope.py` is the crown's shape (umbrella, globose, conical, columnar, weeping,
    irregular) with width, base, widest point, flat top and lobes.
  - `skeleton.py` grows a Weber–Penn style tree: a bole, 1 to 4 leaders forked at a
    height, up to three branching levels with angle, curve, droop, wander and roll, pruned
    to the envelope.
  - `geometry.py` and `model.py` turn it into parts: bark tubes (flare, gnarl, tiled UVs),
    foliage as clumps of crossed alpha cards whose normals come from the crown's
    ellipsoid (soft light, big masses), flower spikes or balls, pods (straight, curved,
    coiled) or round fruit, paired thorns. Old trees lose limbs and lean; dead ones lose
    twigs and their top; fallen ones lie on the ground. Every model is fitted to its
    triangle budget (thinnest branches go first and their clumps stay) and scaled to its
    stage's height. `_ORDER` on foliage, flowers and fruit says which go first.
  - `textures.py` paints the foliage atlas (2 × 2 clump variants, 1024 px, feathery
    bipinnate leaves for the algarrobo; pinnate, broad, needle and scale too) and the bark
    in code. Grey only; the palette colours them.
  - `blend.py` (the only `bpy` importer) and `main.py`: meshes and materials in Blender,
    glTF export, then meshopt compression in `tools/compress`.
- **`genes build-models <id>`** runs it on a look (`--stage`, `--variant`, `--lod` to
  narrow). Same look, same files, byte for byte.
- **`genes refs candidates` / `genes refs add`**: shareable iNaturalist photos to choose
  from, with contact grids and the flower and fruit month histograms; adding one stores it
  at 1280 px with its author, licence and link.
- **`genes contact-sheet <id>`**: renders the models with the viewer's own three.js in
  headless Chromium (`viewer/render.html`), lays the best adult silhouette over each
  whole-tree photo and scores the overlap; then the adults in summer, winter and in
  flower, close-ups, and every stage at one scale beside a 1.75 m person.
- **Validator**: a `plant@1` look's form is checked against
  `schemas/plant-form.v1.json`; a photo's `tree_box` must be ordered and stored.
- **Algarrobo blanco** (`species/plants/neltuma-alba/`): sheet 1 with eight sources,
  19 reference photos (CC0, CC BY, CC BY-SA), look 1, 42 models (7 stages, 3 variants,
  2 variants for dead and fallen, lod0 and lod1) and the contact sheet.
- **`docs/HOW_TO_ADD_A_SPECIES.md`**: the recipe for the next species, written to be
  followed alone (by an agent such as Antigravity).
- Tests: 81 (generator contract for all 42 models, defaults-only form, determinism,
  textures, Blender export when `bpy` is there, refs on recorded iNaturalist answers,
  contact-sheet maths, validator, CLI). `mypy --strict` now covers `tools/blender` too.

## The numbers

| | |
| --- | --- |
| Silhouette overlap with the 5 whole-tree photos | 0.63, 0.70, 0.72, 0.68, 0.71 (mean 0.69; 1.0 is perfect) |
| adult-a lod0 / lod1 | 11,040 / 1,333 triangles (budgets 12,000 / 1,500); 464 KB / 78 KB |
| Largest model | 464 KB (budget 500 KB) |
| The whole look, 42 models | 5.64 MB (budget 6 MB) |
| Build time, 42 models | about 30 s in the cloud |

## Choices I made (please confirm or change)

1. **Compression with gltf-transform (Node), not Blender.** The `bpy` package from PyPI
   ships without its meshopt and Draco libraries, so Blender cannot compress. A tiny
   Node tool, `tools/compress` (gltf-transform 4.5.1 and meshoptimizer, pinned with a
   lockfile), runs dedup and meshopt with quantization after the export. It is a build
   tool only, nothing is served from it.
2. **Textures are lossless WebP, not KTX2** (spec §8 says KTX2). Blender's KTX2 export
   fails silently in `bpy` 5.3. three.js reads WebP natively, the foliage atlas is only
   four greys plus a cut-out (110 KB at lod0, 25 KB at half size for lod1), and the bark is
   9 KB. KTX2 can come later through gltf-transform if pietri.dev's GPU memory asks for it.
3. **Textures made in code, not with fal.ai.** Free, deterministic and good enough to
   start; fal.ai stays possible later with the price told first.
4. **`tree_box` in refs.json** (where the tree is in a whole-tree photo) and the overlap
   score: it gives the agent a number to tune against, so it can iterate without anyone
   looking. 0.6 or more is the bar in the recipe.
5. **`show_scale` for flowers and fruit** (1 = real size): painted exaggeration, so a
   recognisable trait such as the pods still reads from a few metres. The algarrobo uses
   1.6 for flowers and 1.4 for pods.
6. **Adult reference height 7.5 m**, inside the sheet's 5–18 m but below its typical
   10 m: the photographed open-grown trees are about that tall and wider than tall, and
   `scale_range` 0.75–1.3 gives 5.6 to 9.8 m in the world.
7. **Reference links point to the photo's own iNaturalist page**, not the observation's,
   because one observation can give two photos (trunk and pods).
8. **No impostor LOD yet**: spec §7.2 leaves it to phase 3, measured in pietri.dev.
9. The committed `sheet.png` is two thirds of its size in 256 colours (about 600 KB).

## Known limits

- Branches are separate tubes, not one welded skinned mesh (spec §7.2 says "one skinned
  mesh"). Nothing is rigged yet, so nothing needs it; it matters only if trees ever sway
  with bones.
- Flowers and pods are hard to see from the whole-tree views even with `show_scale`;
  the close-ups show them.
- Semi-deciduous winter thins the crown only a little (the viewer reveals 60 % of the
  clumps in leaf-fall months, from the sheet's phenology), which matches "never fully
  bare" in the sources but reads close to summer from far away.
- The byte budget is tight: 12,000 triangles weigh about 350 KB even compressed. A
  species with more variants would need a bigger look budget or fewer triangles.
- The crown width's minimum and typical values were read from the reference photos (the
  sources give only a 10 m maximum); the sheet's note says so.

## Next

Your review round on the viewer (what feels off, in your words), then a PR. After that,
the second species (espinillo or chañar) given to Antigravity with the recipe, as a test
of it.
