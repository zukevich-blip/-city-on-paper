#!/usr/bin/env python3
"""Street-level photos of each depicted site from Panoramax (open, CC BY-SA 4.0 / etalab-2.0), WITH the camera point.

For each site (data/vision-lab/sites.json, grouped by QID): search Panoramax within ~300 m, keep flat (non-360) photos
whose camera is 25–300 m from the site and whose azimuth points at it (|Δ| ≤ 25°). Best 2 per site (different
authors/dates). Saves a resized copy (≤ 900 px, EXIF stripped) under eras/now/ and data/vision-lab/panoramax.json
with camera lat/lon/azimuth/fov, author, licence and a link to the picture on Panoramax. Resumable, ≤ 1 req/s.
"""
from __future__ import annotations

import io
import json
import math
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
VL = ROOT / "data" / "vision-lab"
OUT = VL / "panoramax.json"
IMG = ROOT / "eras" / "now"
UA = "CityOnPaperResearch/0.6 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)"
API = "https://api.panoramax.xyz/api/search"
LIC = {"CC-BY-SA-4.0": ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
       "etalab-2.0": ("Licence Ouverte 2.0 (etalab)", "https://www.etalab.gouv.fr/licence-ouverte-open-licence/"),
       "CC-BY-4.0": ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
       "CC0-1.0": ("CC0", "https://creativecommons.org/publicdomain/zero/1.0/")}


def get(url: str, raw: bool = False):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40) as r:
                return r.read() if raw else json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(30 * (attempt + 1))
                continue
            return None
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5)
    return None


def dist_bearing(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a)), (math.degrees(math.atan2(x, y)) + 360) % 360


def main() -> None:
    sites = json.loads((VL / "sites.json").read_text("utf-8"))["items"]
    groups: dict[str, tuple] = {}
    for s in sites:
        if s.get("qid") and s.get("lat") is not None and s.get("kind") not in ("unresolved", "panorama", "interior") \
                and s.get("confidence") != "low" and s.get("coord_role") != "viewpoint":
            groups.setdefault(s["qid"], (s["lat"], s["lon"], s.get("site_name_ru") or s.get("site_name")))
    out = json.loads(OUT.read_text("utf-8")) if OUT.exists() else {}
    IMG.mkdir(parents=True, exist_ok=True)
    for qid, (lat, lon, _name) in groups.items():
        if qid in out:
            continue
        dlat, dlon = 0.0028, 0.0028 / max(0.2, math.cos(math.radians(lat)))
        d = get(f"{API}?bbox={lon - dlon},{lat - dlat},{lon + dlon},{lat + dlat}&limit=200")
        time.sleep(1)
        cands = []
        for f in (d or {}).get("features", []):
            p = f["properties"]
            az, fov = p.get("view:azimuth"), (p.get("pers:interior_orientation") or {}).get("field_of_view")
            if az is None or (fov or 0) >= 180 or p.get("license") not in LIC:
                continue
            clon, clat = f["geometry"]["coordinates"][:2]
            dist, brg = dist_bearing(clat, clon, lat, lon)
            delta = abs((brg - az + 180) % 360 - 180)
            if not (25 <= dist <= 300) or delta > 25:
                continue
            cands.append((delta / 25 + abs(dist - 110) / 190, f, clat, clon, az, fov, dist))
        cands.sort(key=lambda c: c[0])
        picked, seen = [], set()
        for _, f, clat, clon, az, fov, dist in cands:
            p = f["properties"]
            key = (p.get("geovisio:producer"), (p.get("datetime") or "")[:7])
            if key in seen:
                continue
            raw = get(f["assets"]["sd"]["href"], raw=True)
            time.sleep(1)
            if not raw:
                continue
            try:
                im = Image.open(io.BytesIO(raw)).convert("RGB")
            except OSError:
                continue
            im.thumbnail((900, 900))
            fn = f"pnx-{f['id'][:13]}.jpg"
            im.save(IMG / fn, quality=82, optimize=True, progressive=True)  # no EXIF written
            lic, lic_url = LIC[p["license"]]
            picked.append({"id": f["id"], "file": f"now/{fn}", "camera": {"lat": round(clat, 6), "lon": round(clon, 6),
                           "azimuth": az, "fov": fov or 60, "distance_m": round(dist)},
                           "date": (p.get("datetime") or "")[:10],
                           "author": p.get("geovisio:producer") or "автор Panoramax",
                           "license": lic, "license_url": lic_url,
                           "page": f"https://api.panoramax.xyz/#focus=pic&pic={f['id']}",
                           "note": "уменьшено до 900 px, метаданные EXIF удалены; иначе не изменено"})
            seen.add(key)
            if len(picked) == 2:
                break
        out[qid] = picked
        OUT.write_text(json.dumps(dict(sorted(out.items())), ensure_ascii=False, indent=1) + "\n", "utf-8")
    n = sum(len(v) for v in out.values())
    print(f"{n} Panoramax photos for {sum(1 for v in out.values() if v)} of {len(groups)} sites")


if __name__ == "__main__":
    main()
