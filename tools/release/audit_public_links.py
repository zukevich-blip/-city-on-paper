"""Audit static HTML references in a GitHub Pages distribution.

It checks *local* links and referenced assets; external URLs need a separate online
crawl and are never silently called valid. Dynamic JS-created URLs are out of scope.
"""
from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

PROJECT_PREFIX = "/-city-on-paper/"
IGNORE_SCHEMES = ("http:", "https:", "mailto:", "tel:", "data:", "blob:", "javascript:")


class Refs(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.local: list[tuple[str, str, str]] = []
        self.external: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        for attr in ("href", "src"):
            raw = data.get(attr)
            if not raw:
                continue
            url = raw.strip()
            if url.startswith("#") or url.startswith("//"):
                continue
            if url.lower().startswith(IGNORE_SCHEMES):
                if url.lower().startswith(("http:", "https:")):
                    self.external.append(url)
                continue
            if url.startswith("/"):
                # A root-absolute link on GitHub Pages is a common broken path.
                self.local.append((tag, attr, url))
            else:
                self.local.append((tag, attr, url))
        if data.get("srcset"):
            for entry in data["srcset"].split(","):
                candidate = entry.strip().split(" ")[0]
                if candidate and not candidate.startswith(("http:", "https:", "data:")):
                    self.local.append((tag, "srcset", candidate))


def check_site(root: Path) -> dict:
    root = root.resolve()
    if not (root / "index.html").exists():
        raise FileNotFoundError("Missing public/index.html")
    missing = []
    references = 0
    external: set[str] = set()
    pages = sorted(root.rglob("*.html"))
    for page in pages:
        parser = Refs()
        parser.feed(page.read_text(encoding="utf-8"))
        external.update(parser.external)
        for tag, attr, raw in parser.local:
            references += 1
            path = unquote(urlsplit(raw).path)
            if not path:
                continue
            if path.startswith("/"):
                if path.startswith(PROJECT_PREFIX):
                    path = path[len(PROJECT_PREFIX):]
                    target = root / path
                else:
                    missing.append({"page": str(page.relative_to(root)), "tag": tag,
                                    "attribute": attr, "target": raw,
                                    "why": "root_absolute_outside_project"})
                    continue
            else:
                target = page.parent / path
            resolved = target.resolve()
            if not resolved.is_relative_to(root):
                missing.append({"page": str(page.relative_to(root)), "tag": tag,
                                "attribute": attr, "target": raw,
                                "why": "path_escapes_public_root"})
                continue
            if resolved.is_dir():
                resolved = resolved / "index.html"
            if not resolved.is_file():
                missing.append({"page": str(page.relative_to(root)), "tag": tag,
                                "attribute": attr, "target": raw, "why": "missing_file"})
    return {
        "html_pages": len(pages), "checked_local_references": references,
        "external_references_not_http_verified": len(external),
        "broken_local_references": len(missing), "issues": missing,
        "scope": "Static HTML href/src/srcset only; no JS-generated links or external HTTP status"
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    report = check_site(args.root)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print("LINK AUDIT", json.dumps({k: v for k, v in report.items() if k != "issues"},
                                   ensure_ascii=False))
    for issue in report["issues"][:35]:
        print("BROKEN", issue)
    if args.strict and report["broken_local_references"]:
        raise SystemExit(1)
