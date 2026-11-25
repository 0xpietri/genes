"""The public catalog (genes.site): pages written at build time, readable without JavaScript,
for search engines and language models; the 3D, the simulator, the leaf and the map load in
a real browser without errors."""

from __future__ import annotations

import itertools
import json
import re
import threading
from pathlib import Path

import pytest

from genes import catalog, jsonio, serve, site_i18n, site_static, validate
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
    for page in [*dist.glob("**/index.html")]:
        if "review" in page.parts:
            continue
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
    assert all(a[1] < b[1] for a, b in itertools.pairwise(spans))
    html = (dist / "species" / "neltuma-alba" / "index.html").read_text(encoding="utf-8")
    for st, *_ in spans:
        url = f"/v1/species/neltuma-alba/media/stages/{st}.webp"
        assert url in html, st
        assert (dist / url.lstrip("/")).exists(), url


def test_painted_icons_exist_with_their_sizes(dist: Path) -> None:
    html = (dist / "species" / "neltuma-alba" / "index.html").read_text(encoding="utf-8")
    used = set(re.findall(r'src="/static/site/[0-9a-f]{10}/art/([a-z-]+)\.webp"', html))
    assert {"i-pod", "i-bee", "i-goat", "i-frost", "i-rain"} <= used
    sizes = jsonio.load(SITE_STATIC / "art" / "sizes.json")["sizes"]
    for name in used:
        assert name in sizes and (dist / site_static.url(f"art/{name}.webp").lstrip("/")).exists()


def test_the_map_draws_no_provinces() -> None:
    basemap = jsonio.load(SITE_STATIC / "geo" / "basemap.json")
    assert basemap["rivers"] and basemap["lakes"]
    assert all("d" not in p for p in basemap["provinces"])


def test_every_page_comes_in_english_and_spanish(dist: Path) -> None:
    en = (dist / "species" / "neltuma-alba" / "index.html").read_text(encoding="utf-8")
    es = (dist / "es" / "species" / "neltuma-alba" / "index.html").read_text(encoding="utf-8")
    assert '<html lang="en">' in en and '<html lang="es">' in es
    for html in (en, es):
        assert 'hreflang="en" href="https://genes.pietri.dev/species/neltuma-alba/"' in html
        assert 'hreflang="es" href="https://genes.pietri.dev/es/species/neltuma-alba/"' in html
    assert '<link rel="canonical" href="https://genes.pietri.dev/es/species/neltuma-alba/">' in es
    # One language per page: the Spanish page has the Spanish summary and words only.
    assert "Árbol del Chaco" in es and "Chaco tree" not in es
    assert "Árbol del Chaco" not in en
    for text in ("septiembre, octubre, noviembre", "−11 a −5 °C", "0,3–1,5 m", "Fuentes"):
        assert text in es, text
    for text in ("September", "Sources", "Height"):
        assert f">{text}<" not in es, text
    index = (dist / "es" / "index.html").read_text(encoding="utf-8")
    assert 'href="/es/species/neltuma-alba/"' in index and '<html lang="es">' in index
    sitemap = (dist / "sitemap.xml").read_text(encoding="utf-8")
    assert "<loc>https://genes.pietri.dev/es/species/neltuma-alba/</loc>" in sitemap


def test_every_text_on_the_spanish_pages_is_translated(tmp_path: Path) -> None:
    site_i18n.MISSING.clear()
    catalog.build([SPECIES_DIR], tmp_path / "dist")
    assert not site_i18n.MISSING, sorted(site_i18n.MISSING)


def test_the_site_is_not_about_one_town(dist: Path) -> None:
    for page in [*dist.glob("**/index.html"), dist / "llms.txt"]:
        if "review" in page.parts:
            continue
        text = page.read_text(encoding="utf-8")
        assert "Unquillo" not in text, page


def test_species_tags_are_icons_with_their_words(dist: Path) -> None:
    html = (dist / "species" / "neltuma-alba" / "index.html").read_text(encoding="utf-8")
    tags = re.search(r'<ul class="tags">(.*?)</ul>', html, re.S)
    assert tags
    tips = re.findall(r'data-tip="([^"]+)"', tags.group(1))
    assert tips[0] == "Leaves: Semi-deciduous" and len(tips) == 3
    assert tips[2].startswith("Conservation: Near threatened")


def test_painted_map_pieces_and_skies_exist() -> None:
    for folder in ("map", "scene"):
        sizes = jsonio.load(SITE_STATIC / "art" / folder / "sizes.json")["sizes"]
        assert sizes
        for name, (w, h) in sizes.items():
            assert (SITE_STATIC / "art" / folder / f"{name}.webp").exists(), name
            assert w > 0 and h > 0
    assert {"sky-day", "sky-night", "ground"} <= set(
        jsonio.load(SITE_STATIC / "art" / "scene" / "sizes.json")["sizes"]
    )


