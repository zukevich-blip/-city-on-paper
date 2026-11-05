"""Public preview must exclude private research, even with a private repo."""
from pathlib import Path

from tools.release.make_public_preview import REQUIRED, prepare


def test_public_preview_strips_internal_catalogue_and_discourages_indexing(tmp_path: Path):
    source = tmp_path / "source"
    target = tmp_path / "public"
    for relative in REQUIRED:
        file = source / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        if file.suffix == ".html":
            file.write_text(
                '<!doctype html><html><head></head><body>'
                '<button data-go="research">Поиск в архивах</button>'
                '<section id="research" class="tab wrap"></section>'
                '</body></html>', encoding="utf-8",
            )
        else:
            file.write_text("{}", encoding="utf-8")
    (source / "data/candidates").mkdir(parents=True)
    (source / "data/candidates/restricted.json").write_text("private", encoding="utf-8")
    (source / "docs/consilium").mkdir(parents=True)
    (source / "docs/consilium/NOT_FOR_WEB.md").write_text("private", encoding="utf-8")

    report = prepare(source, target)
    home = (target / "index.html").read_text(encoding="utf-8")
    assert report["html_pages"] >= 5
    assert "data-go=\"research\"" not in home
    assert 'id="research" class="tab wrap" hidden' in home
    assert '<meta name="robots" content="noindex,nofollow,noarchive">' in home
    assert (target / "world/index.html").exists()
    assert not (target / "data/candidates").exists()
    assert not (target / "docs/consilium").exists()
    assert (target / ".nojekyll").exists()
    assert "Disallow: /" in (target / "robots.txt").read_text(encoding="utf-8")


def test_public_preview_must_not_overwrite_source(tmp_path: Path):
    from pytest import raises

    source = tmp_path / "source"
    source.mkdir()
    with raises(ValueError):
        prepare(source, source)
