# How to add a species (plants)

The full recipe for whoever adds the next species: a person, or an agent working alone on
marcos's computer (Antigravity, Gemini, Claude or any other). Follow it in order and do
not skip the checks. A new plant is **data only**:

- a **sheet** of sourced facts;
- **reference photos** with a shareable licence;
- a **look**: the recognisable traits, a palette and form parameters for the generator.

You never touch the generator's code (`tools/blender/plant/`). If a species truly cannot
be drawn with the parameters, stop and explain it in your hand-over; do not change the
generator in a species PR.

The worked example is **algarrobo blanco**: `species/plants/neltuma-alba/`. It went
through seven review rounds with marcos; everything he asked for is now a rule of the
generator or a step below. Copy its files, then change them.

Read these as well:

- `docs/spec/GENES_SPEC_v0.1.md`, sections 5 to 9 (sheet, look, models, photos);
- `AGENTS.md` (the repository's rules);
- `docs/PLANT_FORM_PARAMETERS.md` (every form parameter, its default and what it does);
- `docs/reports/GENES_PHASE2.md`, "Review round 1" to "Review round 7" (what marcos
  rejected and why).

## What you deliver (definition of done)

Every item must be true before you hand over:

1. `species/plants/<id>/sheets/1.json`: every fact has a source; facts without one are
   left out. It includes the leaf colour calendar (`leaf_tones`) and the phenology months.
2. `species/plants/<id>/references/`: 10 to 20 photos with author, licence and link in
   `refs.json`, including 3 to 5 whole trees seen from the side, each with a tight box.
3. `species/plants/<id>/looks/1/look.json`: `recognisable` traits, stages, palette and
   form.
4. All models built (`build-models`), and a contact sheet (`looks/1/sheet.png`) with its
   scores.
5. `species/plants/<id>/i18n/es.json`: the Spanish for every English text of the sheet and
   the look (section 4.2), so the Spanish page has no English in it.
6. `uv run genes validate` prints `ok` and `uv run pytest` passes.
7. You looked at it in the viewer yourself: every stage, variant, season and both
   detail levels (Close and Far), from the side, from above and from below, and its public
   page in both languages (section 7.1).
8. A hand-over message for marcos (section 8), in Spanish, with the exact commands to see
   it on his computer.

## Rules marcos set (not negotiable)

These come from the algarrobo's review rounds. The generator and the tests enforce most
of them. Never try to work around them.

- **No leaf without wood.** Every clump of leaves hangs from a drawn branch; nothing
  floats in the air. The generator guarantees it, and a test checks every card. If the
  build notes say that many clumps "moved onto their wood", the crown is denser than its
  wood: raise `crown.clump_spacing` or add twigs (`branching[2].count`).
- **Leaves on top.** Every living tree has leaves over the whole top of its crown; there
  are no bare tops. Keep `crown.fill_top` at 0.9 to 1.
- **No bare limbs.** Every limb ends in leaves (in leaf seasons).
- **Even on every side.** A tree is as full to the north as to the south. Main limbs are
  spread evenly round the trunk by the generator.
- **Variants differ only in crookedness.** The three variants of a stage have the same
  proportions; only `trunk.tortuosity`, `trunk.twist`, `trunk.gnarl` and `trunk.fluting`
  change between them. Do not try to make one variant wider or taller.
- **Airy, not holed.** Sky shows through the crown between fine twigs and sprays of
  leaves, but the crown has no big empty holes. Use `foliage.density` and twigs, not
  `crown.openness`, to make it airy.
- **Shade.** Seen from above, a mature tree's crown covers the ground under it. Always
  check the view from above.
- **Fine crooked twigs at the tips.** Adult, old and dead trees end every branch in tiny
  crooked twiglets (`tips.*`). They show most on bare winter crowns and dead trees.
- **Real facts only.** A number without a source is left out, never guessed. "Typical for
  the genus" is not a source. Leaf colours too: no source for autumn colours means no
  `autumn` tone.
- **Few, decisive rounds.** marcos dislikes long iteration. Get it right alone first, with
  the contact sheet and the viewer, and show him a finished species, not a draft.

## 0. Set up once per computer

On marcos's computer the repository is `/mnt/marcos/Projects/genes`. Work there:

```
cd /mnt/marcos/Projects/genes
git checkout main
git pull
git checkout -b species/<id>
uv sync --group blender
npm ci --prefix tools/compress
uv run playwright install chromium
uv run genes doctor
```

`genes doctor` checks everything the recipe needs (Python 3.13, Blender's `bpy`, Node, the
model compressor, Chromium, git) and prints the one command that fixes each missing
piece. Continue only when it says `Ready to add a species.`

- `bpy` is Blender as a Python module: no Blender app is needed, and marcos has none.
- Always sync with `uv sync --group blender`. A plain `uv sync` removes `bpy`.
- Node is only used to compress the models. Chromium renders the contact sheets.

## 1. Pick the species, its id and its folder

- Pick a species that grows in the Sierras Chicas of Córdoba (Argentina).
- The id is the accepted scientific name in kebab case: `Neltuma alba` → `neltuma-alba`.
  Check the accepted name on iNaturalist and on GBIF; older names go in `synonyms`.
  - iNaturalist: `https://api.inaturalist.org/v1/taxa?q=<scientific name>` (the taxon id
    is in the result, and in the taxon's web address).
  - GBIF: `https://api.gbif.org/v1/species/match?name=<scientific name>`.
- Make the folder `species/plants/<id>/` with `sheets/`, `looks/1/` and `references/`.

## 2. Where the facts come from

Use several sources and prefer the ones closest to Córdoba. Write down each one in the
sheet's `sources` with its title, address and the date you read it. The algarrobo used:

| Source | Good for |
| --- | --- |
| Flora Argentina, `buscador.floraargentina.edu.ar` | accepted name, size, flowering and fruiting months, distribution |
| Gobierno de Córdoba, SIPEC native trees PDFs | local heights, phenology, uses |
| Aves Argentinas, `avesargentinas.org.ar/ficha-planta/...` | phenology in Córdoba, which birds use it |
| INTA repository, `repositorio.inta.gob.ar` | growth, wood, uses, regional data |
| FAO documents on native trees (for example the Prosopis monograph) | phenology triggers, variability between trees |
| ICRAF Agroforestree database, `apps.worldagroforestry.org/treedb` | climate limits, rainfall, wood density |
| Wikipedia (Spanish and English; cite the revision id) | a start, never the only source for a number |
| iNaturalist and ArgentiNat observations | months of flowers, fruit and leaves; photos dated by month |
| Papers (Google Scholar, SciELO) | frost limits, root depth, growth rates |

Two iNaturalist histograms are valid sources (`kind: observations`); give the counts in the
note:

- flowers and fruit by month:
  `https://api.inaturalist.org/v1/observations/histogram?taxon_id=<id>&quality_grade=research&date_field=observed&interval=month_of_year&term_id=12&term_value_id=13`
  (13 = flowers, 14 = fruits or seeds);
- leaves by month: the same with `term_id=36` and `term_value_id` 37 (breaking leaf buds),
  38 (green leaves), 39 (coloured leaves) or 40 (no live leaves).

`genes refs candidates` (next step) prints the flowering and fruiting months for you.

## 3. Reference photos

```
uv run genes refs candidates <id> --taxon <inaturalist taxon id>
```

It downloads research-grade photos with a shareable licence (CC0, CC BY, CC BY-SA) into
`.work/<id>/candidates/` (not committed), with numbered contact grids `grid-1.jpg`, ...
to look at, and prints the months in which observers marked flowers and fruit.

Look at the grids and pick 10 to 20 photos:

- **3 to 5 whole trees seen from the side**, against the sky if possible, in leaf. The
  model is measured against these. Prefer open-grown trees standing alone.
- photos from **different months**: their dates are the evidence for the leaf colour
  calendar (bright new leaves, mature leaves, dry or coloured leaves, bare);
- one young tree, and one old or dead tree if there is one;
- trunk and bark close up; a branch; leaves; flowers; fruit; thorns if it has them;
- one from Córdoba or the Sierras Chicas if there is one.

Add each one:

```
uv run genes refs add <id> <number> --shows whole,summer --angle side --box 0.12,0.08,0.71,0.88
uv run genes refs add <id> <number> --shows bark --angle detail
```

Each photo also gets a small WebP in `references/thumbs/` (the middle 4:3 crop the page's
photo strip shows); commit it with the photo. `uv run genes refs thumbs <id>` writes any
that are missing.

- `--shows`: a comma list from `whole, trunk, bark, branch, leaves, flowers, fruit,
  seedling, young, old, dead, winter, summer, habitat` (thorns are a `branch` photo).
- `--angle`: `side`, `below`, `above` or `detail`.
- `--box` only for whole-tree side photos: where the tree is, as fractions of the photo's
  width and height, `left,top,right,bottom`. Top is the top of the crown, bottom the foot
  of the trunk. Open the photo in a viewer that shows pixel coordinates and divide by the
  photo's size. Be tight: the box decides the score.

Photos go to `references/r01.jpg`, ... (at most 1280 px), with the author, licence and
link in `references/refs.json`. Never add a photo with another licence; link it in the
sheet instead.

## 4. The sheet: facts with sources

`sheets/1.json`. Copy the algarrobo's and replace everything. Rules (spec §5):

- Every fact is a range `{min, typical, max, source: [...], note}` in real units, or a
  `{value, source, note}`. Each `source` id is listed in `sources`.
- **A fact you cannot source is left out.** Write in `note` what the sources disagree on.
- Measurements read from your own reference photos are allowed for crown width and trunk
  diameter when no text gives them; say so in the note and add the `inat` source.
- Spanish and English names, and a two-sentence summary in both.

Fill as many of these as the sources allow. The viewer's Facts panel shows the starred
ones:

| Group | Fields |
| --- | --- |
| `size` | `adult_height_m`\*, `crown_width_m`\*, `trunk_dbh_m`\*, `trunks`, `height_at_age` |
| `life` | `first_flowering_years`\*, `lifespan_years`\* |
| `phenology` | `leaf_habit`, `leaf_type`, `leaf_out`, `flowering`, `fruiting`, `leaf_fall`, `leaf_tones`, `winter_leaf_share`, `spread_days` (all shown) |
| `water` | `rainfall_mm_year`\*, `drought_tolerance`\*, `root_depth_m`\*, `waterlogging_tolerance` |
| `light` | `shade_tolerance_seedling`, `shade_tolerance_adult` |
| `climate` | `frost_kill_c_adult`\*, `frost_kill_c_seedling`, `heat_limit_c` (measured limits); `habitat_min_c`, `habitat_max_c` (the extremes of the places it grows) |
| `reproduction` | `fruit`, `seeds_per_year`, `dispersal`, `root_suckers`, `resprouts` |
| `wood` | `density_kg_m3`\*, `standing_dead_years`, `fallen_decay_years` |
| `gives` | what it gives to others by month: fruit, nectar, pollen, browse, shade, nesting… |
| `people` | uses, protected status |

### 4.1 Seasons: the phenology and the leaf colour calendar

This is what the viewer's season buttons show (spec §6.3 and §6.4). Get it right.

- `leaf_habit`: `evergreen`, `semi_deciduous` or `deciduous`.
- `leaf_out`, `flowering`, `fruiting`, `leaf_fall`: the usual months in the Sierras Chicas,
  each with its sources, and a `trigger` when a source says what starts it
  (`first_frost`, `first_spring_rains`, `day_length`, `heat_sum`, `rain`, `drought`).
  `leaf_fall.months` is the approximate date the leaves fall.
- `leaf_tones`: which palette tone the leaves show in which months, in the order they
  come. Tones: `new` (fresh leaves), `mature`, `autumn` (only if the leaves really colour)
  and `dry` (killed by frost or drought before they drop).
  - Together the tones cover every month a leaf is on the tree; at most two share a
    month. A shared month is drawn as a gradient across the crown.
  - Photos dated by month are a valid source: name them in the note (for example
    "photos r05 and r06, October, bright green").
  - Add `weeks_per_leaf` (how long one leaf keeps that colour) only if a text says so.
- `winter_leaf_share` (0 to 1: how much of the crown stays on at the barest point) and
  `spread_days` (how many days one tree runs ahead of or behind another): only with a
  source. Without `winter_leaf_share` the viewer uses the habit's default (evergreen 1,
  semi-deciduous 0.35, deciduous 0).

The algarrobo's calendar, as an example:

```
"leaf_tones": [
  { "tone": "new",    "months": [8, 9, 10], "source": ["cba", "inat"], "note": "..." },
  { "tone": "mature", "months": [10, 11, 12, 1, 2, 3, 4, 5, 6, 7], "source": ["inat"], "note": "..." },
  { "tone": "dry",    "months": [7, 8], "trigger": "first_frost", "source": ["fao_prosopis", "cba"], "note": "..." }
],
"spread_days": { "min": 10, "max": 15, "source": ["fao_prosopis"] }
```

Run `uv run genes validate`. It checks the shape, the sources, the ranges and the
calendar.

### 4.2 Spanish texts (`i18n/es.json`)

The public site has one language per page: English at `/species/<id>/`, Spanish at
`/es/species/<id>/`, never mixed. Notes, summaries and traits are written in English in the
sheet and the look; their Spanish goes in `species/plants/<id>/i18n/es.json`, keyed by the
English text exactly (copy the algarrobo's file for its shape):

```
{
  "about": "Spanish for the English texts of this species' sheet and look, shown on the Spanish page (/es/). Keys are the English text exactly; a missing one fails the tests.",
  "texts": { "<English text, exactly>": "<texto en castellano rioplatense>" }
}
```

Write it last, once the sheet and look stop changing: a key that no longer matches its
English text counts as missing. `uv run pytest tests/test_site.py -k translated` lists every
text still in English. If the list names a word of the site itself rather than of your
sheet (a new fruit form, a leaf habit the algarrobo lacks), add it to `UI_ES` in
`src/genes/site_i18n.py`; that is the one code file a species PR may touch.

## 5. The look: traits first, then numbers

`looks/1/look.json`. Set `for_sheet` to the sheet's version and `generator` to `plant@1`.
Every form parameter, its default and what it does: `docs/PLANT_FORM_PARAMETERS.md`.

### 5.1 Write the recognisable traits

Three or four sentences in `recognisable`: what makes someone say "that's an X" from
twenty metres away. Look at the photos, not at the sources. Every number you set next must
serve one of these traits. Example (algarrobo): short trunk forked low into leaning limbs;
wide flat airy crown; limbs arching out and drooping; long pale pods hanging in summer.

### 5.2 Stages and heights

```
"stages": {
  "seedling":      { "ref_height_m": 0.35, "variants": 3 },
  "sapling":       { "ref_height_m": 1.3,  "variants": 3 },
  "young":         { "ref_height_m": 3.5,  "variants": 3 },
  "adult":         { "ref_height_m": 7.5,  "variants": 3 },
  "old":           { "ref_height_m": 8.5,  "variants": 3 },
  "dead_standing": { "ref_height_m": 7,    "variants": 2 },
  "fallen":        { "ref_height_m": 1.3,  "variants": 2 }
},
"lods": ["lod0", "lod1"]
```

- `adult.ref_height_m` must lie inside the sheet's `adult_height_m` range. Pick the height
  of a tree like the ones in your whole-tree photos.
- `fallen` is the height of a trunk lying on the ground: about its diameter plus a stub.
- Shrubs may leave out stages they do not have, but keep `adult`.

### 5.3 Palette (the colours)

Per part, a `lit` and a `shade` hex colour (and an optional `accent`), flat, as a painter
would mix them, picked from your photos in sun and in shade. Parts: `bark`, `foliage`,
`flowers`, `fruit`, `thorns`. Shadows lean cool (blue-violet), as in the algarrobo's.

Foliage has one pair per tone: `new`, `mature`, `dry`, and `autumn` if it colours. Every
tone the sheet's `leaf_tones` names must be here (the validator checks). Pick each from a
photo of that month: fresh spring leaves are usually lighter and yellower than mature
ones. The model carries only the flat lit colour; pietri.dev paints and lights it.

### 5.4 Form, part by part

Write only what makes this species different; everything else takes the default. A range
is a number or `[min, max]`, and its middle is what is drawn. Read the photos in this
order, biggest shapes first.

**Crown (outline)**

| What you see in the photos | Parameters |
| --- | --- |
| Crown wider than tall, or taller than wide | `crown.width_to_height` (from the sheet: crown_width / adult_height) |
| Overall crown shape | `crown.envelope`: `umbrella` (flat, wide), `globose`, `conical`, `columnar`, `weeping`, `irregular` |
| Where the crown starts | `crown.base` (fraction of the height; low = skirt to the ground) |
| Flat top, or rounded | `crown.flat_top` |
| Leaves on the top (every tree has them) | `crown.fill_top`: keep 0.9 to 1 |
| Lobes and gaps in the outline | `crown.irregular` |

**Trunk**

| What you see | Parameters |
| --- | --- |
| One main stem, or a fork | `trunk.count` (leaders above the fork), `trunk.split_height` |
| Leaders spread out, or rise | `trunk.fork_angle_deg`, `trunk.leader_curve` (negative arches them out) |
| Thickness | `trunk.radius_per_height` (from the sheet: dbh / 2 / adult_height), `trunk.taper` |
| Leaning, knotty | `trunk.lean_deg`, `trunk.gnarl`, `trunk.flare` (foot), `trunk.fluting` (spiral ribs, as if stems had fused) |
| Bark | `trunk.bark.pattern` (`smooth`, `fine_fissures`, `deep_fissures`, `plates`, `peeling`), `trunk.bark.depth` |

**Tortuosity (how crooked)**

Crookedness is the one thing that differs between variants, so it gets its own ranges.

| What you see | Parameters |
| --- | --- |
| Big slow S-bends in the trunk and leaders | `trunk.tortuosity` (0 straight, 0.5 clearly crooked, 1 a contorted old algarrobo) |
| How many bends | `trunk.bends` (1 = one long S, 3 = restless) |
| Smooth curves, or straight runs with sharp kinks | `trunk.bend_style`: `smooth` (algarrobo) or `elbows` (tala, espinillo) |
| Crooked all the way, hardly a straight part | `trunk.crooked_to_tip` (0 = calm towards the crown, 1 = crooked to every tip; algarrobo 1) |
| Small zig-zag | `trunk.twist` |
| Crooked branches | `branching[].tortuosity`, `branching[].bend_style`, `branching[].wander` |

Crookedness grows with age by itself: a sapling is nearly straight.

**Branches**

`branching` is a list of levels below the leaders: level 1 the main limbs, 2 the
branches, 3 the twigs. Most trees need 3 levels; shrubs 2.

| What you see | Parameters |
| --- | --- |
| Many or few limbs | `branching[].count` |
| Where along the parent they start | `branching[].start` (low = branches near the trunk too) |
| Angle and length | `branching[].angle_deg`, `branching[].length` |
| Limbs droop at the tips | `branching[].droop`, `branching[].curve` |
| Thickness of each level | `branching[].radius_ratio` |

**Leaves (foliage)**

The leaves are painted clumps (crossed cards) along the finest twigs.

| What you see | Parameters |
| --- | --- |
| Leaf shape on the texture | `foliage.leaf_type` (`bipinnate`, `pinnate`, `broad`, `needle`, `scale`), `foliage.leaf_size_cm` (from the sheet) |
| Size of the sprays | `crown.clump_size_m` |
| More or fewer sprays along each twig | `crown.clump_spacing` (in clump sizes; lower = more) |
| Airy, sky through it | `foliage.density` down (0 = a few sprays, 1 = a solid mass), `foliage.twigs` up (dark twigs inside each clump) |
| More shade from above without a dense ball | `foliage.cards_per_clump` 3 or more (the third card faces the sky) |
| Leaves only towards the twig tips, or all along | `foliage.leafy_from` |

**Twiglets at the tips**

| What you see | Parameters |
| --- | --- |
| A brush of tiny crooked twigs at every branch end (on bare crowns) | `tips.twiglets` (per end), `tips.length`, `tips.crookedness`, `tips.forks`, `tips.stages` |

**Flowers, fruit and thorns**

| What you see | Parameters |
| --- | --- |
| Flowers | `flowers.form`, `flowers.length_cm`, `flowers.where`, `flowers.cover` (sizes from the sheet) |
| Fruit | `fruit.form` (`pod_straight`, `pod_curved`, `pod_coiled`, `berry`, `capsule`, ...), `fruit.length_cm`, `fruit.width_cm`, `fruit.hanging`, `fruit.cover` |
| Flowers or fruit vanish at real size but are a recognisable trait | `show_scale` 1.2 to 1.8 |
| Thorns | `thorns.kind`, `thorns.length_cm`, `thorns.where` |

**Old and dead trees**

| What you see | Parameters |
| --- | --- |
| Old trunk opening from the ground into stems | `old.trunk_split` |
| Low limbs reaching the ground, lying on it and rising again | `old.limb_sag`, `old.sagging_limbs` |
| Broken limbs, thinner crown, extra lean | `old.broken_limbs`, `old.crown_thinning`, `old.extra_lean_deg` |
| Dead trees | `dead.lost_twigs`, `dead.broken_top` |

**One stage only**

`form.stages.<stage>` changes the form for one stage: write it like the form, only what
changes. A `branching` list there replaces the whole list. An old tree is often a
different shape (thicker trunk, wider crown, more limbs): give `stages.old` its own
`trunk`, `crown`, `foliage` and `branching`, as the algarrobo does. A young tree is
narrower and more upright; a seedling has `levels: 0`.

## 6. Build, compare, change, again

```
uv run genes build-models <id>
uv run genes contact-sheet <id>
```

`build-models` writes all models next to `look.json` (about a minute for 42 models) and
prints one JSON line per model: triangles, bytes, height and notes. Read the notes:

- "branches thinner than X cm drawn as N fine twigs out to the leaves": normal.
- "N clumps moved onto their wood": a few are fine; hundreds mean the crown is denser
  than its wood (raise `crown.clump_spacing` or add twigs).
- "N clumps over budget, kept M": the foliage hit its triangle budget; the crown is still
  full, just with bigger clumps.

Use `--stage adult` to rebuild only one stage while tuning.

`contact-sheet` writes `looks/1/sheet.png` and prints the scores:

```
[{"photo": "r01", "model": "adult-c.lod0.glb", "view": "back", "score": 0.63}, ...]
```

The score is the overlap (intersection over union) of the model's silhouette and the tree
in each whole-tree photo; 1.0 is a perfect match. Aim for 0.6 or more for dense crowns.
Airy crowns score lower because sky shows through the model too: the algarrobo sits near
0.5. There the outline matters more than the number.

Open `sheet.png` and look at it:

- top rows: each photo with the best model laid over it in red, inside the yellow box;
- then the adult variants in summer, winter and in flower, painted, and lod1;
- close-ups near the crown's edge (flowers, fruit);
- bottom rows: every stage of variant a at one scale beside a 1.75 m person.

Read the red overlay like a tailor: red outside the tree means the model is too big there;
tree outside the red means too small. Change one or two parameters at a time, then
rebuild:

| On the sheet or in the viewer | Change |
| --- | --- |
| Crown too narrow or too wide | `crown.width_to_height` |
| Crown too round on top | `crown.flat_top` up, or `crown.envelope: umbrella` |
| Crown sits too high or too low on the trunk | `crown.base`, `trunk.split_height` |
| Bare inner crown, clumps only at the rim | `branching[0].start` lower |
| A dense ball, no sky through it | `foliage.density` down, `foliage.twigs` up, fewer twigs (`branching[2].count`) |
| Gaps in the outline where the photo is full | `crown.irregular` down, `branching[].count` up |
| Little shade seen from above | `foliage.cards_per_clump` 3, `crown.clump_spacing` down, `crown.fill_top` 1 |
| Limbs too straight | `trunk.tortuosity`, `trunk.crooked_to_tip`, `branching[].tortuosity` |
| Trunk too thin or too thick | `trunk.radius_per_height` |
| Flowers or fruit invisible in the close-ups | `cover` up, then `show_scale` up to 1.8 |
| Winter looks like summer | the sheet's `leaf_habit` and `leaf_fall` months |
| Wrong leaf colour in a season | the sheet's `leaf_tones` months, then the palette's tone colours |

## 7. Look at it in the viewer, like marcos will

```
uv run genes serve
```

Open `http://127.0.0.1:8810/review/species/<id>` (the public page is
`/species/<id>/`; see `docs/reports/CATALOG_SITE.md`). The review page is the same for every species: the
3D model, the stage, variant and detail (Close, Far) selectors, the season buttons
(Summer, Autumn, Winter, Spring) and month slider, the photos, the facts with their
sources, and the leaf colour calendar. Check every one of these:

- each stage, each variant, Close and Far: no leaves floating, leaves on top, no bare
  limbs, even on every side, the variants alike except in crookedness;
- the camera views from the side, from above (shade) and from below;
- every season button: the leaves come and go, and change colour as the calendar says;
  flowers and fruit appear in their months;
- the Facts panel: every fact shows with its sources;
- the person (1.75 m) beside the tree: the size is believable.

Then:

```
uv run genes validate
uv run pytest
```

`validate` must print `ok`: schemas, sources, heights, the colour calendar, triangle and
byte budgets (`budgets.json`), every model present, and `extras.genes` matching the look.
If a look is over its byte budget, say so: budgets change only with marcos.

### 7.1 The public page

With `uv run genes serve` still running (it builds the whole site), open
`http://127.0.0.1:8810/species/<id>/` and `http://127.0.0.1:8810/es/species/<id>/`.
Check that the Spanish page has no English left, and that the catalog (`/` and `/es/`)
shows the new card. These parts of the page are **not** yours to make in a species PR:

- `media/card.webp` (the card picture) and `media/stages/` (the painted stage pictures):
  marcos paints them with Gemini; the page uses the 3D model until then.
- `lifecycle/<n>.json` (the simulated life): recorded from pietri.dev's simulator, which
  needs the species there first. Without it the page shows no life replay; that is fine.
- `occurrences.json` (the map): run `uv run genes occurrences <id> --taxon <GBIF key>` if
  the computer reaches `api.gbif.org`, and commit the file; otherwise leave it out and the
  map uses the reference photos' places.

## 8. Hand over to marcos

Commit on your branch `species/<id>` (code, commit messages and docs in English):

```
git add species/plants/<id>
git commit -m "Add <scientific name> (<Spanish common name>)"
```

If you can push, open a PR against `main`. Never merge: merging is marcos's approval, and
after it the version is frozen (a later change is `sheets/2.json` or `looks/2/`).

Then write to marcos **in Spanish** (rioplatense, plain words, no jargon). Include:

1. what species it is, and its recognisable traits in one or two sentences;
2. the scores, and which facts you could not source (left out);
3. anything the generator could not draw;
4. the exact commands to see it, one per line, ready to paste:

```
cd /mnt/marcos/Projects/genes
git checkout species/<id>
uv run genes serve
```

and the pages to open: `http://127.0.0.1:8810/review/species/<id>` and
`http://127.0.0.1:8810/es/species/<id>/`, with what to look at
(for example: "probá el botón Invierno y la vista desde arriba").

## When you are stuck

- A fact has no source: leave it out and say so in the hand-over.
- The species cannot be drawn with the parameters (a palm, a cactus, a climber): stop
  and explain what is missing. Do not change `tools/blender/plant/`.
- `validate` fails on something you do not understand: read the message, the spec
  section it names, and the algarrobo's files; do not edit the validator or the tests to
  make it pass.
- `genes doctor` reports something missing: run the fix it prints.
