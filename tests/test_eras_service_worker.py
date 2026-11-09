"""Offline PWA regression: no bogus HTML in scripts/JSON and isolated caches."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_service_worker_is_namespaced_and_never_replaces_code_with_html():
    source = (ROOT / "eras/sw.js").read_text(encoding="utf-8")
    assert 'PREFIX = "city-on-paper-eras-"' in source
    assert 'IMAGE_MAX_ENTRIES = 96' in source
    assert "key.startsWith(PREFIX)" in source
    assert "request.mode === \"navigate\"" in source
    assert "new Response(" in source and "status: 503" in source
    assert 'caches.match("index.html")' not in source
    assert "url.origin !== self.location.origin" in source
    assert "request.method !== \"GET\"" in source


def test_critical_research_museum_shell_files_exist_and_are_precached():
    source = (ROOT / "eras/sw.js").read_text(encoding="utf-8")
    for relative in (
        "journey.js", "journey.css", "cartography.js", "cartography.css",
        "data/map-evidence.json", "atlas.js", "eras.js", "data/atlas.json",
        "city-lab.js", "city-lab.css", "maps.js",
    ):
        assert (ROOT / "eras" / relative).is_file(), relative
        assert f'"{relative}"' in source, relative


def test_cache_does_not_claim_historical_tiles_or_external_sources_offline():
    source = (ROOT / "eras/sw.js").read_text(encoding="utf-8")
    assert "if (url.origin !== self.location.origin) return;" in source
    assert '"map_search_candidate_not_verified"' not in source
    assert "Изображение недоступно без сети" in source
