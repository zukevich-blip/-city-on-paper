#!/usr/bin/env python3
"""Live reachability probe for the provider matrix. One GET per route, no retries, no workarounds.

    python3 -m tools.sources.probe --out data/providers/probe-2026-11-01.json
"""
from __future__ import annotations

import argparse
import json
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tools.sources.connectors import USER_AGENT, redact

ROUTES = [
    # (provider, route, url, extra headers)
    ("met", "search v1.1", "https://collectionapi.metmuseum.org/public/collection/v1.1/search?q=Benoist&hasImages=true", {}),
    ("met", "search v1 (retired)", "https://collectionapi.metmuseum.org/public/collection/v1/search?q=Benoist", {}),
    ("artic", "search + AIC-User-Agent", "https://api.artic.edu/api/v1/artworks/search?q=market&limit=1", {"AIC-User-Agent": USER_AGENT}),
    ("artic", "search without AIC-User-Agent", "https://api.artic.edu/api/v1/artworks/search?q=market&limit=1", {}),
    ("cleveland", "artworks", "https://openaccess-api.clevelandart.org/api/artworks/?q=Paris&limit=1", {}),
    ("commons", "api.php search", "https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch=Benoist&srnamespace=6&format=json", {}),
    ("wikidata", "wbsearchentities", "https://www.wikidata.org/w/api.php?action=wbsearchentities&search=Benoist&language=fr&format=json", {}),
    ("wikidata", "SPARQL", "https://query.wikidata.org/sparql?format=json&query=SELECT%20%3Fx%20WHERE%20%7Bwd%3AQ277187%20wdt%3AP31%20%3Fx%7D", {}),
    ("europeana", "search (api2demo key)", "https://api.europeana.eu/record/v2/search.json?wskey=api2demo&query=Benoist&rows=1", {}),
    ("loc", "photos ?fo=json", "https://www.loc.gov/photos/?q=Benoist&fo=json&c=1&at=pagination", {}),
    ("loc", "item IIIF manifest", "https://www.loc.gov/item/2016652452/manifest.json", {}),
    ("rijksmuseum", "Linked Art search", "https://data.rijksmuseum.nl/search/collection?creator=Benoist", {"Accept": "application/ld+json"}),
    ("vam", "objects/search v2", "https://api.vam.ac.uk/v2/objects/search?q=Benoist&page_size=1", {}),
    ("smithsonian", "openaccess search (DEMO_KEY)", "https://api.si.edu/openaccess/api/v1.0/search?q=Paris&rows=1&api_key=DEMO_KEY", {}),
    ("panoramax", "STAC search bbox", "https://api.panoramax.xyz/api/search?bbox=25.28,54.68,25.29,54.69&limit=1", {}),
    ("gallica", "SRU", "https://gallica.bnf.fr/SRU?operation=searchRetrieve&version=1.2&query=dc.creator%20all%20%22Benoist%22&maximumRecords=1", {}),
    ("gallica", "IIIF info.json", "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8453856h/f1/info.json", {}),
    ("getty", "Linked Art / data.getty.edu", "https://data.getty.edu/museum/collection/object/search?q=Benoist", {}),
    ("getty", "www search page", "https://www.getty.edu/art/collection/search?q=Benoist", {}),
    ("nypl", "new collections API docs", "https://api-collections.nypl.org/docs", {}),
    ("nypl", "legacy api.repo.nypl.org (retired 2026-08-01)", "https://api.repo.nypl.org/api/v2/items/search?q=menu", {}),
    ("harvard", "object (no key)", "https://api.harvardartmuseums.org/object?q=Benoist", {}),
    ("dpla", "items (no key)", "https://api.dp.la/v2/items?q=Benoist", {}),
    ("british_library", "api.bl.uk", "https://api.bl.uk/", {}),
    ("ddb", "Deutsche Digitale Bibliothek search", "https://api.deutsche-digitale-bibliothek.de/2/search/index/search/select?query=Benoist", {}),
    ("onb", "ÖNB IIIF", "https://iiif.onb.ac.at/", {}),
    ("polona", "Polona (PL national library)", "https://polona.pl/api/", {}),
    ("ethz", "ETH e-pics Bildarchiv", "https://ba.e-pics.ethz.ch/", {}),
]


def probe(url: str, headers: dict) -> dict:
    t = time.monotonic()
    try:
        with urlopen(Request(url, headers={"User-Agent": USER_AGENT, **headers}), timeout=20) as r:
            body = r.read(4096)
            return {"status": r.status, "content_type": r.headers.get("Content-Type", ""),
                    "ms": int((time.monotonic() - t) * 1000), "sample": body[:160].decode("utf-8", "replace")}
    except HTTPError as e:
        return {"status": e.code, "error": str(e.reason), "ms": int((time.monotonic() - t) * 1000)}
    except (URLError, ssl.SSLError, TimeoutError, OSError) as e:
        return {"status": None, "error": f"{type(e).__name__}: {e}"[:200], "ms": int((time.monotonic() - t) * 1000)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    rows = []
    for provider, route, url, hdr in ROUTES:
        res = probe(url, hdr)
        rows.append({"provider": provider, "route": route, "url": redact(url), **res})
        print(f"{provider:<16} {route:<45} {res.get('status')} {res.get('error', '')}")
        time.sleep(1.0)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"probed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                 "network": "Claude Code cloud container via egress proxy (results may differ elsewhere)",
                                 "routes": rows}, ensure_ascii=False, indent=1) + "\n", "utf-8")


if __name__ == "__main__":
    main()
