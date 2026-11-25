# Species page: speed, search engines and a photo viewer

Asked by marcos on 2026-11-25: check how long the algarrobo's page takes to load, check its
SEO and that a language model can read it, and open the real photos in a lightbox without
leaving the page.

## Try it

```
uv sync
uv run genes serve --port 8000
```

- <http://localhost:8000/es/species/neltuma-alba/>: click any reference photo (arrows, swipe,
  Escape).
- `uv run pytest tests/test_site.py`: the site's tests (the new ones are at the end).

## What was measured

A local build served with gzip (like Caddy's `encode`), Chromium throttled to 4 Mbit/s and
150 ms of latency, cache off, the Spanish page. Production should be a little better
(zstd, HTTP/2, Cloudflare near the visitor).

| | before | after |
|---|---|---|
| first text painted | 0.75 s | 0.75 s |
| tree on screen | 5.3 s | **3.3 s** (light model) |
| tree at full detail | 5.3 s | 5.2 s |
| reference photos, once scrolled to | 3.9 MB (19 photos of 1024 px) | **0.8 MB** (19 thumbs) |

Where the bytes went before: three.js (2.1 MB as vendored, 420 KB compressed), the grown
tree's `lod0` model (700 KB, already meshopt-compressed and quantised, so it barely
compresses), the life (127 KB, 26 KB compressed), the HTML (93 KB, 15 KB compressed), the
painted icons (about 250 KB, already lazy). And a chain: the data and the model were only
asked for after three.js had arrived and run.

## What changed

- **Photo thumbs.** `references/thumbs/<id>.webp`: the middle 4:3 crop the strip shows, at
  520 x 390 (sharp on 2x screens), about 40 KB each. `genes refs add` writes one with every
  photo; `genes refs thumbs <id>` writes the missing ones. The build only copies them, so
  it stays byte-identical. The tiles are now really 4:3 (the `height` attribute was
  overriding `aspect-ratio`).
- **Preloading.** The head asks at once for the sheet, the look, the life, the grown tree's
  `lod1` model (`<link rel="preload" as="fetch" crossorigin>`, reused by `fetch()` and
  three's loader, tested: each model is requested once) and every module the 3D imports
  (`modulepreload`), so nothing waits for the file before it.
- **Light model first.** `stage.js` shows `lod1` (80 KB) while `lod0` (700 KB) downloads,
  then swaps it in. The look's models are unchanged: same `lod0` at full detail, a moment
  later. Play preloads the other stages' light models first, then their full ones.
- **Photo viewer** (`site/static/js/lightbox.js`): a native `<dialog>` written at build time
  (so its words are translated like the rest of the page), filled from the photo links.
  It shows the thumb at once and sharpens when the stored photo arrives, with the place,
  author and a link to the original on iNaturalist; arrows, swipe and Escape; focus returns
  to the photo. Without JavaScript each thumb is a plain link to the stored photo.
- **Search engines and models.**
  - The name, summary and stat tiles come first in the HTML (CSS still shows them right of
    the 3D on desktop and below it on phones), so a reader without JavaScript meets the
    species before the simulator's buttons.
  - `<link rel="alternate" type="text/markdown">` to the species' Markdown copy.
  - `sitemap.xml` lists every language of every page with `xhtml:link` hreflang alternates.
  - `og:image:width`, `height`, `type` and `alt`, `twitter:image:alt`,
    `og:locale:alternate`.
  - The reference photos as JSON-LD `ImageObject`s with author, place, date and the page of
    the original (`acquireLicensePage`). The licence URL is left out: refs.json stores
    `cc-by` without the licence version, and a version would be a guess.
  - `llms.txt` links both the English and the Spanish page.

What was already fine: every fact, month and source in the HTML; canonical, description,
hreflang, Open Graph; JSON-LD Taxon and breadcrumb; `robots.txt`, `llms.txt`,
`llms-full.txt`; lazy icons, leaf and map; immutable caching of `/static/site/<hash>/`.

## Decisions to confirm

1. **Minified three.js** (not done). three.js ships no minified ES modules any more; the
   vendored files are 2.4 MB (420 KB compressed). Minified with esbuild (same version, no
   bundling, licence kept) they are 0.9 MB (about 200 KB compressed): about half a second
   less on a 4 Mbit/s phone and less parsing. It would be a change to
   `scripts/vendor_three.py` (needs Node to run once) and the vendored files; the rule
   "three.js vendored and pinned, no build step" still holds. Say yes and it goes in its own
   PR.
2. **The share picture** is the card (640 x 698 WebP). Platforms that crop to 1.91:1 cut its
   top and bottom; a 1200 x 630 JPEG made for sharing would look better on WhatsApp,
   LinkedIn and X.

## Seasonal landscape and ground (same day)

marcos painted with Gemini a landscape of the Sierras Chicas with the Pan de Azúcar and a
top-down ground for each season (prompts in the project files, originals in
`genes-catalog/seasons/`).

- `site/static/art/scene/backdrop-<season>.webp` (2736 x 864, the magenta sky keyed out to
  transparency, the top faded because the paintings reach the top edge; winter's repeated
  strip above a magenta seam was dropped) and `ground-<season>.webp` (1024 px).
- `stage.js`: the landscape is an open ring 150 m away, the painting mirrored four times
  round it at its own proportions, its far valley floor at the horizon (the ground disc
  hides its foreground). The ground disc wears the season's soil, a 12 m tile. Both follow
  the shown month (`seasonOf`); while the life plays they keep the season they had, so they
  do not flicker, and catch up when play stops. Day and night stay in code: the painted
  sky dome as before, and the ring and soil tinted blue-grey at night.
- The old `ground.webp` is gone.

To improve: the paintings have almost no sky, so the mountain tops are cut by the frame
and faded. Extending them upward (Gemini, "extend the canvas upward") would show whole peaks.
