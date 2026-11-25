# Prompt to start an agent on a new species

marcos pastes this into the agent (Antigravity, Gemini, Claude or any other) opened in
`/mnt/marcos/Projects/genes`, after replacing the two names in angle brackets.

---

Add a new plant species to this repository: **<scientific name>** (<Spanish common name>).

1. Read `AGENTS.md`, then `docs/HOW_TO_ADD_A_SPECIES.md` completely, then
   `docs/PLANT_FORM_PARAMETERS.md` and the algarrobo's files in
   `species/plants/neltuma-alba/` (the worked example). Read the review rounds in
   `docs/reports/GENES_PHASE2.md` to learn what marcos rejected.
2. Run `uv run genes doctor` and fix whatever it reports before anything else.
3. Follow the recipe in order: branch `species/<id>`, sources and facts, reference photos,
   sheet with its leaf colour calendar, look, models, contact sheet, viewer checks,
   Spanish texts (`i18n/es.json`), the public page in English and Spanish,
   `uv run genes validate` and `uv run pytest`.
4. Never guess a fact: leave out what you cannot source. Never change
   `tools/blender/plant/`, the schemas, the validator or the tests (the one exception: a
   missing site word in `UI_ES`, recipe section 4.2). If the species cannot
   be drawn with the parameters, stop and explain why.
5. Work alone until the species is finished and passes every check of the recipe's
   "definition of done". Then write to me in Spanish (rioplatense, plain words) as the
   recipe's section 8 says, with the exact commands to see it in the viewer.
