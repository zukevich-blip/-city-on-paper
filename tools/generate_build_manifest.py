#!/usr/bin/env python3
"""Deterministic public release manifest. Discovery never bypasses the publication policy."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

DEFAULT_POLICY = Path(__file__).resolve().parent / "release" / "publication_policy.json"
SCHEMA = "city-on-paper/build-manifest/v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_path(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("Empty or invalid publication path")
    if "\\" in value or value.startswith("/") or value.endswith("/"):
        raise ValueError(f"Unsafe publication path: {value!r}")
    path = PurePosixPath(value)
    if path.as_posix() != value or any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError(f"Unnormalized publication path: {value!r}")
    return value


def is_forbidden(rel: str, policy: dict[str, Any]) -> bool:
    parts = PurePosixPath(rel).parts
    if any(x.lower() in {v.lower() for v in policy["forbidden_path_parts"]} for x in parts):
        return True
    if any(rel == p or rel.startswith(p + "/") for p in policy["forbidden_paths"]):
        return True
    return PurePosixPath(rel).suffix.lower() in policy["forbidden_suffixes"]


def _check_file(root: Path, rel: str, policy: dict[str, Any]) -> Path:
    relative_path(rel)
    if is_forbidden(rel, policy):
        raise ValueError(f"Restricted path would enter public build: {rel}")
    path = root / rel
    if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root.parent):
        raise ValueError(f"Symlink disallowed in public build: {rel}")
    if not path.is_file():
        raise FileNotFoundError(f"Required public file missing: {rel}")
    if not path.resolve().is_relative_to(root):
        raise ValueError(f"File outside source: {rel}")
    return path


def _validate_data(path: Path, rel: str) -> None:
    if path.suffix.lower() == ".json":
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise ValueError(f"Invalid public JSON {rel}: {exc}") from exc
        if rel.endswith("/world-cities-v1.json"):
            rows = doc.get("cities")
            if not isinstance(rows, list) or not rows:
                raise ValueError("World cities seed has no cities")
            if doc.get("city_count") != len(rows):
                raise ValueError("World cities count does not match source rows")
            for i, city in enumerate(rows):
                if not isinstance(city, dict) or not isinstance(city.get("name"), str) or not city["name"].strip():
                    raise ValueError(f"Invalid city name at index {i}")
                if not city.get("country"):
                    raise ValueError(f"Missing country for city at index {i}")
    if path.suffix.lower() in {".html", ".htm"}:
        html = path.read_text(encoding="utf-8").lower()
        if "<head" not in html or "</head>" not in html:
            raise ValueError(f"Public HTML is missing <head>: {rel}")


def generate(source: Path, policy_path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    source = source.resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"Missing museum source: {source}")
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if policy.get("schema") != "city-on-paper/publication-policy/v1":
        raise ValueError("Unsupported or missing publication policy schema")
    required = ("pages", "data", "asset_roots", "asset_extensions",
                "forbidden_paths", "forbidden_path_parts", "forbidden_suffixes")
    if any(not isinstance(policy.get(k), list) for k in required):
        raise ValueError("Publication policy must contain explicit lists")
    pages, data = policy["pages"], policy["data"]
    if not pages or not data:
        raise ValueError("Publication policy has zero pages/data")
    approved_exts = {e.lower() for e in policy["asset_extensions"]}
    if any(not e.startswith(".") for e in approved_exts):
        raise ValueError("Invalid asset extension policy")
    entries: dict[str, dict[str, Any]] = {}

    def add(rel: str, kind: str) -> None:
        file = _check_file(source, rel, policy)
        if rel in entries:
            return
        if kind in ("page", "data"):
            _validate_data(file, rel)
        if file.suffix.lower() in {".js", ".json", ".html", ".css"}:
            # An accidental private key in a permitted asset is still forbidden.
            if b"-----BEGIN PRIVATE KEY-----" in file.read_bytes():
                raise ValueError(f"Embedded private key in public file: {rel}")
        entries[rel] = {
            "path": rel, "kind": kind, "size": file.stat().st_size,
            "sha256": sha256(file),
        }

    for rel in pages:
        if not rel.endswith(".html"):
            raise ValueError(f"Public page must be HTML: {rel}")
        add(rel, "page")
    for rel in data:
        add(rel, "data")

    ignored = []
    for root in policy["asset_roots"]:
        relative_path(root)
        if is_forbidden(root, policy):
            raise ValueError(f"Forbidden asset root: {root}")
        folder = source / root
        if folder.is_symlink():
            raise ValueError(f"Asset root symlink: {root}")
        if not folder.exists():
            ignored.append({"root": root, "reason": "optional_root_missing"})
            continue
        if not folder.is_dir():
            raise ValueError(f"Asset root is not a folder: {root}")
        for path in sorted(folder.rglob("*")):
            rel = path.relative_to(source).as_posix()
            if path.is_symlink():
                raise ValueError(f"Symlink in public asset root: {rel}")
            if path.is_dir():
                continue
            if is_forbidden(rel, policy):
                raise ValueError(f"Restricted file under public asset root: {rel}")
            if path.suffix.lower() not in approved_exts:
                ignored.append({"path": rel, "reason": "unsupported_extension"})
                continue
            add(rel, "asset")

    files = sorted(entries.values(), key=lambda e: e["path"])
    if not files or not any(e["kind"] == "page" for e in files):
        raise ValueError("Empty public build manifest")
    return {
        "schema": SCHEMA,
        "policy_sha256": sha256(policy_path),
        "pages": pages,
        "files": files,
        "summary": {
            "files": len(files),
            "pages": len(pages),
            "data": sum(x["kind"] == "data" for x in files),
            "assets": sum(x["kind"] == "asset" for x in files),
            "bytes": sum(x["size"] for x in files),
            "ignored": ignored,
        },
        "notes": "An allowlisted source file is NOT proof of expert artwork attribution or image rights.",
    }


def validate(source: Path, manifest: dict[str, Any], policy_path: Path = DEFAULT_POLICY) -> None:
    if manifest.get("schema") != SCHEMA:
        raise ValueError("Incorrect manifest schema")
    if manifest.get("policy_sha256") != sha256(policy_path):
        raise ValueError("Publication policy has changed since manifest generation")
    names: set[str] = set()
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    for entry in manifest.get("files", []):
        rel = relative_path(entry["path"])
        if rel in names:
            raise ValueError(f"Duplicate manifest file: {rel}")
        names.add(rel)
        actual = _check_file(source.resolve(), rel, policy)
        if actual.stat().st_size != entry["size"] or sha256(actual) != entry["sha256"]:
            raise ValueError(f"Source changed since manifest generation: {rel}")
    if not names or not set(manifest.get("pages", [])).issubset(names):
        raise ValueError("Missing approved HTML pages in manifest")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--out", type=Path, default=Path("dist/BUILD_MANIFEST.json"))
    args = ap.parse_args()
    result = generate(args.source, args.policy)
    validate(args.source, result, args.policy)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS", json.dumps(result["summary"], ensure_ascii=False))
    print("Manifest:", args.out)


if __name__ == "__main__":
    main()
