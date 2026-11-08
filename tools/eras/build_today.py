#!/usr/bin/env python3
""""Как есть": a present-day photo for each depicted site (Wikidata P18 image on Commons) with its licence and author.

Input  data/vision-lab/sites.json (QIDs of depicted sites).
Output data/vision-lab/today-photos.json {qid: {file, image, page, license, license_url, author, credit}}.
Only free licences are kept (CC0, PD, CC BY, CC BY-SA). The photo is shown as "the same place today", never as a
matched viewpoint. Resumable; polite (≤1 request/s).
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VL = ROOT / "data" / "vision-lab"
OUT = VL / "today-photos.json"
UA = "CityOnPaperResearch/0.5 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)"
FREE = re.compile(r"^(cc0|public domain|pd|cc by(-sa)? [1-4]\.0|cc by(-sa)? 2\.[05])", re.I)


def get_json(url: str) -> dict:
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15 * (attempt + 1))
                continue
            raise
    return {}


def strip(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def main() -> None:
    sites = json.loads((VL / "sites.json").read_text("utf-8"))["items"]
    qids = sorted({s["qid"] for s in sites if s.get("qid") and s.get("kind") not in (None, "unresolved", "panorama")})
    out = json.loads(OUT.read_text("utf-8")) if OUT.exists() else {}
    todo = [q for q in qids if q not in out]
    names: dict[str, str] = {}
    for i in range(0, len(todo), 50):
        batch = todo[i:i + 50]
        d = get_json("https://www.wikidata.org/w/api.php?action=wbgetentities&props=claims&format=json&ids="
                     + "|".join(batch))
        time.sleep(1)
        for q in batch:
            claims = (d.get("entities", {}).get(q, {}) or {}).get("claims", {})
            p18 = [c["mainsnak"].get("datavalue", {}).get("value") for c in claims.get("P18", [])]
            p18 = [x for x in p18 if x]
            if p18:
                names[q] = p18[0]
            else:
                out[q] = None
    by_title = {"File:" + n.replace("_", " "): q for q, n in names.items()}
    titles = list(by_title)
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        m = get_json("https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo"
                     "&iiprop=url|extmetadata&iiurlwidth=500&titles=" + urllib.parse.quote("|".join(batch)))
        time.sleep(2)
        norm = {x["to"]: x["from"] for x in m.get("query", {}).get("normalized", [])}
        for page in m.get("query", {}).get("pages", {}).values():
            t = norm.get(page.get("title"), page.get("title"))
            q = by_title.get(t) or by_title.get(page.get("title"))
            if not q:
                continue
            ii = (page.get("imageinfo") or [{}])[0]
            em = ii.get("extmetadata", {})
            lic = strip(em.get("LicenseShortName", {}).get("value"))
            if not FREE.match(lic):
                out[q] = None
                continue
            out[q] = {"file": names[q], "image": ii.get("thumburl") or ii.get("url"), "page": ii.get("descriptionurl"),
                      "license": lic, "license_url": strip(em.get("LicenseUrl", {}).get("value")),
                      "author": strip(em.get("Artist", {}).get("value"))[:120],
                      "date": strip(em.get("DateTimeOriginal", {}).get("value"))[:40]}
    OUT.write_text(json.dumps(dict(sorted(out.items())), ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(f"{sum(1 for v in out.values() if v)} present-day photos for {len(qids)} sites")


if __name__ == "__main__":
    main()
