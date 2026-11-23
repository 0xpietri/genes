# The public catalog at genes.pietri.dev

Asked by marcos on 2026-11-23: a public site, no login, with a card per species and a page
per species: the tree in 3D to turn and zoom, its facts as infographics, a map of where it
grows, the leaf in 3D, the tree's life replayed with an age slider, seasons and play, and
a day and a night sky. Fast, good for search engines and language models, without cutting
down the 3D. Only the algarrobo blanco exists today.

## Try it

```
uv sync
uv run genes serve
```

- <http://127.0.0.1:8810/>: the catalog.
- <http://127.0.0.1:8810/species/neltuma-alba/>: the species page.
- <http://127.0.0.1:8810/review/species/neltuma-alba/>: the review viewer (moved, see below).
- `uv run pytest tests/test_site.py`: the site's tests.

## What was built

- **`genes build` now writes the public pages** (`src/genes/site.py`): every page is plain
  HTML with every fact, month and source already in it, so it reads without JavaScript.
  Each species page also has `index.md` (the same content as Markdown), and the site has
  `sitemap.xml`, `robots.txt`, `llms.txt` and `llms-full.txt`. Pages carry a canonical URL,
  a description, Open Graph tags and JSON-LD (`Taxon` with GBIF and iNaturalist links, and a
  breadcrumb). The build stays byte-identical for the same repository (tested).
- **The catalog** (`/`): a card per species with its cut-out picture on a green glass card;
  on hover the picture lifts, grows and the card leans towards the pointer.
- **The species page** (`/species/<id>/`):
  - The look's own models in 3D (`stage.js`), painted with toon bands and the look's palette,
    clumps revealed by `_order` and leaf tones by month (the same `phenology.js` and
    `paint.js` the review viewer uses, not copies). Drag to turn, wheel or pinch to zoom.
  - **Its life**: an age slider over one recorded life, play at 1×, 4× or 16× (years per
    second), season buttons that stay in the same year, and the stage strip. The model
    follows genes's stages (spec §6.2): seedling, sapling, young (under 60 % of its own
    height), adult, old (from 70 % of its own lifespan), dead standing, then the fallen trunk
    sinking as it rots. Height and crown come from the recorded life; flowers and pods only
    once it is old enough to bear them; a stressed or dying tree shows fewer leaves. The
    camera follows the tree as it grows and keeps the visitor's own zoom. A height-over-age
    chart under it moves with the slider and can be clicked to jump.
  - **Day and night** (`sky.js`): a gradient sky with a sun and drifting clouds, or a moon
    and twinkling stars, all drawn in code (no downloads). It starts by the visitor's clock
    and remembers the choice.
  - **Infographics**, drawn at build time as inline SVG: the year wheel (leaf tones, flowers,
    pods, leaf fall by month, with a needle on the shown month), height and crown against a
    1.75 m person, rainfall and frost ranges, stat tiles, what it gives (with months).
  - **The leaf in 3D** (`leaf.js`): a bipinnate leaf moving in the wind, to turn and zoom.
    It is an illustration of the form from the sheet's `leaf_type` and the look's colours,
    not a measured model (the sheet has no sourced leaflet counts yet).
  - **The map** (`map.js`): South America and the provinces from Natural Earth (public
    domain, `scripts/make_basemap.py`, 28 KB compressed), drawn as SVG, drag and zoom. It
    shows where the 19 reference photos were taken, by province, and Unquillo. No map tiles
    or outside services.
  - Technical details: the facts table with notes and sources, identifiers, versions and
    links to the JSON.
- **Loading**: the HTML (51 KB, 13 KB compressed) shows the text at once; three.js is
  preloaded in parallel; the leaf and the map load only when scrolled near; the other
  stages' models load while the browser is idle, so play never waits. The catalog page does
  not load three.js at all. Nothing of the 3D was reduced: `lod0` models, every stage.

## Decisions to confirm

1. **The life is pietri.dev's, recorded into genes.** Growth, health and death belong to
   pietri.dev (spec §3), so the life is computed there, once, by the world's own simulator
   (`npm run world -- lifecycle`, pietri.dev PR on branch `claude/project-thread-nb2npl`),
   and its output is stored here as `species/plants/neltuma-alba/lifecycle/1.json` with
   the commit and command that made it. genes only replays it. It uses
   `placeholder:algarrobo@1` until phase 3 moves the facts to the genes sheet; then it is
   recorded again. Alternative: pietri.dev publishes the file and genes's build downloads
   it, which breaks "tests never touch the network".
2. **The review viewer moved to `/review/`** (`/review/species/<id>/`), so the public pages
   take `/` and `/species/<id>/` as spec §12 lists them. `robots.txt` keeps search engines
   out of `/review/`. Docs updated.
3. **JSON-LD blocks** are `<script type="application/ld+json">`: data, not code, so the CSP
   (`script-src 'self'`) does not apply to them, but they are inline `<script>` tags.
   The no-inline test allows only that type.
4. **The UI is English**, as AGENTS.md says for the viewer; Spanish common names and the
   Spanish summary lead the page. A Spanish version of the UI is a small change if wanted.
5. **Card pictures** (`species/<kind>/<id>/media/card.webp`) are not versioned, like the
   reference photos. Today's is a placeholder: the adult model rendered by `render.html`
   and cut out. marcos makes the real one with Gemini (prompt in the thread).
6. **The specimen map** shows only the reference photos' provinces. `genes occurrences <id>`
   (new) downloads GBIF sightings and stores only counts per half-degree cell; the map
   draws them when the file exists. This cloud machine cannot reach GBIF, so it has not
   been run: marcos can run it at home (`uv run genes occurrences neltuma-alba`).

## Next phase, asked by marcos (not built)

An admin login, for marcos only, with a panel to move every look parameter of a species
within the ranges the species allows (height, branch density, crown variation and the
rest), preview every stage and play the life, and choose the specimen the public page
shows, without changing the generator's logic or what the species is. When a species
changes, its models and life are regenerated ahead of time, so visitors only download
static files. `site/static/js/account.js` holds the place for the login (accounts at
id.pietri.dev; the pages stay static and shared; an admin's change becomes files in a PR).

## Deploy

`docs/DEPLOY.md`: a Cloudflare record, `genes build` plus `rsync` to factory, and one
Caddy file serving `dist/` (no container).
