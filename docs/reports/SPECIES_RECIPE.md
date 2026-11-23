# Report: the species recipe for other agents

Asked by marcos on 2026-11-23, after phase 2: everything another model needs to add a
species alone on his computer, with what the algarrobo taught us, and how he sees it.

## What changed

- `docs/HOW_TO_ADD_A_SPECIES.md`, rewritten:
  - the definition of done;
  - marcos's rules from the seven algarrobo rounds (no leaf without wood, leaves on top,
    no bare limbs, even on every side, variants differ only in crookedness, airy but
    not holed, shade from above, twiglets, real facts only, few rounds);
  - where the facts come from (the sources the algarrobo used, the iNaturalist
    histograms for flowers, fruit and leaves);
  - the sheet fields the viewer shows, and the leaf colour calendar;
  - the form part by part: crown, trunk, tortuosity, branches, leaves, twiglets, flowers,
    fruit, thorns, old and dead trees, single stages;
  - the build notes, the contact sheet, and the viewer checks;
  - the hand-over to marcos in Spanish, with the commands to see it.
- `docs/PLANT_FORM_PARAMETERS.md`: every form parameter with its type, default and
  description, written from `schemas/plant-form.v1.json` by `uv run genes form-reference`.
  A test fails if it drifts from the schema.
- `uv run genes doctor`: checks Python 3.13, Blender's `bpy`, Node, the model compressor,
  Chromium and git, without the network, and prints the fix for each missing piece.
- `AGENTS.md` now holds the rules for every agent; `CLAUDE.md` and `GEMINI.md` point to
  it.
- `docs/NEW_SPECIES_PROMPT.md`: the prompt marcos pastes into the agent.

## marcos's computer (checked 2026-11-23)

`/mnt/marcos/Projects/genes` has the algarrobo (round 7, branch `fase2`) and a Python 3.13
environment that can serve the viewer. Two things are missing for building models, each
installed once: `uv sync --group blender` (Blender's `bpy`) and
`npm ci --prefix tools/compress` (the model compressor). `uv run genes doctor` lists them.

## Try it

```
uv run genes doctor
uv run genes form-reference
uv run genes serve
```
