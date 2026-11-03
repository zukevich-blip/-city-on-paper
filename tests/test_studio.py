"""Curatorial studio: public provenance may never be overwritten by collector notes."""
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data/research/benoist-production-network-v1.json"


def read_graph():
    return json.loads(GRAPH.read_text(encoding="utf-8"))


def test_provenance_graph_has_two_real_lithographs_and_only_sourced_edges():
    d = read_graph()
    assert d["schema_version"] == "1.0.0"
    assert {w["loc_id"] for w in d["works"]} == {"2016652451", "2016652452"}
    assert {w["plate"] for w in d["works"]} == {"6", "8"}
    assert len(d["connections"]) == 6
    assert len(d["research_questions"]) >= 4
    assert any(a["id"] == "publisher_unknown" and a["status"] == "unknown" for a in d["agents"])
    assert all(e["certainty"] == "documented" for e in d["connections"])
    ids = {a["id"] for a in d["agents"]} | {w["id"] for w in d["works"]}
    assert len(ids) == len(d["agents"]) + len(d["works"])
    for edge in d["connections"]:
        assert edge["from"] in ids and edge["to"] in ids
        assert urlparse(edge["source"]).hostname == "www.loc.gov"
    for work in d["works"]:
        assert urlparse(work["url"]).hostname == "www.loc.gov"
        assert work["image_id"].startswith("LC-DIG-pga-")
        assert urlparse(work["hires_url"]).hostname == "cdn.loc.gov"
        assert work["hires_url"].endswith("u.tif")
        assert (ROOT / "studio" / work["image"]).resolve().is_file()
    assert all(h["certainty"] == "candidate" and h["source"] for h in d["hypotheses"])


def test_studio_is_connected_and_local_only_for_notes():
    html = (ROOT / "studio/index.html").read_text(encoding="utf-8")
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    atlas = (ROOT / "journeys/index.html").read_text(encoding="utf-8")
    assert "benoist-production-network-v1.json" in html
    assert "city-on-paper-curatorial-notebook-v1" in html
    assert "localStorage" in html
    assert "restoreArchive" in html and "exportMarkdown" in html and "exportJson" in html
    assert "textContent" in html and "innerHTML" not in html
    assert "studio/" in home and "../studio/" in atlas
    assert "No known restrictions" in html
    assert "Не установлено" in html or "Неизвест" in html
