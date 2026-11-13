"""Release safety and museum journey regression checks.

The published world index is a sanitized projection, not a research ledger.
"""
import json
from pathlib import Path

from tools.release.build_public_site import ASSETS, PAGES, publish_coverage_index

ROOT = Path(__file__).resolve().parents[1]


def test_unified_release_includes_real_museum_rooms_and_style():
    for page in (
        "index.html", "cities/index.html", "atlas/index.html",
        "world/index.html", "salon/index.html",
        "stories/index.html", "stories/paris-on-paper/index.html",
        "experience/index.html", "poc/compare/index.html",
        "eras/index.html",
    ):
        assert page in PAGES, page
    assert {"assets/hybrid", "cities", "atlas", "stories", "experience"} <= set(ASSETS)
    for page in (
        "cities/index.html", "atlas/index.html", "stories/index.html",
        "stories/paris-on-paper/index.html", "experience/index.html",
    ):
        assert "assets/nav/museum-nav.js" in (ROOT / page).read_text(encoding="utf-8")


def test_published_world_coverage_excludes_research_records(tmp_path):
    origin = tmp_path / "private" / "data" / "coverage"
    origin.mkdir(parents=True)
    payload = {
        "summary": {"combined_names": 2},
        "entries": [
            {
                "name": "Париж", "country": "Франция", "region": "Европа",
                "status": "detailed", "detail_images": 2, "type": "city",
                "source_examples": [{"url": "https://internal.invalid/secret"}],
                "unreviewed_metadata": {"private": "do_not_publish"},
            },
            {
                "name": "Тестовый город", "country": "Тест", "region": "Европа",
                "status": "candidate", "candidate_records": 5,
                "source_examples": [{"url": "https://internal.invalid/not-reviewed"}],
            },
        ],
    }
    (origin / "world-coverage-20261110.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    output = tmp_path / "public"
    publish_coverage_index(tmp_path / "private", output)
    text = (output / "data/coverage/world-coverage-20261110.json").read_text(
        encoding="utf-8"
    )
    safe = json.loads(text)
    assert safe["summary"]["combined_names"] == 2
    assert len(safe["entries"]) == 2
    assert "internal.invalid" not in text
    assert "source_examples" not in text
    assert "unreviewed_metadata" not in text
    assert safe["entries"][1]["candidate_records"] == 5


def test_world_city_artwork_compare_routes_are_real_and_honest():
    city_js = (ROOT / "cities/app.js").read_text(encoding="utf-8")
    atlas_js = (ROOT / "atlas/app.js").read_text(encoding="utf-8")
    world_html = (ROOT / "world/index.html").read_text(encoding="utf-8")
    nav_js = (ROOT / "assets/nav/museum-nav.js").read_text(encoding="utf-8")
    assert 'art.href="../salon/?city="+encodeURIComponent(row.name)' in city_js
    assert 'modern.href="../photography/?city="+encodeURIComponent(row.name)' in city_js
    assert 'if(city==="paris")' in city_js
    assert 'state.city!=="paris"' in atlas_js
    assert 'directoryLink.href="../cities/?query="+encodeURIComponent(c.name)' in world_html
    assert 'object-fit:contain;display:block;filter:none' in world_html
    assert '#museumBar .mbp[hidden]{display:none!important}' in nav_js
