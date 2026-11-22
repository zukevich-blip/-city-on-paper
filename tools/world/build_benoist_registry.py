#!/usr/bin/env python3
"""Merge every Benoist search file into one registry: discovered records, unique works, impressions.

Inputs: data/research/benoist/*.json (shared schema, see SCHEMA.md) and the legacy harvest
data/curation/benoist-harvest-v1.json (mapped to the schema without changing what the museums said).
Outputs:
* data/research/benoist/registry-v1.json  (research tier: every record, grouping, per-source counts)
* book/benoist-registry.json              (public-safe: titles, links, flags; NO image files, no private paths)
Philippe and Félix are never merged: artist_id decides. A record that names neither clearly is ``uncertain-benoist``.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "data" / "research" / "benoist"
LEGACY = ROOT / "data" / "curation" / "benoist-harvest-v1.json"
SHEETS = ROOT / "book" / "benoist-sheets.json"
OUT_RESEARCH = RESEARCH / "registry-v1.json"
OUT_PUBLIC = ROOT / "book" / "benoist-registry.json"
SKIP_FILES = {"registry-v1.json", "duplicate-groups-v1.json", "photo-pairs-report-v1.json", "photos-by-place-v1.json"}
GROUPS = RESEARCH / "duplicate-groups-v1.json"
CITY_COUNTRY = {
    "Paris": "Франция",
    "Nantes": "Франция",
    "Rouen": "Франция",
    "Lyon": "Франция",
    "Bordeaux": "Франция",
    "Rome": "Италия",
    "Naples": "Италия",
    "Florence": "Италия",
    "Venice": "Италия",
    "Milan": "Италия",
    "Genoa": "Италия",
    "Brussels": "Бельгия",
    "Ghent": "Бельгия",
    "Antwerp": "Бельгия",
    "Amsterdam": "Нидерланды",
    "Toledo": "Испания",
    "Madrid": "Испания",
    "Seville": "Испания",
    "Barcelona": "Испания",
    "Moscow": "Россия",
    "London": "Великобритания",
    "Geneva": "Швейцария",
    "Vienna": "Австрия",
}


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def artist_id(names: list[str], hint: str | None = None) -> str:
    if hint in {"philippe-benoist", "felix-benoist", "uncertain-benoist", "other"}:
        return hint
    joined = fold(" ".join(names))
    has_f = "felix" in joined or re.search(r"\bf\b benoist|benoist f\b", joined)
    has_p = "philippe" in joined or re.search(r"\bph\b benoist|benoist ph\b", joined)
    if has_f and not has_p:
        return "felix-benoist"
    if has_p and not has_f:
        return "philippe-benoist"
    return "uncertain-benoist"


def legacy_to_schema(rec: dict) -> dict:
    creators = rec.get("creators") or []
    names = [c.get("name") or "" for c in creators]
    open_file = rec.get("rights_class") == "open" and bool(rec.get("image_url"))
    return {
        "record_id": "legacy:" + rec["id"],
        "artist_id": artist_id(names),
        "participants": [
            {"name": c.get("name"), "role_as_stated": c.get("role_as_stated"), "role_normalized": "unspecified"}
            for c in creators
        ],
        "original_title": rec.get("title_original"),
        "series": None,
        "city": rec.get("place_depicted"),
        "date_as_stated": rec.get("date_as_stated"),
        "object_type": rec.get("kind"),
        "institution": rec.get("holder"),
        "accession": rec.get("accession_id"),
        "record_url": rec.get("record_url"),
        "image_url": rec.get("image_url"),
        "rights_statement": rec.get("rights_statement"),
        "rights_status": "open_confirmed" if open_file else "link_only",
        "verification_status": "source_record_read",
        "attribution_confidence": rec.get("attribution_confidence"),
        "duplicate_hint": None,
        "_origin": "legacy-harvest-v1",
        "known": rec.get("known"),
    }


def year_of(date: str | None) -> int | None:
    """First plausible year (1500-1999) in a date string exactly as a record states it."""
    m = re.search(r"(?<!\d)(1[5-9]\d\d)(?!\d)", date or "")
    return int(m.group(1)) if m else None


def group_key(rec: dict) -> str:
    hint = rec.get("duplicate_hint")
    if hint:
        return f"{rec.get('artist_id')}|{hint}"
    series = fold(rec.get("series") or "")
    title = fold(
        re.sub(
            r"\(\s*\d+\s*\)|\bviews of paris\b|\bvues de paris\b", " ", (rec.get("original_title") or "").split("/")[0]
        )
    )
    return f"{rec.get('artist_id')}|{series}|{rec.get('plate_number') or ''}|{title}"


def load_records() -> tuple[list[dict], dict]:
    records: list[dict] = []
    sources: dict[str, dict] = {}
    if LEGACY.exists():
        legacy = json.loads(LEGACY.read_text(encoding="utf-8"))["records"]
        records += [legacy_to_schema(r) for r in legacy]
        sources["legacy-harvest-v1"] = {"records": len(legacy)}
    for f in sorted(RESEARCH.glob("*.json")):
        if f.name in SKIP_FILES:
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        recs = data.get("records", [])
        for r in recs:
            r.setdefault("_origin", f.name)
        records += recs
        sources[f.name] = {"records": len(recs), "coverage": data.get("coverage")}
    seen: dict[str, dict] = {}
    unique: list[dict] = []
    for r in records:  # the same record read by two searches is one record, never two
        rid = r.get("record_id")
        if rid and rid in seen:
            for k, v in r.items():
                if seen[rid].get(k) in (None, "", []) and v not in (None, "", []):
                    seen[rid][k] = v
            continue
        if rid:
            seen[rid] = r
        unique.append(r)
    return unique, sources


def norm_url(url: str | None) -> str:
    """Compare record pages across ``www.``, scheme, query and language prefixes of the same museum."""
    u = re.sub(r"^https?://(www\.)?", "", (url or "").lower())
    # the Landesarchiv permalink IS its query (?f=4-...); every other museum page is identified by its path
    u = (u if "landesarchiv-bw.de/plink" in u else u.split("?")[0]).rstrip("/")
    return re.sub(r"^(parismuseescollections\.paris\.fr)/(fr|en|de|ru|zh-hans)/", r"\1/", u)


def public_images() -> dict[str, str]:
    """record_url -> local image for sheets the public museum really ships."""
    out: dict[str, str] = {}
    if SHEETS.exists():
        for s in json.loads(SHEETS.read_text(encoding="utf-8"))["sheets"]:
            out[norm_url(s["record_url"])] = s["image"]
    return out


def record_aliases(rid: str) -> list[str]:
    """Ids a record may be known by: the legacy harvest wrote europeana/... where newer searches write europeana:/..."""
    out = [rid]
    if rid.startswith("legacy:"):
        bare = rid[7:]
        out += [bare, bare.replace("/", ":/", 1)]
    return out


def apply_duplicate_groups(groups: dict[str, list[dict]]) -> tuple[dict[str, list[dict]], int, int]:
    """Merge works that a HIGH duplicate group says are one sheet; MEDIUM groups are only counted as possible."""
    if not GROUPS.exists():
        return groups, 0, 0
    data = json.loads(GROUPS.read_text(encoding="utf-8"))
    where: dict[str, str] = {}
    for key, members in groups.items():
        for m in members:
            for a in record_aliases(m.get("record_id") or ""):
                where[a] = key
    parent = {k: k for k in groups}

    def find(k: str) -> str:
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    def keys_of(group: dict) -> set[str]:
        return {where[m["record_id"]] for m in group["members"] if m["record_id"] in where}

    merged = 0
    for g in data.get("high_groups", []):
        ks = sorted(keys_of(g))
        for other in ks[1:]:
            a, b = find(ks[0]), find(other)
            if a != b:
                parent[b] = a
                merged += 1
    possible = sum(1 for g in data.get("medium_groups", []) if len({find(k) for k in keys_of(g)}) > 1)
    out: dict[str, list[dict]] = defaultdict(list)
    for key, members in groups.items():
        out[find(key)].extend(members)
    return out, merged, possible


def build() -> tuple[dict, dict]:
    records, sources = load_records()
    shipped = public_images()
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        r["artist_id"] = r.get("artist_id") or "uncertain-benoist"
        groups[group_key(r)].append(r)
    strict = len(groups)
    groups, merged_by_high, possible = apply_duplicate_groups(groups)
    works = []
    for i, (_key, members) in enumerate(sorted(groups.items()), start=1):
        head = members[0]
        city = next((m.get("city") for m in members if m.get("city")), None)
        image = next(
            (shipped[norm_url(m.get("record_url"))] for m in members if norm_url(m.get("record_url")) in shipped), None
        )
        images = sorted(
            {shipped[norm_url(m.get("record_url"))] for m in members if norm_url(m.get("record_url")) in shipped}
        )
        works.append(
            {
                "id": f"w{i:04d}",
                "artist": head["artist_id"],
                "title": head.get("original_title"),
                "series": next((m.get("series") for m in members if m.get("series")), None),
                "city": city,
                "country": CITY_COUNTRY.get(city or "") if city else None,
                "date": next((m.get("date_as_stated") for m in members if m.get("date_as_stated")), None),
                "year": year_of(next((m.get("date_as_stated") for m in members if m.get("date_as_stated")), None)),
                "kind": head.get("object_type"),
                "impressions": len(members),
                "image": image,
                "images": images,
                "reviewed": any(m.get("verification_status") == "source_record_read" for m in members),
                "open_file": any(m.get("rights_status") == "open_confirmed" for m in members),
                "holders": [
                    {
                        "institution": m.get("institution"),
                        "accession": m.get("accession"),
                        "url": m.get("record_url"),
                        "rights": m.get("rights_status"),
                    }
                    for m in members
                ],
            }
        )
    per_source = Counter(r["_origin"] for r in records)
    summary = {
        "discovered_records": len(records),
        "unique_works": len(works),
        "unique_works_strict": strict,
        "merged_by_high_groups": merged_by_high,
        "possible_merges_medium": possible,
        "extra_impressions": len(records) - len(works),
        "reviewed": sum(w["reviewed"] for w in works),
        "open_file": sum(w["open_file"] for w in works),
        "shipped_with_image": len(json.loads(SHEETS.read_text(encoding="utf-8"))["sheets"]) if SHEETS.exists() else 0,
        "shipped_matched_to_register": len({im for w in works for im in w["images"]}),
        "external_only": sum(1 for w in works if not w["open_file"]),
        "no_image_at_all": sum(1 for w in works if not w["open_file"] and not w["image"]),
        "by_artist": dict(Counter(w["artist"] for w in works)),
        "by_source": dict(per_source),
    }
    research = {"version": 1, "summary": summary, "sources": sources, "works": works}
    public = {
        "version": 1,
        "summary": summary,
        "works": [
            {
                k: w[k]
                for k in (
                    "id",
                    "artist",
                    "title",
                    "series",
                    "city",
                    "country",
                    "date",
                    "year",
                    "kind",
                    "impressions",
                    "image",
                    "images",
                    "open_file",
                )
            }
            | {"links": [{"i": h["institution"], "u": h["url"]} for h in w["holders"] if h["url"]][:4]}
            for w in works
        ],
    }
    return research, public


def main() -> int:
    research, public = build()
    OUT_RESEARCH.write_text(json.dumps(research, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    OUT_PUBLIC.write_text(json.dumps(public, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(research["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
