"""Smoke checks for the source-backed salon discovery UI."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_salon_uses_curated_cc0_catalog():
    html = (ROOT / "salon/index.html").read_text(encoding="utf-8")
    dataset = json.loads((ROOT / "data/curation/cc0-gallery-20261103.json").read_text(encoding="utf-8"))
    assert "cc0-gallery-20261103.json" in html
    assert len(dataset["items"]) >= 30
    assert all(x["rights"] == "cc0" for x in dataset["items"])
    assert all(x.get("url", "").startswith("https://") for x in dataset["items"])
    assert all(x.get("image", "").startswith("https://") for x in dataset["items"])


def test_salon_features_and_no_remote_collection_upload():
    html = (ROOT / "salon/index.html").read_text(encoding="utf-8")
    for identifier in ('id="query"', 'id="city"', 'id="era"', 'id="surprise"', 'id="saved"', 'id="viewer"'):
        assert identifier in html
    assert "localStorage" in html
    assert "fetch('../data/curation/cc0-gallery-20261103.json')" in html
    assert "target='_blank'" in html or 'target="_blank"' in html
