from pathlib import Path

from tools.release.audit_public_links import check_site


def test_static_links_are_checked_without_network(tmp_path: Path) -> None:
    root = tmp_path / "public"
    (root / "gallery").mkdir(parents=True)
    (root / "assets").mkdir()
    (root / "assets" / "museum.js").write_text("console.log('ready')", encoding="utf-8")
    (root / "gallery" / "index.html").write_text("<html><body>Gallery</body></html>",
                                                  encoding="utf-8")
    (root / "index.html").write_text(
        '<html><head><script src="assets/museum.js"></script></head><body>'
        '<a href="gallery/">Open gallery</a>'
        '<a href="https://example.org/source">External</a>'
        '<a href="#/city/paris">App route</a>'
        '<a href="/-city-on-paper/gallery/">Project root</a>'
        '</body></html>', encoding="utf-8"
    )
    report = check_site(root)
    assert report["broken_local_references"] == 0
    assert report["checked_local_references"] == 3
    assert report["external_references_not_http_verified"] == 1


def test_audit_reports_broken_local_and_escaped_paths(tmp_path: Path) -> None:
    root = tmp_path / "public"
    root.mkdir()
    (root / "index.html").write_text(
        '<html><script src="missing.js"></script>'
        '<a href="/wrong-root/site.html">Wrong</a>'
        '<a href="../private/key.txt">Private</a></html>',
        encoding="utf-8",
    )
    report = check_site(root)
    assert report["broken_local_references"] == 3
    assert {"missing_file", "root_absolute_outside_project", "path_escapes_public_root"} == {
        item["why"] for item in report["issues"]
    }
