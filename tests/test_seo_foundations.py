"""SEO checks for static entry points and generated public museum pages."""

from __future__ import annotations

import re
from pathlib import Path

from tools.release.build_public_site import PAGES, info_pages

ROOT = Path(__file__).resolve().parents[1]
STATIC = PAGES


def _description(content: str) -> str:
    matches = re.findall(
        r'<meta\s+name="description"\s+content="([^"]+)"\s*/?>',
        content,
        flags=re.I,
    )
    assert len(matches) == 1, "Each entry point needs exactly one description"
    return matches[0]


def test_public_source_pages_have_one_h1_and_unique_search_descriptions() -> None:
    found = []
    for rel in STATIC:
        content = (ROOT / rel).read_text(encoding="utf-8")
        assert len(re.findall(r"<h1\b", content, flags=re.I)) == 1, rel
        text = _description(content)
        assert 110 <= len(text) <= 160, (rel, len(text))
        found.append(text)
    assert len(found) == len(set(found)), "Descriptions must not be duplicated"


def test_eras_static_html_has_explorable_fallback_before_javascript() -> None:
    html = (ROOT / "eras/index.html").read_text(encoding="utf-8")
    before_scripts = html.split('<script src="vendor/leaflet-1.9.4/leaflet.js">')[0]
    assert "<h1" in before_scripts and "Атлас эпох</h1>" in before_scripts
    assert 'id="app"' in before_scripts
    for target in ("../", "../world/", "../cities/", "../salon/", "../poc/compare/"):
        assert f'href="{target}"' in before_scripts
    assert before_scripts.index('<h1') > before_scripts.index('<main id="app"')


def test_generated_museum_info_pages_have_unique_descriptions(tmp_path: Path) -> None:
    info_pages(tmp_path)
    descriptions = []
    for slug in ("about", "rights", "privacy", "contribute"):
        page = (tmp_path / slug / "index.html").read_text(encoding="utf-8")
        text = _description(page)
        assert 110 <= len(text) <= 160, (slug, len(text))
        assert page.lower().count("<h1") == 1, slug
        assert 'rel="canonical"' in page, slug
        assert slug in page, slug
        descriptions.append(text)
    assert len(set(descriptions)) == 4
    assert "CC BY-SA" in (tmp_path / "rights/index.html").read_text(encoding="utf-8")
    assert "../eras/" in (tmp_path / "about/index.html").read_text(encoding="utf-8")
