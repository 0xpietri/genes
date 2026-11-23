# How to add a species (plants)

A recipe for whoever adds the next species, a person or an agent working alone. Follow it
in order. A new plant is **data only**: a sheet of sourced facts, reference photos and a
look (form parameters). You never touch the generator's code. If a species truly cannot be
drawn with the parameters below, stop and say so in the PR; do not change
`tools/blender/plant/` in a species PR.

The worked example is algarrobo blanco: `species/plants/neltuma-alba/`. Copy its files,
then change them. The specification is `docs/spec/GENES_SPEC_v0.1.md` (sections 5 to 9);
`CLAUDE.md` has the rules.

## 0. Once per computer

```
uv sync --group blender
npm ci --prefix tools/compress
uv run playwright install chromium
```

`bpy` is Blender as a Python module (no Blender app needed). Node is only for the
compression step. Chromium renders the contact sheet.

## 1. Pick the id and the folder

- The id is the accepted scientific name in kebab case: `Neltuma alba` → `neltuma-alba`.
  Check the accepted name on iNaturalist and GBIF; older names go in `synonyms`.
- Folder: `species/plants/<id>/` with `sheets/`, `looks/1/` and `references/`.
- Note the iNaturalist taxon id (from the taxon's URL) and the GBIF id.

## 2. Reference photos

```
uv run genes refs candidates <id> --taxon <inaturalist taxon id>
```

It downloads research-grade photos with a shareable licence (CC0, CC BY, CC BY-SA) into
`.work/<id>/candidates/` (not committed), with numbered contact grids `grid-1.jpg`, ...
to look at, and prints the months in which observers marked flowers and fruit.

Look at the grids and pick 10 to 20 photos:

- **3 to 5 whole trees seen from the side**, against the sky if possible, in leaf. These
  are the ones the model is measured against. Prefer open-grown trees standing alone.
- one in winter (or the dry season), one young tree, one old or dead one if there is one;
- trunk and bark close up; a branch; leaves; flowers; fruit; thorns if it has them;
- one from Córdoba or the Sierras Chicas if there is one.

Add each one:

```
uv run genes refs add <id> <number> --shows whole,summer --angle side --box 0.12,0.08,0.71,0.88
uv run genes refs add <id> <number> --shows bark --angle detail
```

- `--shows`: comma list from `whole, trunk, bark, branch, leaves, flowers, fruit,
  seedling, young, old, dead, winter, summer, habitat` (thorns are a `branch` photo).
- `--angle`: `side`, `below`, `above` or `detail`.
- `--box` only for whole-tree side photos: where the tree is, as fractions of the photo's
  width and height, `left,top,right,bottom`. Top is the top of the crown, bottom the foot
  of the trunk. Open the photo in any viewer that shows pixel coordinates and divide by
  the photo's size. Be tight: the box decides the score.

Photos go to `references/r01.jpg`, ... (at most 1280 px) with the author, licence and link
in `references/refs.json`. Never add a photo with another licence; link it in the sheet
instead.

## 3. The sheet: facts with sources

`sheets/1.json`. Copy the algarrobo's and replace everything. Rules (spec §5):

- Every fact is a range `{min, typical, max, source: [...], note}` in real units, or a
  `{value, source, note}`. Each `source` id is listed in `sources` with its title, URL and
  the date you read it.
- **A fact you cannot source is left out.** Never guess, never "typical for the genus".
  Write in `note` what the sources disagree on.
- The iNaturalist histograms printed by `refs candidates` are a valid source for
  `flowering` and `fruiting` months (`kind: observations`); give the counts in the note.
- Measurements read from your own reference photos are allowed for crown width and trunk
  diameter when no text gives them; say so in the note and add the `inat` source.
- Spanish and English names, and a two-sentence summary in both.
- **Leaf colours through the year** (spec §6.4), in `plant.phenology`:
  - `leaf_fall`: the approximate months and the `trigger` (for example `first_frost`).
  - `leaf_tones`: one entry per palette tone (`new`, `mature`, `autumn`, `dry`) with the
    months it shows, in order. Together they cover every month a leaf is on; at most two
    share a month, and a shared month is the gradient between them. Dated photos of
    whole crowns are a valid source (name them in the note). Add `weeks_per_leaf` only
    if a text says how long one leaf keeps that colour.
  - `winter_leaf_share` (0–1, how much of the crown stays at the barest point) and
    `spread_days` (how many days trees differ), only with a source.
  - No source for autumn colours means no `autumn` tone: do not invent one.

`uv run genes validate` checks the shape, the sources and the ranges.

## 4. The look: traits first, then numbers

`looks/1/look.json`. Set `for_sheet` to the sheet's version and `generator` to `plant@1`.

### 4.1 Write the recognisable traits

Three or four sentences in `recognisable`: what makes someone say "that's an X" from
twenty metres away. Look at the photos, not at the sources. Every number you set next
must serve one of these. Example (algarrobo): short trunk forked low into leaning limbs;
wide flat airy crown; limbs arching out and drooping; long pale pods hanging in summer.

### 4.2 Stages and heights

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

- `adult.ref_height_m` must lie inside the sheet's `adult_height_m` range. Pick the
  height of a tree like the ones in your whole-tree photos (pietri.dev scales each tree
  by `scale_range` around it).
- `fallen` is the height of a trunk lying on the ground: about its diameter plus a stub.
- Shrubs may leave out stages they do not have, but keep `adult`.

### 4.3 Palette

Per part, a `lit` and a `shade` hex colour (and an optional `accent`), flat, as a painter
would mix them, picked from your photos in sun and in shade. Foliage has one pair per
tone: `new`, `mature`, `dry` and `autumn` if it colours; every tone the sheet's
`leaf_tones` names must be here (the validator checks). Parts: `bark`, `foliage`,
`flowers`, `fruit`, `thorns`. Shadows lean cool (blue-violet), as in the algarrobo's.
The model carries only the flat lit colour; pietri.dev paints and lights it (spec §6.4).

### 4.4 Form parameters

Every parameter has a default; write only what makes this species different. The full
list, with what each one does, is `schemas/plant-form.v1.json` (`description` fields). A
"range" is a number or `[min, max]`.

**Rule: variants differ only in how crooked they are.** The generator gives every
variant the middle of each range that sets the tree's proportions (crown width and
height, where it starts, the fork, stems, lean, trunk thickness), and draws each
variant's own value only for `trunk.tortuosity`, `trunk.twist`, `trunk.gnarl` and
`trunk.fluting`. It also spreads the main limbs evenly on every side of the trunk. A
look cannot turn either off: no species gets lopsided or misshapen variants. Ranges
still matter: their middle is what is drawn.

