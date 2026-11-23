"""The viewer: CSP rules on its files, the vendored three.js, and a real browser load."""

from __future__ import annotations

import re
import threading
from pathlib import Path

import pytest

from genes import catalog, jsonio, serve
from genes.paths import VIEWER_DIR

VENDOR = VIEWER_DIR / "static" / "vendor" / "three"


def test_no_inline_scripts_or_styles() -> None:
    for page in VIEWER_DIR.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        assert not re.search(r"<style\b", html), page
        for tag in re.findall(r"<script\b[^>]*>", html):
            assert "src=" in tag, f"{page}: inline script {tag}"
        assert not re.search(r"\son[a-z]+=", html), f"{page}: inline event handler"


def test_three_is_pinned_to_pietri_devs_version() -> None:
    assert (VENDOR / "VERSION").read_text(encoding="utf-8").startswith("three 0.187.0\n")
    # Bare `three` imports were rewritten, so no import map (an inline script) is needed.
    for js in VENDOR.rglob("*.js"):
        code = "\n".join(
            line
            for line in js.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("*")
        )
        assert not re.search(r"from\s+['\"]three['\"]", code), js


def test_viewer_imports_resolve() -> None:
    for js in (VIEWER_DIR / "static").glob("*.js"):
        for target in re.findall(r"from\s+'(\.[^']+)'", js.read_text(encoding="utf-8")):
            assert (js.parent / target).resolve().exists(), f"{js.name}: {target}"


@pytest.fixture
def site(tmp_path: Path, examples: Path):  # type: ignore[no-untyped-def]
    out = tmp_path / "dist"
    catalog.build([examples], out)
    srv = serve.make_server(out, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _browser():  # type: ignore[no-untyped-def]
    sync_api = pytest.importorskip("playwright.sync_api")
    pw = sync_api.sync_playwright().start()
    for kwargs in ({}, {"executable_path": "/opt/pw-browsers/chromium"}):
        try:
            return pw, pw.chromium.launch(
                args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"], **kwargs
            )
        except Exception:  # no browser installed here
            continue
    pw.stop()
    pytest.skip("no Chromium for Playwright on this machine")


def test_species_page_loads_without_errors(site: str) -> None:
    pw, browser = _browser()
    try:
        page = browser.new_page(viewport={"width": 1200, "height": 800})
        errors: list[str] = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{site}/species/example-tree/?month=11")
        page.wait_for_selector("body[data-ready], body[data-error]", timeout=30000)
        assert page.evaluate("document.body.dataset.error") is None
        assert page.locator("h1").inner_text() == "Árbol de prueba"
        assert "2,708 of 12,000" in page.locator(".stats").inner_text()
        page.select_option("select[aria-label=Stage]", "dead_standing")
        page.locator(".stats", has_text="dead_standing-a.lod0.glb").wait_for()
        page.goto(site + "/")
        page.wait_for_selector("body[data-ready]")
        assert page.locator(".card").count() == 1
        assert errors == []
    finally:
        browser.close()
        pw.stop()


def test_month_preview_matches_the_sheet(site: str) -> None:
    """phenology.js: the example tree drops its leaves in May-June, is bare in July-August."""
    pw, browser = _browser()
    try:
        page = browser.new_page()
        page.goto(site + "/")
        sheet = jsonio.load(
            Path(__file__).parents[1] / "examples/species/plants/example-tree/sheets/1.json"
        )
        result = page.evaluate(
            """async (sheet) => {
                const m = await import('/static/phenology.js');
                return [1, 5, 7, 8, 9, 11].map((month) => m.partAmounts(sheet, month));
            }""",
            sheet,
        )
        foliage = [r["foliage"] for r in result]
        assert foliage == [1, 0.4, 0, 0, 0.6, 1]
        assert [r["flowers"] for r in result] == [0, 0, 0, 0, 0, 1]
        assert [r["fruit"] for r in result] == [1, 0, 0, 0, 0, 0]
    finally:
        browser.close()
        pw.stop()
