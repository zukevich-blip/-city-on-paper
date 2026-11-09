"""Protect the public museum output against leakage and accidental source overwrites."""
import json
from pathlib import Path

import pytest

from tools.generate_build_manifest import DEFAULT_POLICY
from tools.release.build_public_site import build

POLICY = json.loads(DEFAULT_POLICY.read_text(encoding="utf-8"))



def make_mock_source(root: Path) -> None:
    for rel in POLICY["pages"]:
        page = root / rel
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(
            '<!doctype html><html lang="ru"><head><title>Музей</title></head>'
            '<body><button data-go="research">Поиск в архивах</button>'
            '<section id="research" class="tab wrap">Черновики</section>'
            '</body></html>',
            encoding="utf-8",
        )
    for rel in POLICY["data"]:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith("world-cities-v1.json"):
            value = {"city_count": 1, "cities": [{"name": "Париж", "country": "France"}]}
        else:
            value = {}
        target.write_text(
            "id,name\n1,demo\n" if target.suffix == ".csv" else json.dumps(value),
            encoding="utf-8",
        )
    for rel in POLICY["support_files"]:
        support = root / rel
        support.parent.mkdir(parents=True, exist_ok=True)
        support.write_text("Required public attribution or vendor license", encoding="utf-8")
    secret = root / "data/candidates/NOT_FOR_PUBLICATION.json"
    secret.parent.mkdir(parents=True, exist_ok=True)
    secret.write_text('{"owner_notes":"sensitive"}', encoding="utf-8")
    private = root / "docs/consilium/private.txt"
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_text("internal", encoding="utf-8")


def test_public_site_is_allowlisted_and_indexable(tmp_path: Path) -> None:
    source, output = tmp_path / "source", tmp_path / "public"
    make_mock_source(source)
    report = build(source, output)

    assert report["html_pages"] == len(POLICY["pages"]) + 4
    assert (output / "index.html").exists()
    assert (output / "about/index.html").exists()
    assert (output / "rights/index.html").exists()
    assert (output / "privacy/index.html").exists()
    assert (output / "contribute/index.html").exists()
    assert "Предложить произведение" in (output / "contribute/index.html").read_text(encoding="utf-8")
    assert (output / "sitemap.xml").exists()
    assert (output / ".nojekyll").exists()
    assert (output / "robots.txt").read_text(encoding="utf-8").startswith("User-agent: *\nAllow: /")
    assert not (output / "data/candidates").exists()
    assert not (output / "docs/consilium").exists()
    assert not (output / "PROJECT_HANDOFF.md").exists()
    assert (source / "data/candidates/NOT_FOR_PUBLICATION.json").exists()

    home = (output / "index.html").read_text(encoding="utf-8")
    assert 'data-go="research"' not in home
    assert 'id="research" class="tab wrap" hidden' in home
    assert 'name="robots" content="index,follow' in home
    assert 'rel="canonical"' in home
    assert "application/ld+json" in home


def test_public_site_prevents_overwriting_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(ValueError):
        build(source, source)
    with pytest.raises(ValueError):
        build(source, source / "child")
