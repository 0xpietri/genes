"""The public catalog (genes.site): pages written at build time, readable without JavaScript,
for search engines and language models; the 3D, the simulator, the leaf and the map load in
a real browser without errors."""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path

import pytest

from genes import catalog, jsonio, serve, validate
from genes import site as genes_site
from genes.paths import REPO_ROOT, SPECIES_DIR
from tests.test_viewer import _browser

SITE_STATIC = REPO_ROOT / "site" / "static"


@pytest.fixture(scope="module")
def dist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("dist")
    catalog.build([SPECIES_DIR], out)
    return out


def _ld(html: str) -> list[dict]:  # type: ignore[type-arg]
    return [
        json.loads(m)
        for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    ]


def test_pages_have_no_inline_code_but_json_ld(dist: Path) -> None:
    for page in [dist / "index.html", *dist.glob("species/*/index.html")]:
        html = page.read_text(encoding="utf-8")
        assert not re.search(r"<style\b", html), page
        for tag in re.findall(r"<script\b[^>]*>", html):
            assert "src=" in tag or 'type="application/ld+json"' in tag, f"{page}: {tag}"
        assert not re.search(r"\son[a-z]+=", html), f"{page}: inline event handler"


def test_species_page_holds_its_facts_without_javascript(dist: Path) -> None:
    html = (dist / "species" / "neltuma-alba" / "index.html").read_text(encoding="utf-8")
    assert "<h1>Algarrobo blanco</h1>" in html
    assert '<link rel="canonical" href="https://genes.pietri.dev/species/neltuma-alba/">' in html
    assert 'name="description"' in html and "og:image" in html
    # Facts, months and sources are text in the page, not drawn by scripts.
    for text in (
        "5–18 m",
        "−11 to −5 °C",
        "September, October, November",
        "Agroforestree Database",
        "Pods eaten fresh",
    ):
        assert text in html, text
    taxon = next(b for b in _ld(html) if b["@type"] == "Taxon")
    assert taxon["name"] == "Neltuma alba"
    assert "Prosopis alba" in taxon["alternateName"]
    assert taxon["sameAs"] == [
        "https://www.gbif.org/species/5358528",
        "https://www.inaturalist.org/taxa/1493104",
    ]


def test_species_page_points_at_its_data(dist: Path) -> None:
    html = (dist / "species" / "neltuma-alba" / "index.html").read_text(encoding="utf-8")
    for attr in ("data-sheet", "data-look", "data-models", "data-lifecycle"):
        url = re.search(rf'{attr}="([^"]+)"', html)
        assert url, attr
        assert (dist / url.group(1).lstrip("/")).exists(), attr
    found = re.search(r'data-points="([^"]+)"', html)
    assert found
    points = json.loads(found.group(1).replace("&quot;", '"'))
    names = {p["name"] for p in points["places"]}
    assert {"Santa Fe", "Córdoba", "Santiago del Estero", "Ñeembucú", "La Paz"} <= names
    assert sum(len(p["photos"]) for p in points["places"]) == 19


def test_catalog_lists_the_lifecycle_and_card(dist: Path) -> None:
    cat = jsonio.load(dist / "v1" / "catalog.json")
    entry = next(s for s in cat["species"] if s["id"] == "neltuma-alba")
    assert entry["lifecycle"]["path"] == "/v1/species/neltuma-alba/lifecycle/1.json"
    assert entry["media"]["path"].startswith("/v1/species/neltuma-alba/media/card.")
    assert (dist / entry["lifecycle"]["path"].lstrip("/")).exists()


def test_index_sitemap_robots_and_llms(dist: Path) -> None:
    index = (dist / "index.html").read_text(encoding="utf-8")
    assert 'href="/species/neltuma-alba/"' in index
    assert "example-tree" not in index
    sitemap = (dist / "sitemap.xml").read_text(encoding="utf-8")
    assert "<loc>https://genes.pietri.dev/species/neltuma-alba/</loc>" in sitemap
    assert "Sitemap: https://genes.pietri.dev/sitemap.xml" in (dist / "robots.txt").read_text(
        encoding="utf-8"
    )
    llms = (dist / "llms.txt").read_text(encoding="utf-8")
    assert llms.startswith("# genes\n") and "/species/neltuma-alba/index.md" in llms
    md = (dist / "species" / "neltuma-alba" / "index.md").read_text(encoding="utf-8")
    assert md.startswith("# Algarrobo blanco (Neltuma alba)")
    assert "at 20 years:" in md and "died of age" in md
    assert "adult_height_m: 5–18, usually 10" in md