Read the photos in this order, biggest shapes first:

| What you see in the photos | Parameters |
| --- | --- |
| Crown wider than tall, or taller than wide | `crown.width_to_height` (sheet: crown_width / adult_height) |
| Overall crown shape | `crown.envelope`: `umbrella` (flat, wide), `globose`, `conical`, `columnar`, `weeping`, `irregular` |
| Where the crown starts | `crown.base` (fraction of height; low = skirt to the ground) |
| Flat top, or rounded | `crown.flat_top` |
| Sky through the foliage (airy, not holed) | `foliage.density` (0 = a few sprays, 1 = a solid mass), `foliage.twigs` (dark twigs inside each clump), `foliage.cards_per_clump`, fewer `branching[2].count` |
| Big gaps in the crown | `crown.openness` (holes between groups of clumps) |
| Leaves on top of the crown (every tree has them) | `crown.fill_top` (keep it 0.9–1: thin crooked branches rise to fill the top) |
| One main stem or a fork | `trunk.count` (leaders above the fork), `trunk.split_height` |
| Leaders spread or rise | `trunk.fork_angle_deg`, `trunk.leader_curve` (negative arches out) |
| Crooked trunk | `trunk.tortuosity` (0 straight … 1 contorted), `trunk.bends` (how many bends), `trunk.bend_style` (`smooth` S-curves or `elbows`) |
| Crooked all along, hardly a straight part | `trunk.crooked_to_tip` (0 = calm towards the crown … 1 = crooked to every tip) |
| Brushes of tiny crooked twigs at the branch ends (bare crowns) | `tips.twiglets`, `tips.length`, `tips.crookedness`, `tips.forks`, `tips.stages` |
| Crooked branches | `branching[].tortuosity`, `branching[].bend_style` (old algarrobo: smooth limbs, elbowed branches) |
| Leaning, knotty trunk | `trunk.lean_deg`, `trunk.twist` (small zig-zag), `trunk.gnarl`, `trunk.flare`, `trunk.fluting` (spiral ribs, as if stems had fused) |
| Trunk thickness | `trunk.radius_per_height` (sheet: dbh / 2 / adult_height) |
| Limbs droop at the tips | `branching[].droop`, `branching[].curve` |
| Dense twigs or sparse limbs | `branching[].count`, `branching[].length` |
| Bark | `trunk.bark.pattern`, `trunk.bark.depth` |
| Leaf texture | `foliage.leaf_type`, `foliage.leaf_size_cm` (from the sheet) |
| Flowers and fruit | `flowers.*`, `fruit.*` (sizes from the sheet); `show_scale` 1.2–1.8 only if they are a recognisable trait and vanish at real size |
| Thorns | `thorns.kind`, `thorns.length_cm`, `thorns.where` |
| Old trees | `old.trunk_split` (the trunk opens from the ground into stems), `old.limb_sag` (0 = low limbs stay up … 1 = they reach the ground, lie on it and rise again), `old.sagging_limbs`, `old.broken_limbs`, `old.crown_thinning` |
| Dead trees | `dead.*` |

