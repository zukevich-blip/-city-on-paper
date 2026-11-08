#!/usr/bin/env python3
"""Prepare review-only evidence from locally saved IIIF Presentation v2/v3 manifests.

This module does not download images, infer rights, identify artists or publish assets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit


def _http_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parts = urlsplit(value)
    return value if parts.scheme in {"http", "https"} and parts.netloc else None


def _first_text(value: object) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        return next((txt for item in value if (txt := _first_text(item))), None)
    if isinstance(value, dict):
        for language in ("value", "ru", "en", "fr", "it", "none", "@value"):
            if language in value and (txt := _first_text(value[language])):
                return txt
        return next((txt for item in value.values() if (txt := _first_text(item))), None)
    return None


def _service_ids(body: object) -> list[str]:
    if not isinstance(body, dict):
        return []
    services = body.get("service", [])
    if isinstance(services, dict):
        services = [services]
    if not isinstance(services, list):
        return []
    return [identifier for service in services if isinstance(service, dict)
            if (identifier := _http_url(service.get("id") or service.get("@id")))]


def audit(manifest: dict) -> dict:
    """Normalize the source's claims for review, without verifying those claims."""
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be a JSON object")
    uri = _http_url(manifest.get("id") or manifest.get("@id"))
    if not uri:
        raise ValueError("Manifest lacks a valid http(s) id/@id")
    kind = manifest.get("type") or manifest.get("@type")
    version = 3 if kind == "Manifest" else 2 if kind == "sc:Manifest" else None
    if version is None:
        raise ValueError("Not a supported IIIF Presentation v2/v3 Manifest")

    bodies: list[dict] = []
    canvases: list[dict] = []
    if version == 3:
        canvases = [c for c in manifest.get("items", []) if isinstance(c, dict)]
        for canvas in canvases:
            for page in canvas.get("items", []):
                if not isinstance(page, dict):
                    continue
                for annotation in page.get("items", []):
                    if not isinstance(annotation, dict) or annotation.get("motivation") != "painting":
                        continue
                    body = annotation.get("body")
                    bodies.extend(b for b in (body if isinstance(body, list) else [body]) if isinstance(b, dict))
    else:
        for seq in manifest.get("sequences", []):
            if not isinstance(seq, dict):
                continue
            for canvas in seq.get("canvases", []):
                if not isinstance(canvas, dict):
                    continue
                canvases.append(canvas)
                for annotation in canvas.get("images", []):
                    if isinstance(annotation, dict) and isinstance(annotation.get("resource"), dict):
                        bodies.append(annotation["resource"])

    service_ids = list(dict.fromkeys(s for body in bodies for s in _service_ids(body)))
    rights_value = _first_text(manifest.get("rights") or manifest.get("license"))
    credit_value = _first_text(manifest.get("requiredStatement") or manifest.get("attribution"))
    warnings: list[str] = []
    if not canvases:
        warnings.append("No canvas found")
    if not service_ids:
        warnings.append("No verified IIIF Image API service URL found; retain source-page fallback")
    if not rights_value:
        warnings.append("No rights statement in manifest; check institution's object record")
    if not credit_value:
        warnings.append("No credit/required statement; check institutional attribution requirements")
    return {
        "schema_version": 1,
        "status": "needs_curator_review",
        "publishable": False,
        "iiif_presentation_version": version,
        "manifest_url": uri,
        "title_as_supplied": _first_text(manifest.get("label")),
        "rights_as_supplied": rights_value,
        "credit_as_supplied": credit_value,
        "rights_clearance": "not_checked",
        "canvas_count": len(canvases),
        "image_service_ids": service_ids,
        "depicted_place": None,
        "artist_viewpoint": None,
        "photo_camera": None,
        "author_attribution": None,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_files", nargs="+", type=Path, help="Locally saved IIIF v2/v3 JSON")
    parser.add_argument("--output", type=Path, help="Save candidate JSON; defaults to stdout")
    args = parser.parse_args()
    results: list[dict] = []
    for path in args.manifest_files:
        raw = path.read_bytes()
        entry = audit(json.loads(raw))
        entry["input_file"] = str(path)
        entry["input_sha256"] = hashlib.sha256(raw).hexdigest()
        results.append(entry)
    payload = {"schema": "city-on-paper/iiif-review-candidates/v1", "count": len(results), "candidates": results}
    output = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
