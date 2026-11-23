# Phase 1 report: the base

Date: 2026-11-23. Spec: `docs/spec/GENES_SPEC_v0.1.md` §17 phase 1. No Blender yet.

## Try it (on marcos's PC, in the genes folder)

```
uv sync
uv run genes serve --examples
```

Then open <http://127.0.0.1:8810/> and the example tree. Other commands:

```
uv run genes validate --examples
uv run pytest
uv run genes build --examples
```

## What was built

- **Schemas** (`schemas/`): `sheet.v1` (the shared core, the plant block of spec §5.3 and
  the animal block reserved with only `class` and `domestic`), `look.v1`, `refs.v1`,
  `catalog.v1`, and `common.v1` with the shared pieces (sourced range, level, phase,
  tones, ids). Every fact is `{min, typical, max, source}` or a sourced level or phase.
- **Validator** (`genes validate`): schemas; folder, id, version and kind agree; versions
  1..n without gaps; every source id exists; min ≤ typical ≤ max; relations name a known
  species or are marked `planned`; a look's `for_sheet` exists; the adult reference height
  sits inside the sheet's adult height; look references exist; every model the look's
  stages, variants and LODs call for exists and nothing else; per model: triangles and
  size against `budgets.json`, only the parts `bark`, `foliage`, `flowers`, `fruit`,
  `thorns`, `_ORDER` on the phenology parts, no cameras or lights, base at y = 0, origin
  inside the footprint, height within 10 % of its stage, `extras.genes` matching;
  stored photos only with a shareable licence; and versions merged into `main` are
  frozen (compared with git).
- **glTF reader and writer** (`src/genes/glb.py`), pure Python: the reader measures
  what the checks need from accessor counts and bounds, so it will also read
  meshopt-compressed files from phase 2.
- **Catalog** (`genes build`): the static site in `dist/` as spec §12, byte-identical for
  the same files.
- **Viewer** (plain JS, three.js 0.187.0 vendored, the same version as pietri.dev): the
  catalog, and a page per species with the model turning beside a 1.75 m person; stage,
  variant (A/B/C) and detail (close/far); a month slider that shows or hides leaves,
  flowers and fruit clump by clump from the sheet's months; a rough painted preview
  (three flat bands); triangles and size against the budget; recognisable traits, facts
  with their sources, and the reference photos with a button to look from each photo's
  angle.
- **Example species** (`examples/species/plants/example-tree/`): a made-up tree whose
  models are built in code (`genes make-example`), so the viewer and the checks have
  something to load. It is shown only with `--examples`.
- 49 tests (pytest; two load the viewer in Chromium through Playwright and are skipped
  where no browser is installed). ruff and mypy strict pass.

## Own choices, for marcos to confirm

1. **Example species.** Ids starting `example-` live only under `examples/`, with sources
   of kind `example` and status `example`; the validator refuses all three anywhere else.
   The spec did not say how to test without a real species.
2. **Catalog release number** = how many sheet and look versions the catalog holds. It
   only grows, because merged versions are never removed, and needs no counter file.
3. **`params_hash`** = the first 16 hex digits of the SHA-256 of the look's `form` as
   canonical JSON; `extras.genes` sits on the glTF scene (three.js reads it as
   `scene.userData.genes`).
4. **Budgets** are a data file, `budgets.json`, so phase 2 can tune them without code.
   It adds lod1 and impostor numbers the spec left open.
5. **The month preview** in the viewer: leaves at 40 % (deciduous) or 60 % (semi) in the
   leaf-fall months, 0 % or 35 % in the months between leaf fall and leaf-out, 60 % or
   75 % while leafing out. Only a preview; the world uses its own weather.

## Not done (later phases)

The `bpy` generator, compression (meshopt, KTX2) and contact sheets (phase 2);
pietri.dev reading genes (phase 3); grass tufts (phase 4); deploy (phase 5).
