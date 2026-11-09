#!/usr/bin/env python3
"""Prepare a worldwide, source-attributed major-city research queue from GeoNames.

Source: official GeoNames cities15000.zip gazetteer, CC BY 4.0.
The population threshold is a selection heuristic, not a reliable census.
NO records are automatically published as a verified museum city or artwork.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://download.geonames.org/export/dump/cities15000.zip"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
MAX_ZIP_BYTES = 18_000_000
MAX_TEXT_BYTES = 90_000_000
CITY_CODES = {"PPL", "PPLA", "PPLA2", "PPLA3", "PPLA4", "PPLC", "PPLC2", "PPLG"}
CAPITAL_CODES = {"PPLC", "PPLC2"}


def download() -> bytes:
    req = Request(URL, headers={
        "User-Agent": "CityOnPaperResearch/1.0 (https://github.com/zukevich-blip/-city-on-paper)"
    })
    with urlopen(req, timeout=55) as resp:
        data = resp.read(MAX_ZIP_BYTES + 1)
    if len(data) > MAX_ZIP_BYTES:
        raise ValueError("GeoNames compressed dump exceeds download limit")
    return data


def parse(data: bytes, min_population: int = 250000, max_cities: int = 12000) -> tuple[dict, dict]:
    if not (15000 <= min_population <= 10000000):
        raise ValueError("Population cutoff must be 15,000..10,000,000")
    if not (100 <= max_cities <= 50000):
        raise ValueError("Major-city limit must be 100..50,000")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if "cities15000.txt" not in archive.namelist():
            raise ValueError("Expected official cities15000.txt inside GeoNames archive")
        info = archive.getinfo("cities15000.txt")
        if info.file_size > MAX_TEXT_BYTES:
            raise ValueError("Uncompressed GeoNames dump exceeds safety limit")
        rows = []
        seen: set[int] = set()
        with archive.open(info) as handle, io.TextIOWrapper(
            handle, encoding="utf-8", errors="strict"
        ) as stream:
            for line in stream:
                fields = line.rstrip("\n").split("\t")
                if len(fields) < 19:
                    continue
                try:
                    geoid = int(fields[0])
                    lat, lon = float(fields[4]), float(fields[5])
                    population = int(fields[14])
                except ValueError:
                    continue
                feature = fields[7]
                if fields[6] != "P" or feature not in CITY_CODES:
                    continue
                if population < min_population and feature not in CAPITAL_CODES:
                    continue
                name, ascii_name, iso2 = fields[1].strip(), fields[2].strip(), fields[8].strip()
                if (not geoid or geoid in seen or not name or not iso2 or
                        len(iso2) != 2 or not math.isfinite(lat) or
                        not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180):
                    continue
                seen.add(geoid)
                rows.append({
                    "geonames_id": geoid,
                    "candidate_city_id": "geonames-" + str(geoid),
                    "name": name, "name_ascii": ascii_name or name,
                    "country_iso2": iso2, "admin1_code": fields[10],
                    "lat": lat, "lon": lon,
                    "population_reported_by_geonames": population,
                    "feature_code": feature,
                    "source_url": "https://www.geonames.org/" + str(geoid) + "/",
                    "identity_status": "gazetteer_candidate_requires_entity_resolution",
                    "artworks_verified": 0,
                    "historic_maps_georeferenced": 0,
                })
        rows.sort(key=lambda x: (-x["population_reported_by_geonames"], x["geonames_id"]))
        rows = rows[:max_cities]
    output = {
        "schema": "city-on-paper/geonames-major-city-candidates/v1",
        "source_url": URL, "source_license": "CC BY 4.0",
        "license_url": LICENSE,
        "download_sha256": hashlib.sha256(data).hexdigest(),
        "generated": date.today().isoformat(),
        "publication_status": "research_only_unmatched_geonames_candidates",
        "selection": {
            "minimum_population_reported": min_population,
            "include_capitals_under_threshold": True,
            "max_city_rows": max_cities,
        },
        "warnings": [
            "GeoNames population values may be stale or incomparable across countries.",
            "A geonamesid identifies a populated place candidate, not necessarily a city as used by historians.",
            "Coordinates refer to a gazetteer location, NOT a 19th-century GCP.",
            "Never merge multilingual/homonymous cities by name alone.",
            "GeoNames requires attribution (CC BY 4.0); do not drop source/license.",
        ],
        "cities": rows,
    }
    summary = {
        "source": URL,
        "number_of_major_city_candidates": len(rows),
        "countries_with_candidates": len({x["country_iso2"] for x in rows}),
        "capitals_included": sum(x["feature_code"] in CAPITAL_CODES for x in rows),
        "population_ge_cutoff": sum(
            x["population_reported_by_geonames"] >= min_population for x in rows),
        "source_license": "GeoNames CC BY 4.0",
        "status": "research_candidates_not_published",
    }
    return output, summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-zip", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--min-population", type=int, default=250000)
    p.add_argument("--max-cities", type=int, default=12000)
    a = p.parse_args()
    data = a.source_zip.read_bytes() if a.source_zip else download()
    doc, summary = parse(data, a.min_population, a.max_cities)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "geonames-major-cities-research.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (a.out / "geonames-major-city-report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
