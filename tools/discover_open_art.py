#!/usr/bin/env python3
"""Read-only museum/Commons discovery. Never publishes or downloads image bytes."""
import argparse
import html
import json
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = {
    "met": "https://collectionapi.metmuseum.org/public/collection",
    "artic": "https://api.artic.edu/api/v1/artworks/search",
    "cleveland": "https://openaccess-api.clevelandart.org/api/artworks/",
    "commons": "https://commons.wikimedia.org/w/api.php",
}
USER_AGENT = "CityOnPaperResearch/0.1 (read-only, attribution-preserving)"
delay_seconds = 1.25
remaining_requests = 0

def fetch_json(base, params=None):
    """Bounded, polite requests. Abort on budget exhaustion; do not bypass blocks."""
    global remaining_requests
    if remaining_requests <= 0:
        raise RuntimeError("Request budget exhausted")
    remaining_requests -= 1
    url = base + ("?" + urlencode(params) if params else "")
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urlopen(req, timeout=18) as response:
                data = json.load(response)
            time.sleep(delay_seconds)
            return data
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            time.sleep((attempt + 1) * 4)
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep((attempt + 1) * 4)

def clean(s):
    return html.unescape(re.sub(r"<[^>]*>", "", str(s or ""))).strip()

def candidate(source, item_id, title, creator, date, page, image, license_name, license_url):
    return {
        "id": f"{source}:{item_id}",
        "source": source,
        "source_id": str(item_id),
        "title": clean(title),
        "creator": clean(creator),
        "date": clean(date),
        "source_url": page,
        "image_url": image,
        "rights_statement": clean(license_name),
        "rights_url": license_url or "",
        "review_status": "candidate_unverified",
        "viewpoint_status": "not_checked",
        "note": "Not published; attribution, location, historical viewpoint and licence must be reviewed."
    }

def met(query, limit):
    ids = fetch_json(API["met"] + "/v1.1/search",
                     {"q": query, "hasImages": "true", "limit": min(limit * 3, 90)}).get("objectIDs") or []
    found = []
    for obj_id in ids:
        if len(found) >= limit:
            break
        data = fetch_json(API["met"] + "/v1/objects/" + str(obj_id))
        if not data.get("isPublicDomain") or not data.get("primaryImage"):
            continue
        found.append(candidate("met", obj_id, data.get("title"),
            data.get("artistDisplayName"), data.get("objectDate"),
            data.get("objectURL") or f"https://www.metmuseum.org/art/collection/search/{obj_id}",
            data["primaryImageSmall"] or data["primaryImage"], "CC0",
            "https://creativecommons.org/publicdomain/zero/1.0/"))
    return found

def artic(query, limit):
    data = fetch_json(API["artic"], {
        "q": query, "query[term][is_public_domain]": "true", "limit": limit,
        "fields": "id,title,artist_display,date_display,image_id,is_public_domain"
    })
    base = (data.get("config") or {}).get("iiif_url") or "https://www.artic.edu/iiif/2"
    found = []
    for obj in data.get("data") or []:
        if obj.get("is_public_domain") is not True or not obj.get("image_id"):
            continue
        obj_id = obj["id"]
        image = f"{base}/{obj['image_id']}/full/843,/0/default.jpg"
        found.append(candidate("artic", obj_id, obj.get("title"),
            obj.get("artist_display"), obj.get("date_display"),
            f"https://www.artic.edu/artworks/{obj_id}", image,
            "Public domain (artwork and image status from museum)",
            "https://www.artic.edu/image-licensing"))
    return found

def cleveland(query, limit):
    data = fetch_json(API["cleveland"], {
        "q": query, "cc0": "", "has_image": 1, "limit": limit
    })
    found = []
    for obj in data.get("data") or []:
        if obj.get("share_license_status") != "CC0":
            continue
        image = (obj.get("images") or {}).get("web") or {}
        image_url = image.get("url") or (obj.get("images") or {}).get("print", {}).get("url")
        if not image_url:
            continue
        creators = obj.get("creators") or []
        author = ", ".join(c.get("description") or c.get("name") or "" for c in creators if isinstance(c, dict))
        obj_id = obj["id"]
        found.append(candidate("cleveland", obj_id, obj.get("title"), author,
            obj.get("creation_date"), f"https://www.clevelandart.org/art/{obj.get('accession_number') or obj_id}",
            image_url, "CC0", "https://creativecommons.org/publicdomain/zero/1.0/"))
    return found

def commons(query, limit):
    data = fetch_json(API["commons"], {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": limit,
        "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 800
    })
    found = []
    for page in (data.get("query") or {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        attr = lambda name: clean((meta.get(name) or {}).get("value"))
        lic = attr("LicenseShortName")
        # Commons includes non-free media; do not trust the search query itself.
        normalized = lic.lower()
        allowed = ("public domain" in normalized or normalized.startswith("pd-")
                   or normalized.startswith("cc0") or normalized.startswith("cc by")
                   or normalized.startswith("cc-by"))
        if not allowed:
            continue
        page_title = page.get("title", "")
        found.append(candidate("commons", page.get("pageid"), page_title.removeprefix("File:"),
            attr("Artist"), attr("Date"),
            "https://commons.wikimedia.org/wiki/" + page_title.replace(" ", "_"),
            info.get("thumburl") or info.get("url"), lic, attr("LicenseUrl")))
    return found

READERS = {"met": met, "artic": artic, "cleveland": cleveland, "commons": commons}

def main():
    global delay_seconds, remaining_requests
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", action="append", required=True, help="Repeat for cities/authors/collections")
    parser.add_argument("--sources", nargs="+", choices=READERS, default=list(READERS))
    parser.add_argument("--per-source", type=int, default=10)
    parser.add_argument("--request-budget", type=int, default=70)
    parser.add_argument("--delay", type=float, default=1.25)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not 1 <= args.per_source <= 30 or not 1 <= args.request_budget <= 250 or args.delay < 1:
        parser.error("per-source 1..30, request-budget 1..250, delay >= 1 second")
    delay_seconds = args.delay
    remaining_requests = args.request_budget
    items, errors, seen = [], [], set()
    for query in args.query:
        for source in args.sources:
            try:
                for entry in READERS[source](query, args.per_source):
                    if entry["id"] not in seen:
                        seen.add(entry["id"])
                        entry["search_query"] = query
                        items.append(entry)
            except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError, KeyError) as exc:
                errors.append({"source": source, "query": query, "error": str(exc)})
                print(f"Skipped {source} / {query}: {exc}", file=sys.stderr)
                if remaining_requests <= 0:
                    break
        if remaining_requests <= 0:
            break
    out = {"schema": "city-on-paper/candidates-v1", "published": False,
           "items": items, "errors": errors, "requests_remaining": remaining_requests}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{len(items)} candidate records; {len(errors)} provider errors. Not added to the exhibition.")

if __name__ == "__main__":
    main()
