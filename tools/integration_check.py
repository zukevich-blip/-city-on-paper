#!/usr/bin/env python3
"""Fail-closed audit of a built City on Paper site and optional catalog/GCP data.

Reuses the repository's existing tools/release/audit_public_links.py rather
than pretending external URLs or rendered pixels have been checked.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from urllib.parse import unquote, urlsplit

PROJECT_PREFIX = "/-city-on-paper/"


def load_link_auditor(script: Path):
    if not script.is_file():
        raise FileNotFoundError(f"Required existing local link auditor missing: {script}")
    spec = importlib.util.spec_from_file_location("city_on_paper_audit_public_links", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load link auditor: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "check_site", None)):
        raise ValueError("Existing link auditor lacks check_site(root) contract")
    return module.check_site


def validate_catalog(path: Path, root: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Required catalog missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError("Catalog must contain a nonempty list or {'items': [...]} object")
    errors: list[str] = []
    refs_count = external_count = 0
    for number, entry in enumerate(items, 1):
        if not isinstance(entry, dict):
            errors.append(f"Item #{number}: expected object")
            continue
        url = entry.get("image_url") or entry.get("image")
        if not isinstance(url, str) or not url.strip():
            errors.append(f"Item #{number}: no image URL; cannot validate asset")
            continue
        split = urlsplit(url.strip())
        if split.scheme in {"http", "https"} and split.netloc:
            external_count += 1
            continue  # Recorded as UNVERIFIED, never silently accepted as HTTP 200.
        if split.scheme or split.netloc or not split.path or url.startswith("//"):
            errors.append(f"Item #{number}: unsupported URL: {url}")
            continue
        rel = unquote(split.path)
        if rel.startswith(PROJECT_PREFIX):
            rel = rel[len(PROJECT_PREFIX):]
        elif rel.startswith("/"):
            errors.append(f"Item #{number}: absolute path outside published prefix: {url}")
            continue
        target = (root / rel).resolve()
        if not target.is_relative_to(root.resolve()):
            errors.append(f"Item #{number}: asset escapes publication root: {url}")
        elif not target.is_file():
            errors.append(f"Item #{number}: image missing: {url}")
        else:
            refs_count += 1
    return {"records": len(items), "verified_local_assets": refs_count,
            "external_urls_unverified": external_count, "errors": errors}


def validate_gcp_dir(directory: Path) -> dict:
    if not directory.is_dir():
        raise FileNotFoundError(f"Required candidate directory missing: {directory}")
    files = sorted(directory.glob("*.json"))
    if not files:
        raise ValueError("Candidate GCP directory is empty")
    errors = []
    total = 0
    candidates = 0
    for file in files:
        try:
            d = json.loads(file.read_text(encoding="utf-8"))
            if d.get("schema_version") != "city-on-paper.gcp-candidates.v1":
                raise ValueError("schema_version mismatch")
            if d.get("status") not in {"auto_fail", "candidate_auto"}:
                raise ValueError("unrecognized or falsely verified status")
            if d.get("review_required") is not True or d.get("scientific_accuracy_verified") is not False:
                raise ValueError("machine outputs must explicitly remain unverified")
            points = d.get("gcp_pairs")
            if not isinstance(points, list):
                raise ValueError("gcp_pairs must be a list")
            for p in points:
                if p.get("status") != "unverified_machine_match":
                    raise ValueError("GCP falsely marked as verified")
                for k in ("source_pixel", "reference_pixel"):
                    xy = p.get(k)
                    if not (isinstance(xy, list) and len(xy) == 2 and
                            all(isinstance(v, (int, float)) and math.isfinite(v) for v in xy)):
                        raise ValueError(f"invalid pixel coordinate {k}")
                if "longitude_latitude" in p:
                    ll = p["longitude_latitude"]
                    if not (isinstance(ll, list) and len(ll) == 2 and
                            all(isinstance(v, (int, float)) and math.isfinite(v) for v in ll)
                            and -180 <= ll[0] <= 180 and -90 <= ll[1] <= 90):
                        raise ValueError("invalid lon/lat")
            if d["status"] == "candidate_auto" and len(points) < 4:
                raise ValueError("candidate_auto needs 4+ point pairs")
            if d["status"] == "candidate_auto":
                candidates += 1
            total += 1
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as ex:
            errors.append(f"{file}: {ex}")
    return {"files": len(files), "validated_json_files": total,
            "machine_candidates": candidates, "errors": errors}


def check(root: Path, auditor_script: Path, catalog: Path | None = None,
          gcp_dir: Path | None = None) -> dict:
    result = {"status": "FAIL", "checks": {}, "errors": [],
              "not_checked": ["External HTTP availability", "JS-created dynamic references",
                              "Browser visual alignment", "Historical landmark correctness"]}
    errors = result["errors"]
    if not root.is_dir() or not (root / "index.html").is_file():
        errors.append(f"Published site root missing index.html: {root}")
    else:
        try:
            audited = load_link_auditor(auditor_script)(root)
            if not isinstance(audited, dict) or "broken_local_references" not in audited:
                raise ValueError("Auditor returned invalid result")
            result["checks"]["public_html_links"] = audited
            if audited["broken_local_references"]:
                errors.append(f"Broken internal site links: {audited['broken_local_references']}")
        except Exception as ex:
            errors.append(f"Local link audit failed: {ex}")
    if catalog is not None:
        try:
            c = validate_catalog(catalog, root)
            result["checks"]["catalog"] = c
            errors.extend(c["errors"])
        except Exception as ex:
            errors.append(f"Catalog audit failed: {ex}")
    else:
        result["not_checked"].append("Catalog image URL inventory (no --catalog supplied)")
    if gcp_dir is not None:
        try:
            g = validate_gcp_dir(gcp_dir)
            result["checks"]["gcp_candidates"] = g
            errors.extend(g["errors"])
        except Exception as ex:
            errors.append(f"GCP candidate audit failed: {ex}")
    else:
        result["not_checked"].append("Machine GCP candidate files (no --gcp-dir supplied)")
    if not errors and "public_html_links" in result["checks"]:
        result["status"] = "PASS_SCOPED"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--auditor", type=Path, default=Path("tools/release/audit_public_links.py"))
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--gcp-dir", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = check(args.root, args.auditor, args.catalog, args.gcp_dir)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "errors": result["errors"],
                      "not_checked": result["not_checked"], "report": str(args.report)},
                     ensure_ascii=False))
    return 0 if result["status"] == "PASS_SCOPED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
