"""Offline and deterministic tests: synthetic fixtures, no claims about real museum items."""
import pytest

from tools.iiif.audit_manifest import audit


def v3(**overrides):
    doc = {
        "id": "https://museum.example.org/iiif/123/manifest",
        "type": "Manifest",
        "label": {"fr": ["Vue de la ville"], "ru": ["Вид города"]},
        "rights": "http://creativecommons.org/publicdomain/mark/1.0/",
        "requiredStatement": {"label": {"en": ["Attribution"]}, "value": {"en": ["Example museum"]}},
        "items": [{"type": "Canvas", "items": [{"type": "AnnotationPage", "items": [{
            "type": "Annotation", "motivation": "painting",
            "body": {"type": "Image", "service": [
                {"id": "https://images.example.org/iiif/123", "type": "ImageService3"}
            ]},
        }]}]}],
    }
    return {**doc, **overrides}


def v2():
    return {
        "@id": "https://museum.example.org/iiif/old/manifest", "@type": "sc:Manifest",
        "label": "Old engraving", "license": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "Example Archive", "sequences": [{"canvases": [{
            "images": [{"resource": {"service": {"@id": "https://images.example.org/v2/old"}}}]
        }]}],
    }


def test_v3_extracts_image_service_and_multilingual_title():
    out = audit(v3())
    assert out["iiif_presentation_version"] == 3
    assert out["title_as_supplied"] == "Вид города"
    assert out["image_service_ids"] == ["https://images.example.org/iiif/123"]
    assert out["canvas_count"] == 1
    assert out["credit_as_supplied"] == "Example museum"


def test_v2_is_supported():
    out = audit(v2())
    assert out["iiif_presentation_version"] == 2
    assert out["image_service_ids"] == ["https://images.example.org/v2/old"]
    assert out["rights_as_supplied"].endswith("/by/4.0/")


def test_rights_statement_never_grants_publication():
    out = audit(v3())
    assert out["publishable"] is False
    assert out["rights_clearance"] == "not_checked"
    assert out["status"] == "needs_curator_review"
    assert out["depicted_place"] is None
    assert out["artist_viewpoint"] is None


def test_missing_rights_and_service_require_fallback():
    out = audit(v3(rights=None, items=[{"type": "Canvas", "items": []}]))
    assert out["image_service_ids"] == []
    assert any("rights" in w for w in out["warnings"])
    assert any("fallback" in w for w in out["warnings"])


def test_duplicate_services_deduplicated():
    doc = v3()
    item = doc["items"][0]["items"][0]["items"][0]
    doc["items"][0]["items"][0]["items"].append(dict(item))
    assert len(audit(doc)["image_service_ids"]) == 1


@pytest.mark.parametrize("bad", [
    [], {}, {"id": "file:///secret", "type": "Manifest"},
    {"id": "https://example.org/x", "type": "Collection"},
])
def test_invalid_inputs_rejected(bad):
    with pytest.raises(ValueError):
        audit(bad)


def test_no_canvas_warns():
    out = audit(v3(items=[]))
    assert "No canvas found" in out["warnings"]
