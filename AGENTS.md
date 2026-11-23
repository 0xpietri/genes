# Rules for AI agents working in this repository

These rules apply to every coding agent (Claude, Gemini, Antigravity, Codex or any other).
`CLAUDE.md` and `GEMINI.md` only point here.

**Adding a species?** Follow `docs/HOW_TO_ADD_A_SPECIES.md` step by step (start with
`uv run genes doctor`). Every form parameter is in `docs/PLANT_FORM_PARAMETERS.md`.

## Source of truth
- This repository is genes (genes.pietri.dev): the only place in the pietri.dev ecosystem where species are defined, their biology facts and their looks.
- The specification is `docs/spec/GENES_SPEC_v0.1.md`. Read it fully before any change.
- Implement **only the phase you were asked for** (spec §17). Each phase ends with tests, a short report in `docs/reports/` (with the one-line commands to try it locally) and a stop.
- If the spec is ambiguous or contradicts itself, stop on that point, explain it, and propose options. Do not silently fill architectural gaps.

## Language
- Code, comments, commit messages, docs and the viewer UI: **English**. Species keep their Spanish common names too.
- The owner (marcos) talks in Spanish (rioplatense); user-facing chat is Spanish.

## Boundaries
- Facts and looks live here; growth, health, death and every individual live in pietri.dev (spec §3). No duplicated code between repositories, however small.
- Stateless: no users, no database, nothing computed per request; published files never change (spec §12).
- Every fact is a sourced range in real units (spec §5.1). A fact without a source is left out, never guessed.
- Merged sheet and look versions are frozen; a change is a new version (spec §4).
- Only reference photos with a shareable licence (CC0, CC BY, CC BY-SA) are stored, with attribution; others are links only (spec §9).
- Models carry shape and flat colour only; pietri.dev paints and lights them (spec §8).
- Never read or write another project's database; talk only over HTTP. Nothing here talks to the agents' office (`0xpietri/agents`) or holds its keys.
- Agents open PRs; they never merge. Merging a species version is marcos's approval. Deploy only when marcos says.

## Engineering
- Python 3.13 (Blender's `bpy` needs it), `uv` with a lockfile, pytest, ruff, mypy. `bpy` only in the `blender` dependency group; nothing outside `tools/blender/` imports it.
- Viewer: plain HTML, CSS and JS, no build step, three.js vendored and pinned. No inline `<script>` or `<style>` blocks (inline `style=""` attributes are allowed).
- Every behaviour change comes with tests. Tests never touch the network; iNaturalist and GBIF answers are recorded fixtures.
- fal.ai only with the price told first; key only in `FAL_KEY`.
- Secrets only in `.env` / environment; commit `.env.example` with placeholders only.
