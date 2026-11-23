# Changelog

## [Unreleased]

- The public catalog for genes.pietri.dev (`docs/reports/CATALOG_SITE.md`): pages written at
  build time with every fact in the HTML, JSON-LD, `sitemap.xml`, `robots.txt`, `llms.txt`
  and a Markdown copy per species; species cards; the species page with the 3D tree, one
  recorded life from pietri.dev's simulator (age slider, seasons, play), day and night sky,
  infographics, a 3D leaf and a map; `genes occurrences` for GBIF sightings per cell;
  `docs/DEPLOY.md`. The review viewer moved to `/review/`. Second pass: a cartoon dashboard
  with glass modules, marcos's painted icons and stage pictures, illustrated charts (height
  to scale, wood dial, trunk logs, rain gauge, thermometer, life stages) and a toy map
  without provinces.
- The species recipe for any agent: `docs/HOW_TO_ADD_A_SPECIES.md` rewritten with marcos's
  rules, sources, the leaf colour calendar and the viewer checks;
  `docs/PLANT_FORM_PARAMETERS.md` written from the schema (`genes form-reference`);
  `genes doctor` checks a computer is ready; `AGENTS.md` holds the rules (`CLAUDE.md` and
  `GEMINI.md` point to it); `docs/NEW_SPECIES_PROMPT.md` starts an agent on a species.
- Phase 2: the plant generator (`plant@1`, Blender headless through `bpy`, meshopt
  through gltf-transform), `genes build-models`, `genes refs candidates|add`,
  `genes contact-sheet`, `docs/HOW_TO_ADD_A_SPECIES.md`, and the first species, algarrobo
  blanco (`neltuma-alba`): sheet 1, 19 reference photos, look 1 and 42 models.
- Phase 1, the base: schemas for sheets (plants, animals reserved), looks, reference
  photos and the catalog; `genes validate`, `genes build`, `genes serve`; the viewer;
  a code-made example tree.

## 2026-11-23

- Phase 0: the specification.
