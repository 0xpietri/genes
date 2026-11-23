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

## Second pass: a cartoon dashboard (asked by marcos the same evening)

marcos found the first version plain and asked for a softer, more cartoon look like his
dashboard reference: glass modules, little drawings for each fact, real charts for height, wood
and size, and a smaller map that shows only where the plant is.

- **Look**: Fredoka for titles and Nunito for text (SIL OFL, subset to Latin and vendored in
  `site/static/fonts/`, 28 KB and 38 KB); every module, tile and control is frosted glass
  over a painted backdrop of soft colour blobs.
- **marcos's illustrations** (Gemini, his own sheet): cut out on the white background and
  stored as WebP. Generic icons in `site/static/art/` (pod, flower, bee, goat, rain, frost,
  log, roots, fire, nest, person and more, with `sizes.json`); the algarrobo at each stage in
  `species/plants/neltuma-alba/media/stages/` (also with `sizes.json`), copied to
  `/v1/species/<id>/media/stages/`. Where no painted icon exists, a drawn SVG one stands in
  (`src/genes/site_art.py`). The card picture is his Gemini tree, cut out.
- **Charts** (`site_art.py`, inline SVG at build time): small, usual and tallest adults drawn
  to scale next to the painted person; a wood density dial from 0 to 1,200 kg/m³ with water's
  1,000 marked; trunk diameters as nested cut logs; a rain gauge and a thermometer; drought
  and shade as three-dot meters; the life's height as a filled area under KPIs (years lived,
  tallest, cause of death, when it is gone) and a strip of the seven stage pictures with
  their years, which jump the 3D tree to that stage.
- **Map**: no province lines. A toy map from Natural Earth countries, rivers and lakes
  (`scripts/make_basemap.py` now keeps only where provinces are, for placing photos), sea,
  white shore and a little algarrobo on each place with sightings, and a house on Unquillo;
  4:3 and at most 420 px tall. With `occurrences.json` each tree is a half-degree area with
  GBIF sightings, sized by count; until then, a province with reference photos.

Still to come: the painted sky, ground and map pieces (second Gemini sheet), which replace
the code-drawn sky dome and ground texture and the drawn map trees.

## Third pass: two languages and painted sky, soil and map

marcos asked for a language selector with no mixing, for the page not to be centred on one
town, and for the leaf habit, form and conservation tags to become icons with a hover.

- **English and Spanish, one per page.** English at `/` and `/species/<id>/`, Spanish at
  `/es/` and `/es/species/<id>/`, linked with `hreflang` and an EN/ES switch in the top bar.
  Page code is written in English and every visible text passes through
  `genes.site_i18n.T`: the site's own words are in `UI_ES`, a species' sheet and look texts
  in `species/<kind>/<id>/i18n/es.json`. A text with no Spanish is collected in `MISSING`
  and a test fails. Numbers use a decimal comma on Spanish pages. The scripts' few words
  (simulator readout, day/night, map tips) come from `site/static/js/i18n.js`, which reads
  `<html lang>`. Markdown copies and `llms.txt` stay in English.
- **Not about one town.** No "status in the Sierras Chicas" badge, no house on the map, the
  life text says "the real weather of central Argentina".
- **Tags as icons.** Leaf habit, form and conservation are three icons; the words show on
  hover or keyboard focus and are kept for screen readers.
- **marcos's second sheet** (cut out here, originals in the project files): the day and night
  skies wrap round the 3D dome (four mirrored copies so seams match; gradient sky until they
  load), the painted soil tiles the ground disc (5 m a tile, mirrored), and the map uses his
  six little algarrobos as pins and his mountains on real peaks of the Andes and the Sierras
  (decoration only). Files: `site/static/art/scene/` and `site/static/art/map/`, each with
  `sizes.json`. The house, hill and lagoon were not used.

Try it: `uv run genes serve --port 8000`, then open http://localhost:8000/es/species/neltuma-alba/.

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
6. **The specimen map** shows the reference photos' provinces until GBIF is fetched. `genes occurrences <id>`
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
