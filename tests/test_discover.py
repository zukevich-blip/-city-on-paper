"""Public discovery experience must reuse sourced artwork and protect visitor privacy."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_discovery_is_source_led_and_does_not_collect_visitors():
    html = (ROOT / "discover/index.html").read_text(encoding="utf-8")
    assert "madeleine-dossier-20261103.json" in html
    assert "https://www.loc.gov/item/2016652452/" in html
    assert "1845–1860" in html
    assert "Panoramax" in html and "CC BY-SA 4.0" in html
    assert "заказал литографию Бенуа" in html
    assert "подлинный" in html.lower()
    assert "innerHTML" not in html
    assert "localStorage" not in html
    assert "<form" not in html
    assert "navigator.share" in html
    assert "navigator.clipboard" in html
    assert "data-path" in html
    assert "og:description" in html
    for path in [
        "../poc/compare/pairs/madeleine-historic-loc-pga14315v.jpg",
        "../poc/compare/pairs/madeleine-photo-panoramax-38b6d262.jpg",
        "../data/stories/madeleine-dossier-20261103.json",
    ]:
        assert (ROOT / "discover" / path).resolve().is_file(), path


def test_discovery_is_reachable_from_exhibition_and_atlas():
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    atlas = (ROOT / "journeys/index.html").read_text(encoding="utf-8")
    assert 'href="discover/"' in home
    assert 'href="../discover/"' in atlas
    qa = (ROOT / ".github/workflows/qa-city-on-paper.yml").read_text()
    assert "tests/browser/qa_discover.js" in qa
    assert "cp discover/index.html /tmp/city-on-paper-package/discover/" in qa
    pages = (ROOT / ".github/workflows/pages-preview.yml").read_text()
    assert "cp discover/index.html public/discover/index.html" in pages
