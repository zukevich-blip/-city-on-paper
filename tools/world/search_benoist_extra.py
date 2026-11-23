#!/usr/bin/env python3
"""Second-wave Benoist search: Heidelberg vol. 3, Wikimedia Commons, Gallica probe, further libraries.

Writes data/research/benoist/benoist-extra-sources-v1.json (schema: data/research/benoist/SCHEMA.md).
Polite (>= 1.5 s between requests, project User-Agent), curl --http1.1, no image downloads.
403 / 429 / 401 / bot challenges are never bypassed: they are written to coverage.blocked and the host is dropped.
Philippe and Félix Benoist are different people; artist_id decides, uncertain plates stay uncertain-benoist.

Usage: python3 -m tools.world.search_benoist_extra
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from tools.world.search_bnf_europeana_ia import make_record, parse_heidelberg_manifest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "research" / "benoist" / "benoist-extra-sources-v1.json"
UA = "CityOnPaperResearch/0.9 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)"
GAP = 1.6
OPEN_LICENSE = re.compile(r"^(cc0|cc[- ]by|pd|public domain)", re.I)
COMMONS_CATEGORIES = (
    ("Philippe Benoist", "philippe-benoist"),
    ("Félix Benoist", "felix-benoist"),
    ("Félix Benoist (lithographer)", "felix-benoist"),
)
COMMONS_SEARCHES = ("Benoist lithographie", "Benoist lith. Paris dans sa splendeur")


class Http:
    def __init__(self) -> None:
        self.last = 0.0
        self.dead: dict[str, str] = {}
        self.blocked: list[str] = []
        self.requests = 0

    def get(self, url: str) -> tuple[int, str]:
        host = urllib.parse.urlsplit(url).netloc
        if host in self.dead:
            return 0, ""
        wait = GAP - (time.monotonic() - self.last)
        if wait > 0:
            time.sleep(wait)
        self.last = time.monotonic()
        self.requests += 1
        res = subprocess.run(
            ["curl", "-sS", "-L", "--http1.1", "-m", "60", "-A", UA, "-w", "\n%{http_code}", url],
            capture_output=True,
        )
        body, _, code = res.stdout.rpartition(b"\n")
        status = int(code) if code.strip().isdigit() else 0
        text = body.decode("utf-8", "replace")
        challenge = re.search(r"not a bot|Just a moment|Attention Required|_Incapsula", text[:3000])
        if status in (401, 403, 429) or challenge:
            self.dead[host] = f"HTTP {status or 200} (challenge/refusal); not bypassed"
            self.blocked.append(f"{url}: {self.dead[host]}")
            return status, ""
        if status == 0:
            self.blocked.append(f"{url}: no response ({res.stderr.decode(errors='replace')[:80].strip()})")
        return status, text

    def json(self, url: str) -> dict:
        status, text = self.get(url)
        try:
            return json.loads(text) if status == 200 else {}
        except ValueError:
            return {}


# ---------------------------------------------------------------- pure helpers


def commons_rights(extmeta: dict) -> tuple[str, str | None]:
    lic = (extmeta.get("LicenseShortName") or {}).get("value")
    url = (extmeta.get("LicenseUrl") or {}).get("value")
    stmt = " ".join(x for x in (lic, url) if x) or None
    if lic and OPEN_LICENSE.match(lic):
        return "open_confirmed", stmt
    return ("rights_pending" if lic else "unknown"), stmt


def commons_record(title: str, info: dict, artist_id: str, found_by: str) -> dict:
    ext = info.get("extmetadata") or {}
    rights, stmt = commons_rights(ext)
    desc = re.sub(r"<[^>]+>", "", (ext.get("ImageDescription") or {}).get("value") or "").strip() or None
    credit = re.sub(r"<[^>]+>", "", (ext.get("Artist") or {}).get("value") or "").strip() or None
    page = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
    from_cat = found_by.startswith("Category:")
    return make_record(
        record_id=f"commons:{title}",
        artist_id=artist_id if from_cat else "uncertain-benoist",
        participants=[{"name": credit, "role_as_stated": "Commons 'Artist' field", "role_normalized": "unspecified"}]
        if credit
        else [],
        original_title=re.sub(r"^File:|\.[A-Za-z]{3,4}$", "", title),
        institution="Wikimedia Commons",
        accession=None,
        record_url=page,
        image_url=info.get("url"),
        image_width=info.get("width"),
        image_height=info.get("height"),
        rights_statement=stmt,
        rights_status=rights,
        object_type="print",
        verification_status="search_hit_only",
        attribution_confidence="low",
        attribution_note=(
            f"Found by {found_by}; category/search membership is not an attribution. Description: {desc}"
            if desc
            else f"Found by {found_by}; category/search membership is not an attribution."
        ),
        source_hit_query=found_by,
    )


# ---------------------------------------------------------------- runners


def run_heidelberg(h: Http) -> tuple[list[dict], dict]:
    url = "https://digi.ub.uni-heidelberg.de/diglit/iiif/audiganne1861bd3/manifest.json"
    man = h.json(url)
    if not man:
        return [], {"status": "failed", "url": url}
    recs = parse_heidelberg_manifest(man, "audiganne1861bd3", "Band 3")
    n = len((man.get("sequences") or [{}])[0].get("canvases") or [])
    return recs, {
        "status": "read",
        "url": url,
        "canvases": n,
        "plates": len(recs) - 1,
        "note": "Manifest only; page HTML/OCR is behind a bot challenge (not bypassed). Plates are uncertain-benoist.",
    }


def run_commons(h: Http) -> tuple[list[dict], dict]:
    api = "https://commons.wikimedia.org/w/api.php?"
    found: dict[str, tuple[str, str]] = {}
    status: dict = {"categories": {}, "searches": {}}
    for cat, who in COMMONS_CATEGORIES:
        query = {"action": "query", "list": "categorymembers", "cmtitle": f"Category:{cat}", "cmlimit": 500,
                 "format": "json"}
        d = h.json(api + urllib.parse.urlencode(query))
        members = (d.get("query") or {}).get("categorymembers", [])
        subcats = [m["title"] for m in members if m["ns"] == 14]
        status["categories"][cat] = {"members": len(members), "subcategories": subcats}
        for m in members:
            if m["ns"] == 6:
                found.setdefault(m["title"], (who, f"Category:{cat}"))
        if "commons.wikimedia.org" in h.dead:
            status["stopped"] = h.dead["commons.wikimedia.org"]
            break
    if "commons.wikimedia.org" not in h.dead:
        for q in COMMONS_SEARCHES:
            d = h.json(api + urllib.parse.urlencode(
                {"action": "query", "list": "search", "srsearch": q, "srnamespace": 6, "srlimit": 50, "format": "json"}
            ))
            hits = (d.get("query") or {}).get("search", [])
            status["searches"][q] = len(hits)
            for s in hits:
                found.setdefault(s["title"], ("uncertain-benoist", f"search:{q}"))
    recs: list[dict] = []
    titles = list(found)
    for i in range(0, len(titles), 40):
        if "commons.wikimedia.org" in h.dead:
            break
        d = h.json(api + urllib.parse.urlencode(
            {"action": "query", "titles": "|".join(titles[i : i + 40]), "prop": "imageinfo",
             "iiprop": "url|size|extmetadata", "format": "json"}
        ))
        for p in ((d.get("query") or {}).get("pages") or {}).values():
            info = (p.get("imageinfo") or [{}])[0]
            who, by = found[p["title"]]
            recs.append(commons_record(p["title"], info, who, by))
    return recs, status


def run_bpl(h: Http) -> tuple[list[dict], dict]:
    recs, hits = [], {}
    for q in ('"Benoist, Philippe"', '"Benoist, Félix"'):
        url = "https://www.digitalcommonwealth.org/search.json?" + urllib.parse.urlencode({"q": q, "per_page": 50})
        d = h.json(url)
        hits[q] = ((d.get("meta") or {}).get("pages") or {}).get("total_count")
        for x in d.get("data") or []:
            a = x["attributes"]
            names = a.get("name_tsim") or []
            fel = any(re.match(r"Benoist, F[ée]lix", n) for n in names)
            phi = any(re.match(r"Benoist, Philippe", n) for n in names)
            if not (fel or phi):
                continue
            resp = " ".join(a.get("note_resp_tsim") or [])
            who = "felix-benoist" if fel and not phi else "philippe-benoist" if phi and not fel else "uncertain-benoist"
            role = "; ".join(a.get("name_role_tsim") or []) or None
            parts = [{"name": n, "role_as_stated": role, "role_normalized": "unspecified"} for n in names]
            if resp:
                parts.append({"name": resp, "role_as_stated": "statement of responsibility (note)",
                              "role_normalized": "unspecified"})
            recs.append(make_record(
                record_id=f"bpl:{x['id']}",
                artist_id=who,
                participants=parts,
                original_title=a.get("title_info_primary_tsi"),
                city=(a.get("pubplace_tsi")),
                date_as_stated="; ".join(a.get("date_tsim") or []) or None,
                object_type="print",
                technique_as_stated="; ".join(a.get("genre_basic_ssim") or []) or None,
                institution="Boston Public Library / " + (a.get("sub_location_tsi") or ""),
                accession="; ".join(a.get("identifier_local_call_tsim") or []) or None,
                record_url=a.get("identifier_uri_ss"),
                iiif_manifest=a.get("identifier_iiif_manifest_ss"),
                rights_statement=" / ".join(x for x in (a.get("rights_ss"), a.get("license_ss")) if x) or None,
                rights_status="link_only",
                verification_status="source_record_read",
                attribution_confidence="high",
                attribution_note="Name authority and note 'del. & lith.' read in the Digital Commonwealth record. "
                "'No known restrictions' is a statement of no known copyright, not CC0: link only.",
                source_hit_query=q,
            ))
    return recs, {"hits": hits, "records": len(recs)}


# Sources probed once each; status recorded, nothing guessed.
PROBES = (
    ("gallica", "SRU", "https://gallica.bnf.fr/SRU?version=1.2&operation=searchRetrieve&query=%28dc.creator%20all%20%22Benoist%20Philippe%22%29&maximumRecords=5"),
    ("gallica", "OAIRecord", "https://gallica.bnf.fr/services/OAIRecord?ark=btv1b10542617d"),
    ("gallica", "IIIF manifest", "https://gallica.bnf.fr/iiif/ark:/12148/btv1b10542617d/manifest.json"),
    ("nypl", "public API without token", "https://api.repo.nypl.org/api/v2/items/search?q=Benoist"),
    ("nypl", "digitalcommons.nypl.org search page", "https://digitalcollections.nypl.org/search/index?keywords=Philippe+Benoist+lithograph"),
    ("bodleian", "digital.bodleian search page", "https://digital.bodleian.ox.ac.uk/search/?q=Philippe+Benoist"),
    ("getty", "getty.edu/research/collections", "https://www.getty.edu/research/collections/"),
    ("hertziana", "digital.biblhertz.it", "https://digital.biblhertz.it/iiif/"),
    ("europeana_bne", "Europeana API, provider BNE", "https://api.europeana.eu/record/v2/search.json?wskey=api2demo&query=Benoist+lithographie&qf=DATA_PROVIDER:%22Biblioteca+Nacional+de+Espa%C3%B1a%22&rows=5"),
)


def run_probes(h: Http) -> list[dict]:
    out = []
    for src, what, url in PROBES:
        status, text = h.get(url)
        dead = h.dead.get(urllib.parse.urlsplit(url).netloc)
        note = dead or (f"HTTP {status}, {len(text)} bytes" if status else "unreachable through the session proxy")
        if src == "europeana_bne" and status == 200:
            try:
                note += f"; totalResults={json.loads(text).get('totalResults')}"
            except ValueError:
                pass
        if src == "bodleian" and status == 200:
            note += "; JS-rendered shell, no records readable without a browser (not scraped)"
        out.append({"source": src, "what": what, "url": url, "result": note})
    return out


def main() -> int:
    h = Http()
    records: list[dict] = []
    hd, hd_cov = run_heidelberg(h)
    commons, commons_cov = run_commons(h)
    bpl, bpl_cov = run_bpl(h)
    records = hd + commons + bpl
    probes = run_probes(h)
    result = {
        "version": 1,
        "source": "extra: heidelberg vol.3, wikimedia commons, boston public library, probes of further libraries",
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "coverage": {
            "queries": [
                "heidelberg: audiganne1861bd3 IIIF manifest",
                *[f"commons: Category:{c}" for c, _ in COMMONS_CATEGORIES],
                *[f"commons: search '{q}' (File namespace)" for q in COMMONS_SEARCHES],
                "bpl: digitalcommonwealth search.json \"Benoist, Philippe\" / \"Benoist, Félix\"",
                *[f"probe {p['source']}: {p['url']}" for p in probes],
            ],
            "pages_walked": h.requests,
            "hits_total_reported_by_source": {"heidelberg": hd_cov, "commons": commons_cov, "bpl": bpl_cov},
            "records_kept": len(records),
            "blocked": h.blocked,
            "probes": probes,
            "notes": [
                "Heidelberg plate records are uncertain-benoist: plate credit is printed on the page image only.",
                "Commons category membership is not attribution; rights_status from the file's own LicenseShortName.",
            ],
        },
        "records": records,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}: {len(records)} records; blocked={len(h.blocked)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
