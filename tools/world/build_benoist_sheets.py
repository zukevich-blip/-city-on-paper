#!/usr/bin/env python3
"""Build book/benoist-sheets.json: the Benoist prints whose IMAGE the holder itself releases as open.

Source: data/curation/benoist-harvest-v1.json (records collected by tools/world/collect_benoist.py).
A sheet is included only when the record names Benoist with high confidence, the holder states an open
image licence (Public Domain Mark here, Rijksmuseum) and an image URL. Roles are copied as the holder states them.
With --fetch the 900 px IIIF copies are downloaded politely into book/img/benoist/ (one per sheet).
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "curation" / "benoist-harvest-v1.json"
PM = ROOT / "data" / "curation" / "benoist-parismusees-batch-v1.json"
OUT = ROOT / "book" / "benoist-sheets.json"
IMG_DIR = ROOT / "book" / "img" / "benoist"
UA = "CityOnPaperResearch/0.9 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)"
ROLES_RU = {
    "printmaker": "автор оттиска (printmaker)",
    "publisher": "издатель",
    "printer (person)": "печатник",
    "after drawing by": "по рисунку",
    "after design by": "по рисунку",
    "after own design by": "по собственному рисунку",
}


def file_name(record_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", record_id) + ".jpg"


def eligible(rec: dict) -> bool:
    return (
        rec.get("source") == "rijks"
        and rec.get("rights_class") == "open"
        and bool(rec.get("image_url"))
        and rec.get("attribution_confidence") == "high"
        and "publicdomain/mark" in (rec.get("image_rights_statement") or "")
    )


def sheet(rec: dict) -> dict:
    seen, creators = set(), []
    for c in rec.get("creators", []):
        key = (c["name"], c["role_as_stated"])
        if key not in seen:
            seen.add(key)
            creators.append(
                {
                    "name": c["name"],
                    "role": c["role_as_stated"],
                    "role_ru": ROLES_RU.get(c["role_as_stated"], c["role_as_stated"]),
                }
            )
    return {
        "id": rec["id"],
        "title": rec["title_original"],
        "holder": rec["holder"],
        "accession": rec["accession_id"],
        "record_url": rec["record_url"],
        "image": "img/benoist/" + file_name(rec["id"]),
        "rights": "Public Domain Mark",
        "rights_url": rec["image_rights_statement"],
        "creators": creators,
    }


PM_ROLES_RU = {
    "dessinateur-lithographe": "рисовал и литографировал",
    "dessinateur": "рисовал",
    "lithographe": "литографировал",
    "imprimeur-lithographe": "печатал (литограф)",
    "imprimeur": "печатал",
    "editeur": "издатель",
    "éditeur": "издатель",
}
PM_TITLES = {
    "320290066": "La Sainte-Chapelle",
    "320291197": "Palais du Luxembourg, côté jardin",
    "320294285": "Le Château d'Eau et le marché aux fleurs",
    "320291945": "Notre-Dame",
    "320290399": "Galerie d'Orléans au Palais-Royal",
    "320292157": "Colonne de la place Vendôme",
    "320288755": "Le Louvre achevé et la nouvelle rue de Rivoli",
    "320290954": "Saint-Sulpice et Saint-Étienne-du-Mont",
    "320291211": "Rue de Rivoli, ministères des Finances et de la Marine",
    "320291262": "Bourse et Tribunal de Commerce",
    "320291352": "Colonnade du Louvre",
}


def pm_name(raw: str) -> str:
    """'Benoist, Philippe' -> 'Philippe Benoist'; names without a comma are kept."""
    last, _, first = raw.partition(", ")
    return f"{first} {last}".strip() if first else raw


def roles_ru(roles: list[dict]) -> list[dict]:
    """Roles exactly as the museum's record page states them (French), with a plain Russian rendering beside them."""
    seen, out = set(), []
    for r in roles:
        key = (pm_name(r["name"]), r.get("role"))
        if key in seen or not r.get("role"):
            continue
        seen.add(key)
        out.append({"name": key[0], "role": r["role"], "role_ru": PM_ROLES_RU.get(r["role"], r["role"])})
    return out


def pm_sheets() -> list[dict]:
    if not PM.exists():
        return []
    records = json.loads(PM.read_text(encoding="utf-8"))["records"]
    extra: dict[str, list[dict]] = {}
    for r in records:
        if r.get("impression_of"):
            extra.setdefault(r["impression_of"], []).append(
                {"accession": "node " + r["node"], "record_url": r["record_url"], "image": r["image"]}
            )
    out = []
    for r in records:
        if r.get("impression_of"):
            continue
        names = []
        for a in r["participants"]:
            n = pm_name(a)
            if n not in names:
                names.append(n)
        out.append(
            {
                "id": r["id"],
                "title": PM_TITLES.get(r["node"], r["title"]),
                "title_original": r["title"],
                "holder": "Paris Musées / Musée Carnavalet"
                if "carnavalet" in r.get("holder", "carnavalet").lower()
                else "Paris Musées / " + r["holder"],
                "accession": "node " + r["node"],
                "record_url": r["record_url"],
                "image": r["image"],
                "rights": "CC0 Paris Musées",
                "rights_url": r["rights_url"],
                "technique": r["technique"] if isinstance(r["technique"], str) else ", ".join(r["technique"]),
                "participants": names,
                "extra_impressions": len(extra.get(r["node"], [])),
                "impressions": extra.get(r["node"], []),
                "creators": roles_ru(r.get("roles") or []),
            }
        )
    return out


def build() -> dict:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    sheets = pm_sheets() + [sheet(r) for r in data["records"] if eligible(r)]
    return {
        "version": 1,
        "source": "data/curation/benoist-harvest-v1.json",
        "holders": ["Paris Musées / Musée Carnavalet", "Rijksmuseum"],
        "note": "Роли указаны так, как их называет музей. Это не наша атрибуция.",
        "sheets": sheets,
    }


def fetch(data: dict) -> None:
    harvest = {r["id"]: r for r in json.loads(SRC.read_text(encoding="utf-8"))["records"]}
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    for s in data["sheets"]:
        dest = ROOT / "book" / s["image"]
        if dest.exists():
            continue
        m = re.search(r"micr\.io/([^/]+)/", harvest[s["id"]]["image_url"])
        req = urllib.request.Request(
            f"https://iiif.micr.io/{m.group(1)}/full/900,/0/default.jpg", headers={"User-Agent": UA}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
        time.sleep(1.1)


def main(argv: list[str]) -> int:
    data = build()
    if "--fetch" in argv:
        fetch(data)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(len(data["sheets"]), "sheets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
