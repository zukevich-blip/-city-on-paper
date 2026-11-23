#!/usr/bin/env python3
"""Validate IIIF Presentation manifests and produce a machine-readable intake report.

No bypass, retries on 403/429, or automatic public publication.
Usage: python tools/research/check_iiif_benoist.py \
    --catalog research/collections/benoist-paris-musees-batch-02.json --out /tmp/benoist-iiif-report.json
"""

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path


def extract_services(manifest):
    services = []
    for item in manifest.get("items", []):
        for page in item.get("items", []):
            for anno in page.get("items", []):
                body = anno.get("body", {})
                for svc in body.get("service", []):
                    services.append(svc.get("id") or svc.get("@id"))
    for sequence in manifest.get("sequences", []):
        for canvas in sequence.get("canvases", []):
            for image in canvas.get("images", []):
                resource = image.get("resource", {})
                for svc in resource.get("service", []):
                    services.append(svc.get("@id") or svc.get("id"))
    return sorted(set(s for s in services if s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=15)
    args = ap.parse_args()
    data = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    results = []
    for record in data["records"]:
        url = record.get("iiif_manifest")
        result = {"id": record["id"], "manifest": url, "status": "no_manifest", "services": []}
        if url:
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "Accept": "application/ld+json, application/json",
                        "User-Agent": "CityOnPaperResearch/1.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=args.timeout) as response:
                    doc = json.load(response)
                result["status"] = (
                    "valid_manifest" if doc.get("items") or doc.get("sequences") else "unexpected_structure"
                )
                result["services"] = extract_services(doc)
                result["label"] = doc.get("label")
            except urllib.error.HTTPError as exc:
                result["status"] = "http_error"
                result["http_status"] = exc.code
            except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
                result["status"] = "fetch_error"
                result["error"] = str(exc)[:240]
        results.append(result)
    output = {
        "source_catalog": args.catalog,
        "results": results,
        "verified": sum(x["status"] == "valid_manifest" for x in results),
        "images_downloaded": 0,
        "viewpoint_pairs_verified": 0,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(results), "verified": output["verified"], "output": args.out}))


if __name__ == "__main__":
    main()
