#!/usr/bin/env python3
"""Ingest a hand-picked set of Benoist sheets from holders that state an open licence for the file itself.

The allowlist below was chosen by reading each record (attribution to Benoist named in the record, licence on the
record). Images are downloaded once (polite, HTTP/1.1), re-encoded to at most 1280 px and stored in book/img/benoist/.
Output: data/curation/benoist-open-sheets-v1.json. Anything that cannot be fetched stays in ``failures`` and is retried.
"""

from __future__ import annotations

import glob
import io
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "data" / "research" / "benoist"
OUT = ROOT / "data" / "curation" / "benoist-open-sheets-v1.json"
IMG_DIR = ROOT / "book" / "img" / "benoist"
UA = "CityOnPaperResearch/0.9 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)"
# record_id -> how the sheet is shown (credit line, licence label); everything else comes from the record itself
PICKS = {
    "europeana:/542/item_B5OHYCJFHXY5EUVULKZP2COBNYZYGXBW": {
        "slug": "labw-freiburg-1",
        "rights": "CC BY 3.0",
        "credit": "Landesarchiv Baden-Württemberg, Hauptstaatsarchiv Stuttgart",
    },
    "europeana:/542/item_NOHVZIMUAQBNAFFOXHV2Z6MEAWARL2D3": {
        "slug": "labw-freiburg-2",
        "rights": "CC BY 3.0",
        "credit": "Landesarchiv Baden-Württemberg, Hauptstaatsarchiv Stuttgart",
    },
    "europeana:/991/https___catalonica_bnc_cat_catalonicahub_lod_oai_cdm21055_contentdm_oclc_org_vistes____1845_ent0": {
        "slug": "icgc-cadix-1845",
        "rights": "Public Domain Mark",
        "credit": "Institut Cartogràfic i Geològic de Catalunya",
    },
    "europeana:/991/https___catalonica_bnc_cat_catalonicahub_lod_oai_cdm21055_contentdm_oclc_org_vistes____1847_ent0": {
        "slug": "icgc-cadix-1847",
        "rights": "Public Domain Mark",
        "credit": "Institut Cartogràfic i Geològic de Catalunya",
    },
    "europeana:/991/https___catalonica_bnc_cat_catalonicahub_lod_oai_cdm21055_contentdm_oclc_org_vistes____679_ent0": {
        "slug": "icgc-cadix-679",
        "rights": "Public Domain Mark",
        "credit": "Institut Cartogràfic i Geològic de Catalunya",
    },
    "europeana:/401/item_5K3LW3OVRSRUREBLF5BG7HM5MRW56KIV": {
        "slug": "ekm-salerno",
        "rights": "CC0",
        "credit": "Eesti Kunstimuuseum (Art Museum of Estonia)",
    },
    "europeana:/401/item_MSMJAXRUAH6MAK5MQMESZLQ5BP3D23IE": {
        "slug": "ekm-amalfi",
        "rights": "CC0",
        "credit": "Eesti Kunstimuuseum (Art Museum of Estonia)",
    },
    "europeana:/401/item_PH6L2ZH66RF5NKPCAFYVIB5LVL5GSSVV": {
        "slug": "ekm-temple-ruins",
        "rights": "CC0",
        "credit": "Eesti Kunstimuuseum (Art Museum of Estonia)",
    },
}


def fetch(url: str) -> bytes:
    for attempt in range(3):
        res = subprocess.run(
            ["curl", "-sS", "-L", "--http1.1", "-m", "120", "-A", UA, "-w", "\n%{http_code}", url], capture_output=True
        )
        body, _, code = res.stdout.rpartition(b"\n")
        time.sleep(2 * (attempt + 1))
        if code == b"200" and body:
            return body
    raise RuntimeError(f"HTTP {code.decode(errors='replace')} {res.stderr.decode(errors='replace')[:80]}")


def save(slug: str, data: bytes) -> str:
    from PIL import Image

    im = Image.open(io.BytesIO(data))
    im.load()
    im = im.convert("RGB")
    im.thumbnail((1280, 1280))
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    im.save(IMG_DIR / f"os-{slug}.jpg", "JPEG", quality=84, optimize=True)
    return f"img/benoist/os-{slug}.jpg"


def records() -> dict[str, dict]:
    found: dict[str, dict] = {}
    for f in sorted(glob.glob(str(RESEARCH / "*-v1.json"))):
        if "registry" in f or "photo-pairs" in f:
            continue
        for r in json.loads(Path(f).read_text(encoding="utf-8")).get("records", []):
            if r.get("record_id") in PICKS:
                found.setdefault(r["record_id"], r)
    return found


def main() -> int:
    have = {s["id"]: s for s in json.loads(OUT.read_text(encoding="utf-8"))["sheets"]} if OUT.exists() else {}
    recs, failures = records(), []
    for rid, pick in PICKS.items():
        rec = recs.get(rid)
        if not rec:
            failures.append({"id": rid, "why": "record not found in research files"})
            continue
        sid = "os-" + pick["slug"]
        if sid in have and (IMG_DIR / f"{sid}.jpg").exists():
            continue
        try:
            image = save(pick["slug"], fetch(rec["image_url"]))
        except Exception as exc:  # noqa: BLE001 - recorded, retried next run
            failures.append({"id": rid, "why": str(exc)[:160]})
            continue
        have[sid] = {
            "id": sid,
            "title": (rec.get("original_title") or "").split(" - ")[0].strip(),
            "holder": pick["credit"],
            "accession": rec.get("accession") or "",
            "record_url": rec["record_url"],
            "image": image,
            "rights": pick["rights"],
            "rights_url": rec["rights_statement"],
            "participants": [p["name"] for p in rec.get("participants", []) if p.get("name")],
            "technique": rec.get("technique_as_stated"),
            "artist": rec["artist_id"],
            "source_record": rid,
            "attribution_note": rec.get("attribution_note"),
        }
    OUT.write_text(
        json.dumps(
            {
                "version": 1,
                "source": "hand-picked open-licence records",
                "sheets": list(have.values()),
                "failures": failures,
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(len(have), "sheets,", len(failures), "failures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
