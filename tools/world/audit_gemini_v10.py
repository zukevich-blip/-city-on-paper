"""Audit the Gemini BENOIST INTEGRATION READY v10 data before anything of it reaches the museum.

Reads the v10 files kept in data/research/benoist/gemini-v10/ (research tier, never published) and writes
data/research/benoist/gemini-v10-audit.json. Rules (all deterministic, nothing is guessed):

* the person is taken from the museum/Commons credit text; "Guillaume Philippe Benoist" (18th-century engraver) is
  excluded; other named artists (Cicéri, Bayot, Lalaisse...) and uploader names never become "Benoist";
* a place comes from the file title only; a publisher or a mention in a description never decides it;
* missing coordinates stay null (never [0, 0], never the centre of Paris);
* a licence on a Commons page is a claim until the file page is re-read, so the status says so;
* album pages are counted by distinct image, not by page number.
"""
# ruff: noqa: E501
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/research/benoist/gemini-v10"
OUT = ROOT / "data/research/benoist/gemini-v10-audit.json"

PLACES = [  # title tokens -> (place, country); first match wins, order matters
    (r"\bjersey\b|guernesey", ("Джерси и Гернси", "Нормандские острова")),
    (r"\bparis\b|madeleine|tuileries|louvre|notre-dame|sainte-chapelle|luxembourg|invalides", ("Париж", "Франция")),
    (r"bretagne|elven|quimper|vannes|morbihan|finist", ("Бретань", "Франция")),
    (r"\bnantes\b", ("Нант", "Франция")),
    (r"\brome\b|roma|vaccino|ripetta", ("Рим", "Италия")),
    (r"\bnice\b|savoie", ("Ницца и Савойя", "Франция")),
]
OTHERS = re.compile(r"cic[ée]ri|lalaisse|bayot|villaamil|lacourarie|lacauchie|frond|martinet|bichebois|moreau|argonitros|fab5669|man vyi|rijksmuseum", re.I)


def person(artist_raw: str | None, title: str) -> tuple[str | None, str]:
    """-> (artist or None, basis). Only the credit text and the file title count."""
    raw = f"{artist_raw or ''} | {title}"
    if re.search(r"guillaume[\s-]+philippe", raw, re.I):
        return None, "excluded_other_person_guillaume_philippe_benoist"
    p = re.search(r"philippe\s+benoist|benoist,\s*philippe|ph\.\s*benoist", raw, re.I)
    f = re.search(r"f[ée]lix\s+benoist|benoist,\s*f[ée]lix|\bf\.\s*benoist", raw, re.I)
    if p and f:
        return None, "both_named_roles_unknown"
    if p:
        return "Philippe Benoist", "named_in_credit_or_title"
    if f:
        return "Félix Benoist", "named_in_credit_or_title"
    if OTHERS.search(artist_raw or ""):
        return None, "credit_names_other_people_not_benoist"
    return None, "no_benoist_in_credit"


def place(title: str) -> tuple[str | None, str | None]:
    for rx, val in PLACES:
        if re.search(rx, title, re.I):
            return val
    return None, None


def coords(c) -> list | None:
    """null, [null, null], [0, 0] and the centre-of-Paris default are 'unknown', never a place."""
    if not isinstance(c, (list, tuple)) or len(c) != 2 or any(v is None for v in c):
        return None
    if tuple(c) in {(0, 0), (0.0, 0.0), (2.3499, 48.853)}:
        return None
    return [float(c[0]), float(c[1])]


def main() -> int:
    commons = json.loads((SRC / "benoist-commons-harvest-v10.json").read_text(encoding="utf-8"))["records"]
    legacy = json.loads((SRC / "benoist-legacy-v9.json").read_text(encoding="utf-8"))
    out, stats = [], Counter()
    for r in commons:
        title = r["titleClean"]
        who, basis = person(r.get("artistRaw"), title)
        city, country = place(title)
        lic = r.get("license") or ""
        out.append({
            "id": f"commons-{r['commonsPageId']}", "title": title, "record_url": r["recordUrl"], "image_url": r["originalUrl"],
            "artist": who, "artist_basis": basis, "artist_as_claimed_by_harvest": r["artist"], "credit_text": r.get("artistRaw"),
            "city": city, "country": country, "coords": None,
            "licence_claim": lic, "licence_status": "claimed_on_commons_page_not_rechecked",
            "share_alike": "BY-SA" in lic, "year": r.get("year"), "title_page_or_cover": bool(r.get("isTitlePageOrCover")),
        })
        stats[basis] += 1
    pages = [pg for al in legacy["restoredAlbums"]["albums"] for pg in al["pages"]]
    unique_images = {pg["imageUrl"].split("?")[0] for pg in pages if pg.get("imageUrl")}
    jersey = [pg for al in legacy["restoredAlbums"]["albums"] if al["id"] == "album-ile-de-jersey" for pg in al["pages"]]
    summary = {
        "commons_records": len(out), "by_artist_basis": dict(stats),
        "harvest_artist_changed": sum(1 for o in out if o["artist"] != o["artist_as_claimed_by_harvest"]),
        "album_pages": len(pages), "album_pages_unique_images": len(unique_images),
        "jersey_pages": len(jersey), "jersey_pages_linked_to_paris_by_harvest": sum(1 for pg in jersey if pg.get("cityRu") == "Париж"),
        "jersey_after_audit_in_paris": sum(1 for o in out if "jersey" in o["title"].lower() and o["city"] == "Париж"),
        "page_coords_invented_default": sum(1 for pg in pages if coords(pg.get("coords")) is None and pg.get("coords")),
        "share_alike_records": sum(1 for o in out if o["share_alike"]),
        "benoist_confirmed_records": sum(1 for o in out if o["artist"]),
    }
    OUT.write_text(json.dumps({"version": 1, "source": "gemini-v10", "summary": summary, "records": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
