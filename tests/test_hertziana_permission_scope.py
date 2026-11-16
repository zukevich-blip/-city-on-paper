"""Safeguards for narrowly granted Bibliotheca Hertziana web-thumbnail permission."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERMIT = ROOT / "data/rights/hertziana-rome-web-20261116.json"


def test_hertziana_permission_scoped_not_an_open_license():
    permit = json.loads(PERMIT.read_text(encoding="utf-8"))
    assert permit["id"] == "hertziana-rome-dans-sa-grandeur-web-thumbnails-20261116"
    assert permit["correspondence"]["reply_date"] == "2026-11-16"
    scope = permit["specific_scope"]
    assert scope["website_use"].startswith("non-commercial")
    assert scope["max_image_dimension_px"] <= 1000
    assert scope["original_unmodified"] and scope["full_image_no_cropping"]
    assert {x["id"] for x in scope["catalog_records"]} == {
        "obj08003573", "obj08003574"
    }
    assert scope["total_plates_referenced_in_request"] == 40
    assert "not Creative Commons" in scope["reuse_license"]
    assert permit["publication_status"]["automatic_publication"] is False


def test_no_broad_public_domain_reclassification_before_source_checks():
    permit = json.loads(PERMIT.read_text(encoding="utf-8"))
    assert permit["publication_status"]["source_file_checks_complete"] is False
    for name in (
        "benoist-rome-grandeur-vatican-hertziana-bhfc135a54.json",
        "benoist-rome-grandeur-villa-borghese-hertziana-bhfc135b64.json",
        "benoist-rome-grandeur-civitavecchia-hertziana-bhfc135c86.json",
    ):
        work = json.loads((ROOT / "data/catalog/works" / name).read_text(encoding="utf-8"))
        assert work["rights"]["redistribution"] == "link_only"
        assert "In Copyright" in work["rights"]["image"]