def test_the_simulator_holds_the_life(dist: Path) -> None:
    html = (dist / "species" / "neltuma-alba" / "index.html").read_text(encoding="utf-8")
    module = re.search(r'<div class="hero-main panel">.*?</section>', html, re.S)
    assert module
    for part in (
        'class="life-stages"',
        "data-life-cursor",
        "data-play",
        "data-info-toggle",
        'class="seasons stage-seasons"',
        'class="info" data-tip="One algarrobo grown alone',
    ):
        assert part in module.group(0), part
    assert "sim-kpis" not in html and "is what it dies of" not in html
    assert "data-stage-chip" not in html


def test_sources_link_straight_to_their_pages(dist: Path) -> None:
    html = (dist / "species" / "neltuma-alba" / "index.html").read_text(encoding="utf-8")
    assert '<ol class="sources">' not in html
    assert re.search(r'<td class="src"><a href="https?://[^"]+" title="Orwa C\. et al', html)


def test_home_and_footer(dist: Path) -> None:
    index = (dist / "index.html").read_text(encoding="utf-8")
    assert "Sierras Chicas of Córdoba" in index
    assert 'class="filters"' not in index and 'id="about"' not in index
    assert ">Animals<" not in index and ">About<" not in index
    assert index.count('class="foot-col"') == 3


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
        assert page.locator("[data-map-canvas] .pin").count() == 9
        assert page.locator("[data-map-canvas] .peak").count() >= 4
        assert errors == []
    finally:
        browser.close()
        pw.stop()


def test_the_spanish_page_speaks_spanish_in_the_simulator(served: str) -> None:
    pw, browser = _browser()
    try:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{served}/es/species/neltuma-alba/")
        page.wait_for_selector("body[data-ready], body[data-error]", timeout=60000)
        assert page.evaluate("document.body.dataset.error") is None
        readout = page.locator("[data-readout]").inner_text()
        assert "Año" in readout and "Adulto" in readout
        page.locator("[data-season='7']").click()
        assert "julio" in page.locator("[data-readout]").inner_text()
        assert page.locator("[data-season='7']").get_attribute("aria-pressed") == "true"
        assert errors == []
    finally:
        browser.close()
        pw.stop()


def test_stages_follow_the_recorded_life(served: str) -> None:
    pw, browser = _browser()
    try:
        page = browser.new_page()
        page.goto(f"{served}/")
        stages = page.evaluate(
            """async () => {
            const m = await import('"""
            + site_static.url("js/life.js")
            + """');
            const life = await (await fetch('/v1/species/neltuma-alba/lifecycle/1.json')).json();
            const at = (years) => life.samples.age_days.findIndex((d) => d >= years * 365.25);
            return [0, 7, 15, 60, 200, 232].map((y) => m.stageAt(life, at(y)))
              .concat([m.stageAt(life, life.samples.date.length - 1)]);
        }"""
        )
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


def test_static_files_live_in_a_folder_named_by_their_content(dist: Path) -> None:
    html = (dist / "es" / "species" / "neltuma-alba" / "index.html").read_text(encoding="utf-8")
    v = site_static.version()
    assert re.fullmatch(r"[0-9a-f]{10}", v)
    for ref in (f"/static/site/{v}/site.css", f"/static/site/{v}/js/species.js"):
        assert ref in html and (dist / ref.lstrip("/")).exists(), ref
    # Nothing links the unversioned folder, which would let an old file be cached.
    assert not re.search(r'"/static/site/(?![0-9a-f]{10}/)', html)
    for js in (SITE_STATIC / "js").glob("*.js"):
        assert "/static/site/" not in js.read_text(encoding="utf-8"), js.name


# ---------------------------------------------------------------- loading, SEO, photo viewer


def test_reference_photos_show_small_thumbs_and_link_the_original(dist: Path) -> None:
    refs = jsonio.load(SPECIES_DIR / "plants" / "neltuma-alba" / "references" / "refs.json")
    html = (dist / "species" / "neltuma-alba" / "index.html").read_text(encoding="utf-8")
    base = dist / "v1" / "species" / "neltuma-alba" / "references"
    for p in refs["photos"]:
        thumb = base / "thumbs" / f"{p['id']}.webp"
        # Every stored photo has its thumb, much lighter than the photo itself.
        assert thumb.exists(), p["id"]
        assert thumb.stat().st_size < (base / p["file"]).stat().st_size / 2, p["id"]
        assert f'src="/v1/species/neltuma-alba/references/thumbs/{p["id"]}.webp"' in html
        # Without JavaScript the thumb opens the stored photo; the original's page is linked.
        assert f'<a href="/v1/species/neltuma-alba/references/{p["file"]}" data-photo>' in html
        assert f'href="{p["url"]}" rel="noopener" data-source>iNaturalist</a>' in html
    assert html.count("<dialog") == 1
    gallery = next(b for b in _ld(html) if "@graph" in b)["@graph"]
    assert len(gallery) == len(refs["photos"])
    assert all(g["@type"] == "ImageObject" and g["creditText"] for g in gallery)


