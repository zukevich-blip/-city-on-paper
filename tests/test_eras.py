"""Issue #34 'Atlas of eras' prototype: data integrity, rights and reproducibility (offline)."""
import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from tools.eras.build_eras import build

ROOT = Path(__file__).resolve().parents[1]
ERAS = ROOT / "eras"
DATA = json.loads((ERAS / "data" / "eras.json").read_text("utf-8"))
IMAGES = [(c["id"], p, i) for c in DATA["cities"] for p in c["places"] for i in p["images"]]


def test_committed_json_is_reproducible():
    assert build() == DATA


def test_counts_are_real():
    assert len(DATA["cities"]) == 3
    assert sum(len(c["places"]) for c in DATA["cities"]) == 6
    assert sum(1 for *_, i in IMAGES if i.get("file")) >= 15


@pytest.mark.parametrize("cid,place,img", IMAGES, ids=[i["id"] for *_, i in IMAGES])
def test_every_record_is_sourced(cid, place, img):
    assert img["institution"] and img["object_url"].startswith("https://")
    assert img["rights"] and img["rights_class"] in {"open", "link"}
    assert img["era"] in {"print", "photo", "today"}
    if img.get("file"):
        assert img["rights_class"] == "open", "only rights-checked images may be embedded"
        f = ERAS / img["file"]
        assert hashlib.sha256(f.read_bytes()).hexdigest() == img["sha256"]


def test_historic_files_are_byte_copies_of_curator_downloads():
    cur = json.loads((ROOT / "data/vision-lab/sources-eras-curator.json").read_text("utf-8"))
    by_id = {i["id"]: i for c in cur["cities"].values() for p in c["places"].values() for i in p["images"]}
    checked = 0
    for *_, img in IMAGES:
        src = by_id.get(img["id"])
        if src and img.get("file") and img["era"] != "today":
            assert img["sha256"] == src["sha256"]
            checked += 1
    assert checked >= 10


def test_modern_photos_carry_no_exif_and_derivatives_are_labelled():
    for *_, img in IMAGES:
        if img["era"] == "today" and img.get("file"):
            exif = Image.open(ERAS / img["file"]).getexif()
            assert 0x8825 not in exif, f"GPS in {img['file']}"
            if img["id"].startswith("derived-"):
                assert "производн" in (img.get("note", "") + img["title"] + img["rights"])


def test_pairs_reference_existing_images_and_never_claim_close_without_review():
    for c in DATA["cities"]:
        for p in c["places"]:
            ids = {i["id"] for i in p["images"]}
            for pair in p["pairs"]:
                assert pair["a"] in ids and pair["b"] in ids
                assert pair["rating"] in {"close", "partial", "different_viewpoint"}
                assert pair["reason"] and pair["by"]
                if pair["rating"] == "close":
                    assert "координатор" in pair["by"]


def test_portal_and_plans_have_rights_and_files():
    P = DATA["portal"]
    assert (ERAS / P["image"]).exists() and P["rights_class"] == "open"
    assert set(P["pins"]) == {c["id"] for c in DATA["cities"]}
    for c in DATA["cities"]:
        if c.get("plan"):
            assert (ERAS / c["plan"]["image"]).exists()
            w, h = Image.open(ERAS / c["plan"]["image"]).size
            assert (w, h) == (c["plan"]["width"], c["plan"]["height"])


def test_story_html_has_only_https_links_and_no_script():
    for c in DATA["cities"]:
        for p in c["places"]:
            s = p.get("story", "")
            assert "<script" not in s.lower()
            assert 'href="http:' not in s and "javascript:" not in s


def test_camera_points_fall_inside_the_plan_detail():
    p = DATA["cities"][0]["places"][0]
    d = p["plan_detail"]
    cams = [i["camera"] for i in p["images"] if i.get("camera", {}).get("px") is not None]
    assert len(cams) >= 5
    for c in cams:
        assert 0 <= c["px"] <= d["width"] and 0 <= c["py"] <= d["height"]


def test_share_alike_and_derivatives_disclose_licence_and_changes():
    imgs = {i["id"]: i for *_, i in IMAGES}
    sa = imgs["panoramax-38b6d262-648f-461e-b9a3-ab05eb22d92a"]
    assert sa["license_url"].startswith("https://creativecommons.org/licenses/by-sa/4.0")
    assert "Изменения" in sa["rights"] and "jerome92370" in sa["rights"]
    for i in imgs.values():
        if i["id"].startswith("derived-"):
            assert i["license_url"].startswith("https://") and "Производная" in i["rights"]


def test_portal_pins_match_reviewed_glyph_positions():
    pins = DATA["portal"]["pins"]
    assert (pins["florence"]["x"], pins["florence"]["y"]) == (812, 1168)  # not Lucca (786,1161)
    assert (pins["naples"]["x"], pins["naples"]["y"]) == (885, 1294)  # coast glyph, not the sea


ATLAS = json.loads((ERAS / "data" / "atlas.json").read_text("utf-8"))


def test_atlas_cities_are_valid_and_unique():
    ids = [c["id"] for c in ATLAS["cities"]]
    assert len(ids) == len(set(ids)) and len(ids) >= 180
    for c in ATLAS["cities"]:
        assert -30 < c["lon"] < 60 or c["country"] in {"Бразилия", "Канада"}, c["name"]
        assert 0 < c["lat"] < 72 or c["country"] == "Бразилия", c["name"]
        if c["xy"]:
            assert 0 <= c["xy"][0] <= ATLAS["portal"]["width"] and 0 <= c["xy"][1] <= ATLAS["portal"]["height"]


def test_benoist_works_are_sourced_and_only_open_images_embedded():
    works = [w for c in ATLAS["cities"] for w in c["works"]]
    assert len(works) >= 300
    for w in works:
        assert w["url"].startswith(("https://", "http://")), w
        if "gallica.bnf.fr" in w["url"]:
            assert w["url"].startswith("https://"), w
        assert w["artist"] and "Guillaume" not in w["artist"]
        if w["image"]:
            assert w["rights_class"] == "open" and w["image"].startswith("https://")
        else:
            assert w["rights_class"] in {"open", "link"}


def test_atlas_build_is_reproducible():
    from tools.eras.build_atlas import build as build_atlas
    assert build_atlas() == ATLAS
