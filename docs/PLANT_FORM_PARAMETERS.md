# Plant form parameters (generator `plant@1`)

Every parameter a look's `form` can set, written from `schemas/plant-form.v1.json` by `uv run genes form-reference`. Do not edit by hand.

A look writes only what makes its species different; everything else takes the default. Ranges: their middle is what is drawn, except `trunk.tortuosity`, `trunk.twist`, `trunk.gnarl` and `trunk.fluting`, which each variant draws from its range (variants differ only in crookedness). How to choose them from photos: `docs/HOW_TO_ADD_A_SPECIES.md`.

## `crown`

The crown's outline: how wide, how high it starts, flat or round, airy or full.

| Parameter | Value | Default | What it does |
| --- | --- | --- | --- |
| `crown.envelope` | `umbrella` \| `globose` \| `columnar` \| `conical` \| `weeping` \| `irregular` | "globose" | Shape the branches are pruned to. |
| `crown.width_to_height` | number or [min, max] | [0.8, 1.0] | Crown width divided by tree height. From the sheet: crown_width_m / adult_height_m. Above 1 = wider than tall. |
| `crown.base` | 0–1, or [min, max] | [0.3, 0.4] | Height where the crown starts, as a fraction of the tree's height. |
| `crown.widest` | 0–1, or [min, max] |  | Where the crown is widest, as a fraction of its depth from its base. Default from the envelope: umbrella 0.7, globose 0.5, conical 0.05, columnar 0.5, weeping 0.6, irregular 0.5. |
| `crown.flat_top` | 0–1, or [min, max] | 0 | 0 = rounded top; 1 = cut flat, the crown keeps its width up to the top. |
| `crown.irregular` | 0–1, or [min, max] | 0.15 | Lobes and gaps around the crown's outline. |
| `crown.openness` | 0–1, or [min, max] | 0.3 | How much sky shows through the crown: 0 = a dense ball, 0.6 = airy, branches visible. |
| `crown.clump_size_m` | number or [min, max] | [0.5, 0.8] | Size of one painted foliage clump on an adult. Smaller stages scale it down. |
| `crown.fill_top` | 0–1 | 0.9 | How fully the top of the crown is covered: where no foliage reaches the crown's upper surface, a thin crooked branch rises from the nearest limb with leaves at its tips. 0 = leave gaps; 1 = every gap filled. Trees always have leaves on top, so keep it high. |
| `crown.clump_spacing` | number | 0.9 | Distance between clumps along a twig, in clump sizes. |

## `trunk`

The trunk and the leaders above the fork: count, fork, lean, crookedness, girth.

