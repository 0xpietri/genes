"""Contact sheets: the models beside the reference photos (spec §7.1).

`genes contact-sheet <id>` builds the site into a temporary folder, serves it,
renders every model with the viewer's own three.js (render.html) in a headless
Chromium, and composes `looks/<n>/sheet.png`:

1. Each reference photo that has a `tree_box`, with the best-matching adult
   silhouette laid over it (red), and the overlap score: intersection over
   union of the model's silhouette and the photo's tree (non-sky pixels in the
   box). 1.0 would be a perfect match; above about 0.6 the shapes agree.
2. The adult variants in summer, in the barest month of the leaf calendar (a deciduous
   tree's bare net of twigs) and in flower, painted, and close to the crown's edge in
   fruit and in flower.
3. The adult and the old tree from above (shade, and the crown even on every side) and
   from below, looking up into the crown (the dark crooked limbs).
4. Every stage of variant a at one scale (the same metres per pixel), each beside a
   1.75 m person; then each stage fitted to its picture, to see the small ones.

Needs the `dev` group (Pillow, Playwright). The scores are printed too, so an
agent can iterate without looking at the picture.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from PIL import Image, ImageDraw, ImageFont

from genes import catalog, glb, jsonio, serve
from genes.species import Species, discover, variant_letters

STAGES = ["seedling", "sapling", "young", "adult", "old", "dead_standing", "fallen"]
VIEWS = ["side", "front", "back", "left"]
SIZE = 480
MASK = 120  # side of the square the overlap is measured on
CHROMIUM_FALLBACK = "/opt/pw-browsers/chromium"


@dataclass(frozen=True)
class Shot:
    model: str  # file name in the look folder
    view: str = "side"
    mode: str = "painted"
    month: int = 1
    person: bool = False
    frame: float = 0.0  # metres; 0 fits the model


@dataclass
class Match:
    photo_id: str
    model: str
    view: str
    score: float
    overlay: Image.Image


@contextmanager
def _site(roots: list[Path]) -> Iterator[str]:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="genes-sheet-") as tmp:
        out = Path(tmp)
        catalog.build(roots, out)
        srv = serve.make_server(out, port=0)
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{srv.server_address[1]}"
        finally:
            srv.shutdown()
            srv.server_close()


@contextmanager
def browser() -> Iterator[Any]:
    from playwright.sync_api import Error, sync_playwright

    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Error:
            b = p.chromium.launch(executable_path=CHROMIUM_FALLBACK)
        try:
            yield b
        finally:
            b.close()


def render(
    page: Any, base: str, sp: Species, look: int, shot: Shot, size: int = SIZE
) -> Image.Image:
    sheet = sp.latest_sheet
    query = {
        "model": f"/v1/species/{sp.id}/looks/{look}/{shot.model}",
        "view": shot.view,
        "mode": shot.mode,
        "month": shot.month,
        "w": size,
        "h": size,
    }
    if shot.person:
        query["person"] = 1
    if shot.frame:
        query["frame"] = round(shot.frame, 2)
    if sheet is not None:
        query["sheet"] = f"/v1/species/{sp.id}/sheets/{sheet.number}.json"
    query["look"] = f"/v1/species/{sp.id}/looks/{look}/look.json"
    page.goto(f"{base}/render.html?{urlencode(query)}")
    page.wait_for_selector("body[data-ready], body[data-error]", state="attached")
    error = page.evaluate("document.body.dataset.error || ''")
    if error:
        raise RuntimeError(f"{shot.model}: {error}")
    return Image.open(BytesIO(page.locator("canvas").screenshot())).convert("RGB")


def _bbox(mask: Image.Image) -> tuple[int, int, int, int] | None:
    return mask.getbbox()


def model_mask(img: Image.Image) -> Image.Image:
    """Black silhouette on white → 1-bit mask of the model."""
    return img.convert("L").point(lambda v: 255 if v < 128 else 0).convert("1")


def photo_mask(photo: Image.Image) -> Image.Image:
    """The tree in a photo: what is not sky. Sky is bright and low in saturation (clouds,
    haze) or blue; good enough for photos against the sky, which is what tree_box is for."""
    hsv = photo.convert("HSV")
    out = Image.new("1", photo.size)
    src = hsv.load()
    dst = out.load()
    assert src is not None and dst is not None
    w, h = photo.size
    for y in range(h):
        for x in range(w):
            hue, sat, val = src[x, y]  # type: ignore[misc]
            sky = (val > 170 and sat < 60) or (120 <= hue <= 175 and sat > 35 and val > 120)
            dst[x, y] = 0 if sky else 255
    return out


def _fit(mask: Image.Image, size: tuple[int, int]) -> Image.Image:
    """The model's silhouette at the box's height (one scale, so the crown keeps its
    proportions), centred, standing on the box's bottom edge."""
    out = Image.new("1", size)
    box = _bbox(mask)
    if box is None:
        return out
    crop = mask.crop(box)
    scale = size[1] / crop.height
    w = max(1, round(crop.width * scale))
    scaled = crop.resize((w, size[1]), Image.Resampling.NEAREST)
    out.paste(scaled, ((size[0] - w) // 2, 0))
    return out


def overlap(a: Image.Image, b: Image.Image) -> float:
    pa, pb = a.load(), b.load()
    assert pa is not None and pb is not None
    inter = union = 0
    w, h = a.size
    for y in range(h):
        for x in range(w):
            ia, ib = bool(pa[x, y]), bool(pb[x, y])
            inter += ia and ib
            union += ia or ib
    return inter / union if union else 0.0


def match_photo(
    photo: Image.Image, box: list[float], silhouettes: dict[tuple[str, str], Image.Image]
) -> tuple[str, str, float, Image.Image]:
    """The adult silhouette that best covers the tree in the photo, and an overlay picture."""
    w, h = photo.size
    left, top = int(box[0] * w), int(box[1] * h)
    right, bottom = int(box[2] * w), int(box[3] * h)
    crop = photo.crop((left, top, right, bottom))
    small = crop.resize((MASK, MASK))
    tree = photo_mask(small)
    best: tuple[str, str, float] = ("", "", -1.0)
    for (model, view), sil in silhouettes.items():
        score = overlap(tree, _fit(model_mask(sil), (MASK, MASK)))
        if score > best[2]:
            best = (model, view, score)
    model, view, score = best
    overlay = photo.copy()
    sil = _fit(model_mask(silhouettes[(model, view)]), (right - left, bottom - top))
    red = Image.new("RGB", sil.size, (220, 30, 30))
    region = overlay.crop((left, top, right, bottom))
    region = Image.composite(Image.blend(region, red, 0.55), region, sil)
    overlay.paste(region, (left, top))
    ImageDraw.Draw(overlay).rectangle((left, top, right, bottom), outline=(255, 255, 0), width=2)
    return model, view, score, overlay


def _label(img: Image.Image, text: str) -> Image.Image:
    out = img.copy()
    d = ImageDraw.Draw(out)
    font = ImageFont.load_default(size=16)
    d.rectangle((0, 0, out.width, 22), fill=(255, 255, 255))
    d.text((6, 3), text, fill=(0, 0, 0), font=font)
    return out


def _grid(rows: list[list[Image.Image]], side: int, width: int) -> Image.Image:
    """Rows of pictures; each row splits the sheet's width evenly (photo rows are wider)."""
    sheet = Image.new("RGB", (width, len(rows) * side), (255, 255, 255))
    for y, row in enumerate(rows):
        cell = width // max(len(row), 7 if len(row) > 4 else len(row))
        cell = min(cell, width // len(row))
        for x, img in enumerate(row):
            t = img.copy()
            t.thumbnail((cell - 8, side - 8))
            sheet.paste(t, (x * cell + (cell - t.width) // 2, y * side + (side - t.height) // 2))
    return sheet


def contact_sheet(
    roots: list[Path], species_id: str, out: Path | None = None
) -> tuple[Path, list[Match]]:
    found = [s for s in discover(roots) if s.id == species_id]
    if not found:
        raise SystemExit(f"no species {species_id}")
    sp = found[0]
    lv = sp.latest_look
    if lv is None or lv.data is None:
        raise SystemExit(f"{species_id} has no look")
    look: dict[str, Any] = lv.data
    look_n = lv.number
    look_dir = lv.path.parent
    refs = sp.refs.data if sp.refs and sp.refs.data else {"photos": []}
    stages = [s for s in STAGES if s in look["stages"]]
    adult = "adult" if "adult" in stages else stages[-1]
    adult_variants = variant_letters(int(look["stages"][adult].get("variants", 1)))
    fruit_month, _, flower_month = _months(sp)
    bare_month = barest_month(sp.latest_sheet.data if sp.latest_sheet else None)
    old = "old" if "old" in stages else adult

    rows: list[list[Image.Image]] = []
    matches: list[Match] = []
    # One frame for the stage row, so the stages show their real sizes beside a person.
    frame = 2.0 + 1.15 * max(_extent(look_dir / f"{s}-a.lod0.glb") for s in stages)
    with _site(roots) as base, browser() as b:
        page = b.new_page(viewport={"width": SIZE, "height": SIZE})
        silhouettes = {
            (f"{adult}-{v}.lod0.glb", view): render(
                page,
                base,
                sp,
                look_n,
                Shot(f"{adult}-{v}.lod0.glb", view, "silhouette", fruit_month),
            )
            for v in adult_variants
            for view in VIEWS
        }
        photo_row: list[Image.Image] = []
        for photo in refs.get("photos", []):
            box = photo.get("tree_box")
            if not box or not photo.get("file"):
                continue
            img = Image.open(sp.folder / "references" / photo["file"]).convert("RGB")
            model, view, score, overlay = match_photo(img, box, silhouettes)
            matches.append(Match(photo["id"], model, view, score, overlay))
            photo_row.append(
                _label(overlay, f"{photo['id']}: {model.split('.')[0]} {view} {score:.2f}")
            )
        for i in range(0, len(photo_row), 3):
            rows.append(photo_row[i : i + 3])
        for month, name in (
            (fruit_month, "summer"),
            (bare_month, f"barest, month {bare_month}"),
            (flower_month, "flowers"),
        ):
            rows.append(
                [
                    _label(
                        render(
                            page,
                            base,
                            sp,
                            look_n,
                            Shot(f"{adult}-{v}.lod0.glb", "side", "painted", month),
                        ),
                        f"{adult}-{v} {name}",
                    )
                    for v in adult_variants
                ]
                + [
                    _label(
                        render(
                            page,
                            base,
                            sp,
                            look_n,
                            Shot(f"{adult}-a.lod1.glb", "side", "painted", month),
                        ),
                        f"{adult}-a lod1 {name}",
                    )
                ]
            )
        rows.append(
            [
                _label(
                    render(
                        page,
                        base,
                        sp,
                        look_n,
                        Shot(f"{adult}-{v}.lod0.glb", "close", "painted", month),
                    ),
                    f"{adult}-{v} close, {name}",
                )
                for v in adult_variants[:2]
                for month, name in ((fruit_month, "fruit"), (flower_month, "flowers"))
            ]
        )
        rows.append(
            [
                _label(
                    render(page, base, sp, look_n, Shot(f"{s}-a.lod0.glb", view, "painted", m)),
                    f"{s}-a {view}" + (f", month {m}" if m != fruit_month else ""),
                )
                for s in dict.fromkeys((adult, old))
                for view, m in (
                    ("above", fruit_month),
                    ("below", fruit_month),
                    ("above", bare_month),
                )
            ]
        )
        for scale, label in ((frame, "{}"), (0.0, "{} (fitted, no person)")):
            rows.append(
                [
                    _label(
                        render(
                            page,
                            base,
                            sp,
                            look_n,
                            Shot(
                                f"{s}-a.lod0.glb", "side", "painted", fruit_month, scale > 0, scale
                            ),
                        ),
                        label.format(s),
                    )
                    for s in stages
                ]
            )
    sheet = _grid(rows, SIZE, SIZE * 7)
    target = out or look_dir / "sheet.png"
    save_sheet(sheet, target)
    return target, matches


def save_sheet(sheet: Image.Image, target: Path) -> None:
    """Two thirds of the size in 256 colours: the sheet is committed with every look."""
    small = sheet.resize((sheet.width * 2 // 3, sheet.height * 2 // 3), Image.Resampling.LANCZOS)
    small.quantize(256, method=Image.Quantize.FASTOCTREE).save(target, optimize=True)


def _extent(model: Path) -> float:
    info = glb.inspect(model)
    lo, hi = info.bbox_min, info.bbox_max
    return max(hi[1], 2 * max(abs(lo[0]), hi[0]), 2 * max(abs(lo[2]), hi[2]))


def _months(sp: Species) -> tuple[int, int, int]:
    """A month with fruit, one in winter, one in flower, from the sheet's phenology."""
    sheet = sp.latest_sheet.data if sp.latest_sheet and sp.latest_sheet.data else {}
    phen = sheet.get("plant", {}).get("phenology", {})

    def middle(phase: str, default: int) -> int:
        months = phen.get(phase, {}).get("months")
        return int(months[len(months) // 2]) if months else default

    return middle("fruiting", 1), middle("leaf_fall", 7), middle("flowering", 10)


def barest_month(sheet: dict[str, Any] | None) -> int:
    """The month the crown is barest by the leaf calendar: the middle of the longest run
    of months with no leaf tone, else of months with only dry leaves, else mid leaf fall."""
    phen = (sheet or {}).get("plant", {}).get("phenology", {})
    tones = phen.get("leaf_tones") or []
    on = {m: {t["tone"] for t in tones if m in t.get("months", [])} for m in range(1, 13)}
    tests: list[Callable[[int], bool]] = [lambda m: not on[m], lambda m: on[m] == {"dry"}]
    for bare in tests:
        runs: list[list[int]] = []
        for k in range(24):  # twice round the year, so a run over New Year stays whole
            m = k % 12 + 1
            if tones and bare(m):
                if runs and runs[-1][-1] % 12 + 1 == m and len(runs[-1]) < 12:
                    runs[-1].append(m)
                else:
                    runs.append([m])
        if runs:
            best = max(runs, key=len)
            return best[len(best) // 2]
    months = phen.get("leaf_fall", {}).get("months")
    return int(months[len(months) // 2]) if months else 7


def scores_json(matches: list[Match]) -> str:
    return jsonio.dumps(
        [
            {"photo": m.photo_id, "model": m.model, "view": m.view, "score": round(m.score, 3)}
            for m in matches
        ]
    )
