"""Prepare a public *subset* of the verified museum bundle for GitHub Pages.

The source repository is private but GitHub Pages is usually public.
Do not expose the unpublished 1,019-item research ledger or internal consilia.
This script is deliberately separate from the private/portable ZIP.
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

EXCLUDE = (
    "data/candidates",
    "data/curation/world-graphic-progress-v1.json",
    "docs/consilium",
    "docs/ux/mockups",
    "PROJECT_HANDOFF.md",
    "RELEASE_QA.json",
    "art-cache-report.json",
    "world-graphic-report.json",
    "museum-expansion-report.json",
    "modern-photo-discovery-report.json",
    "featured-cities-report.json",
    "serve_local.py",
)
REQUIRED = (
    "index.html", "salon/index.html", "world/index.html",
    "photography/index.html", "exhibitions/lost-florence/index.html",
    "poc/compare/index.html", "data/curation/benoist-paris-musees-v1.json",
    "data/curation/world-graphic-archive-v1.json",
)


def prepare(source: Path, target: Path) -> dict:
    source, target = source.resolve(), target.resolve()
    if source == target or target.is_relative_to(source):
        raise ValueError("Public output must be separate from the private bundle")
    for rel in REQUIRED:
        if not (source / rel).is_file():
            raise FileNotFoundError(source / rel)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)

    for rel in EXCLUDE:
        item = target / rel
        if item.is_dir():
            shutil.rmtree(item)
        elif item.exists():
            item.unlink()

    html_count = 0
    for path in target.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        if "</head>" not in text:
            raise ValueError(f"Missing HTML head: {path}")
        text = text.replace(
            "</head>",
            '<meta name="robots" content="noindex,nofollow,noarchive"></head>',
            1,
        )
        if path == target / "index.html":
            # Unreviewed research is for the local archive, not a public link.
            text = re.sub(
                r'<button\s+data-go="research"\s*>[^<]*</button>', "", text
            )
            text = re.sub(
                r'(<section\s+id="research"\s+class="tab wrap")',
                r'\1 hidden',
                text,
                count=1,
            )
        path.write_text(text, encoding="utf-8")
        html_count += 1

    (target / ".nojekyll").touch()
    (target / "robots.txt").write_text(
        "User-agent: *\nDisallow: /\n", encoding="utf-8"
    )
    (target / "ABOUT_PUBLIC_PREVIEW.txt").write_text(
        "City on Paper — public preview of the private repository.\n"
        "This static website may be reachable by anyone who has the URL.\n"
        "No user photos or local bookmarks are sent to this deployment.\n"
        "The unpublished research candidate ledger and internal consilia "
        "are intentionally excluded.\n"
        "Image licenses and attributions are available in artwork cards.\n"
        "No-index metadata is not password protection.\n",
        encoding="utf-8",
    )
    assert not (target / "data/candidates").exists()
    assert not (target / "docs/consilium").exists()
    return {
        "html_pages": html_count,
        "files": len([p for p in target.rglob("*") if p.is_file()]),
        "research_ledger_excluded": True,
        "publicly_accessible": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.source, args.out))


if __name__ == "__main__":
    main()