| Parameter | Value | Default | What it does |
| --- | --- | --- | --- |
| `trunk.count` | integer or [min, max] | 1 | Leaders above the fork. 1 = one main axis that runs to the top (a pine, a young tree); 2–4 = the trunk splits into that many limbs (algarrobo, most open-grown broadleaves). |
| `trunk.split_height` | 0–1, or [min, max] | 0.45 | Height of the fork as a fraction of the tree's height. Low (0.1–0.3) = short trunk forked low; 0 = several stems from the ground. With count 1 it is where the main axis starts carrying the crown. |
| `trunk.fork_angle_deg` | number or [min, max] | [20, 35] | Angle of each leader from the trunk's axis at the fork. Wide (40–60) gives a spreading, umbrella crown; narrow (10–25) a vase or an upright crown. |
| `trunk.leader_reach` | 0–1, or [min, max] | [0.8, 0.95] | How far each leader runs towards the crown's edge, as a fraction of the distance to it. |
| `trunk.leader_curve` | -1–1, or [min, max] | 0.1 | Bend of the leaders along their length: positive turns them up (upright crowns), negative arches them outwards and down (algarrobo, spreading trees). |
| `trunk.lean_deg` | number or [min, max] | [0, 4] | Lean of the whole trunk from vertical. Each variant leans its own way. |
| `trunk.twist` | 0–1, or [min, max] | 0.2 | How much the trunk and the leaders wander and twist instead of running straight. |
| `trunk.tortuosity` | 0–1, or [min, max] | 0.15 | Big slow S-bends of the trunk and the leaders (and, at 60 %, of the level-1 limbs), snaking in three dimensions: 0 = straight, 0.5 = clearly crooked, 1 = a contorted old algarrobo. Not the small zig-zag of twist. |
| `trunk.bends` | number or [min, max] | [0.8, 1.6] | How many bends along the trunk and each leader (waves along its length): 1 = one long S, 3 = a restless trunk. |
| `trunk.bend_style` | `smooth` \| `elbows` | "smooth" | smooth = slow S-curves that turn in space (algarrobo); elbows = straight runs broken by sharp kinks (tala, espinillo). |
| `trunk.crooked_to_tip` | 0–1 | 0 | How far up the bends reach: 0 = the trunk and stems are crooked low down and calm towards the crown; 1 = crooked all along, from the foot to every tip, with hardly a straight part (algarrobo). Also gives more bends to long limbs. |
| `trunk.kinks` | 0–1, or [min, max] | 0 | Sympodial growth, as in algarrobos, talas and quebrachos: the trunk, the leaders and the limbs grow in runs of uneven length, and at each break the course itself turns (by trunk.kink_angle_deg) in any direction, so the turns add up instead of swinging back to a straight average line. 0 = off (the slow bends of tortuosity only); 0.5 = about two breaks along each branch; 1 = about four. Each variant draws its own. Level 1 limbs follow it at 80 %, finer levels at 60 %, unless a level sets its own kinks. |
| `trunk.kink_angle_deg` | number or [min, max] | [40, 90] | How far the course turns at each sympodial break, in degrees (with trunk.kinks above 0). |
| `trunk.light_bias` | 0–1 | 0.35 | After each sympodial break the new run leans back towards the light (up and out from the crown's axis) by this share of the turn, so crooked limbs stay inside the crown and never fold back over the trunk. |
| `trunk.knots` | 0–1 | 0 | Swellings of the wood where it turns or forks: at sympodial breaks and where a branch leaves its parent the bark bulges by up to a third of its radius, instead of tapering smoothly. 0 = smooth taper. |
| `trunk.fluting` | 0–1, or [min, max] | 0 | Ribs and grooves running up the trunk and the leaders in a slow spiral, as if several stems had fused (old algarrobos, quebrachos). 0 = round. |
| `trunk.gnarl` | 0–1, or [min, max] | 0.2 | Bumps, lobes and buttresses on the trunk's surface. |
| `trunk.radius_per_height` | number or [min, max] | [0.022, 0.03] | Trunk radius at 1.3 m divided by the tree's height. From the sheet: (trunk_dbh_m / 2) / adult_height_m. |
| `trunk.taper` | 0–1, or [min, max] | 0.6 | How fast the trunk and every branch thin towards the tip. |
| `trunk.flare` | 0–1, or [min, max] | 0.2 | Extra width at the foot of the trunk. |
| `trunk.bark.pattern` | `smooth` \| `fine_fissures` \| `deep_fissures` \| `plates` \| `peeling` | "fine_fissures" | The bark texture's pattern. |
| `trunk.bark.depth` | 0–1 | 0.5 | Contrast of the pattern. |
| `trunk.bark.tile_m` | number | 0.6 | Real size of one repeat of the bark texture. |

## `branching`

Levels of branches below the leaders (1 = main limbs, 2 = branches, 3 = twigs), one entry per level.

One entry per branching level below the leaders, from the thickest (1) to the twigs (3 at most). Each level grows on the one before.

| Parameter | Value | Default | What it does |
| --- | --- | --- | --- |
| `branching[].level` | integer |  |  |
| `branching[].count` | integer or [min, max] |  | Branches on a parent of typical length for its level (longer parents carry more). |
| `branching[].start` | [min, max] | [0.3, 1.0] | Part of the parent where branches grow, as fractions of its length from its base. |
| `branching[].angle_deg` | number or [min, max] | [35, 55] | Angle from the parent at the base of the branch. |
| `branching[].length` | number or [min, max] | [0.4, 0.6] | Length relative to the parent. Branches near the parent's tip are shorter; all are cut at the crown's envelope. |
| `branching[].curve` | -1–1, or [min, max] | 0.2 | Bend over the branch: positive turns up, negative turns away from up. |
| `branching[].droop` | 0–1, or [min, max] | 0.2 | Sag under its own weight, strongest at the tip. |
| `branching[].wander` | 0–1, or [min, max] | 0.3 | Random zig-zag. |
| `branching[].tortuosity` | 0–1, or [min, max] |  | Big bends of the branches of this level, like trunk.tortuosity. Default: 60 % of the trunk's for level 1, none for the others. |
| `branching[].bend_style` | `smooth` \| `elbows` |  | Default: the trunk's bend_style. Old algarrobos: smooth limbs, elbowed branches. |
| `branching[].kinks` | 0–1, or [min, max] |  | Sympodial breaks of the branches of this level, like trunk.kinks. Default: 80 % of the trunk's for level 1, 60 % for finer levels. |
| `branching[].radius_ratio` | number or [min, max] | [0.5, 0.7] | Base radius relative to the parent's radius where it grows. |
| `branching[].roll` | `spiral` \| `opposite` \| `alternate` | "spiral" | How branches turn around the parent. |

## `foliage`

The leaves: clumps of painted cards along the twigs.

| Parameter | Value | Default | What it does |
| --- | --- | --- | --- |
| `foliage.leaf_type` | `bipinnate` \| `pinnate` \| `broad` \| `needle` \| `scale` | "broad" | Sets the painted clump texture: bipinnate is feathery and airy, broad is a dense mass. |
| `foliage.leaf_size_cm` | number or [min, max] | [4, 8] | Real leaf length; the texture's marks scale with it. |
| `foliage.cards_per_clump` | integer | 3 | Crossed cards in one clump (two triangles each). |
| `foliage.density` | 0–1 | 0.6 | How full each clump's texture is: 0 = a few sprays you see through, 1 = a solid mass. Airy trees (algarrobo, espinillo) 0.2–0.3. |
| `foliage.twigs` | 0–1 | 0 | Dark crooked twigs painted inside each clump, under the leaves: the fine branch net that shows through airy foliage. 0 = none, 1 = a dense net (old algarrobos). |
| `foliage.leafy_from` | 0–1 | 0.35 | Clumps sit on twigs from this fraction of their length to the tip. |
| `foliage.carry_share` | 0–1 | 0.3 | Share of the bark's triangles kept for the fine twigs that carry the leaves out to the crown's edge (lod0). Wide airy crowns whose build notes say hundreds of clumps 'moved onto their wood' need more: 0.4–0.5. |

## `tips`

The fine crooked twiglets at every branch end (what shows on a bare crown).

Twiglets: the fine crooked twigs that bristle from the end of every branch, so a bare crown reads as a net and not as cut sticks (old algarrobos in winter).

| Parameter | Value | Default | What it does |
| --- | --- | --- | --- |
| `tips.twiglets` | integer or [min, max] | 0 | Twiglets at the end of each drawn branch. 0 = none. |
| `tips.length` | number or [min, max] | [0.03, 0.06] | Length of a twiglet, as a fraction of the tree's height. |
| `tips.crookedness` | 0–1 | 0.7 | 0 = straight twiglets; 1 = twisting in every direction. |
| `tips.forks` | 0–1 | 0.5 | Chance that a twiglet forks once more halfway. |
| `tips.share` | 0–1 | 0.3 | Share of the bark's triangles kept for twiglets; the highest branch ends get them first. |
| `tips.stages` | list of `seedling` \| `sapling` \| `young` \| `adult` \| `old` \| `dead_standing` \| `fallen` | ["adult", "old", "dead_standing"] | Stages that have twiglets. |

## `flowers`

Flowers, shown in the sheet's flowering months.

| Parameter | Value | Default | What it does |
| --- | --- | --- | --- |
| `flowers.form` | `none` \| `spike` \| `ball` \| `bell` \| `single` \| `panicle` | "none" |  |
| `flowers.length_cm` | number or [min, max] | [2, 4] | Real length of one flower or inflorescence. |
| `flowers.where` | `tips` \| `axils` \| `along` | "axils" |  |
| `flowers.cover` | 0–1 | 0.3 | Share of the clumps that carry flowers at peak. |
| `flowers.per_clump` | integer or [min, max] | [1, 3] |  |
| `flowers.show_scale` | number | 1 | Painted exaggeration: the real size times this, so the part still reads from a few metres away (a recognisable trait). 1 = real size. |

## `fruit`

Fruit, shown in the sheet's fruiting months.

| Parameter | Value | Default | What it does |
| --- | --- | --- | --- |
| `fruit.form` | `none` \| `pod_straight` \| `pod_curved` \| `pod_coiled` \| `pod_beaded` \| `berry` \| `drupe` \| `samara` \| `capsule` | "none" | pod_beaded = a moniliform pod pinched between its seeds, like a string of beads (tusca, some algarrobos). |
| `fruit.length_cm` | number or [min, max] | [1, 2] |  |
| `fruit.width_cm` | number or [min, max] | [1, 2] | Pods and samaras: width; round fruit: ignored (length is the diameter). |
| `fruit.beads` | integer or [min, max] | [6, 10] | pod_beaded: how many seeds (beads) along one pod. |
| `fruit.constriction` | 0–1 | 0.45 | pod_beaded: how deep the pinch between beads is, as a share of the width (0 = a smooth pod, 0.8 = almost separate beads). |
| `fruit.accent` | `none` \| `spots` \| `streaks` \| `tip` \| `blush` | "none" | Where the palette's fruit.accent colour shows on each fruit, painted into its texture: spots (mottled), streaks (lengthwise lines, like the violet-streaked pods of the algarrobo negro), tip (the end darkens), blush (one cheek, like a ripe berry). none = flat fruit.lit. |
| `fruit.hanging` | boolean | true | Pods and bunches hang down from the twig. |
| `fruit.per_bunch` | integer or [min, max] | [1, 3] |  |
| `fruit.cover` | 0–1 | 0.3 | Share of the clumps that carry fruit at peak. |
| `fruit.show_scale` | number | 1 | Painted exaggeration: the real size times this, so the part still reads from a few metres away (a recognisable trait). 1 = real size. |

## `thorns`

Thorns on twigs, branches or trunk.

| Parameter | Value | Default | What it does |
| --- | --- | --- | --- |
| `thorns.kind` | `none` \| `short_paired` \| `long_paired` \| `single` | "none" |  |
| `thorns.length_cm` | number or [min, max] | [1, 2] |  |
| `thorns.where` | `young_twigs` \| `branches` \| `trunk` \| `all` | "young_twigs" |  |
| `thorns.spacing_m` | number | 0.3 | Distance between thorn nodes along a branch. |

## `old`

What changes when the tree is old.

| Parameter | Value | Default | What it does |
| --- | --- | --- | --- |
| `old.broken_limbs` | integer or [min, max] | [0, 1] | Main limbs broken off, leaving a stub. |
| `old.extra_lean_deg` | number or [min, max] | [0, 5] |  |
| `old.trunk_split` | 0–1 | 0 | How far an old tree's trunk has opened: 0 = one whole trunk, 1 = it splits from near the ground into stems that rise side by side with a crack between them, then part (old algarrobos). Also dead and fallen trees. |
| `old.limb_sag` | 0–1 | 0 | How far down the sagging low limbs of an old (or dead standing) tree reach: 0 = they stay up in the crown, 0.5 = they arch out and sag halfway to the ground, 1 = they reach the ground, lie along it and rise again (old algarrobos). |
| `old.sagging_limbs` | 0–1 | 0.35 | Share of the low main limbs that sag as limb_sag says. |
| `old.crown_thinning` | 0–1 | 0.25 | Share of the clumps an old tree has lost. |

## `dead`

What changes when the tree is dead.

| Parameter | Value | Default | What it does |
| --- | --- | --- | --- |
| `dead.lost_twigs` | 0–1 | 0.7 | Share of the thinnest branches gone from a dead tree. |
| `dead.broken_top` | 0–1, or [min, max] | [0.6, 0.9] | Leaders of a dead tree keep this fraction of their length. |

## `stages`

Overrides for one stage.

Changes for one stage, written like the form itself (only what changes; a `branching` list replaces the whole list), plus `levels`: how many branching levels the stage grows. Defaults: seedling 0 levels, sapling 1, young 2, no flowers or fruit before young.
