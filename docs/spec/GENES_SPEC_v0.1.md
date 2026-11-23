# genes: specification v0.1

Status: draft for marcos's approval, 2026-11-23. Owner: marcos. Approved by
merging it as the first PR of `0xpietri/genes`. Open points are in section 16;
16.2 is answered (public, marcos, 2026-11-23).

## 1. Purpose

genes (genes.pietri.dev, repository `0xpietri/genes`) is **the only place in
the pietri.dev ecosystem where species are defined**: what a living thing is
in reality (its biology, with sources) and what it looks like (its 3D models,
made to resemble the real one in the world's painted style). It starts with
plants and is designed from day one for animals.

It is a catalog, not a simulator. pietri.dev (the living world,
`0xpietri/pietri.dev`) consumes it and keeps everything that happens to a
plant or animal over time: growing, ageing, flowering this year, dying. A
later app or another world could consume the same catalog.

The name is the same in Spanish and English.

Decided rules (marcos, 2026-11-22 and 2026-11-23):

- **One sector, one place to fix.** If a species looks wrong or a fact about
  it is wrong, the fix lives here. If the simulation behaves wrongly, the fix
  lives in pietri.dev. No duplicated code between repositories, however small.
- **Stateless, like origen.** No users, no database, no request-time
  computation. genes.pietri.dev serves files that never change once
  published.
- **Real species, one by one, slowly and in detail.** The world is born with
  no trees (pietri.dev life spec §18.6); marcos adds species one at a time.
- **Blender runs headless** from Python scripts, in the cloud or on a server.
  marcos does not need Blender on his PC; he reviews in a browser 3D viewer.
- **Only what is merged into `main` exists.** Agents and Claude open PRs;
  marcos merges. Merging a species version is approving it.

## 2. Scope

### 2.1 Version 1 (phases 1 to 5)

- Plants: trees and shrubs (individuals) and grasses and herbs (cover), the
  growth forms pietri.dev's simulator already knows.
- Per species: a **sheet** (biology facts with sources), a **look** (form
  parameters, palette, built 3D models per growth stage), **reference
  photos**, and a page in the **viewer**.
- The published **catalog** that pietri.dev pins and downloads.

### 2.2 Reserved now, built later

- **Animals** (section 6): the sheet's core and the catalog already carry
  them; their own blocks, body-plan generators, rigs and clips are a later
  phase.
- Domestic animals and their varieties (cat, dog), which pietri.dev's pets
  (Toto, Bulma, Pepa, Lola) will use as individuals.
- Agents researching species on their own (`0xpietri/agents` phase 4): they
  open PRs here, under the same rules as anyone.
- Sounds (bird calls, wind in leaves) as part of a look.

### 2.3 Not genes's

- Growth over time, health, death, seeds landing, populations: pietri.dev's
  simulator.
- Where a plant stands, how old it is, which individuals exist: pietri.dev's
  world state.
- The painted shading (cel bands, violet shade, ink outline): pietri.dev's
  material factory (painted spec §5.1). genes ships shapes and flat colours;
  pietri.dev paints them (section 8).
- The sky: origen. Accounts: id.pietri.dev.

## 3. Who owns what (genes and pietri.dev)

The line is **facts versus model**. A fact can be cited from a source and is
true whatever simulator reads it. A model parameter exists only because one
simulator approximates reality in one particular way.

| Thing | Lives in | Example |
|---|---|---|
| Identity, names, taxonomy, sources | genes, sheet | `neltuma-alba`, "algarrobo blanco" |
| Biology facts, as sourced ranges | genes, sheet | adult height 5–12 m, flowers Sep–Nov |
| Form parameters, palette, models | genes, look | wide umbrella crown, hanging pods |
| Reference photos and their licences | genes | iNaturalist research-grade photos |
| Simulator calibration | pietri.dev | health lost per bad day, response curves |
| Growth curve fit (Chapman–Richards k, shape) | pietri.dev | fitted so it passes through genes's height-at-age facts |
| Individuals, ages, positions, state | pietri.dev | the algarrobo marcos planted by the river |
| How a model is painted and lit | pietri.dev | cel bands, outline |

**Each number lives in one place.** pietri.dev's simulator reads the facts it
needs (adult height, crown width, lifespan, fruiting months, frost limits,
dispersal...) straight from the pinned genes sheet, and keeps in its own
calibration file only what is specific to its model. Today's
`world/schema/plant.schema.json` mixes both; section 13.3 says how it splits.

genes facts are also **pietri.dev's test oracle**: the single-tree check
(seeds spec §7) must grow a tree whose height and crown at 5, 20, 50 and
100 years fall inside the ranges genes gives.

## 4. Concepts

- **Species**: one entry in the catalog, with a stable `id`.
- **Sheet**: the species's identity and biology facts. Versioned on its own
  (`sheet` versions 1, 2, ...). A new sheet version can change what the
  simulation does, so pietri.dev adopts it with a dated `ruleset` event
  (life spec §10).
- **Look**: how it looks: form parameters, palette, the built models and
  their metadata. Versioned on its own (`look` versions). A new look never
  changes the simulation, so pietri.dev can adopt it any day.
- **Reference set**: photos of the real species and what each one shows.
- **Catalog release**: a numbered snapshot of the whole catalog (`catalog`
  1, 2, ...) made on every merge that adds or changes a species version.

Versions are **frozen once merged**: a merged `sheets/2.json` or `looks/3/`
is never edited again; a change is a new version. Before its first merge a
version is a draft and can change freely. A test compares against `main`.

### 4.1 Ids and names

Taxonomy moves. The white carob is *Prosopis alba* in the GBIF backbone and
*Neltuma alba* in iNaturalist and POWO since the 2022 split of *Prosopis*
(checked 2026-11-23). So:

- `id` is a lowercase slug of the accepted scientific name **on the day the
  species is created** (`neltuma-alba`), and **never changes**. Kebab case,
  ASCII, unique across plants and animals.
- `scientific_name` follows iNaturalist's accepted name (the source of most
  reference photos) and may change in a new sheet version; `synonyms[]` keeps
  the others; `external` holds `gbif`, `inaturalist` and `powo` keys.
