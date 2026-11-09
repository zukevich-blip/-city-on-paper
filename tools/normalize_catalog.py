#!/usr/bin/env python3
"""Conservative, repeatable archival catalog normalizer for City on Paper.

Inputs: the actual repository folders data/curation and data/catalog.
No network access by default. Online enrichment verifies ONLY explicitly
provided QIDs/GeoNames IDs, or suggests search hits without auto-attribution.
All output stays out of the public publication allowlist.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[1]
USER_AGENT = "CityOnPaperCatalog/1.0 (https://github.com/zukevich-blip/-city-on-paper; research catalog)"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
GEONAMES_API = "https://secure.geonames.org"
QID_RE = re.compile(r"^Q[1-9][0-9]*$")
GEONAME_RE = re.compile(r"^[1-9][0-9]*$")
TRUE_KINDS = {"museum_api": "museum_recorded", "verified": "source_claimed_verified"}
MAX_API_CALLS = 30
MAX_RESPONSE_BYTES = 2_000_000


def fold(value: Any) -> str:
    """Unicode normalization for comparison, never an authority identifier."""
    s = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"\s+", " ", s).strip()


def stable_id(prefix: str, key: str) -> str:
    return prefix + "-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:18]


def canonical_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    parts = urlsplit(value.strip())
    if parts.scheme.lower() not in ("https", "http") or not parts.hostname:
        return None
    host = parts.hostname.lower()
    port = f":{parts.port}" if parts.port else ""
    path = re.sub(r"/+", "/", parts.path).rstrip("/") or "/"
    # Do not strip meaningful query IDs: they can identify an archival item.
    return urlunsplit((parts.scheme.lower(), host + port, path,
                       parts.query, ""))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _record(src: str, idx: int, item: dict[str, Any], *,
            title: str, institution: str, accession: str | None,
            url: str | None, city: str, country: str, maker: str,
            date: str, rights: str, qid: str | None = None) -> dict[str, Any]:
    return {
        "origin_file": src, "origin_index": idx,
        "title": title.strip(), "institution": institution.strip(),
        "accession": (str(accession).strip() if accession else None),
        "object_url": canonical_url(url),
        "depicted_city_claim": city.strip(), "country_claim": country.strip(),
        "creator_claim": maker.strip(), "date_claim": date.strip(),
        "rights_claim": rights.strip(), "wikidata_claim": qid,
        "source_record": item,
    }


def collect(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Import only known source schemas; never indiscriminately crawl data/."""
    records: list[dict[str, Any]] = []
    cities: list[dict[str, Any]] = []
    warnings: list[str] = []

    city_file = root / "data/curation/world-cities-v1.json"
    if city_file.is_file():
        data = _read_json(city_file)
        if not isinstance(data.get("cities"), list):
            raise ValueError("Invalid world cities seed")
        for idx, city in enumerate(data["cities"]):
            if not isinstance(city, dict):
                warnings.append(f"City seed row {idx} is not an object")
                continue
            cities.append({
                "name": str(city.get("name") or "").strip(),
                "country": str(city.get("country") or "").strip(),
                "region": str(city.get("region") or "").strip(),
                "wikidata_claim": city.get("wikidata_id") or city.get("wikidata"),
                "geonames_claim": city.get("geoname_id") or city.get("geonames_id"),
                "latitude_claim": city.get("lat"),
                "longitude_claim": city.get("lon"),
                "source": "data/curation/world-cities-v1.json",
                "source_index": idx,
            })

    gallery = root / "data/curation/cc0-gallery-20261103.json"
    if gallery.is_file():
        data = _read_json(gallery)
        if not isinstance(data.get("items"), list):
            raise ValueError("Invalid curated gallery")
        for idx, row in enumerate(data["items"]):
            if not isinstance(row, dict):
                warnings.append(f"Gallery row {idx} is not an object")
                continue
            records.append(_record(
                "data/curation/cc0-gallery-20261103.json", idx, row,
                title=str(row.get("title_original") or row.get("name") or ""),
                institution=str(row.get("source") or "Cleveland Museum of Art"),
                accession=str(row.get("source_id") or row.get("id") or ""),
                url=row.get("url"), city=str(row.get("city") or ""),
                country=str(row.get("country") or ""),
                maker=str(row.get("maker") or ""), date=str(row.get("date") or ""),
                rights=str(row.get("rights") or ""),
                qid=row.get("wikidata_id"),
            ))

    ledger = root / "data/catalog/ledger-2026-11-01.csv"
    if ledger.is_file():
        with ledger.open(encoding="utf-8-sig", newline="") as handle:
            for idx, row in enumerate(csv.DictReader(handle)):
                records.append(_record(
                    "data/catalog/ledger-2026-11-01.csv", idx, row,
                    title=str(row.get("title") or ""),
                    institution=str(row.get("institution") or ""),
                    accession=str(row.get("accession_id") or ""),  # source ID only
                    url=row.get("object_url"), city=str(row.get("depicted_city") or ""),
                    country=str(row.get("depicted_country") or ""),
                    maker=str(row.get("artists_roles") or ""),
                    date=str(row.get("date") or ""),
                    rights=str(row.get("redistribution") or ""),
                    qid=row.get("wikidata_id"),
                ))

    works_dir = root / "data/catalog/works"
    if works_dir.exists():
        for path in sorted(works_dir.glob("*.json")):
            row = _read_json(path)
            if not isinstance(row, dict):
                warnings.append(f"{path.name}: not a JSON object")
                continue
            h = row.get("holding") or {}
            if not isinstance(h, dict):
                h = {}
            names = row.get("titles") or []
            title = next((str(t.get("text")) for t in names
                          if isinstance(t, dict) and t.get("text")), "")
            place = row.get("place") or {}
            if not isinstance(place, dict):
                place = {}
            persons = row.get("agents") or []
            agents = "; ".join(str(a.get("name")) for a in persons
                               if isinstance(a, dict) and a.get("name"))
            rights = row.get("rights") or {}
            if not isinstance(rights, dict):
                rights = {}
            records.append(_record(
                f"data/catalog/works/{path.name}", 0, row,
                title=title, institution=str(h.get("institution") or ""),
                accession=str(h.get("accession_id") or ""),
                url=h.get("object_url"), city=str(place.get("city") or ""),
                country=str(place.get("country") or ""),
                maker=agents, date=str(row.get("date") or ""),
                rights=str(rights.get("redistribution") or ""),
                qid=row.get("wikidata_id"),
            ))
    if not records:
        raise ValueError("No recognized archival records: nothing to normalize")
    return records, cities, warnings