def test_refs_thumb_is_the_tiles_middle_crop() -> None:
    from io import BytesIO

    from PIL import Image

    from genes import refs

    src = BytesIO()
    Image.new("RGB", (768, 1024), "green").save(src, "JPEG")
    out = Image.open(BytesIO(refs.thumb(src.getvalue())))
    assert out.format == "WEBP" and out.size == refs.THUMB_SIZE


def test_species_page_preloads_what_the_3d_needs(dist: Path) -> None:
    html = (dist / "species" / "neltuma-alba" / "index.html").read_text(encoding="utf-8")
    fetches = re.findall(r'<link rel="preload" href="([^"]+)" as="fetch" crossorigin>', html)
    assert fetches == [
        "/v1/species/neltuma-alba/sheets/1.json",
        "/v1/species/neltuma-alba/looks/1/look.json",
        "/v1/species/neltuma-alba/lifecycle/1.json",
        "/v1/species/neltuma-alba/looks/1/adult-a.lod1.glb",
    ]
    for url in fetches:
        assert (dist / url.lstrip("/")).exists(), url
    modules = re.findall(r'<link rel="modulepreload" href="([^"]+)">', html)
    assert site_static.url("js/stage.js") in modules
    assert "/static/vendor/three/addons/loaders/GLTFLoader.js" in modules
    for url in modules:
        assert (dist / url.lstrip("/")).exists(), url
    # The catalog page loads no 3D at all.
    assert "modulepreload" not in (dist / "index.html").read_text(encoding="utf-8")


def test_species_page_reads_well_for_search_engines_and_models(dist: Path) -> None:
    for lg, path in (("en", "species/neltuma-alba"), ("es", "es/species/neltuma-alba")):
        html = (dist / path / "index.html").read_text(encoding="utf-8")
        # The name and summary come before the 3D controls in the HTML.
        assert html.index("<h1>") < html.index("data-stage")
        assert 'type="text/markdown" hreflang="en" href="/species/neltuma-alba/index.md"' in html
        assert '<meta property="og:image:width" content="640">' in html
        assert '<meta property="og:image:alt" content="Algarrobo blanco (Neltuma alba)">' in html
        other = "es_AR" if lg == "en" else "en_GB"
        assert f'<meta property="og:locale:alternate" content="{other}">' in html
    sitemap = (dist / "sitemap.xml").read_text(encoding="utf-8")
    assert sitemap.count("<url>") == 4
    assert (
        '<xhtml:link rel="alternate" hreflang="es" '
        'href="https://genes.pietri.dev/es/species/neltuma-alba/"/>' in sitemap
    )
    assert "https://genes.pietri.dev/es/species/neltuma-alba/" in (dist / "llms.txt").read_text(
        encoding="utf-8"
    )


def test_webp_size_reads_the_header(tmp_path: Path) -> None:
    from PIL import Image

    for size, kw in (((640, 698), {"lossless": False}), ((33, 17), {"lossless": True})):
        p = tmp_path / f"{size[0]}.webp"
        Image.new("RGBA" if kw["lossless"] else "RGB", size, "red").save(p, "WEBP", **kw)
        assert genes_site.webp_size(p) == size


def test_photos_open_in_the_lightbox(served: str) -> None:
    pw, browser = _browser()
    try:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{served}/es/species/neltuma-alba/")
        page.wait_for_selector("body[data-ready], body[data-error]", timeout=60000)
        page.locator("[data-photo]").nth(1).click()
        box = page.locator("dialog[data-lightbox]")
        box.wait_for(state="visible")
        assert page.url.endswith("/es/species/neltuma-alba/")  # still on the page
        page.wait_for_selector("dialog[data-lightbox]:not(.loading)")
        src = page.evaluate("document.querySelector('[data-lb-img]').src")
        assert src.endswith("/references/r02.jpg")
        assert page.locator("[data-lb-count]").inner_text() == "2 / 19"
        assert page.locator("[data-lb-source]").get_attribute("href") == (
            "https://www.inaturalist.org/photos/145111445"
        )
        page.keyboard.press("ArrowRight")
        assert page.locator("[data-lb-count]").inner_text() == "3 / 19"
        page.locator("[data-lb-prev]").click()
        page.locator("[data-lb-prev]").click()
        assert page.locator("[data-lb-count]").inner_text() == "1 / 19"
        page.keyboard.press("Escape")
        box.wait_for(state="hidden")
        assert errors == []
    finally:
        browser.close()
        pw.stop()


def test_the_tree_shows_the_light_model_then_the_full_one(served: str) -> None:
    pw, browser = _browser()
    try:
        page = browser.new_page()
        asked: list[str] = []
        page.on("request", lambda r: asked.append(r.url) if r.url.endswith(".glb") else None)
        page.goto(f"{served}/species/neltuma-alba/")
        page.wait_for_selector("canvas[data-lod='0']", state="attached", timeout=60000)
        assert any(u.endswith("adult-a.lod1.glb") for u in asked)
        assert any(u.endswith("adult-a.lod0.glb") for u in asked)
        # Each model is asked for once: the preload is reused, not fetched twice.
        assert len(asked) == len(set(asked))
    finally:
        browser.close()
        pw.stop()