- Common names per language: `names.es[]`, `names.en[]`, the first one is
  the one shown. Spanish names are the local ones (Córdoba), with region
  notes if a name means different species elsewhere ("algarrobo" alone is
  ambiguous: blanco, negro, and the Mediterranean *Ceratonia*).
- Domestic varieties (later): `canis-familiaris` with `varieties[]`.

## 5. The sheet (facts)

One JSON Schema, `schemas/sheet.v1.json`, for every living thing: a shared
**core** and one block per **kind** (`plant`, later `animal`), and inside
`plant` one block per **growth form**.

### 5.1 Traits

Every number is a trait in real units (metres, years, °C, mm of rain a year,
months 1–12, sRGB), with the unit in the field name (`adult_height_m`), and
cites a source:

```
{ "min": 5, "typical": 9, "max": 12, "source": ["s1", "s3"], "note": "optional" }
```

- `min` and `max` are what the sources say a healthy adult reaches in its
  range; `typical` is the usual value. Never a made-up spread: pietri.dev
  turns the range into its own distribution (its percentiles, life spec §6.1).
- A fact for which no source was found is left out, never guessed. A schema
  field may be `required` only where the simulator cannot run without it.
- `source` ids must exist in `sources[]`. Allowed sources (seeds spec §3,
  moved here): Wikipedia, GBIF, iNaturalist, POWO, Flora Argentina
  (Instituto Darwinion), Universidad Nacional de Córdoba and Museo Botánico de
  Córdoba papers, other peer-reviewed papers, regional field guides. Each
  source: `{ id, kind, title, url, accessed }`.
- Monthly facts are month lists (`[9, 10, 11]`) plus, where known, the
  **trigger** (`first_spring_rains`, `first_frost`, `day_length`,
  `heat_sum`), so a dry spring can delay flowering in the simulation.

### 5.2 Core (every species)

