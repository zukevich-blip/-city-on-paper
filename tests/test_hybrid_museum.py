"""Hybrid City on Paper: story-first homepage and real-source atlas safeguards."""
from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.local = []
        self.images = []
        self.h1 = 0
        self.ids = set()
        self.duplicates = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "h1":
            self.h1 += 1
        if tag == "img":
            self.images.append(a)
        if a.get("id"):
            if a["id"] in self.ids:
                self.duplicates.add(a["id"])
            self.ids.add(a["id"])
        for name in ("src", "href"):
            url = a.get(name)
            if url:
                self.local.append(url)


def test_hybrid_home_prioritizes_historical_story_and_keeps_previous_sections():
    page = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'href="stories/paris-on-paper/" class="btn primary"' in page
    assert 'href="experience/"' in page
    assert 'href="atlas/"' in page
    assert 'href="studio/"' in page
    assert page.index('href="stories/paris-on-paper/" class="btn primary"') < page.index('class="stats"')
    assert page.index("Город на бумаге · Музей") < page.index("<style>")
    assert 'class="museum-pathway"' in page
    assert 'data-go="catalog"' in page
    assert 'id="research"' in page
    assert 'id="catalog"' in page


def test_hybrid_atlas_html_has_one_h1_accessible_images_and_valid_links():
    file = ROOT / "atlas/index.html"
    parsed = Scan()
    parsed.feed(file.read_text(encoding="utf-8"))
    assert parsed.h1 == 1
    assert len(parsed.images) >= 2
    assert all(img.get("alt") for img in parsed.images)
    assert not parsed.duplicates
    for url in parsed.local:
        u = urlsplit(url)
        if u.scheme or u.netloc or not u.path:
            continue
        f = (file.parent / unquote(u.path)).resolve()
        assert f.is_relative_to(ROOT), url
        if u.path.endswith("/"):
            f /= "index.html"
        assert f.is_file(), url


def test_archive_dataset_contains_genuine_reviewed_source_links():
    data = json.loads((ROOT / "eras/data/eras.json").read_text(encoding="utf-8"))
    names = {x["id"] for x in data["cities"]}
    assert {"paris", "florence", "naples"}.issubset(names)
    source_count = 0
    for city in data["cities"]:
        if city["id"] not in {"paris", "florence", "naples"}:
            continue
        for place in city["places"]:
            for item in place["images"]:
                if item.get("rights_class") == "open" and item.get("file"):
                    source = item["object_url"]
                    assert source.startswith("https://")
                    assert item.get("institution")
                    assert (ROOT / "eras" / item["file"]).is_file(), item["file"]
                    source_count += 1
    assert source_count >= 9


def test_atlas_filters_use_existing_metadata_not_fabricated_gcp_coordinates():
    script = (ROOT / "atlas/app.js").read_text(encoding="utf-8")
    for marker in ('rights_class==="open"', 'img.object_url', 'img.creators',
                   "img.institution", 'img.file', "URLSearchParams",
                   'aria-pressed', 'city.places', "selectedSource"):
        assert marker in script, marker
    assert "latitude" not in script
    assert "longitude" not in script
    assert "homography" not in script
    assert ".innerHTML" not in script
    assert "cloudSync" not in script


def test_shared_design_tokens_are_linked_on_all_museum_modes():
    sources = [
        "index.html", "stories/index.html", "stories/paris-on-paper/index.html",
        "experience/index.html", "atlas/index.html",
    ]
    for file in sources:
        content = (ROOT / file).read_text(encoding="utf-8")
        assert "hybrid/tokens.css" in content, file
    css = (ROOT / "assets/hybrid/tokens.css").read_text(encoding="utf-8")
    for color in ("#F4EFE5", "#29463D", "#292D29", "#B79567", "#88513B"):
        assert color in css


def test_hybrid_mobile_and_calm_mode_are_supported():
    for file in ("assets/hybrid/museum.css", "atlas/styles.css"):
        text = (ROOT / file).read_text(encoding="utf-8")
        assert "@media(max-width:" in text
        assert "prefers-reduced-motion" in text
    assert "prefers-reduced-motion" in (ROOT / "experience/styles.css").read_text(encoding="utf-8")
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'href="experience/"' in home
    atlas = (ROOT / "atlas/index.html").read_text(encoding="utf-8")
    assert "<noscript>" in atlas
    assert 'id="selectedSource"' in atlas
    assert "Историческое изображение" in atlas
