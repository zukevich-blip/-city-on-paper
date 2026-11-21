#!/usr/bin/env python3
"""Ingest Paris Musées (Musée Carnavalet) prints from the research catalogues.

Only records whose own IIIF manifest states a CC0 licence for the actual digital file are taken.
Reads research/collections/*.json (records with an ``iiif_manifest``), fetches each manifest politely,
requires the canvas metadata ``Copyright`` = CC0 public-domain-zero, downloads the ``4k`` file once,
stores a 1280 px JPEG in book/img/benoist/ and writes data/curation/benoist-parismusees-batch-v1.json.
Same-composition impressions are grouped, never counted twice.
Nothing is bypassed: any non-200 answer is recorded as a failure and the record is skipped.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOGS = sorted((ROOT / "research" / "collections").glob("*.json"))
OUT = ROOT / "data" / "curation" / "benoist-parismusees-batch-v1.json"
SEARCH = ROOT / "data" / "research" / "benoist" / "parismusees-search-v1.json"
KNOWN = ROOT / "data" / "curation" / "benoist-paris-musees-v1.json"
IMG_DIR = ROOT / "book" / "img" / "benoist"
UA = "CityOnPaperResearch/0.9 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)"
CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"
# Same composition printed twice (two museum impressions): the second one is recorded, not shown as a separate work.
DELAY = 1.1
IMPRESSION_OF = {"320288773": "320288755", "320291365": "320291352"}


def get(url: str, binary: bool = False):
    """Polite GET through curl: urllib gets truncated bodies (IncompleteRead) from this museum's CDN, curl does not."""
    last = ""
    for attempt in range(3):
        res = subprocess.run(
            ["curl", "-sS", "-L", "-m", "90", "-A", UA, "-H", "Accept: application/json", "-w", "\n%{http_code}", url],
            capture_output=True,
        )
        body, _, code = res.stdout.rpartition(b"\n")
        time.sleep(DELAY * (attempt + 1))
        if code == b"200" and body:
            return body if binary else json.loads(body)
        last = f"HTTP {code.decode(errors='replace')} {res.stderr.decode(errors='replace')[:80]}"
    raise RuntimeError(last)


def node_id(manifest_url: str) -> str:
    return re.search(r"/iiif/(\d+)/manifest", manifest_url).group(1)


def meta(manifest: dict) -> dict:
    out: dict = {}
    for m in manifest.get("metadata", []):
        out.setdefault(m["label"], m["value"])
    return out


def canvas_facts(manifest: dict) -> dict | None:
    """Return image URL and the licence the museum states for this file, or None without a canvas."""
    for seq in manifest.get("sequences", []):
        for canvas in seq.get("canvases", []):
            facts = {m["label"]: m["value"] for m in canvas.get("metadata", [])}
            images = canvas.get("images", [])
            if images:
                return {
                    "image": images[0]["resource"]["@id"],
                    "rights": facts.get("Droits", ""),
                    "licence_url": facts.get("Copyright", ""),
                }
    return None


def parse(
    manifest: dict, nid: str, record_url: str, roles: list | None = None, title: str | None = None
) -> dict | None:
    facts = canvas_facts(manifest)
    if not facts or facts["licence_url"].rstrip("/") != CC0.rstrip("/") or "CC0" not in facts["rights"]:
        return None
    md = meta(manifest)
    authors = md.get("Auteur") or []
    return {
        "id": f"parismusees-{nid}",
        "node": nid,
        "title": manifest["label"],
        "record_url": record_url,
        "manifest": f"https://apicollections.parismusees.paris.fr/iiif/{nid}/manifest",
        "holder": md.get("Institution", "Musée Carnavalet, Histoire de Paris"),
        "participants": [
            a if isinstance(a, str) else str(a) for a in (authors if isinstance(authors, list) else [authors])
        ],
        "technique": md.get("Matériaux et techniques"),
        "rights": facts["rights"],
        "rights_url": facts["licence_url"],
        "image_source": facts["image"],
        "image": f"img/benoist/pm-{nid}.jpg",
        "impression_of": IMPRESSION_OF.get(nid),
    }


def save_image(nid: str, url: str) -> None:
    from PIL import Image

    dest = IMG_DIR / f"pm-{nid}.jpg"
    if dest.exists():
        return
    im = Image.open(io.BytesIO(get(url, binary=True))).convert("RGB")
    im.thumbnail((1280, 1280))
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=84, optimize=True)


def search_records() -> list[dict]:
    """Records the search found with a manifest; each manifest is re-checked for CC0 before anything is taken."""
    if not SEARCH.exists():
        return []
    out = []
    for rec in json.loads(SEARCH.read_text(encoding="utf-8")).get("records", []):
        if rec.get("rights_status") == "open_confirmed" and rec.get("iiif_manifest"):
            roles = [
                {"name": p["name"], "role": p.get("role_as_stated")}
                for p in rec.get("participants", [])
                if p.get("name")
            ]
            out.append(
                {
                    "iiif_manifest": rec["iiif_manifest"],
                    "source_url": rec["record_url"],
                    "_roles": roles,
                    "_title": (rec.get("original_title") or "").strip().rstrip("."),
                }
            )
    return out


def main(argv: list[str]) -> int:
    """Resumable: records already in the batch file are kept, the site's 503/short reads only add to ``failures``."""
    global DELAY
    if "--delay" in argv:
        DELAY = float(argv[argv.index("--delay") + 1])
    known = {i["source_id"] for i in json.loads(KNOWN.read_text(encoding="utf-8"))["items"]}
    have = {r["node"]: r for r in json.loads(OUT.read_text(encoding="utf-8"))["records"]} if OUT.exists() else {}
    failures: list[dict] = []
    batches = [json.loads(c.read_text(encoding="utf-8")).get("records", []) for c in CATALOGS] + [search_records()]
    seen: set[str] = set()
    for records_in in batches:
        for rec in records_in:
            url = rec.get("iiif_manifest")
            if not url or node_id(url) in seen:
                continue
            nid = node_id(url)
            seen.add(nid)
            if nid in have and (IMG_DIR / f"pm-{nid}.jpg").exists():
                if rec.get("_roles") and not have[nid].get("roles"):
                    have[nid]["roles"] = rec["_roles"]
                continue
            try:
                parsed = parse(get(url), nid, rec["source_url"], rec.get("_roles"), rec.get("_title"))
                if not parsed:
                    failures.append({"node": nid, "why": "manifest does not state CC0 for the file"})
                    continue
                if "--no-images" not in argv:
                    save_image(nid, parsed["image_source"])
                parsed["known_before"] = nid in known
                have[nid] = parsed
            except Exception as exc:  # noqa: BLE001 - recorded, never hidden
                failures.append({"node": nid, "why": str(exc)[:160]})
    records = list(have.values())
    OUT.write_text(
        json.dumps(
            {"version": 1, "source": "Paris Musées IIIF manifests", "records": records, "failures": failures},
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(len(records), "records,", len(failures), "failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
