"""Editorial navigation/source tests for the City on Paper story entry."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGES = (
    ROOT / "stories/index.html",
    ROOT / "stories/paris-on-paper/index.html",
)


class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.images = []
        self.headings = []
        self.altless = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if tag in {"a", "link"} and props.get("href"):
            self.links.append(props["href"])
        if tag == "img":
            self.images.append(props.get("src"))
            if not props.get("alt"):
                self.altless.append(props.get("src"))
        if tag == "h1":
            self.headings.append(tag)


@pytest.mark.parametrize("page", PAGES)
def test_every_story_page_has_exactly_one_h1_and_accessible_images(page):
    data = Scan()
    data.feed(page.read_text(encoding="utf-8"))
    assert len(data.headings) == 1
    assert not data.altless
    assert len(data.images) >= 1


@pytest.mark.parametrize("page", PAGES)
def test_story_local_resources_and_links_exist(page):
    parser = Scan()
    parser.feed(page.read_text(encoding="utf-8"))
    for url in parser.links + parser.images:
        assert url is not None
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        relative = unquote(parsed.path)
        target = (page.parent / relative).resolve()
        assert target.is_relative_to(ROOT), (page, url)
        if relative.endswith("/"):
            target /= "index.html"
        assert target.is_file(), (page.relative_to(ROOT), url)


def test_homepage_presents_story_before_the_collection_and_research_queues():
    body = (ROOT / "index.html").read_text(encoding="utf-8")
    assert body.index("Начать историю Парижа") < body.index('class="stats"')
    assert 'href="stories/"' in body
    assert 'href="stories/paris-on-paper/"' in body
    assert 'class="museum-pathway"' in body
    assert 'class="allrooms"' in body
    assert 'id="catalog"' in body
    assert 'data-go="research"' in body


def test_benoist_story_has_real_sources_honest_metadata_and_two_photo_credits():
    body = PAGES[1].read_text(encoding="utf-8")
    for expected in (
        "https://www.loc.gov/item/2016652451/",
        "https://www.loc.gov/item/2016652452/",
        "LC-DIG-pga-14314",
        "LC-DIG-pga-14315",
        "fgouget",
        "jerome92370",
        "CC BY-SA 4.0",
        "противоположен",
        "не будем утверждать",
        "источники",
    ):
        assert expected.lower() in body.lower()
    assert "40 пикселей/метр" not in body
    assert "подтверждённая географическая точность" not in body


def test_shared_css_has_mobile_and_reduced_motion_modes():
    css = (ROOT / "stories/story.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in css
    assert "max-width:720px" in css
    assert ":focus-visible" in css
