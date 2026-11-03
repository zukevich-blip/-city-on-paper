"""Validate source provenance, editorial lessons and safe museum-viewer structure."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relpath: str) -> dict:
    return json.loads((ROOT / relpath).read_text(encoding="utf-8"))


def test_all_close_reading_lessons_have_real_source_objects():
    lessons = load("data/curation/close-reading-20261103.json")["lessons"]
    cc0 = {x["id"]: x for x in load("data/curation/cc0-gallery-20261103.json")["items"]}
    loc = {x["id"]: x for x in load("data/curation/close-reading-benoist-20261103.json")["records"]}
    assert len(lessons) == 11
    assert len({x["id"] for x in lessons}) == 11
    assert len(loc) == 2
    for lesson in lessons:
        assert lesson["theme"] and lesson["tag"]
        assert len(lesson["steps"]) == 3
        assert all(step.get("label") and step.get("question") and step.get("hint") for step in lesson["steps"])
        work_id = lesson["id"]
        assert work_id in (cc0.keys() | loc.keys()), work_id
        work = cc0.get(work_id) or loc[work_id]
        assert work["url"].startswith("https://")
        if work_id in cc0:
            assert work["rights"] == "cc0"
            assert work["image"].startswith("https://")
        else:
            assert work["rights"] == "loc_no_known_restrictions"
            assert "does not own or grant rights" in work["rights_note"]
            assert work["source"] == "Library of Congress, Prints and Photographs Division"
            assert work["image"].startswith("../poc/compare/pairs/")
            image_path = ROOT / "poc/compare/pairs" / Path(work["image"]).name
            assert image_path.is_file()


def test_closeup_accessibility_privacy_and_navigation():
    html = (ROOT / "closeup/index.html").read_text(encoding="utf-8")
    for fragment in ('id="stage"', 'id="studyImage"', 'id="zoomIn"', 'id="zoomOut"',
                     'id="reset"', 'id="stepDots"', 'id="notes"', 'id="original"'):
        assert fragment in html
    assert "pointerdown" in html and "pointermove" in html
    assert "touch-action:none" in html
    assert "localStorage" in html and "textContent" in html
    assert "innerHTML" not in html
    assert "CC0" in html and "No known restrictions on publication" in html

    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    salon = (ROOT / "salon/index.html").read_text(encoding="utf-8")
    exhibition = (ROOT / "exhibitions/city-as-evidence/index.html").read_text(encoding="utf-8")
    assert 'href="closeup/"' in homepage
    assert 'href="../closeup/"' in salon
    assert "../closeup/?art=" in salon
    assert "../../closeup/?art=" in exhibition
