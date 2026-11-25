"""Reference photos from iNaturalist (spec §9): find candidates, then add the chosen ones.

    genes refs candidates <id> --taxon <inaturalist taxon id>
        Research-grade photos under a shareable licence (CC0, CC BY, CC BY-SA) go into
        .work/<id>/candidates/ (git-ignored), numbered, with contact grids grid-1.jpg ...
        to look at, and the month histograms of flowers and fruit for the sheet.

    genes refs add <id> <number> --shows whole,summer --angle side [--box l,t,r,b]
        Stores candidate <number> at most 1280 px in references/, with its author,
        licence and link, and appends it to references/refs.json, plus a small WebP copy
        in references/thumbs/ for the species page's photo grid.

    genes refs thumbs <id>
        Writes the missing thumbs for photos stored before thumbs existed.

    genes refs grid <id> <number or r-id> [--box l,t,r,b]
        The photo with a fine grid of 0.0–1.0 coordinates over it (and the box, if given,
        in yellow) in .work/<id>/, to read a tree box off without other tools.

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

from PIL import Image, ImageDraw, ImageFont, ImageOps

from genes import jsonio
from genes.paths import REPO_ROOT

API = "https://api.inaturalist.org/v1"
SHAREABLE = ("cc0", "cc-by", "cc-by-sa")
WORK = REPO_ROOT / ".work"
MAX_SIDE = 1280
# The page shows photos as 4:3 tiles at most 260 px wide, cropped from the middle (object-fit:
# cover): a thumb is that crop at 520 x 390, sharp on 2x screens. The full photo only loads in
# the lightbox.
THUMB_SIZE = (520, 390)
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


def thumb(data: bytes) -> bytes:
    """A small WebP of a stored photo: the middle 4:3 crop the page's tile shows."""
    img = Image.open(BytesIO(data)).convert("RGB")
    img = ImageOps.fit(img, THUMB_SIZE, Image.Resampling.LANCZOS)
    out = BytesIO()
    img.save(out, "WEBP", quality=72, method=6)
    return out.getvalue()


def thumb_path(refs_dir: Path, photo: dict[str, Any]) -> Path:
    return refs_dir / "thumbs" / f"{Path(photo['file']).stem}.webp"


def write_thumbs(species_dir: Path) -> list[Path]:
    """Writes the thumbs that are missing; returns the new files."""
    refs_dir = species_dir / "references"
    refs: dict[str, Any] = jsonio.load(refs_dir / "refs.json")
    made = []
    for photo in refs["photos"]:
        if "file" not in photo:
            continue
        out = thumb_path(refs_dir, photo)
        if out.exists():
            continue
        out.parent.mkdir(exist_ok=True)
        out.write_bytes(thumb((refs_dir / photo["file"]).read_bytes()))
        made.append(out)
    return made


def grid_picture(photo: Image.Image, box: list[float] | None = None) -> Image.Image:
    """`photo` with lines every 0.05 of its width and height (labelled every 0.1), the
    fractions `--box` takes; and `box` (left, top, right, bottom) drawn in yellow."""
    img = photo.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    w, h = img.size
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    font = ImageFont.load_default(size=max(11, w // 70))
    for k in range(1, 20):
        f = k / 20
        major = k % 2 == 0
        colour = (255, 255, 255, 200) if major else (255, 255, 255, 90)
        x, y = round(f * (w - 1)), round(f * (h - 1))
        d.line((x, 0, x, h), fill=colour, width=1)
        d.line((0, y, w, y), fill=colour, width=1)
        if major:
            text = f"{f:.1f}"
            for tx, ty in ((x + 2, 2), (2, y + 2)):
                d.text(
                    (tx, ty),
                    text,
                    fill=(255, 255, 255, 255),
                    font=font,
                    stroke_width=2,
                    stroke_fill=(0, 0, 0, 255),
                )
    if box:
        left, top, right, bottom = box
        d.rectangle(
            (left * (w - 1), top * (h - 1), right * (w - 1), bottom * (h - 1)),
            outline=(255, 230, 0, 255),
            width=3,
        )
    return Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")


def grid(
    species_dir: Path, which: str, box: list[float] | None = None, work: Path | None = None
) -> Path:
    """Write the grid picture for candidate number `which`, or stored photo `which` (r03)."""
    species_id = species_dir.name
    folder = (work or WORK) / species_id
    if which.startswith("r"):
        src = species_dir / "references" / f"{which}.jpg"
    else:
        src = folder / "candidates" / f"{int(which):03d}.jpg"
    if not src.exists():
        raise SystemExit(f"no photo {src}")
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"box-{which}.jpg"
    grid_picture(Image.open(src), box).save(out, quality=88)
    return out


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
    stored = resized(get(c.large))
    (refs_path.parent / f"{ref_id}.jpg").write_bytes(stored)
    (refs_path.parent / "thumbs").mkdir(exist_ok=True)
    (refs_path.parent / "thumbs" / f"{ref_id}.webp").write_bytes(thumb(stored))
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
