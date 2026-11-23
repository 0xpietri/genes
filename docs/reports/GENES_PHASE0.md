# Phase 0 report: the specification

Date: 2026-11-23.

## What was done

- `docs/spec/GENES_SPEC_v0.1.md`: what genes owns and what stays in pietri.dev (facts
  versus simulator calibration), the sheet format for plants with the animal block
  reserved, the look (form parameters for a procedural generator, stages, variants,
  phenology inside one model, palette), how a look is made to resemble the real species,
  the model contract and budgets, reference photos and licences, layout, stack, the
  published catalog, how pietri.dev consumes it, the review flow on marcos's PC, tests and
  phases. Worked example: algarrobo blanco (`neltuma-alba`).
- `README.md`, `CLAUDE.md`, `LICENSE` (MIT).

## Decided

- Name genes, repository public (marcos, 2026-11-22 and 2026-11-23).

## Open for marcos (spec §16)

1. Facts here, simulator calibration in pietri.dev.
2. ~~Public repository~~ answered: public.
3. Models committed in git.
4. Python 3.13 because of `bpy`.
5. Which algarrobo first (blanco proposed).
6. Algarrobo first, Unquillo's grasses right after, both before play.

## Checked while writing

- iNaturalist taxon 1493104 is *Neltuma alba*; GBIF's backbone (5358528) still accepts
  *Prosopis alba*. Hence stable slug ids and synonyms (spec §4.1).
- `bpy` 5.3.0 on PyPI is built for Python 3.13 only (Linux x86-64, macOS arm64, Windows).

## Next

Phase 1 (base: schemas, validator, catalog builder, viewer with a test model; no
Blender), only when marcos asks.
