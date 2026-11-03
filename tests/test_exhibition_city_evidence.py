"""Editorial routes must point to real CC0 records and provide a complete narrative."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_exhibition_sources_and_interactions():
    html = (ROOT / "exhibitions/city-as-evidence/index.html").read_text(encoding="utf-8")
    museum = json.loads((ROOT / "data/curation/cc0-gallery-20261103.json").read_text(encoding="utf-8"))
    works = {art["id"]: art for art in museum["items"]}
    selected = [
        "cma-1922-225", "cma-1922-5", "cma-1967-187",
        "cma-1951-83", "cma-1962-169", "cma-1930-23",
        "cma-1946-36-20", "cma-1946-36-22", "cma-1987-80",
    ]
    for work_id in selected:
        assert work_id in html, f"Missing editorial reference: {work_id}"
        assert work_id in works, f"Missing museum source: {work_id}"
        assert works[work_id]["rights"] == "cc0"
        assert works[work_id]["url"].startswith("https://")
        assert works[work_id]["image"].startswith("https://")

    assert "museum" not in html.lower() or "source" in html
    assert 'id="routes"' in html
    assert 'id="next"' in html
    assert 'id="prev"' in html
    assert 'id="compare"' in html
    assert 'aria-pressed' in html
    assert "innerHTML" not in html
    assert "fetch('../../data/curation/cc0-gallery-20261103.json')" in html
