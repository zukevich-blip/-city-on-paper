"""Rebuild the order of "Paris dans sa splendeur" (Audiganne, 1861) from the Heidelberg digital library records.

Source: data/research/benoist/bnf-europeana-heidelberg-ia-v1.json (records read from the library; rights statement of the
library: Public Domain Mark). Order: plate number printed in the library's own page title (1..70, contiguous), volume from the
record URL. The artist of a single plate is NOT stated by the library (the title page credits 18 artists, Philippe Benoist
first), so no plate is attributed to Benoist here.
out: book/albums/paris-dans-sa-splendeur.json, book/img/albums/psd/*.jpg
"""
# ruff: noqa: E501, E402
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.world.imgfetch import fetch  # noqa: E402

SRC = ROOT / "data/research/benoist/bnf-europeana-heidelberg-ia-v1.json"
OUT = ROOT / "book/albums/paris-dans-sa-splendeur.json"
IMG = ROOT / "book/img/albums/psd"


def main() -> int:
    recs = [r for r in json.loads(SRC.read_text(encoding="utf-8"))["records"]
            if r.get("rights_status") == "open_confirmed" and r.get("image_url") and "audiganne1861" in (r.get("record_url") or "")]
    pages, volumes = [], []
    for r in recs:
        vol = int(re.search(r"audiganne1861bd(\d)", r["record_url"]).group(1))
        m = re.match(r"Planches? ?(\d+)( bis)?", r["original_title"])
        if m:
            pages.append((int(m.group(1)), vol, r, bool(m.group(2))))
        else:
            volumes.append((vol, r))
    pages.sort(key=lambda t: (t[0], t[3], t[1]))
    vols = sorted(volumes, key=lambda t: t[0])
    jobs = [(f"v{v}-cover", r["image_url"]) for v, r in vols] + [(f"p{n:03d}{'b' if bis else ''}", r["image_url"]) for n, v, r, bis in pages]
    with ThreadPoolExecutor(4) as ex:
        res = dict(zip((j[0] for j in jobs), ex.map(lambda j: fetch(j[1], IMG / f"{j[0]}.jpg"), jobs), strict=True))
    key = lambda n, bis: f"p{n:03d}{'b' if bis else ''}"  # noqa: E731
    plates = [{"n": n, "bis": bis, "volume": v, "title": f"Планша {n}" + (" bis" if bis else ""), "image": f"img/albums/psd/{key(n, bis)}.jpg", "record_url": r["record_url"],
               "rights": "Public Domain Mark (по данным библиотеки)", "rights_url": "https://creativecommons.org/publicdomain/mark/1.0/",
               **{k: res[key(n, bis)][k] for k in ("w", "h")}} for n, v, r, bis in pages if res.get(key(n, bis))]
    covers = [{"volume": v, "image": f"img/albums/psd/v{v}-cover.jpg", "record_url": r["record_url"],
               "title": re.sub(r"\$d.*?:", ":", r["original_title"]).split(":")[0] + ": Paris dans sa splendeur", **{k: res[f"v{v}-cover"][k] for k in ("w", "h")}}
              for v, r in vols if res.get(f"v{v}-cover")]
    doc = {
        "id": "paris-dans-sa-splendeur", "title": "Paris dans sa splendeur", "years": "1861", "publisher": "Henri Charpentier, Nantes et Paris",
        "full_title": "Paris dans sa splendeur: monuments, vues, scènes historiques, descriptions et histoire; dessins et lithographies par MM. Philippe Benoist [und 17 weitere]; texte par MM. Audiganne [und 23 weitere]",
        "holder": "Universitätsbibliothek Heidelberg (digi.ub.uni-heidelberg.de)", "source_url": "https://digi.ub.uni-heidelberg.de/diglit/audiganne1861bd1",
        "order_basis": "Номер планши в названии страницы у библиотеки (1–70 подряд); том из адреса записи. Это порядок самого издания, не кураторская подборка.",
        "coverage": {"plates_here": len(plates), "plates_missing": [n for n in range(1, 71) if n not in {p['n'] for p in plates}], "bis_plates": [p['n'] for p in plates if p['bis']],
                     "note": "Издание больше (в третьем томе и дальше планши в нашей выборке не прочитаны). Здесь только то, что библиотека отдаёт открыто и что мы прочитали."},
        "attribution_note": "На титульном листе назван Philippe Benoist среди 18 художников. Автор каждой отдельной планши библиотекой не указан, поэтому ни одна планша не приписана Бенуа.",
        "covers": covers, "plates": plates,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(len(covers), "covers,", len(plates), "plates, missing", doc["coverage"]["plates_missing"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
