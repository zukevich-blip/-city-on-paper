"""Source, provenance, information architecture and safety checks for the Book of Cities."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.files = []
        self.headings = []
        self.alt_errors = []
        self.ids = set()
        self.duplicate_ids = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for name in ("src", "href"):
            if a.get(name):
                self.files.append(a[name])
        if tag == "h1":
            self.headings.append(tag)
        if tag == "img" and not a.get("alt"):
            self.alt_errors.append(a.get("src"))
        if a.get("id"):
            if a["id"] in self.ids:
                self.duplicate_ids.add(a["id"])
            self.ids.add(a["id"])


def test_book_has_single_h1_accessible_pictures_and_no_duplicate_ids():
    page = PageParser()
    page.feed((ROOT / "experience/index.html").read_text(encoding="utf-8"))
    assert len(page.headings) == 1
    assert not page.alt_errors
    assert not page.duplicate_ids


def test_book_local_resources_exist_in_source_repository():
    parser = PageParser()
    file = ROOT / "experience/index.html"
    parser.feed(file.read_text(encoding="utf-8"))
    for url in parser.files:
        target = urlsplit(url)
        if target.scheme or target.netloc or not target.path:
            continue
        location = (file.parent / unquote(target.path)).resolve()
        if target.path.endswith("/"):
            location /= "index.html"
        assert location.is_relative_to(ROOT), url
        assert location.is_file(), url


def test_all_nine_chapters_use_source-linked_allowed_images():
    js = (ROOT / "experience/app.js").read_text(encoding="utf-8")
    paths = [
        "poc/compare/pairs/madeleine-historic-loc-pga14315v.jpg",
        "poc/compare/pairs/palais-royal-historic-loc-pga14314v.jpg",
        "eras/img/paris_madeleine_c1890-1900_photochrom_rue-royale_loc-ppmsc-05184.jpg",
        "eras/img/florence_pontevecchio_1859-66_sommer-behles_stereo_loc-1s53703.jpg",
        "eras/img/florence_pontevecchio_1883_pennell_etching_aic-194443.jpg",
        "eras/img/florence_duomo_c1890-1900_photochrom_loc-ppmsc-06455.jpg",
        "eras/img/naples_santalucia_1846_calvert-jones_aic-27086.jpg",
        "eras/img/naples_palazzoreale_pre1852_bridges_cma-1997.13.jpg",
        "eras/img/naples_plebiscito_c1890-1900_photochrom_loc-ppmsc-06576.jpg",
    ]
    assert js.count('          src: "../') == 9
    for path in paths:
        assert path in js, path
        assert (ROOT / path).is_file(), path
    for url in (
        "https://www.loc.gov/item/2016652452/",
        "https://www.loc.gov/item/2016652451/",
        "https://www.loc.gov/item/2001698526/",
        "https://www.loc.gov/item/2024722637/",
        "https://www.artic.edu/artworks/194443",
        "https://www.loc.gov/item/2001700795/",
        "https://www.artic.edu/artworks/27086",
        "https://clevelandart.org/art/1997.13",
        "https://www.loc.gov/item/2001700916/",
    ):
        assert url in js


def test_1769_map_source_is_credited_and_pins_are_not_fabricated():
    html = (ROOT / "experience/index.html").read_text(encoding="utf-8")
    js = (ROOT / "experience/app.js").read_text(encoding="utf-8")
    assert "https://www.loc.gov/item/97683588/" in html
    assert "loc-97683588-carte-d-europe-1769" in html
    assert "без ложной геопривязки" in html
    assert "latitude" not in js
    assert "longitude" not in js


def test_calm_mode_and_keyboard_accessibility_have_real_implementation():
    html = (ROOT / "experience/index.html").read_text(encoding="utf-8")
    js = (ROOT / "experience/app.js").read_text(encoding="utf-8")
    css = (ROOT / "experience/styles.css").read_text(encoding="utf-8")
    for fragment in ("quietToggle", "mapDialog", "imageDialog", "topicsPanel",
                     "chapterList", "reading", "openBook", "closeBook"):
        assert f'id="{fragment}"' in html
    assert 'prefers-reduced-motion: reduce' in css
    assert "ArrowLeft" in js and "ArrowRight" in js
    assert 'aria-expanded' in js
    assert 'role="status"' in html
    assert 'dialog' in html
    assert "localStorage" in js


def test_home_has_real_book_as_first_call_to_action_without_losing_old_home():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'href="experience/" class="btn primary"' in html
    assert 'href="stories/paris-on-paper/"' in html
    assert html.index('href="experience/" class="btn primary"') < html.index('class="stats"')
    assert 'id="home"' in html
    assert 'id="catalog"' in html