`format` (`genes.sheet.v1`), `id`, `version`, `kind` (`plant` | `animal`),
`scientific_name`, `authority`, `synonyms[]`, `family`, `external{}`,
`names{es[], en[]}`, `status_in_sierras_chicas` (`native` | `exotic` |
`invasive` | `domestic`), `conservation` (IUCN if any), `range_note`,
`sources[]`, `summary{es, en}` (two or three plain sentences for the viewer
and the world's card), `relations[]` (section 5.5).

### 5.3 Plant block

`growth_form`: `tree` | `shrub` | `grass` | `herb` | `cactus` | `climber`.
Groups (fields illustrative; the schema in phase 1 is the reference, and it
must cover every fact today's `plant.schema.json` takes as a fact, section
13.3):

- **Size**: adult height, crown width, trunk diameter at breast height,
  number of trunks; height at known ages when sources give them (the growth
  curve's evidence: `height_at_age[]` of `{age_years, height_m, source}`).
- **Life**: age of first flowering, typical and maximum lifespan.
- **Leaves and phenology**: `leaf_habit` (`evergreen` | `semi_deciduous` |
  `deciduous`), months and triggers of leaf-out, flowering, fruiting, leaf
  fall; leaf type (simple, compound, bipinnate, needle, scale). Also, when
  sources give them: `leaf_tones` (which leaf colour shows in which months,
  section 6.4), `winter_leaf_share` (share of the leaves still on at the
  barest moment of the year) and `spread_days` (how many days one tree runs
  ahead of or behind another in the same place).
- **Water**: rainfall range it lives in (mm a year), drought tolerance
  (`low` | `medium` | `high` with sources), root depth, waterlogging
  tolerance.
- **Light**: shade tolerance as seedling and as adult.
- **Climate**: lowest temperature survived as seedling and adult, heat
  limit.
- **Reproduction**: seed or fruit kind, seeds a year when known, dispersal
  (`gravity` | `wind` | `animals` with which guilds | `water`), root suckers,
  resprouting after cutting or fire.
- **Wood and decay**: wood density (kg/m³), how long dead wood stands and
  lasts when sources say so.
- **Gives to others** (per month): fruit, nectar, browse, nest sites, shade,
  nitrogen fixing.
- **People**: firewood, protected status, uses.

### 5.4 Animal block (reserved; schema in the animals phase)

`class` (`bird` | `mammal` | `reptile` | `amphibian` | `insect` | ...),
`domestic`; body length and mass by sex and life stage, sexual dimorphism;
lifespan, maturity; activity (`diurnal` | `nocturnal` | `crepuscular`) and
season; diet by month as items pointing to other species and parts
(`{ species: "neltuma-alba", part: "fruit", months: [12, 1, 2] }`); water;
habitat needs (nests in trees of given species, needs mud near water, rock,
open grass); home range and group size; reproduction (season, clutch or
litter, care); movement (gaits and speeds, flight style); predators and prey;
typical density per hectare in the Sierras Chicas when known. Same trait
format and source rule as plants.

### 5.5 Relations

`relations[]` link species to each other: `eats`, `eaten_by`, `pollinates`,
`disperses_seeds_of`, `nests_in`, `host_of`. A relation is written once, on
one side, and the catalog builder adds the reverse. The validator checks
that every species id it names exists in the catalog (or is listed as
`planned`).

## 6. The look

`species/<kind>/<id>/looks/<n>/look.json` (schema `schemas/look.v1.json`)
plus the built models in the same folder.

### 6.1 Plant looks: what the generator is told

A tree is not modelled by hand. A **generator** (section 7.2) builds it from
about thirty **form parameters**, the species's "visual genes". They describe
the species, not one tree: each one is a range, and each variant draws its
own value, so no two individuals are alike. Groups:

- **Trunk**: number of trunks and how low they fork; lean and twist; how
  gnarled; taper; base flare; bark (pattern, fissure depth, colour).
- **Branching** (per level, 2 to 4 levels): how many branches, where along
  the parent they start, angle from the parent, length relative to the
  parent, curvature, droop under their own weight, random wander.
- **Crown**: envelope (`umbrella`, `globose`, `columnar`, `conical`,
  `weeping`, `irregular`), width-to-height ratio, flat top, openness (how
  much sky shows through), clump size and spacing.
- **Foliage**: leaf type and size (it sets the texture of the clumps: a
  bipinnate leaf gives an airy, feathery mass; a broad leaf a dense one).
- **Thorns**: kind, length, where.
- **Flowers**: form (spike, ball, bell, single), size, where on the branch,
  and how much of the crown they cover at peak.
- **Fruit**: form (pod straight or curved, berry, drupe, samara), size,
  hanging or upright, how much of the crown at peak.
- **Old age**: broken limbs, hollows, extra lean, thinning crown.
- **Recognisable traits**: three or four sentences, each naming the
  parameters that serve it (seeds spec §4.11, moved here). These come first:
  a model that gets them right reads as the species even when small.

### 6.2 Stages and variants

| Stage | Reaches | Notes |
|---|---|---|
| `seedling` | up to 0.5 m | few leaves, no branches |
| `sapling` | 0.5 m to 2 m | one stem, first branches |
| `young` | 2 m to 60 % of adult height | crown still narrow |
| `adult` | 60 % to 100 % of adult height | the species's full form |
| `old` | from 70 % of typical lifespan | broken limbs, thinner crown |
| `dead_standing` | after death | no leaves, losing branches |
| `fallen` | after it falls | trunk on the ground, decaying |

- **Variants**: three per stage (`a`, `b`, `c`), each from its own generator
  seed. pietri.dev picks one per individual from its random number.
- Each model declares its **reference size** (height and crown width at
  scale 1) and the **scale range** it stays believable in (default 0.75–1.3
  in height, crown scaled on its own). pietri.dev scales the model to the
  simulated height and crown and swaps to the next stage when it leaves the
  range.
- Grasses and herbs (cover) have no individual models: their look is a
  **tuft** (a few blades or a small clump, one model, two variants) plus
  blade parameters (height, width, bend, flower heads, colours by season)
  for pietri.dev's grass system (painted spec §5.5).

### 6.3 One model, every season

A model holds every part the year needs, as separate named meshes:
`bark`, `foliage`, `flowers`, `fruit`, `thorns`. pietri.dev shows or hides
parts by month and phenology instead of loading a different model per
season:

- Every foliage clump, flower and fruit carries a per-vertex value
  `_ORDER` (0–1, random by clump). pietri.dev reveals clumps whose order is
  under the season's amount, so leaves fall and come back clump by clump,
  and flowers open and fade gradually.
- Bare winter, full leaf, flowering and fruiting are therefore the same
  file; the viewer previews them with a month slider.

### 6.4 Palette

Per part and phase, one `lit` and one `shade` colour (sRGB hex), and at most
one `accent` (painted spec §3.1: fewer tones; shade is a colour, not
darkness). Phases for foliage: `new`, `mature`, `dry` (stress), `autumn` if
it colours. Starting colours are picked by the agent from the reference
photos (the median lit and shaded tone of the part), then tuned with marcos
on renders.

**Leaf colour through the year (amended in phase 2, asked by marcos).** The
look holds the colours; the sheet holds *when* each shows, as sourced facts,
so any agent or simulator reads the same calendar:

- `plant.phenology.leaf_tones` is a list of `{ tone, months, trigger?,
  weeks_per_leaf?, source, note? }`. `tone` names a foliage tone of the
  palette (`new`, `mature`, `autumn`, `dry`); `months` are the months it
  shows in a usual year at the species' place in the Sierras Chicas, listed
  in the order they come; `trigger` is what starts it when the weather
  decides (same values as the other phases); `weeks_per_leaf` is how long
  one leaf keeps that tone, only when a source says so. The tones together
  cover every month a leaf is on the tree; at most two tones share a month.
- `dry` as a tone in the calendar means leaves killed by frost or the
  winter drought before they drop. Drought stress in summer is not in the
  calendar: pietri.dev shows `dry` from its own water state.
- `leaf_fall.months` is the approximate date of leaf fall; its `trigger` says
  what brings it forward or holds it back (for example `first_frost`).
  `winter_leaf_share` (a 0–1 range) is how much of the crown stays on at the
  barest point; without a source, the habit's default applies: evergreen 1,
  semi-deciduous 0.35, deciduous 0.
- `spread_days` (a range) is the natural spread between trees: pietri.dev
  gives each individual a fixed offset within it, so a stand does not change
  colour on the same day.

**How a month is painted (the gradient).** In a month with one tone, every
shown clump has it. In a month two tones share, the tone that arrives takes
a share of the shown clumps that grows through the overlap: in the i-th of
k shared months it is i / (k + 1). It takes the clumps with the highest
`_ORDER` first (those are the first to fall and the last to come out), except
when new leaves age to `mature`: then the lowest go first (the first leaves
out are the first to age). The edge between the two tones is soft, about a
tenth of the order range wide, so the change runs across
the crown as a gradient instead of a switch. The viewer previews exactly this
from the sheet's months; in the world pietri.dev moves the same calendar with
the weather (trigger, `spread_days`) and the leaf amount of section 6.3.
A species without `leaf_tones` shows `mature` all year (and `autumn` while
its leaves fall, if the palette has it).

### 6.5 Animal looks (later)

Same idea: a **body-plan generator** per plan (`quadruped`, `bird`,
`reptile`, ...) with proportion parameters (head, neck, legs, tail, beak),
coat or plumage pattern and palette by sex, age and season; a rig with the
plan's bones; clips named per plan (`idle`, `walk`, `run`, `eat`, `rest`,
and for birds `hop`, `fly`, `glide`, `perch`); stages `juvenile` and
`adult`, by sex where they differ (the cardinal). Budgets as the walker's
(painted spec §7.4) for close animals, with a lighter LOD.

## 7. Making a look resemble the real species

### 7.1 The loop

1. **References.** The agent gathers 10 to 20 research-grade photos
   (section 9): the whole tree in summer and winter, trunk and bark, a
   branch, leaves, flowers, fruit, a young tree, an old one, and if possible
   one in Unquillo or the Sierras Chicas. Each photo is tagged with what it
   shows and the camera angle (`side`, `below`, `detail`).
2. **Traits.** From the sources and photos, the agent writes the three or
   four recognisable traits and the form parameters that serve them.
3. **Build.** The generator builds every stage and variant headless.
4. **Compare.** A contact sheet renders each stage from the same angles as
   the reference photos, with the photo beside it and the two silhouettes
   overlaid (model in black, photo's tree masked), plus a 1.75 m person for
   scale. The agent lists what is off (crown too round, trunk too straight,
   pods too short) and changes parameters until the silhouettes and traits
   match. It does this on its own before showing marcos.
5. **Review.** marcos opens the viewer on his PC (section 14), says what
   feels wrong in his own words ("más torcido", "la copa más chata", "las
   vainas más amarillas"); the agent turns it into parameter changes and
   rebuilds. This is the same quick round he already does with the terrain.
6. **Approve.** marcos merges the PR.

### 7.2 The plant generator

- Our own Python script for Blender (`tools/blender/plant/`), run headless
  through the `bpy` module (section 11). It grows trunks and branches
  recursively from the form parameters (Weber–Penn style), prunes them to the
  crown envelope, and turns branches into one skinned mesh with bark UVs.
  Space colonisation may be added later if a species needs it.
- **Foliage as painted clumps**, not single leaves, as in marcos's
  references (`referencia-pintado-1..3`): small groups of alpha-cut cards
  carrying a painted leaf-mass texture, sitting at branch tips. Their normals
  are transferred from a smooth proxy of the crown, so the light falls on
  the whole crown as on a soft ball and pietri.dev's cel bands split it into
  big lit and shaded masses instead of noise. Dark branches show through the
  gaps.
- Each model is built three ways: `lod0` (walk view, close), `lod1` (island
  view), and a flat `impostor` card set for far away if the island view needs
  it (decided in phase 3 by measuring).
- Deterministic: same look parameters, seed and generator version give the
  same geometry on the same platform. The generator version and a hash of the
  parameters go into each model's metadata.
- The painted textures (bark, leaf-mass cards) may be made with fal.ai from
  the reference photos and marcos's painted references, as the planets were
  (price told first; key only in `FAL_KEY`; prompts and model recorded in the
  look).

## 8. The model contract (what pietri.dev receives)

- glTF binary (`.glb`), Y up, 1 unit = 1 m, origin at the base of the main
  trunk on the ground, facing +Z, real size at scale 1.
- Named meshes and materials only from: `bark`, `foliage`, `flowers`,
  `fruit`, `thorns` (plants); later the animal plans' parts. No lights,
  cameras or scene extras.
- Materials carry **flat colour and the painted texture only** (base colour
  map, alpha for clumps, normal for bark if needed). No baked lighting: the
  world lights and paints them.
- Per-vertex `_ORDER` on clumps (section 6.3).
- `extras.genes`: `{ id, look, stage, variant, lod, ref_height_m,
  ref_crown_m, scale_range, generator, params_hash }`.
- Compressed: meshopt geometry, KTX2 textures (stage 1 spec §11.1's tools),
  done here, so the file marcos reviewed is the file that ships.

### 8.1 Budgets (proposed; measured and tuned in phase 2)

| Item | Budget |
|---|---|
| Adult or old tree, `lod0` | ≤ 12 k triangles |
| Adult or old tree, `lod1` | ≤ 1.5 k triangles |
| Seedling or sapling, `lod0` | ≤ 1.5 k triangles |
| Grass tuft | ≤ 300 triangles |
| Textures per species | one atlas, 1024 px (2048 only with marcos's yes) |
| One `lod0` file, compressed | ≤ 500 KB |
| A whole look version, compressed | ≤ 6 MB |

These sit inside the painted spec's walk-view budget (§9: 800 k triangles on
screen including grass); a world of a few hundred trees fits.

## 9. Reference photos

- Listed in `references/refs.json`: `{ id, url, author, licence, source,
  observed_on, place, shows[], angle, used_for[] }`.
- The repository is public (marcos, 2026-11-23), so only photos whose licence
  allows sharing (CC0, CC BY, CC BY-SA) are stored, resized to 1280 px, with
  attribution shown in the viewer. Others (CC BY-NC and all rights reserved)
  are kept as links only; agents may still look at them.
- marcos's own photos (a tree in Unquillo) are welcome and preferred: CC BY
  by marcos, or private links if he wants them kept out of the repository.

## 10. Repository layout

```
genes/
  README.md  LICENSE  CLAUDE.md  CHANGELOG.md
  docs/spec/GENES_SPEC_v0.1.md      this file
  docs/reports/                     one short report per phase
  schemas/
    sheet.v1.json  look.v1.json  refs.v1.json  catalog.v1.json
  species/
    plants/neltuma-alba/
      sheets/1.json                 facts, frozen once merged
      looks/1/look.json             form parameters, palette, stages
      looks/1/adult-a.lod0.glb ...  built models, frozen once merged
      looks/1/sheet.png             the contact sheet of section 7.1
      references/refs.json
      references/*.jpg              only shareable licences
    animals/                        later
  src/genes/                        Python package: validate, catalog, serve, cli
  tools/blender/plant/              the plant generator (bpy)
  tools/blender/animal/             later
  viewer/                           static HTML, CSS, JS; vendored three.js
  tests/
  pyproject.toml  uv.lock
```

`.github/ISSUE_TEMPLATE/especie.yml` (moved from pietri.dev's seeds spec):
common name, scientific name if known, why, notes.

## 11. Stack

- **Python 3.13** with `uv` and a lockfile, pytest, ruff, mypy. 3.13 and not
  the ecosystem's 3.12 because Blender's `bpy` module on PyPI (5.3.0) is
  built only for 3.13 (open point 16.4).
- **Blender as a pinned dependency**, `bpy` in its own `blender` dependency
  group (about 430 MB, Linux x86-64 in the cloud container; also macOS and
  Windows). Nothing else imports it, so validating, building the catalog and
  serving never need it.
- `jsonschema` for validation; `gltf-transform` (Node, pinned with its own
  lockfile under `tools/compress/`) for meshopt and KTX2.
- **Viewer**: plain HTML, CSS and JavaScript, no build step; three.js
  vendored as one pinned ES module under `viewer/static/`; no inline
  `<script>` or `<style>` (same CSP rule as origen and micelio).
- No framework, engine or service beyond these without marcos.
- Licence: code MIT; sheets and looks CC BY 4.0; photos keep their own
  (open point 16.2).

## 12. The published catalog

`genes build` writes a static site into `dist/`; Caddy on marcos's server
serves it at genes.pietri.dev (phase 5). Nothing runs per request.

| URL | What |
|---|---|
| `/` and `/species/<id>` | the viewer |
| `/v1/catalog.json` | every species with its versions and file hashes |
| `/v1/species/<id>/sheets/<n>.json` | a sheet version |
| `/v1/species/<id>/looks/<n>/look.json` | a look version |
| `/v1/species/<id>/looks/<n>/<stage>-<variant>.<lod>.glb` | a model |
| `/v1/species/<id>/references.json` | the reference set with attribution |

```
catalog.json
{
  "format": "genes.catalog.v1",
  "catalog": 7,
  "species": [
    {
      "id": "neltuma-alba",
      "kind": "plant",
      "growth_form": "tree",
      "names": { "es": ["Algarrobo blanco"], "en": ["White carob"] },
      "sheets": [{ "version": 1, "sha256": "..." }],
      "looks": [{ "version": 1, "sha256": "...",
                  "files": [{ "path": "adult-a.lod0.glb", "sha256": "...", "bytes": 412337 }] }]
    }
  ]
}
```

Contract rules (as origen's §4):

- Published files never change: their URLs are cached forever.
- Within `v1`, fields may be added, never renamed, removed or changed in
  meaning or unit. Breaking changes go to `v2`.
- Same repository state, same `dist/`: byte-identical JSON (sorted keys,
  fixed rounding, no build timestamps).

## 13. How pietri.dev consumes genes

Built in pietri.dev, as its own step with its own spec amendment (phase 3
here). Proposed shape:

### 13.1 Pin and sync

- `world/genes.lock.json`: the catalog base URL and, per species in use, the
  sheet and look versions with their sha256.
- `npm run genes:sync` downloads exactly those files into `.genes/`
  (git-ignored) and checks every hash. `GENES_DIR=../genes` reads them from
  marcos's local genes folder instead, so a species can be tried in the world
  before anything is pushed.
- The tick, the simulator and the build read only `.genes/`. The browser
  loads models from pietri.dev's own origin, never from genes.pietri.dev, as
  it never calls origen directly.

### 13.2 The renderer

Per plant in `life.json`: the species's model for its stage (from age,
height and status), its variant (from its random number), scaled to the
simulated height and crown; parts revealed by the month's phenology; status
tints as today. Instanced per species, stage, variant and LOD. Placeholder
species keep today's blobs.

### 13.3 The simulator and the split of `plant.schema.json`

- Facts move to genes's sheet: adult height and crown, stem diameter,
  lifespan, maturity, fruiting and germination months, frost limits, wood
  density, dispersal kind and distance, suckers, minimum spacing when
  sourced.
- Calibration stays in pietri.dev, in `world/species/calibration/<id>@<n>.json`
  validated by pietri.dev's own `calibration.schema.json`: the Chapman–Richards
  rate and shape (fitted to genes's `height_at_age`), leaf area index if not
  sourced, water demand, response curves (drought, shade, temperature),
  health points and thresholds, seed bank loss.
- The simulator composes both into today's in-memory `SpeciesVersion`, so its
  maths does not change. A `ruleset` event names the sheet and calibration
  versions in force.
- `placeholder:*` species stay in pietri.dev as test and preview fixtures,
  in the composed form; they are not in genes.
- pietri.dev's tests read recorded genes sheets from `tests/fixtures/genes/`
  and never the network (as with origen).

### 13.4 What this changes in pietri.dev's specs (in that step's PR)

- `SEEDS_SPEC_v0.1.md`: superseded by this spec (identity, sources rule,
  ordering and approving species, animal seed, starting list). Its
  simulation rules (§6) and checks (§7) stay in pietri.dev's life spec.
- Life spec §12: species = genes sheet + pietri.dev calibration; §13 drawing
  from genes models; §18.6 "each tree species follows the seeds spec" becomes
  "follows genes".
- Stage 1 spec §11.1: genes models enter through the lock, not
  `assets/manifest.json`.
- `CLAUDE.md`: genes owns species; seeds spec retired.
- `0xpietri/agents` phase 4 (agents writing seeds) points here.

## 14. Review and approval, step by step

marcos tries everything on his PC first and pushes only what works.

1. marcos asks for a species (chat or an `especie` issue).
2. Claude (or an agent) researches, writes the sheet, gathers references,
   writes the look, builds the models headless in the cloud and iterates on
   the contact sheet alone (section 7.1).
3. The work reaches marcos's `genes` folder as a local git branch (bundle,
   as with pietri.dev's steps). He runs one command,
   `uv run genes serve`, and opens `http://localhost:8810/species/neltuma-alba`.
4. **The viewer page**: the model orbiting on a turntable with a 1.75 m
   person beside it; a stage slider (seedling to fallen); a month slider
   (bare, leaf, flowers, pods); variants a/b/c; `lod0`/`lod1`; a "how it
   looks in the world" toggle with a flat sun and simple bands (a preview,
   not the world's painter); the reference photos in a strip, each one
   switching the camera to its angle; the facts card with sources; triangle
   counts and file sizes against the budgets.
5. To see it in the real world: in pietri.dev, `GENES_DIR=../genes npm run
   dev` and plant it with the dev time control (from pietri.dev step 8c).
6. marcos replies in chat; rounds repeat until he says OK.
7. Pushed as a PR to genes; marcos merges = approved; the catalog release
   number goes up.
8. In pietri.dev, a small PR bumps `world/genes.lock.json`; marcos plants it.

## 15. Tests and checks

- Every sheet, look and reference set validates against its schema.
- Every trait's sources exist; every relation and diet item names a known
  species; no draft-only `planned` id in a merged species without a note.
- Frozen versions: a merged sheet or look differs from `main` → fail.
- Models: triangles within budget for stage and LOD; only allowed part
  names; Y up, base at y = 0 within 1 cm, centred; reference height inside
  the sheet's adult height range for `adult` at scale 1; `extras.genes`
  present and its `params_hash` equal to the look's.
- Generator (with `bpy`): same parameters and seed twice give the same
  geometry hash; every stage builds for the worked example.
- Catalog: deterministic; every file hash matches; nothing in `dist/` that
  is not merged.
- Viewer: Playwright loads a species page with no console errors; no inline
  scripts or styles.
- Licences: every stored photo has a shareable licence and attribution.
- Tests never touch the network; iNaturalist and GBIF answers used by
  scripts are recorded as fixtures.

## 16. Open points for marcos

1. **Facts here, calibration in pietri.dev** (section 3). Recommended: yes;
   the alternative, the whole `plant.schema.json` in genes, means every
   simulator tune is a PR in two repositories.
2. **Public repository**, code MIT, data CC BY 4.0. Answered: public, like
   origen (marcos, 2026-11-23).
3. **Models committed in git** (compressed, about 2–6 MB per look version).
   Recommended: yes, so the file marcos approved is the file that ships. If
   the repository passes about 1 GB, move old versions to release assets.
4. **Python 3.13** for this repository because of `bpy`. Recommended: yes.
5. **Which algarrobo first**: blanco (*Neltuma alba*, the worked example)
   or negro (*Neltuma nigra*). Both grow in Córdoba's Chaco; few
   research-grade observations near Unquillo for either.
6. **Order with the real grasses**: pietri.dev needs real grasses before play
   (life spec §18.6 step 4). Recommended: algarrobo first to prove the whole
   pipeline (it is the hard case), grasses right after (phase 4), both
   before play.

## 17. Phases

Each phase ends with tests, a short report in `docs/reports/` with one-line
commands to try it locally, and a stop.

0. **This spec**, README (one paragraph), `CLAUDE.md`, licence. Approved by
   merging.
1. **Base**: schemas (sheet core and plant block; animal block as a stub),
   validator, catalog builder, `genes serve`, the viewer loading a test model
   made in code (a cone and a cylinder), tests. No Blender.
2. **Plant generator and the first species**: the `bpy` generator, LODs,
   compression, checks, contact sheets; algarrobo blanco end to end (sheet
   with sources, references, look, models); review rounds on marcos's PC.
3. **pietri.dev reads genes** (built in pietri.dev, section 13): lock, sync,
   calibration split, the renderer drawing genes models.
4. **Grasses**: the tuft and blade look; Unquillo's real grasses replace
   `placeholder:pasto` and `placeholder:paja`.
5. **Deploy** genes.pietri.dev on marcos's server (Caddy, static), only when
   marcos says.

Later, each asked for separately: animals (schema block, body-plan
generators, rigs and clips; the hornero as a first example), domestic
varieties for the pets, agents writing species, sounds.

## Appendix A. Worked example: algarrobo blanco

The values below show the **shape** of the files. They are not yet checked
against sources; phase 2 replaces them with sourced ones.

### A.1 What makes it recognisable

1. A short, thick trunk, often forked low into two or three leaning, twisted
   limbs.
2. A wide, flat-topped crown, usually wider than the tree is tall, airy and
   see-through: fine bipinnate leaves make a feathery, light-green mass.
3. Limbs that arch out and droop at the tips.
4. In summer, long straw-yellow curved pods hanging in bunches.

### A.2 Sheet (abridged)

```
{
  "format": "genes.sheet.v1",
  "id": "neltuma-alba",
  "version": 1,
  "kind": "plant",
  "scientific_name": "Neltuma alba",
  "authority": "(Griseb.) C.E.Hughes & G.P.Lewis",
  "synonyms": ["Prosopis alba Griseb."],
  "family": "Fabaceae",
  "external": { "inaturalist": 1493104, "gbif": 5358528 },
  "names": { "es": ["Algarrobo blanco", "Ibopé"], "en": ["White carob", "White mesquite"] },
  "status_in_sierras_chicas": "native",
  "summary": {
    "es": "El árbol del monte chaqueño: copa ancha y rala, tronco corto y torcido, vainas dulces en verano.",
    "en": "The Chaco woodland's tree: a wide airy crown on a short twisted trunk, sweet pods in summer."
  },
  "sources": [
    { "id": "s1", "kind": "flora", "title": "Flora Argentina: Prosopis alba", "url": "...", "accessed": "2026-..." },
    { "id": "s2", "kind": "observations", "title": "iNaturalist: Neltuma alba", "url": "https://www.inaturalist.org/taxa/1493104", "accessed": "2026-11-23" }
  ],
  "plant": {
    "growth_form": "tree",
    "size": {
      "adult_height_m":   { "min": 5, "typical": 9, "max": 12, "source": ["s1"] },
      "crown_width_m":    { "min": 6, "typical": 10, "max": 14, "source": ["s1"] },
      "trunk_dbh_m":      { "min": 0.3, "typical": 0.6, "max": 1.0, "source": ["s1"] },
      "trunks":           { "min": 1, "typical": 1, "max": 3, "source": ["s1"] }
    },
    "life": {
      "first_flowering_years": { "min": 5, "typical": 8, "max": 12, "source": ["s1"] },
      "lifespan_years":        { "min": 150, "typical": 200, "max": 300, "source": ["s1"] }
    },
    "phenology": {
      "leaf_habit": "semi_deciduous",
      "leaf_type": "bipinnate",
      "leaf_out":  { "months": [9, 10], "trigger": "first_spring_rains", "source": ["s1"] },
      "flowering": { "months": [9, 10, 11], "source": ["s1"] },
      "fruiting":  { "months": [12, 1, 2], "source": ["s1"] },
      "leaf_fall": { "months": [7, 8], "trigger": "first_frost", "source": ["s1"] },
      "leaf_tones": [
        { "tone": "new",    "months": [9, 10], "source": ["s1"] },
        { "tone": "mature", "months": [10, 11, 12, 1, 2, 3, 4, 5, 6, 7], "source": ["s1"] },
        { "tone": "dry",    "months": [7, 8], "trigger": "first_frost", "source": ["s1"] }
      ],
      "spread_days": { "min": 10, "max": 15, "source": ["s1"] }
    },
    "water": {
      "rainfall_mm_year": { "min": 350, "typical": 700, "max": 1200, "source": ["s1"] },
      "drought_tolerance": { "value": "high", "source": ["s1"] },
      "root_depth_m": { "min": 3, "typical": 8, "max": 20, "source": ["s1"] }
    },
    "light": { "shade_tolerance_seedling": "low", "shade_tolerance_adult": "low", "source": ["s1"] },
    "climate": {
      "frost_kill_c_seedling": { "min": -6, "typical": -4, "max": -3, "source": ["s1"] },
      "frost_kill_c_adult":    { "min": -12, "typical": -9, "max": -7, "source": ["s1"] }
    },
    "reproduction": {
      "fruit": "pod",
      "dispersal": [{ "by": "animals", "guilds": ["mammals", "cattle"], "source": ["s1"] }]
    },
    "wood": { "density_kg_m3": { "min": 700, "typical": 780, "max": 850, "source": ["s1"] } },
    "gives": [
      { "what": "fruit", "months": [12, 1, 2], "to": ["mammals", "people"] },
      { "what": "nectar", "months": [9, 10, 11], "to": ["bees"] },
      { "what": "nitrogen_fixing" }
    ]
  }
}
```

### A.3 Look (abridged)

```
{
  "format": "genes.look.v1",
  "id": "neltuma-alba",
  "look": 1,
  "for_sheet": 1,
  "generator": "plant@1",
  "recognisable": [
    { "trait": "short thick trunk forked low, leaning and twisted",
      "params": ["trunk.split_height", "trunk.lean_deg", "trunk.twist"] },
    { "trait": "wide flat-topped airy crown, wider than tall",
      "params": ["crown.envelope", "crown.width_to_height", "crown.flat_top", "crown.openness"] },
    { "trait": "limbs arch out and droop at the tips",
      "params": ["branching.1.angle_deg", "branching.2.droop"] },
    { "trait": "straw-yellow curved pods hanging in bunches in summer",
      "params": ["fruit.form", "fruit.length_cm", "fruit.cover"] }
  ],
  "form": {
    "trunk": { "count": [1, 3], "split_height": [0.15, 0.35], "lean_deg": [5, 20],
               "twist": [0.3, 0.6], "taper": 0.7, "flare": 0.25,
               "bark": { "pattern": "deep_fissures", "depth": 0.7 } },
    "branching": [
      { "level": 1, "count": [3, 6], "start": [0.2, 0.5], "angle_deg": [45, 70],
        "length": [0.6, 0.9], "curve": 0.3, "droop": 0.1, "wander": 0.4 },
      { "level": 2, "count": [6, 12], "start": [0.3, 1.0], "angle_deg": [35, 60],
        "length": [0.3, 0.5], "curve": 0.2, "droop": 0.5, "wander": 0.3 },
      { "level": 3, "count": [8, 16], "start": [0.4, 1.0], "angle_deg": [30, 50],
        "length": [0.2, 0.35], "droop": 0.6, "wander": 0.2 }
    ],
    "crown": { "envelope": "umbrella", "width_to_height": [1.1, 1.6], "flat_top": 0.7,
               "openness": 0.55, "clump_size_m": [0.5, 0.9] },
    "foliage": { "leaf_type": "bipinnate", "leaf_size_cm": [5, 10] },
    "thorns": { "kind": "short_paired", "length_cm": [0, 1.5], "where": "young_twigs" },
    "flowers": { "form": "spike", "length_cm": [5, 11], "where": "axils", "cover": 0.35 },
    "fruit": { "form": "pod_curved", "length_cm": [12, 25], "hanging": true, "cover": 0.3 },
    "old": { "broken_limbs": [0, 2], "hollow": 0.3, "extra_lean_deg": [0, 10] }
  },
  "palette": {
    "bark":    { "lit": "#7a6a58", "shade": "#45405a" },
    "foliage": { "new":    { "lit": "#b5c46a", "shade": "#5f7a6e" },
                 "mature": { "lit": "#8fa155", "shade": "#4c5f6a" },
                 "dry":    { "lit": "#b9a35c", "shade": "#6b6070" } },
    "flowers": { "lit": "#e6dc8a", "shade": "#9a9a78" },
    "fruit":   { "lit": "#e3c46b", "shade": "#9c8466", "accent": "#c79a4a" }
  },
  "stages": {
    "seedling":      { "ref_height_m": 0.3,  "variants": 3 },
    "sapling":       { "ref_height_m": 1.2,  "variants": 3 },
    "young":         { "ref_height_m": 3.5,  "variants": 3 },
    "adult":         { "ref_height_m": 8.5,  "ref_crown_m": 11, "variants": 3 },
    "old":           { "ref_height_m": 9,    "ref_crown_m": 12, "variants": 3 },
    "dead_standing": { "ref_height_m": 8,    "variants": 2 },
    "fallen":        { "ref_height_m": 1.2,  "variants": 2 }
  },
  "references": ["r01", "r02", "r05", "r09"]
}
```

### A.4 What pietri.dev reads from it

From the sheet: adult height 5–12 m and crown 6–14 m (each new algarrobo
draws its own within them), lifespan, flowering months 9–11 and fruiting
12–2, frost limits, pods for the animals later. From its own calibration
file: how fast it closes on that height (fitted so a 20-year algarrobo is
still small, as the sources say), water demand, health rules. From the look:
the `young` model until the tree reaches 60 % of its own adult height (about
5 m), then `adult`, then `old` past 70 % of its lifespan (about 140 years); pods shown from December to February.
