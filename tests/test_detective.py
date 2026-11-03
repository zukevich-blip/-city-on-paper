"""Source and chronology integrity for the interactive Madeleine casefile."""
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/stories/madeleine-dossier-20261103.json"


def test_casefile_sources_and_unknown_patron():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    assert data["record_id"] == "ph-benoist-paris-la-madeleine-loc-2016652452"
    assert len(data["clues"]) >= 5
    assert len(data["chronology"]) >= 6
    assert len(data["technique"]) == 4
    assert len(data["questions"]) == 3
    assert any(a["role"] == "Патрон или инициатор издания" and a["status"] == "unknown" for a in data["actors"])
    assert "не обнаружены" in data["framing"]
    assert all(c["certainty"] == "documented" for c in data["clues"])
    assert all(0 <= c["x"] <= 100 and 0 <= c["y"] <= 100 for c in data["clues"])
    assert len({c["id"] for c in data["clues"]}) == len(data["clues"])
    for collection in ["clues", "chronology", "technique", "actors"]:
        for record in data[collection]:
            assert urlparse(record["source"]).scheme == "https"
    assert all(0 <= q["correct"] < len(q["a"]) for q in data["questions"])


def test_casefile_originals_and_public_nav():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    for field in ["original_image", "modern_image"]:
        assert (ROOT / "detective" / data["object"][field]).resolve().is_file()
    html = (ROOT / "detective/index.html").read_text(encoding="utf-8")
    assert "temporalTrack" in html and "timeDial" in html
    assert "ракурс" in html and "не" in html
    assert "clueFilters" in html and "quizAnswers" in html
    assert "madeleine-dossier-20261103.json" in html
    assert 'href="detective/"' in (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'href="../detective/"' in (ROOT / "journeys/index.html").read_text(encoding="utf-8")
