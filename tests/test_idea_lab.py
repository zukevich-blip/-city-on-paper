"""Quality gates for City on Paper idea radar, historical print lab, private fieldwork."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_idea_radar_sources_and_readiness():
    data = json.loads((ROOT / "data/ideas/radar-20261103.json").read_text())
    assert len(data["ideas"]) == 14
    assert len(data["schemes"]) == 3
    assert set(data["rank_method"]["weights"]) == {
        "visual", "learning", "originality", "source_readiness", "rights_safety"
    }
    assert abs(sum(data["rank_method"]["weights"].values()) - 1) < 1e-9
    assert len({x["id"] for x in data["ideas"]}) == len(data["ideas"])
    for idea in data["ideas"]:
        assert idea["status"] in {"implemented", "pilot", "research", "later"}
        assert len(idea["sources"]) > 0
        assert all(s["url"].startswith("https://") for s in idea["sources"])
        assert all(1 <= value <= 5 for value in idea["metrics"].values())
        if idea["module"]:
            assert (ROOT / idea["module"] / "index.html").is_file()
    assert all(x["flow"] and len(x["flow"]) >= 5 for x in data["schemes"])


def test_print_lab_sources_and_museum_truth():
    text = (ROOT / "printlab/index.html").read_text()
    assert "www.metmuseum.org" in text and "www.vam.ac.uk" in text
    assert "www.loc.gov/item/2016652452/" in text
    assert "ручная раскраска" in text.lower()
    assert 'id="stone"' in text and 'id="sheet"' in text
    assert "localStorage" in text and "toDataURL" in text
    assert 'src="../poc/compare/pairs/madeleine-historic-loc-pga14315v.jpg"' in text
    assert not any(s in text for s in ["gtag(", "analytics.js", "fetch('https://"])


def test_fieldwork_local_only_and_publication_boundaries():
    text = (ROOT / "fieldwork/index.html").read_text()
    assert "image/jpeg" in text and "15*1024*1024" in text
    assert "URL.createObjectURL" in text and "URL.revokeObjectURL" in text
    assert "photo_filename" in text and "No image bytes" in text
    assert "Никаких загрузок фотографии на сервер" in text or "Снимок, выбранный с вашего устройства, в интернет не отправляется" in text
    assert "CC BY-SA 4.0" in text
    assert "геометрическое совмещение" in text
    assert "navigator.geolocation" not in text
    assert not any(s in text for s in ["FormData", "XMLHttpRequest", "fetch("])
    assert 'id="place"' in text and 'id="picture"' in text


def test_three_new_modules_linked_from_home():
    text = (ROOT / "index.html").read_text()
    assert 'href="ideas/"' in text
    assert 'href="printlab/"' in text
    assert 'href="fieldwork/"' in text
    assert "Город на бумаге" in text
