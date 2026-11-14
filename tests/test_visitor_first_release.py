"""Visitor-first museum invariants and publication-contract smoke checks."""
from pathlib import Path

from tools.release.build_public_site import PAGES

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_visitor_routes_are_shipped_in_public_bundle():
    assert {"walk/index.html", "submit/index.html"} <= set(PAGES)
    home = read("index.html")
    assert 'class="museum-frontdoor museum-wow"' in home
    assert 'class="wow-features"' in home
    assert 'href="poc/compare/#madeleine-ph-benoist"' in home
    assert 'id="museumFind"' in home
    assert 'href="walk/?city=paris&amp;place=0"' in home
    assert 'href="submit/"' in home
    nav = read("assets/nav/museum-nav.js")
    assert '["walk/", "Маршрут по времени"' in nav
    assert '["submit/", "Предложить находку"' in nav


def test_historical_routes_keep_originals_and_say_when_no_modern_pair():
    walk = read("walk/index.html")
    for text in ("../eras/data/eras.json", "object-fit:contain",
                 "Другой исторический год", "точные точки съёмки",
                 "selectedCity", "selectedPlace", "rights_class"):
        assert text in walk
    assert "document.getElementById" in walk
    assert 'pair.hidden=selectedCity!=="paris"||index!==0;' in walk


def test_photo_submission_is_manual_and_license_checked():
    submit = read("submit/index.html")
    assert "публичное обращение GitHub" in submit
    assert "не отправляется" in submit
    assert "github.com/zukevich-blip/-city-on-paper/issues/new?" in submit
    assert "URL.createObjectURL" in submit
    assert "Статус прав" in submit


def test_mobile_image_and_book_are_not_hard_clipped():
    book = read("experience/styles.css")
    salon = read("salon/index.html")
    assert "position:relative!important" in book
    assert "height:auto!important" in book
    assert "min-height:44px" in book
    assert "#viewer[open]{display:flex" in salon
    assert "#viewerStage{flex:1 1 auto" in salon
    assert ".viewerTools{display:grid" in salon