def test_builds_are_byte_identical(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    catalog.build([SPECIES_DIR], a)
    catalog.build([SPECIES_DIR], b)
    for f in a.rglob("*"):
        if f.is_file() and f.suffix in {".html", ".md", ".txt", ".xml", ".json"}:
            assert f.read_bytes() == (b / f.relative_to(a)).read_bytes(), f


def test_site_imports_resolve() -> None:
    for js in (SITE_STATIC / "js").glob("*.js"):
        code = js.read_text(encoding="utf-8")
        for target in re.findall(r"""from\s+'([^']+)'|import\('([^']+)'\)""", code):
            t = next(x for x in target if x)
            if t.startswith("/static/site/"):
                path = SITE_STATIC / t.removeprefix("/static/site/")
            elif t.startswith("/static/"):
                path = REPO_ROOT / "viewer" / "static" / t.removeprefix("/static/")
            else:
                path = js.parent / t
            assert path.resolve().exists(), f"{js.name}: {t}"


def test_place_points_read_inaturalist_place_codes() -> None:
    basemap = jsonio.load(SITE_STATIC / "geo" / "basemap.json")
    refs = {
        "photos": [
            {"id": "a", "place": "Jiménez, AR-SE, AR"},
            {"id": "b", "place": "La Paz, BO"},
            {"id": "c", "place": "Nowhere, XX"},
        ]
    }
    pts = genes_site.place_points(refs, basemap)
    assert [p["name"] for p in pts] == ["La Paz", "Santiago del Estero"]


def test_stage_strip_follows_the_life_and_its_pictures_exist(dist: Path) -> None:
    sp = next(s for s in validate.discover([SPECIES_DIR]) if s.id == "neltuma-alba")
    life = genes_site.lifecycle_of(sp)
    assert life is not None
    spans = genes_site.stage_spans(life[1])
    assert [s[0] for s in spans] == [
        "seedling",
        "sapling",
        "young",
        "adult",
        "old",
        "dead_standing",
        "fallen",
    ]
    assert all(a[1] < b[1] for a, b in zip(spans, spans[1:], strict=False))
    html = (dist / "species" / "neltuma-alba" / "index.html").read_text(encoding="utf-8")
    for st, *_ in spans:
        url = f"/v1/species/neltuma-alba/media/stages/{st}.webp"
        assert url in html, st
        assert (dist / url.lstrip("/")).exists(), url


def test_painted_icons_exist_with_their_sizes(dist: Path) -> None:
    html = (dist / "species" / "neltuma-alba" / "index.html").read_text(encoding="utf-8")
    used = set(re.findall(r'src="/static/site/art/([a-z-]+)\.webp"', html))
    assert {"i-pod", "i-bee", "i-goat", "i-frost", "i-rain"} <= used
    sizes = jsonio.load(SITE_STATIC / "art" / "sizes.json")["sizes"]
    for name in used:
        assert name in sizes and (dist / "static" / "site" / "art" / f"{name}.webp").exists()


def test_the_map_draws_no_provinces() -> None:
    basemap = jsonio.load(SITE_STATIC / "geo" / "basemap.json")
    assert basemap["rivers"] and basemap["lakes"]
    assert all("d" not in p for p in basemap["provinces"])


def test_recorded_lifecycle_is_valid() -> None:
    species = [s for s in validate.discover([SPECIES_DIR]) if s.id == "neltuma-alba"]
    assert validate._lifecycle_problems(species[0]) == []


@pytest.fixture(scope="module")
def served(dist: Path):  # type: ignore[no-untyped-def]
    srv = serve.make_server(dist, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def test_public_pages_run_without_errors(served: str) -> None:
    pw, browser = _browser()
    try:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors: list[str] = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{served}/")
        page.wait_for_selector("body[data-ready]")
        page.goto(f"{served}/species/neltuma-alba/")
        page.wait_for_selector("body[data-ready], body[data-error]", timeout=60000)
        assert page.evaluate("document.body.dataset.error") is None
        assert "Adult" in page.locator("[data-readout]").inner_text()
        # Winter: the same year, July.
        page.locator("[data-season='7']").click()
        assert "July" in page.locator("[data-readout]").inner_text()
        # The end of the life: a fallen trunk.
        page.evaluate("""() => { const a = document.querySelector('[data-age]');
            a.value = a.max; a.dispatchEvent(new Event('input')); }""")
        assert "Fallen" in page.locator("[data-readout]").inner_text()
        page.locator("[data-daynight]").click()
        assert page.evaluate("document.body.dataset.mode") in ("day", "night")
        page.locator("#map").scroll_into_view_if_needed()
        page.locator("[data-map-canvas] svg").wait_for(timeout=30000)
        assert page.locator("[data-map-canvas] .pin").count() == 10
        assert errors == []
    finally:
        browser.close()
        pw.stop()


def test_stages_follow_the_recorded_life(served: str) -> None:
    pw, browser = _browser()
    try:
        page = browser.new_page()
        page.goto(f"{served}/")
        stages = page.evaluate("""async () => {
            const m = await import('/static/site/js/life.js');
            const life = await (await fetch('/v1/species/neltuma-alba/lifecycle/1.json')).json();
            const at = (years) => life.samples.age_days.findIndex((d) => d >= years * 365.25);
            return [0, 7, 15, 60, 200, 232].map((y) => m.stageAt(life, at(y)))
              .concat([m.stageAt(life, life.samples.date.length - 1)]);
        }""")
        assert stages == ["seedling", "sapling", "young", "adult", "old", "dead_standing", "fallen"]
    finally:
        browser.close()
        pw.stop()


@pytest.fixture
def example_site(tmp_path: Path, examples: Path):  # type: ignore[no-untyped-def]
    out = tmp_path / "dist"
    catalog.build([examples], out)
    srv = serve.make_server(out, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def test_a_species_without_a_recorded_life_still_shows_its_tree(example_site: str) -> None:
    """The example tree has a look but no lifecycle: the page shows its adult model."""
    pw, browser = _browser()
    try:
        page = browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{example_site}/species/example-tree/")
        page.wait_for_selector("body[data-ready], body[data-error]", timeout=60000)
        assert page.evaluate("document.body.dataset.error") is None
        assert errors == []
    finally:
        browser.close()
        pw.stop()
