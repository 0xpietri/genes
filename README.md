# genes

Species of the pietri.dev world: real biology and painted 3D models.

genes is the catalog of living things for [pietri.dev](https://pietri.dev)'s little world
over Unquillo, Córdoba, and for anything else that wants them. Each species has a sheet of
real facts with their sources (how tall it grows, when it flowers, how much frost it takes),
a look made by a procedural generator so it resembles the real one (3D models for every
stage of its life, from seedling to fallen trunk), the reference photos it was checked
against, and a page in a browser viewer. It starts with the trees and grasses of the Chaco
Serrano and is built to hold animals too.

genes stores no users and computes nothing per request: it publishes files that never change
once released. What happens to a plant over time (growing, flowering this year, dying) is
pietri.dev's simulator; genes only says what the species is.

Status: phase 2. The first species is the algarrobo blanco (*Neltuma alba*); the plant
generator runs Blender headless from Python.

## Run it

```
uv sync
uv run genes serve
```

Then open <http://127.0.0.1:8810/species/neltuma-alba>. `uv run genes validate` checks every
species and `uv run pytest` runs the tests.

To add a species, follow [`docs/HOW_TO_ADD_A_SPECIES.md`](docs/HOW_TO_ADD_A_SPECIES.md).

- Specification: [`docs/spec/GENES_SPEC_v0.1.md`](docs/spec/GENES_SPEC_v0.1.md)
- Phase reports: [`docs/reports/`](docs/reports/)
- Rules for AI agents working here: [`CLAUDE.md`](CLAUDE.md)

## Licence

Code: MIT ([`LICENSE`](LICENSE)). Species sheets and looks: CC BY 4.0. Reference photos keep
the licence and attribution listed next to each one.