`branching` is a list of levels below the leaders: level 1 the main limbs, 2 the
branches, 3 the twigs. Most trees need 3 levels; shrubs 2.

Crookedness grows with age by itself (a sapling is nearly straight). An old tree is often a
different shape: give `stages.old` its own `trunk`, `foliage` and even a whole `branching`
list (it replaces the adult's), as the algarrobo does.

`stages` inside `form` changes the form for one stage only (a young tree is narrower
and more upright; a seedling has `levels: 0`). Look at the algarrobo's.

## 5. Build, compare, change, again

```
uv run genes build-models <id>
uv run genes contact-sheet <id>
```

`build-models` writes all models next to `look.json` (about 30 s for 42 models) and
prints one JSON line per model: triangles, bytes, height, and notes (for example, how
thin a branch had to be to fit the triangle budget). `--stage adult` builds only one
stage while tuning.

`contact-sheet` writes `looks/1/sheet.png` and prints the scores:

```
[{"photo": "r01", "model": "adult-c.lod0.glb", "view": "back", "score": 0.63}, ...]
```

The score is the overlap (intersection over union) of the model's silhouette and the
tree in each whole-tree photo. 1.0 is a perfect match; **aim for 0.6 or more on every
whole-tree photo, and a mean of 0.65 or more** for dense crowns. Airy crowns score lower
because the sky shows through the model too (the algarrobo sits near 0.5 after marcos
asked for see-through foliage); there the outline matters, not the number. Open
`sheet.png` and look at it too:

- top rows: each photo with the best model laid over it in red, inside the yellow box;
- then the adult variants in summer, winter and in flower, painted, and lod1;
- close-ups near the crown's edge (flowers, fruit);
- the bottom rows: every stage of variant a at one scale beside a 1.75 m person, then
  each stage fitted to its picture.

Read the red overlay like a tailor: red outside the tree means the model is too big
there; tree outside the red means too small. Then change one or two parameters at a
time and rebuild:

| On the sheet | Change |
| --- | --- |
| Crown too narrow or too wide overall | `crown.width_to_height` |
| Crown too round on top | `crown.flat_top` up, or `crown.envelope: umbrella` |
| Crown sits too high or too low on the trunk | `crown.base`, `trunk.split_height` |
| Bare inner crown, clumps only at the rim | `branching[0].start` lower, `crown.openness` down |
| A dense ball, no sky through it | `foliage.density` down, `foliage.twigs` up, fewer twigs (`branching[2].count`) |
| Gaps in the outline where the photo is full | `crown.irregular` down, `branching[].count` up |
| Limbs too straight | `trunk.tortuosity`, `branching[].tortuosity`, `branching[].wander` |
| Trunk too thin or too thick | `trunk.radius_per_height` |
| Flowers or fruit invisible in the close-ups | `cover` up, then `show_scale` up to 1.8 |
| Winter looks like summer | the sheet's `leaf_habit` and `leaf_fall` months (pietri.dev drops the clumps by their order) |
| Wrong leaf colour in a season | the sheet's `leaf_tones` months, then the palette's tone colours |
| Leaves seem to float | nothing to tune: the generator forbids it (fine twigs carry every clump; a test fails otherwise). If many clumps "moved onto their wood" in the notes, the crown is denser than its wood: fewer clumps (`crown.clump_spacing` up) |

Stop when the scores pass, every trait in `recognisable` shows on the sheet, and the
stages look like the same tree growing old. Do this alone before asking anyone.

## 6. Check and hand over

```
uv run genes validate
uv run pytest
uv run genes serve
```

`validate` must print `ok`: schemas, sources, heights, triangle and byte budgets
(`budgets.json`), every model present, `extras.genes` matching the look. The generator
fits every model to its triangle budget by itself (the notes say what it dropped). If a
look is still over its byte budget, say so in the PR: budgets change only with marcos.

Then open `http://127.0.0.1:8810/species/<id>` and look at every stage, month, variant
and LOD.

Open a PR with the sheet, look, models, `sheet.png` and references. In its description:
the scores, the traits, which sources you could not find (facts left out), and anything
the generator could not draw. Agents open PRs; they never merge. Merging is marcos's
approval, and after it the version is frozen: any later change is a new sheet or look
version (`sheets/2.json`, `looks/2/`).
