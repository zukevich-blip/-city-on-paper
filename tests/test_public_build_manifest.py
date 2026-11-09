"""Regression tests for the actual public museum publication manifest."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.generate_build_manifest import generate, validate
from tools.release.build_public_site import build


def setup_site(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    policy_path = tmp_path / "policy.json"
    files = {
        "index.html": (
            "<!doctype html><html><head><title>City on Paper</title>"
            "</head><body><footer></footer></body></html>"
        ),
        "salon/index.html": "<html><head><title>Salon</title></head><body>Art</body></html>",
        "data/curation/world-cities-v1.json": json.dumps({
            "city_count": 1,
            "cities": [{"name": "Париж", "country": "France"}],
        }, ensure_ascii=False),
        "eras/viewer.js": "window.preview = true;",
        "eras/art/scan.jpg": "fake-image-bytes",
        "eras/notes.md": "Internal notes that are NOT permitted by extension",
        "data/candidates/do-not-publish.json": '{"secret":"unreviewed"}',
    }
    for rel, value in files.items():
        out = source / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(value, encoding="utf-8")
    policy_path.write_text(json.dumps({
        "schema": "city-on-paper/publication-policy/v1",
        "pages": ["index.html", "salon/index.html"],
        "data": ["data/curation/world-cities-v1.json"],
        "asset_roots": ["eras"],
        "asset_extensions": [".js", ".jpg"],
        "forbidden_paths": ["data/candidates", ".github", "docs/consilium"],
        "forbidden_path_parts": [".git", ".github", "private", "secrets", ".env"],
        "forbidden_suffixes": [".pem", ".key", ".db"],
    }), encoding="utf-8")
    return source, policy_path


def test_manifest_is_deterministic_and_restricted(tmp_path: Path) -> None:
    source, policy = setup_site(tmp_path)
    manifest = generate(source, policy)
    assert manifest == generate(source, policy)
    assert manifest["summary"]["files"] == 5
    assert "data/candidates/do-not-publish.json" not in {x["path"] for x in manifest["files"]}
    assert "eras/notes.md" not in {x["path"] for x in manifest["files"]}
    assert manifest["summary"]["ignored"] == [
        {"path": "eras/notes.md", "reason": "unsupported_extension"}
    ]
    validate(source, manifest, policy)


def test_build_only_selected_files_and_metadata(tmp_path: Path) -> None:
    source, policy = setup_site(tmp_path)
    manifest = generate(source, policy)
    manifest_path = tmp_path / "BUILD_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "public"
    result = build(source, out, manifest_path, policy)
    assert result["manifest_files"] == 5
    assert (out / "BUILD_MANIFEST.json").exists()
    assert (out / "PUBLIC_BUILD.json").exists()
    assert (out / "salon/index.html").exists()
    assert (out / "eras/art/scan.jpg").exists()
    assert not (out / "data/candidates").exists()
    assert not (out / "eras/notes.md").exists()
    assert (out / "about/index.html").exists()
    assert "sitemap.xml" in [p.name for p in out.iterdir()]
    assert "canonical" in (out / "index.html").read_text(encoding="utf-8")


def test_changed_file_invalidates_manifest(tmp_path: Path) -> None:
    source, policy = setup_site(tmp_path)
    m = generate(source, policy)
    (source / "eras/viewer.js").write_text("new source bytes", encoding="utf-8")
    with pytest.raises(ValueError, match="Manifest does not match"):
        validate(source, m, policy)


def test_injected_unapproved_file_is_rejected(tmp_path: Path) -> None:
    source, policy = setup_site(tmp_path)
    hidden = source / "data/curation/internal-unapproved.json"
    hidden.write_text('{"exists":true}', encoding="utf-8")
    m = generate(source, policy)
    from tools.generate_build_manifest import sha256
    m["files"].append({
        "path": "data/curation/internal-unapproved.json", "kind": "data",
        "size": hidden.stat().st_size, "sha256": sha256(hidden),
    })
    with pytest.raises(ValueError, match="Manifest does not match"):
        validate(source, m, policy)


def test_bad_city_seed_fails_closed(tmp_path: Path) -> None:
    source, policy = setup_site(tmp_path)
    (source / "data/curation/world-cities-v1.json").write_text(
        json.dumps({"city_count": 1, "cities": [{"name": "", "country": "France"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid city name"):
        generate(source, policy)


def test_secret_in_asset_root_blocks_build(tmp_path: Path) -> None:
    source, policy = setup_site(tmp_path)
    secret = source / "eras/secrets/password.js"
    secret.parent.mkdir(parents=True)
    secret.write_text("const foo = 1;", encoding="utf-8")
    with pytest.raises(ValueError, match="Restricted file"):
        generate(source, policy)


def test_invalid_policy_and_symlinks(tmp_path: Path) -> None:
    source, policy = setup_site(tmp_path)
    doc = json.loads(policy.read_text(encoding="utf-8"))
    doc["pages"].append("../another.html")
    policy.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="Unnormalized"):
        generate(source, policy)
    doc["pages"].pop()
    policy.write_text(json.dumps(doc), encoding="utf-8")
    (source / "eras/other.jpg").symlink_to(source / "eras/art/scan.jpg")
    with pytest.raises(ValueError, match="Symlink"):
        generate(source, policy)


def test_private_key_payload_is_not_copied(tmp_path: Path) -> None:
    source, policy = setup_site(tmp_path)
    (source / "eras/viewer.js").write_text(
        "/* -----BEGIN PRIVATE KEY----- */", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Embedded private key"):
        generate(source, policy)
