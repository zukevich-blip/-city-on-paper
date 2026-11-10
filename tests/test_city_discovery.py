"""Proof and usability checks for the world-wide city discovery index."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Audit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.duplicates = []
        self.images = []
        self.links = []
        self.headings = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "h1":
            self.headings += 1
        if a.get("id"):
            if a["id"] in self.ids:
                self.duplicates.append(a["id"])
            self.ids.add(a["id"])
        if tag == "img":
            self.images.append(a)
        for attr in ("src", "href"):
            if a.get(attr):
                self.links.append(a[attr])


def test_city_discovery_uses_source_images_and_real_links():
    file = ROOT / "cities/index.html"
    scan = Audit()
    scan.feed(file.read_text(encoding="utf-8"))
    assert scan.headings == 1
    assert not scan.duplicates
    assert len(scan.images) == 3
    assert all(img.get("alt") for img in scan.images)
    for url in scan.links:
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        location = (file.parent / unquote(parsed.path)).resolve()
        assert location.is_relative_to(ROOT)
        if parsed.path.endswith("/"):
            location /= "index.html"
        assert location.is_file(), url


def test_city_discovery_is_provenance_safe_and_progressive():
    js = (ROOT / "cities/app.js").read_text(encoding="utf-8")
    html = (ROOT / "cities/index.html").read_text(encoding="utf-8")
    assert "world-coverage-20261110.json" in js
    assert "world-cities-v1.json" in js
    assert "validateRegistry" in js
    assert "candidate" in html and "seed_only" in html and "detailed" in html
    assert "document.createElement" in js
    assert ".innerHTML" not in js
    assert "new URL(" in js
    assert "statusLabels" in js
    assert "Санкт-Петербург" in html
    assert "https://www.loc.gov/item/2016652452/" in html
    assert "https://www.artic.edu/artworks/194443" in html
    assert "https://www.artic.edu/artworks/27086" in html


def test_hybrid_home_and_shared_navigation_expose_world_city_directory():
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    nav = (ROOT / "assets/nav/museum-nav.js").read_text(encoding="utf-8")
    atlas = (ROOT / "atlas/index.html").read_text(encoding="utf-8")
    for text in (home, nav):
        assert "cities/" in text
    assert "../cities/" in atlas
    assert "История продолжается за пределами Европы" in home


def test_city_index_is_responsive_and_has_accessible_filter_labels():
    html = (ROOT / "cities/index.html").read_text(encoding="utf-8")
    css = (ROOT / "cities/styles.css").read_text(encoding="utf-8")
    home_css = (ROOT / "assets/hybrid/museum.css").read_text(encoding="utf-8")
    for control in ("query", "region", "status", "type"):
        assert f'<label for="{control}">' in html
        assert f'id="{control}"' in html
    assert 'id="coverageStats"' in html
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html
    assert "@media(max-width:400px)" in css
    assert "@media(max-width:720px)" in css
    assert "prefers-reduced-motion" in css
    assert "header .navlinks" in home_css
    assert 'header .navlinks>a[href="studio/"]{display:none}' in home_css
