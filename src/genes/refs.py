"""Reference photos from iNaturalist (spec §9): find candidates, then add the chosen ones.

    genes refs candidates <id> --taxon <inaturalist taxon id>
        Research-grade photos under a shareable licence (CC0, CC BY, CC BY-SA) go into
        .work/<id>/candidates/ (git-ignored), numbered, with contact grids grid-1.jpg ...
        to look at, and the month histograms of flowers and fruit for the sheet.

    genes refs add <id> <number> --shows whole,summer --angle side [--box l,t,r,b]
        Stores candidate <number> at most 1280 px in references/, with its author,
        licence and link, and appends it to references/refs.json.

Network only here, never in tests: the parsing is tested on recorded answers.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from genes import jsonio
from genes.paths import REPO_ROOT

API = "https://api.inaturalist.org/v1"
SHAREABLE = ("cc0", "cc-by", "cc-by-sa")
WORK = REPO_ROOT / ".work"
MAX_SIDE = 1280
USER_AGENT = "genes-species-tool/0.1"
PHENOLOGY = {"flowers": 13, "fruit": 14, "flower_buds": 15}

Fetch = Callable[[str], bytes]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as res:
        data: bytes = res.read()
        return data


@dataclass
class Candidate:
    number: int
    observation: int
    photo: int
    licence: str
    attribution: str
    medium: str
    large: str
    observed_on: str
    place: str
    user: str

    @property
    def page(self) -> str:
        """The photo's own page on iNaturalist (it links to its observation)."""
        return f"https://www.inaturalist.org/photos/{self.photo}"


def parse_observations(answer: dict[str, Any], start: int = 0) -> list[Candidate]:
    """Shareable photos of research-grade observations, numbered from `start`."""
    out: list[Candidate] = []
    for obs in answer.get("results", []):
        for photo in obs.get("photos", []):
            lic = (photo.get("license_code") or "").lower()
            if lic not in SHAREABLE:
                continue
            square = photo.get("url") or ""
            out.append(
                Candidate(
                    number=start + len(out),
                    observation=int(obs["id"]),
                    photo=int(photo["id"]),
                    licence=lic,
                    attribution=photo.get("attribution", ""),
                    medium=square.replace("/square.", "/medium."),
                    large=square.replace("/square.", "/large."),
                    observed_on=obs.get("observed_on") or "",
                    place=obs.get("place_guess") or "",
                    user=(obs.get("user") or {}).get("login", ""),
                )
            )
    return out


def parse_histogram(answer: dict[str, Any]) -> dict[int, int]:
    months = answer.get("results", {}).get("month_of_year", {})
    return {int(k): int(v) for k, v in months.items()}


def phenology_summary(histograms: dict[str, dict[int, int]]) -> list[str]:
    """One line per phase: months with annotated observations, peak first."""
    lines = []
    for phase, months in histograms.items():
        seen = {m: n for m, n in sorted(months.items()) if n}
        if not seen:
            lines.append(f"{phase}: no annotations")
            continue
        listing = ", ".join(f"{m} ({n})" for m, n in seen.items())
        lines.append(f"{phase}: months {listing}")
    return lines


