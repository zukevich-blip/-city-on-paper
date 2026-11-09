#!/usr/bin/env python3
"""Bounded, resume-friendly official LoC historical-map discovery for world cities.

Existing atlas entries and global seed are used as *search candidates*.
Returned museum records are NEVER promoted to verified city/map/georeference.
No image mirroring, no third-party tile downloads, no fake GPS.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from tools.curation.audit_global_cities import ATLAS, SEED, audit, normalize

LOC_API = "https://www.loc.gov/maps/"
UA = "CityOnPaperResearch/1.0 (https://github.com/zukevich-blip/-city-on-paper; archival index)"
MAX_BYTES = 3_000_000
PRIORITY_CITIES = (
    # Round-robin continents: the first research batch must not be Europe-only.
    "Париж", "Токио", "Нью-Йорк", "Каир", "Сидней", "Рио-де-Жанейро",
    "Рим", "Пекин", "Кейптаун", "Лондон", "Стамбул", "Буэнос-Айрес",
    "Флоренция", "Шанхай", "Мехико", "Амстердам", "Дели", "Мельбурн",
    "Венеция", "Москва", "Иерусалим", "Неаполь", "Сан-Франциско",
    "Вена", "Берлин", "Прага", "Гонконг", "Санкт-Петербург",
    "Лиссабон", "Чикаго", "Торонто", "Мадрид", "Барселона",
    "Александрия", "Брюссель", "Афины", "Будапешт",
    "Стокгольм", "Копенгаген", "Сингапур", "Бангкок",
    "Киото", "Осака", "Бомбей", "Мумбаи", "Калькутта",
    "Бостон", "Квебек", "Константинополь", "Дубай",
)
ART_TERMS = re.compile(
    r"\b(lithographs?|engravings?|woodblock|prints?|artworks?|photographs?|"
    r"drawings?|paintings?|etchings?|views?|pictures?|illustrations?)\b",
    flags=re.I,
)


def search_phrase(city: dict) -> str:
    """Respect existing English transliteration from source seed when known."""
    raw = str(city.get("discovery_query") or city.get("name_original") or city["name"]).strip()
    stem = ART_TERMS.sub(" ", raw)
    stem = re.sub(r"\s+", " ", stem).strip()
    if not stem:
        stem = city["name"]
    # A LoC maps collection search, not an assertion of 19th-century dating.
    return stem + " map"


def build_queue(atlas: dict, seed: dict, geonames: dict | None = None) -> list[dict]:
    registry, _, _ = audit(atlas, seed)
    cities = registry["cities"]
    wanted = {normalize(x): i for i, x in enumerate(PRIORITY_CITIES)}
    filtered = [
        c for c in cities
        if c.get("place_type_review") != "review_city_vs_site"
    ]
    # Search all possible cities, not merely Europe or the 150 seed entries.
    rows = []
    for c in filtered:
        rows.append({
            "city_id": c["city_id"], "name": c["name"], "country": c["country"],
            "lat": c["lat"], "lon": c["lon"],
            "query": search_phrase(c),
            "priority": wanted.get(normalize(c["name"]), 999),
            "identity_status": c["review_status"],
            "review_status": "search_queued_not_a_verified_map",
            "source": LOC_API,
        })
    if geonames:
        if geonames.get("schema") != "city-on-paper/geonames-major-city-candidates/v1":
            raise ValueError("Unexpected GeoNames candidate schema")
        for item in geonames.get("cities", []):
            rows.append({
                "city_id": item["candidate_city_id"],
                "name": item["name"], "country": item["country_iso2"],
                "lat": item["lat"], "lon": item["lon"],
                "query": item["name_ascii"] + " historical city map",
                "priority": 1000,
                "population_reported_by_geonames":
                    item["population_reported_by_geonames"],
                "identity_status": "geonames_candidate_not_reconciled_with_atlas",
                "review_status": "search_queued_not_a_verified_map",
                "source": LOC_API,
                "geonames_source_url": item["source_url"],
            })
    rows.sort(key=lambda x: (x["priority"], normalize(x["country"]), normalize(x["name"])))
    return rows


def loc_url(query: str, limit: int) -> str:
    if not 1 <= limit <= 10 or len(query) > 256:
        raise ValueError("Invalid bounded LoC request")
    return LOC_API + "?" + urlencode({"fo": "json", "q": query, "c": limit, "sp": 1})


def fetch_loc_json(url: str) -> dict:
    if not url.startswith(LOC_API + "?"):
        raise ValueError("Only official Library of Congress maps API is allowed")
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=25) as response:
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("LoC API response exceeded safe size")
        return json.loads(body.decode("utf-8"))


def official_loc_record(hit: dict) -> dict | None:
    if not isinstance(hit, dict):
        return None
    url = str(hit.get("id") or hit.get("url") or "")
    parsed = urlparse(url)
    if parsed.hostname not in ("www.loc.gov", "loc.gov"):
        return None
    if not re.match(r"^/(?:item|resource)/[a-zA-Z0-9._-]+/?$", parsed.path):
        # Search can return collections, newspapers and other non-item pages.
        return None
    object_url = "https://www.loc.gov" + parsed.path
    title = str(hit.get("title") or "").strip()
    if not title:
        return None
    year_data = hit.get("date")
    if isinstance(year_data, list):
        year_data = ", ".join(str(v) for v in year_data[:4])
    rights = hit.get("rights_advisory") or hit.get("rights_information") or None
    return {
        "object_url": object_url,
        "title": title[:450],
        "date_as_reported": str(year_data)[:120] if year_data else None,
        "institution": "Library of Congress",
        "rights_advisory_as_reported": str(rights)[:350] if rights else None,
        "source_api": LOC_API,
        "classification": "map_search_candidate_not_verified",
        "hd_verified": False,
        "iiif_image_api_verified": False,
        "georeferencing_status": "not_attempted",
        "depicted_city_verified": False,
        "independent_gcp_review": False,
    }



def relevance(hit: dict, city: dict) -> str | None:
    """Explicit city title/location overlap; query search alone is not evidence."""
    query = str(city["query"])
    stop = re.search(
        r"\b(?:architecture|historical|historic|city|old|early|map|plan|"
        r"lithograph|engraving|woodblock|port|harbou?r|street|19th|18th|"
        r"landscape|architecture|palace|views?)\b",
        query, flags=re.I,
    )
    alias = query[:stop.start()].strip() if stop else query.strip()
    if not alias:
        return None
    variants = [alias.casefold()]
    aliases = {
        "edo": ["tokyo", "edo"],
        "constantinople": ["istanbul", "constantinople"],
        "peking": ["beijing", "peking"],
        "bombay": ["mumbai", "bombay"],
        "saigon": ["ho chi minh", "saigon"],
    }
    variants.extend(aliases.get(alias.casefold(), []))
    title = str(hit.get("title") or "").casefold()
    raw_locations = hit.get("location") or []
    if isinstance(raw_locations, str):
        raw_locations = [raw_locations]
    if not isinstance(raw_locations, list):
        raw_locations = []
    location_text = " | ".join(str(t).casefold() for t in raw_locations)
    # Reject explicit conflicting country metadata before accepting homonymous
    # title matches such as London, England vs London, Ohio.
    known_countries = {
        "united states": "US", "united kingdom": "GB", "england": "GB",
        "france": "FR", "italy": "IT", "china": "CN", "japan": "JP",
        "brazil": "BR", "australia": "AU", "russia": "RU",
        "egypt": "EG", "turkey": "TR", "spain": "ES",
        "canada": "CA", "india": "IN", "germany": "DE",
        "netherlands": "NL", "argentina": "AR", "south africa": "ZA",
    }
    country_aliases = {
        "франция": "FR", "великобритания": "GB", "италия": "IT",
        "сша": "US", "китай": "CN", "япония": "JP",
        "бразилия": "BR", "австралия": "AU", "россия": "RU",
        "египет": "EG", "турция": "TR", "испания": "ES",
        "канада": "CA", "индия": "IN", "германия": "DE",
        "нидерланды": "NL", "аргентина": "AR", "юар": "ZA",
    }
    expected_country = country_aliases.get(str(city.get("country", "")).casefold(),
                                            str(city.get("country", "")).upper())
    explicit_countries = {
        known_countries[loc]
        for loc in (str(t).casefold().strip() for t in raw_locations)
        if loc in known_countries
    }
    if expected_country and explicit_countries and expected_country not in explicit_countries:
        return None
    for variant in variants:
        term = re.compile(r"(?<![a-z])" + re.escape(variant) + r"(?![a-z])", re.I)
        if term.search(title):
            return "city_alias_in_title"
        if term.search(location_text):
            return "city_alias_in_location"
    return None



def discover(
    queue: list[dict], budget: int = 12, per_city: int = 4, delay: float = 1.25,
    start_index: int = 0, fetch=fetch_loc_json,
) -> tuple[dict, dict]:
    if not 0 <= budget <= 80 or not 0 <= start_index < max(1, len(queue)):
        raise ValueError("Search budget/index out of range")
    if not 0 <= delay <= 30:
        raise ValueError("Delay out of range")
    results, errors, attempts, throttled = [], [], 0, False
    for row in queue[start_index:]:
        if attempts >= budget:
            break
        attempts += 1
        url = loc_url(row["query"], per_city)
        try:
            response = fetch(url)
            hits = response.get("results") or []
            if not isinstance(hits, list):
                raise ValueError("Unexpected LoC results payload")
            seen: set[str] = set()
            items = []
            for hit in hits[:per_city]:
                reason = relevance(hit, row)
                if reason is None:
                    continue
                rec = official_loc_record(hit)
                if rec and rec["object_url"] not in seen:
                    rec["candidate_place_match_reason"] = reason
                    seen.add(rec["object_url"])
                    items.append(rec)
            results.append({
                "city_id": row["city_id"], "city": row["name"],
                "country": row["country"], "query": row["query"],
                "source_search_url": url,
                "candidate_count": len(items),
                "candidate_maps": items,
                "status": "source_search_completed_candidates_only",
            })
        except HTTPError as exc:
            errors.append({
                "city_id": row["city_id"], "error": "HTTP " + str(exc.code),
                "retry_after": exc.headers.get("Retry-After") if exc.headers else None,
            })
            if exc.code in (429, 503):
                throttled = True
                break
        except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append({"city_id": row["city_id"], "error": str(exc)[:200]})
        if delay:
            time.sleep(delay)
    archive = {
        "schema": "city-on-paper/historical-map-discovery/v1",
        "generated": date.today().isoformat(),
        "source": "Library of Congress JSON Maps API",
        "source_url": LOC_API,
        "status": "unreviewed_source_candidates_do_not_publish_as_georeferenced",
        "city_search_results": results,
    }
    report = {
        "schema": "city-on-paper/historical-map-discovery-run/v1",
        "generated": date.today().isoformat(),
        "queued_city_count": len(queue),
        "start_index": start_index, "attempted_city_count": attempts,
        "cities_with_responses": len(results),
        "map_candidate_count": sum(len(x["candidate_maps"]) for x in results),
        "cities_with_candidates": sum(bool(x["candidate_maps"]) for x in results),
        "throttled": throttled, "errors": errors,
        "rights_confirmed_count": 0,
        "georeferenced_city_count": 0,
        "notes": [
            "All returned item titles and dates require independent source verification.",
            "None of the city-search results is an accepted GCP georeference.",
            "No copyright rights were inferred from the age of a map.",
            "LoC API may throttle or limit searches; respect Retry-After.",
        ],
    }
    return archive, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas", type=Path, default=ATLAS)
    parser.add_argument("--seed", type=Path, default=SEED)
    parser.add_argument("--geonames", type=Path, help="Optional research-only GeoNames major-city JSON")
    parser.add_argument("--out", type=Path, default=Path("/tmp/city-global-maps"))
    parser.add_argument("--budget", type=int, default=12)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--per-city", type=int, default=4)
    parser.add_argument("--delay", type=float, default=1.25)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    atlas = json.loads(args.atlas.read_text("utf-8"))
    seed = json.loads(args.seed.read_text("utf-8"))
    geo = json.loads(args.geonames.read_text("utf-8")) if args.geonames else None
    queue = build_queue(atlas, seed, geo)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "world-historic-map-search-queue.json").write_text(
        json.dumps({"schema": "city-on-paper/historical-map-search-queue/v1",
                    "generated": date.today().isoformat(), "cities": queue},
                   ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    if args.dry_run:
        print(json.dumps({"queued_cities": len(queue), "network_calls": 0}))
        return
    archive, report = discover(queue, args.budget, args.per_city, args.delay, args.start_index)
    (args.out / "world-historic-map-candidates.json").write_text(
        json.dumps(archive, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    (args.out / "world-historic-map-discovery-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