def city_index(raw_cities: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    cities: dict[str, dict[str, Any]] = {}
    index: dict[str, list[str]] = defaultdict(list)
    for row in raw_cities:
        name, country = row["name"], row["country"]
        if not name or not country:
            continue
        key = fold(country) + "|" + fold(name)
        city_id = stable_id("city", key)
        if city_id not in cities:
            qid, geo = row["wikidata_claim"], row["geonames_claim"]
            cities[city_id] = {
                "id": city_id, "name": name, "country": country,
                "region": row["region"],
                "wikidata_id": qid if isinstance(qid, str) and QID_RE.fullmatch(qid) else None,
                "geonames_id": str(geo) if geo and GEONAME_RE.fullmatch(str(geo)) else None,
                "geonames_status": "location_pending",
                "latitude": row["latitude_claim"], "longitude": row["longitude_claim"],
                "source": row["source"], "provenance": "research_seed_not_verified",
            }
        if city_id not in index[fold(name)]:
            index[fold(name)].append(city_id)
    return sorted(cities.values(), key=lambda c: c["id"]), dict(index)


def _holding_key(rec: dict[str, Any]) -> tuple[str, str]:
    # Institution + accession is strongest. If accession is merely a local
    # gallery slug, the full object URL remains a safer authority.
    institution = fold(rec["institution"])
    accession = fold(rec["accession"])
    if institution and accession and not accession.startswith(("cma-", "loc-")):
        return "accession", institution + "|" + accession
    if rec["object_url"]:
        return "url", rec["object_url"]
    return "source_row", f'{rec["origin_file"]}|{rec["origin_index"]}'


def _record_work(rec: dict[str, Any], city_ids: list[str]) -> dict[str, Any]:
    key_type, key = _holding_key(rec)
    holding_id = stable_id("holding", key_type + "|" + key)
    wd = rec["wikidata_claim"]
    qid = wd if isinstance(wd, str) and QID_RE.fullmatch(wd) else None
    return {
        "id": stable_id("work", holding_id),
        "title": rec["title"],
        "creator": {"label": rec["creator_claim"], "status": "source_claim_only"},
        "date": {"label": rec["date_claim"], "status": "source_claim_only"},
        "wikidata_id": qid,
        "wikidata_status": "not_checked" if qid else "no_explicit_qid",
        "depiction": {
            "source_city": rec["depicted_city_claim"],
            "source_country": rec["country_claim"],
            "city_ids": city_ids,
            "status": ("linked_to_seed_not_verified" if len(city_ids) == 1
                       else "ambiguous" if len(city_ids) > 1 else "location_pending"),
        },
        "rights": {
            "source_label": rec["rights_claim"],
            "status": "source_claim_only",
            "reuse_approved_by_this_pipeline": False,
        },
        "holdings": [{
            "id": holding_id, "institution": rec["institution"],
            "accession_id": rec["accession"],
            "object_url": rec["object_url"], "source_file": rec["origin_file"],
            "source_index": rec["origin_index"],
        }],
        "review_status": "needs_editorial_review",
    }


def normalize(records: list[dict[str, Any]],
              raw_cities: list[dict[str, Any]]) -> dict[str, Any]:
    cities, lookup = city_index(raw_cities)
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    possible: dict[tuple[str, str], list[str]] = defaultdict(list)
    conflicts = []
    identical = []

    for rec in records:
        if not rec["title"] or not rec["institution"] or not rec["object_url"]:
            conflicts.append({
                "type": "incomplete_holding", "origin": rec["origin_file"],
                "index": rec["origin_index"],
            })
            continue
        if rec["depicted_city_claim"]:
            city_ids = lookup.get(fold(rec["depicted_city_claim"]), [])
            if rec["country_claim"]:
                city_ids = [cid for cid in city_ids if any(
                    c["id"] == cid and fold(c["country"]) == fold(rec["country_claim"])
                    for c in cities
                )]
        else:
            city_ids = []

        key = _holding_key(rec)
        if key in by_key:
            existing = by_key[key]
            identical.append({"holding_id": existing["holdings"][0]["id"],
                              "source_file": rec["origin_file"],
                              "source_index": rec["origin_index"]})
            if fold(existing["title"]) != fold(rec["title"]):
                conflicts.append({
                    "type": "conflicting_titles_same_holding",
                    "holding_id": existing["holdings"][0]["id"],
                    "title_a": existing["title"], "title_b": rec["title"],
                })
            existing["holdings"][0].setdefault("cross_references", []).append({
                "source_file": rec["origin_file"], "source_index": rec["origin_index"],
            })
            continue

        work = _record_work(rec, city_ids)
        by_key[key] = work
        # Same explicit QID suggests a common work, but does not justify
        # merging archival holdings without authoritative object identity.
        if work["wikidata_id"]:
            possible[("wikidata", work["wikidata_id"])].append(work["id"])
        if rec["title"] and rec["creator_claim"]:
            possible[("title_creator", fold(rec["title"]) + "|" + fold(rec["creator_claim"]))].append(work["id"])

    suggestions = [{
        "reason": key[0], "match_key": key[1], "work_ids": sorted(ids),
        "action": "review_only_do_not_merge",
    } for key, ids in sorted(possible.items()) if len(ids) > 1]

    works = sorted(by_key.values(), key=lambda x: x["id"])
    return {
        "schema": "city-on-paper/normalized-catalog/v1",
        "cities": cities, "works": works,
        "review_queue": {"conflicts": conflicts, "exact_duplicates": identical,
                         "possible_duplicates": suggestions},
        "policy": {
            "raw_archival_claims_preserved": True,
            "wikidata_is_not_an_attribution_certificate": True,
            "geonames_city_centroid_is_not_artwork_location": True,
            "license_requires_image_file_review": True,
            "public_release_approved": False,
        },
    }


def _claim_value(entity: dict[str, Any], prop: str) -> list[Any]:
    result = []
    for stmt in entity.get("claims", {}).get(prop, []):
        snak = stmt.get("mainsnak") or {}
        if snak.get("snaktype") != "value":
            continue
        value = (snak.get("datavalue") or {}).get("value")
        if isinstance(value, dict) and "id" in value:
            result.append(value["id"])
        elif isinstance(value, dict) and "time" in value:
            result.append({
                "time": value["time"], "precision": value.get("precision"),
                "calendar": value.get("calendarmodel"),
            })
    return result


def wikidata_claims(entity: dict[str, Any]) -> dict[str, Any]:
    """Extraction only. Never assume a property's claim is independently true."""
    return {
        "entity_id": entity.get("id"),
        "creators_p170": _claim_value(entity, "P170"),
        "authors_p50": _claim_value(entity, "P50"),
        "inception_p571": _claim_value(entity, "P571"),
        "publication_p577": _claim_value(entity, "P577"),
        "point_in_time_p585": _claim_value(entity, "P585"),
        "provenance": "Wikidata statement, requires institution corroboration",
    }


class DeferredRemote(Exception):
    """A rate limit or temporary failure must not be recast as 'no record'."""


class API:
    def __init__(self, cache: Path, *, timeout: int = 12,
                 retries: int = 2, sleeper: Any = time.sleep):
        self.cache = cache
        self.cache.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.retries = retries
        self.sleep = sleeper
        self.calls = 0

    def get(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        key = hashlib.sha256((url + "?" + urlencode(sorted(params.items()))).encode()).hexdigest()
        path = self.cache / (key + ".json")
        if path.is_file():
            value = _read_json(path)
            if isinstance(value, dict):
                return value
        if self.calls >= MAX_API_CALLS:
            raise DeferredRemote("Network budget exhausted: defer instead of guessing")
        for attempt in range(self.retries + 1):
            try:
                self.calls += 1
                req = Request(url + "?" + urlencode(params), headers={
                    "User-Agent": USER_AGENT, "Accept": "application/json",
                    "Accept-Encoding": "identity",
                })
                with urlopen(req, timeout=self.timeout) as response:
                    payload = response.read(MAX_RESPONSE_BYTES + 1)
                if len(payload) > MAX_RESPONSE_BYTES:
                    raise ValueError("API response too large")
                data = json.loads(payload.decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("API response is not an object")
                if data.get("error"):
                    raise DeferredRemote("Remote API error: " + str(data["error"])[:180])
                path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
                return data
            except HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504):
                    raise DeferredRemote(f"HTTP {exc.code}") from exc
                value = exc.headers.get("Retry-After") if exc.headers else None
                try:
                    delay = max(float(value), 0) if value else max(5, 5 * 2 ** attempt)
                except ValueError:
                    delay = max(5, 5 * 2 ** attempt)
                # Respect long server Retry-After by deferring the whole run,
                # not hammering the server or blocking CI for 20 minutes.
                if delay > 20 or attempt >= self.retries:
                    raise DeferredRemote(f"HTTP {exc.code}, retry after {delay:g}s") from exc
                self.sleep(delay)
            except (URLError, TimeoutError) as exc:
                if attempt >= self.retries:
                    raise DeferredRemote(str(exc)) from exc
                self.sleep(max(5, 5 * 2 ** attempt))
        raise DeferredRemote("Unavailable")


def enrich_catalog(catalog: dict[str, Any], api: API, *,
                   enable_wikidata: bool, enable_geonames: bool,
                   geonames_user: str | None, suggest_limit: int = 0) -> dict[str, Any]:
    results: dict[str, Any] = {
        "wikidata_checked": 0, "geonames_checked": 0,
        "suggestions_checked": 0, "deferred": [],
    }
    if enable_wikidata:
        for work in catalog["works"]:
            qid = work["wikidata_id"]
            if not qid:
                continue
            try:
                response = api.get(WIKIDATA_API, {
                    "action": "wbgetentities", "format": "json", "ids": qid,
                    "props": "claims|labels", "maxlag": "5",
                })
                entity = (response.get("entities") or {}).get(qid) or {}
                if entity.get("missing") is not None or entity.get("id") != qid:
                    work["wikidata_status"] = "id_unresolved"
                else:
                    work["wikidata_status"] = "metadata_retrieved_not_verified"
                    work["wikidata_metadata"] = wikidata_claims(entity)
                    results["wikidata_checked"] += 1
            except DeferredRemote as exc:
                work["wikidata_status"] = "remote_deferred"
                results["deferred"].append({"source": "Wikidata", "id": qid,
                                            "reason": str(exc)})
                break

        for work in catalog["works"]:
            if results["suggestions_checked"] >= suggest_limit:
                break
            if work["wikidata_id"] or not work["title"]:
                continue
            try:
                response = api.get(WIKIDATA_API, {
                    "action": "wbsearchentities", "format": "json",
                    "search": work["title"], "language": "en", "limit": "3",
                    "type": "item", "maxlag": "5",
                })
                work["wikidata_suggestions"] = [{
                    "id": it.get("id"), "label": it.get("label"),
                    "description": it.get("description"), "status": "search_hit_unverified",
                } for it in response.get("search", []) if QID_RE.fullmatch(str(it.get("id", "")))]
                results["suggestions_checked"] += 1
            except DeferredRemote as exc:
                results["deferred"].append({"source": "Wikidata search",
                                            "id": work["id"], "reason": str(exc)})
                break

    if enable_geonames:
        if not geonames_user or geonames_user == "demo":
            results["deferred"].append({
                "source": "GeoNames", "reason": "GEONAMES_USERNAME required; demo account forbidden",
            })
        else:
            for city in catalog["cities"]:
                gid = city["geonames_id"]
                if not gid:
                    continue
                try:
                    response = api.get(GEONAMES_API + "/getJSON", {
                        "geonameId": gid, "username": geonames_user,
                    })
                    remote_id = str(response.get("geonameId") or "")
                    lat = response.get("lat")
                    lon = response.get("lng")
                    if remote_id != gid or not valid_coords(lat, lon):
                        city["geonames_status"] = "geonames_conflict"
                    else:
                        city["geonames_status"] = "geonames_id_retrieved"
                        city["geonames_coordinates"] = {
                            "lat": float(lat), "lon": float(lon),
                            "evidence_url": f"https://www.geonames.org/{gid}/",
                        }
                        results["geonames_checked"] += 1
                except DeferredRemote as exc:
                    city["geonames_status"] = "remote_deferred"
                    results["deferred"].append({
                        "source": "GeoNames", "id": gid, "reason": str(exc),
                    })
                    break
    return results


def valid_coords(lat: Any, lon: Any) -> bool:
    try:
        la, lo = float(lat), float(lon)
    except (ValueError, TypeError):
        return False
    return math.isfinite(la) and math.isfinite(lo) and -90 <= la <= 90 and -180 <= lo <= 180


def report(catalog: dict[str, Any], source_count: int,
           warnings: list[str], remote: dict[str, Any]) -> dict[str, Any]:
    works, cities = catalog["works"], catalog["cities"]
    return {
        "schema": "city-on-paper/normalization-report/v1",
        "input_records": source_count, "normalized_holdings": len(works),
        "city_seed": len(cities),
        "missing_creator_claims": sum(not w["creator"]["label"] for w in works),
        "city_links_pending": sum(w["depiction"]["status"] != "linked_to_seed_not_verified"
                                  for w in works),
        "cities_location_pending": sum(c["geonames_status"] == "location_pending"
                                        for c in cities),
        "exact_duplicates_merged": len(catalog["review_queue"]["exact_duplicates"]),
        "possible_duplicate_groups": len(catalog["review_queue"]["possible_duplicates"]),
        "conflicts": len(catalog["review_queue"]["conflicts"]),
        "input_warnings": warnings, "online": remote,
        "scientific_status": "source claims retained; expert review not performed",
        "publication": "NOT APPROVED — raw/normalized files stay outside public allowlist",
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
                    + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=REPO)
    parser.add_argument("--out", type=Path, default=Path("dist/catalog"))
    parser.add_argument("--online", action="store_true", help="Opt-in verification of supplied IDs")
    parser.add_argument("--suggest", type=int, default=0,
                        help="Optional Wikidata title search, always unverified (max 10)")
    parser.add_argument("--geonames-user", default=os.getenv("GEONAMES_USERNAME", ""))
    args = parser.parse_args(argv)
    if args.suggest < 0 or args.suggest > 10:
        parser.error("--suggest must be 0..10")
    # Never accidentally write unreviewed raw research into tracked museum
    # folders. For output inside the repo only an ignored dist/ is allowed.
    root = args.root.resolve()
    out = args.out.resolve()
    if out == root or (out.is_relative_to(root) and
                       not out.is_relative_to(root / "dist")):
        raise ValueError("Unreviewed catalog output within repo must use dist/")
    raw, raw_cities, warnings = collect(args.root)
    catalog = normalize(raw, raw_cities)
    remote: dict[str, Any] = {"status": "offline_no_api_calls"}
    if args.online:
        api = API(args.out / ".cache")
        remote = enrich_catalog(
            catalog, api, enable_wikidata=True, enable_geonames=True,
            geonames_user=args.geonames_user, suggest_limit=args.suggest,
        )
    # Do not copy raw archive records into a page or build artifact.
    out = args.out
    write_json(out / "catalog_raw.json", {
        "schema": "city-on-paper/raw-catalog/v1", "records": raw,
        "source_cities": raw_cities,
    })
    write_json(out / "normalized_catalog.json", catalog)
    result = report(catalog, len(raw), warnings, remote)
    write_json(out / "normalization_report.json", result)
    print("PASS", json.dumps({
        k: v for k, v in result.items()
        if k not in ("input_warnings", "online")
    }, ensure_ascii=False))
    if result["conflicts"] or result["possible_duplicate_groups"]:
        print("REVIEW REQUIRED: inspect normalization_report.json / normalized_catalog.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