def _grid(images: list[tuple[int, Image.Image]], side: int = 220, cols: int = 8) -> Image.Image:
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * side, rows * side), (255, 255, 255))
    font = ImageFont.load_default(size=18)
    for k, (number, img) in enumerate(images):
        t = img.copy()
        t.thumbnail((side - 6, side - 6))
        x, y = (k % cols) * side, (k // cols) * side
        sheet.paste(t, (x + 3, y + 3))
        d = ImageDraw.Draw(sheet)
        d.rectangle((x + 3, y + 3, x + 46, y + 25), fill=(255, 255, 255))
        d.text((x + 6, y + 4), str(number), fill=(200, 0, 0), font=font)
    return sheet


def candidates(species_id: str, taxon: int, pages: int = 2, get: Fetch = fetch) -> Path:
    folder = WORK / species_id / "candidates"
    folder.mkdir(parents=True, exist_ok=True)
    found: list[Candidate] = []
    for page in range(1, pages + 1):
        query = urllib.parse.urlencode(
            {
                "taxon_id": taxon,
                "quality_grade": "research",
                "photos": "true",
                "photo_license": ",".join(SHAREABLE),
                "per_page": 200,
                "page": page,
                "order_by": "votes",
            }
        )
        answer = json.loads(get(f"{API}/observations?{query}"))
        found += parse_observations(answer, len(found))
        if page * 200 >= int(answer.get("total_results", 0)):
            break
    (folder / "candidates.json").write_text(
        jsonio.dumps([asdict(c) for c in found]), encoding="utf-8"
    )
    images: list[tuple[int, Image.Image]] = []
    for c in found:
        path = folder / f"{c.number:03d}.jpg"
        if not path.exists():
            path.write_bytes(get(c.medium))
        images.append((c.number, Image.open(path).convert("RGB")))
    for k in range(0, len(images), 48):
        _grid(images[k : k + 48]).save(folder / f"grid-{k // 48 + 1}.jpg", quality=85)
    histograms = {}
    for phase, value in PHENOLOGY.items():
        query = urllib.parse.urlencode(
            {
                "taxon_id": taxon,
                "quality_grade": "research",
                "date_field": "observed",
                "interval": "month_of_year",
                "term_id": 12,
                "term_value_id": value,
            }
        )
        histograms[phase] = parse_histogram(
            json.loads(get(f"{API}/observations/histogram?{query}"))
        )
    (folder / "phenology.json").write_text(jsonio.dumps(histograms), encoding="utf-8")
    for line in phenology_summary(histograms):
        print(line)
    print(f"{len(found)} shareable photos in {folder}; look at grid-*.jpg")
    return folder


def resized(data: bytes) -> bytes:
    img = Image.open(BytesIO(data)).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = BytesIO()
    img.save(out, "JPEG", quality=85, optimize=True)
    return out.getvalue()


def add(
    species_dir: Path,
    number: int,
    shows: list[str],
    angle: str,
    box: list[float] | None = None,
    used_for: list[str] | None = None,
    get: Fetch = fetch,
    work: Path | None = None,
) -> dict[str, Any]:
    species_id = species_dir.name
    folder = (work or WORK) / species_id / "candidates"
    listing = json.loads((folder / "candidates.json").read_text(encoding="utf-8"))
    c = Candidate(**next(x for x in listing if x["number"] == number))
    refs_path = species_dir / "references" / "refs.json"
    refs_path.parent.mkdir(parents=True, exist_ok=True)
    refs: dict[str, Any] = (
        jsonio.load(refs_path)
        if refs_path.exists()
        else {
            "$schema": "../../../../schemas/refs.v1.json",
            "format": "genes.refs.v1",
            "id": species_id,
            "photos": [],
        }
    )
    if any(p.get("url") == c.page and p.get("file") for p in refs["photos"]):
        raise SystemExit(f"candidate {number} is already in refs.json")  # same photo
    ref_id = f"r{len(refs['photos']) + 1:02d}"
    (refs_path.parent / f"{ref_id}.jpg").write_bytes(resized(get(c.large)))
    entry: dict[str, Any] = {
        "id": ref_id,
        "url": c.page,
        "author": c.attribution or c.user,
        "licence": c.licence,
        "source": "inaturalist",
        "shows": shows,
        "angle": angle,
        "file": f"{ref_id}.jpg",
    }
    if c.observed_on:
        entry["observed_on"] = c.observed_on
    if c.place:
        entry["place"] = c.place
    if used_for:
        entry["used_for"] = used_for
    if box:
        entry["tree_box"] = box
    refs["photos"].append(entry)
    refs_path.write_text(jsonio.dumps(refs), encoding="utf-8")
    return entry
