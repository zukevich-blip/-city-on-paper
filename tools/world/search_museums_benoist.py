#!/usr/bin/env python3
"""Search museum/library catalogues for works by Philippe Benoist and, separately, Felix Benoist.

Output (schema: data/research/benoist/SCHEMA.md): data/research/benoist/museums-v1.json

Stdlib only, re-runnable, polite (>= 1.2 s between calls to a host, >= 3 s and long pauses for loc.gov,
stop a host after repeated 429/403/challenge and record it in ``coverage.blocked``). No image bytes are
downloaded: only record JSON, CSV open data and IIIF ``info.json`` (for real pixel sizes of open images).

Sources (each runner reports queries / pages walked / hits reported by the source / records kept / blocked):
  loc (item ids + name authority), nga (open data CSV), met, morgan (probe), rijks, getty (ULAN authority only),
  vam, british_museum (probe), aic, cleveland, yale_lux (probe), brown, harvard (probe), nypl (probe),
  bne (probe) + europeana (aggregator, also carries BnF/BNE/Gallica providers), hertziana (probe),
  antiquarian (leads only, never an image source).

Rules: Philippe Benoist (1813-ca.1905) and Felix Benoist (1818-1896) are different people; Guillaume-Philippe
Benoist, Antoine Benoist, J.-L. Benoist, Marie-Guillemine Benoist etc. are excluded and counted. Unknown = null.
``open_confirmed`` only for an explicit CC0 / PDM / CC BY(-SA) statement on the image; archival "no known
restrictions" / "no copyright" advisories are ``rights_pending`` (never CC0).

Usage:  python -m tools.world.search_museums_benoist [--only nga,met] [--skip loc] [--loc-pause 45] [--cache DIR]
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "research" / "benoist" / "museums-v1.json"
HARVEST = ROOT / "data" / "curation" / "benoist-harvest-v1.json"
SHEETS = ROOT / "book" / "benoist-sheets.json"
UA = "CityOnPaperResearch/0.9 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)"
DEFAULT_GAP = 1.2
MIN_GAP = {"www.loc.gov": 3.2}
MAX_429 = 3
LOC_PAUSES = (30, 60)  # seconds slept between retries of a 429 from loc.gov

# --------------------------------------------------------------------------------------------------
# Pure helpers (unit-tested, no network)
# --------------------------------------------------------------------------------------------------


def fold(text: str | None) -> str:
    """Lower-case, accent-free, single-spaced."""
    t = unicodedata.normalize("NFKD", text or "")
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return " ".join(t.lower().split())


def classify_artist(name: str | None, bio: str | None = None) -> tuple[str | None, str]:
    """-> (artist_id | None, note). None = text names no Benoist at all."""
    raw = f"{name or ''} {bio or ''}"
    t = fold(raw)
    if "benoist" not in t:
        return None, ""
    n = fold(name)
    if re.search(r"guillaume[\s-]*philippe", t) or re.search(r"\b17(2\d|30)\b", fold(bio)) and "philippe" in n:
        return "other", "Guillaume-Philippe Benoist (1725-1800) or other non-1813 Philippe"
    if re.search(r"benoist[\s,-]*m[eé]chin|marie[\s-]*guillemine", t):
        return "other", "different Benoist"
    m = re.search(r"benoist,\s*([a-z][a-z.\- ]*?)(?:\s*[,(\[]|\s+\d|$)", n) or re.search(
        r"([a-z][a-z.\-]*(?:\s+[a-z][a-z.\-]*)?)\s+benoist\b", n)
    fore = (m.group(1).strip() if m else "").replace("[", "").replace("]", "")
    last = fore.split()[-1] if fore else ""
    felix = last.startswith("felix") or bool(re.search(r"\bfelix\b", n))
    phil = last in ("philippe", "ph", "ph.") or bool(re.search(r"\bphilippe\b", n))
    if felix and phil:
        return "uncertain-benoist", "both Felix and Philippe named in one string"
    if felix:
        return "felix-benoist", ""
    if phil:
        return "philippe-benoist", ""
    if re.search(r"\b1818\b", t) or re.search(r"\b189[68]\b", t):
        return "felix-benoist", "assigned by dates 1818-1896 only"
    if re.search(r"\b1813\b|\b1905\b", t):
        return "philippe-benoist", "assigned by dates 1813-1905 only"
    forename_like = r"\bbenoist\s+(?!del\b|lith|imp\b|dess|and\b|et\b|after|pinx|fecit|sc\b|ph\b)[a-z]{4,}"
    if re.search(forename_like, n) and "," not in n:
        return "other", "Benoist is a forename here (e.g. 'Benoist Boullay')"
    if last and re.fullmatch(r"[a-z]\.?", last):
        return "uncertain-benoist", f"initial {last!r} only; Felix and Philippe both possible"
    if last and last not in ("by", "par", "de", "von", "van", "after", "d'apres", "mr", "m."):
        return "other", f"forename {fore!r} is not Philippe or Felix"
    return "uncertain-benoist", "surname Benoist without forename"


def pick_artist_id(ids: list[str]) -> tuple[str | None, str]:
    s = {i for i in ids if i and i != "other"}
    if not s:
        return None, ""
    if s == {"philippe-benoist"}:
        return "philippe-benoist", ""
    if s == {"felix-benoist"}:
        return "felix-benoist", ""
    if s == {"uncertain-benoist"}:
        return "uncertain-benoist", ""
    if "philippe-benoist" in s and "felix-benoist" in s:
        return "uncertain-benoist", "both Philippe and Felix are named on this record"
    return ("philippe-benoist" if "philippe-benoist" in s else "felix-benoist"), "also an uncertain Benoist on record"


def normalize_role(role: str | None, note: str | None = None) -> str:
    r = fold(role)
    n = fold(note)
    if re.search(r"lithograph|lith\.|lithographe", r):
        return "lithographer"
    if re.search(r"engrav|grave|graveur|etcher|aquafort", r):
        return "engraver"
    if re.search(r"print(er|ed)|imprim|imp\.|drukker|druck", r):
        return "printer"
    if re.search(r"publish|editeur|uitgever|verlag|diteur", r):
        return "publisher"
    if re.search(r"auteur du texte|author|writer|autor", r):
        return "author_of_text"
    if re.search(r"designer|draughts|draftsm|drawer|dessinateur|dessin|draw|del\.|delin|zeichner|tekenaar|after", r):
        return "designer"
    if n == "after":
        return "designer"
    return "unspecified"


SERIES = (
    "Paris dans sa splendeur", "Promenade dans Paris et ses environs", "Vues de Paris", "Rome dans sa grandeur",
    "Espana artistica y monumental", "Nice et Savoie", "Paris et ses environs", "Voyage pittoresque",
    "La Normandie", "La Bretagne contemporaine", "Souvenirs de Paris",
)


_NOT_SERIES_PREFIX = ("nouvelles", "nouvelle", "anciennes", "grandes", "petites", "autres")


def detect_series(*texts: str | None) -> str | None:
    """Known series name found in the text as a whole phrase (not as the tail of e.g. 'Nouvelles Vues de Paris')."""
    blob = fold(" ".join(t for t in texts if t))
    for name in SERIES:
        for m in re.finditer(re.escape(fold(name)), blob):
            prev = blob[:m.start()].split()
            if prev and prev[-1] in _NOT_SERIES_PREFIX:
                continue
            return name
    return None


def dup_hint(title: str | None, series: str | None, plate: str | None) -> str | None:
    if not title:
        return None
    t = fold(re.split(r"\s/\s", title)[0])
    t = re.sub(r"\[[^\]]*\]", " ", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = " ".join(t.split())
    return "|".join([t, fold(series) if series else "", str(plate or "")])


def norm_url(u: str | None) -> str:
    if not u:
        return ""
    u = re.sub(r"^https?://", "", u.strip().lower())
    return re.sub(r"^www\.", "", u).rstrip("/")


_OPEN_URL = re.compile(
    r"publicdomain/(zero|mark)|creativecommons\.org/licenses/by(-sa)?/|\bcc0\b|\bcc[- ]by(-sa)?\b|public domain mark|"
    r"^public domain$", re.I)
_NOT_OPEN = re.compile(r"noc-oklr|inc/1\.0|-nc|nc-nd|nc-sa|noncommercial|all rights reserved|in copyright|©", re.I)
_ADVISORY = re.compile(r"no known (copyright )?restrictions|noc-us|no copyright|noc-oklr|noc-nc|no known", re.I)


def rights_status_for(statement: str | None, file_level: bool = True) -> str:
    """open_confirmed | rights_pending | link_only | unknown (statement verbatim in, status out)."""
    s = (statement or "").strip()
    if not s:
        return "unknown"
    if _NOT_OPEN.search(s):
        return "link_only"
    if _ADVISORY.search(s):
        return "rights_pending"  # advisory, NOT a CC0/PDM licence
    if file_level and _OPEN_URL.search(s):
        return "open_confirmed"
    return "rights_pending"


def part(name, role_as_stated=None, note=None):
    return {"name": name, "role_as_stated": role_as_stated, "role_normalized": normalize_role(role_as_stated, note)}


def make_record(**kw) -> dict:
    """Full SCHEMA record; every missing value is None, never a guess."""
    names = [p["name"] for p in kw.get("participants") or []]
    ids, notes = [], []
    for p in kw.get("participants") or []:
        a, nt = classify_artist(p["name"], p.get("_bio"))
        p.pop("_bio", None)
        if a:
            ids.append(a)
            if nt:
                notes.append(f"{p['name']}: {nt}")
    artist, extra = pick_artist_id(ids)
    named = sorted({i for i in ids if i and i != "other"})
    if extra:
        notes.append(extra)
    series = kw.get("series") or detect_series(kw.get("original_title"), kw.get("series_text"))
    status = kw.get("rights_status") or "unknown"
    img = kw.get("image_url") if status == "open_confirmed" else None
    rec = {
        "record_id": kw["record_id"],
        "artist_id": artist,
        "artist_ids_named": named,
        "participants": kw.get("participants") or [],
        "original_title": kw.get("original_title"),
        "translated_title_ru": None,
        "series": series,
        "plate_number": kw.get("plate_number"),
        "volume": kw.get("volume"),
        "city": kw.get("city"),
        "place": kw.get("place"),
        "country": kw.get("country"),
        "geo_confidence": kw.get("geo_confidence") or "unknown",
        "date_as_stated": kw.get("date_as_stated"),
        "technique_as_stated": kw.get("technique_as_stated"),
        "object_type": kw.get("object_type"),
        "institution": kw.get("institution"),
        "accession": kw.get("accession"),
        "record_url": kw.get("record_url"),
        "iiif_manifest": kw.get("iiif_manifest"),
        "image_url": img,
        "image_width": kw.get("image_width") if img else None,
        "image_height": kw.get("image_height") if img else None,
        "rights_statement": kw.get("rights_statement"),
        "rights_status": status,
        "duplicate_hint": dup_hint(kw.get("original_title"), series, kw.get("plate_number")),
        "impression_note": kw.get("impression_note"),
        "verification_status": kw.get("verification_status") or "source_record_read",
        "attribution_confidence": kw.get("attribution_confidence")
        or ("low" if artist == "uncertain-benoist" else "high"),
        "attribution_note": "; ".join(dict.fromkeys(n for n in notes if n)) or kw.get("attribution_note"),
        "source_type": kw.get("source_type") or "museum",
        "other_benoist_names_on_record": [n for n in names if classify_artist(n)[0] == "other"] or None,
    }
    if artist == "uncertain-benoist" and rec["attribution_confidence"] == "high":
        both = len(named) == 2
        explicit = all(p["role_normalized"] != "unspecified" for p in rec["participants"] if classify_artist(
            p["name"])[0] in ("philippe-benoist", "felix-benoist"))
        rec["attribution_confidence"] = "high" if (both and explicit) else ("medium" if both else "low")
    return rec


# ---- per-source parsers (each returns a record dict, or None when no Philippe/Felix/uncertain Benoist) ----

def _kept(rec_participants: list[dict]) -> bool:
    ids = [classify_artist(p["name"], p.get("_bio"))[0] for p in rec_participants]
    return any(i and i != "other" for i in ids)


def parse_met_object(o: dict) -> dict | None:
    if not o or not o.get("objectID"):
        return None
    dn = [x.strip() for x in (o.get("artistDisplayName") or "").split("|")]
    db = [x.strip() for x in (o.get("artistDisplayBio") or "").split("|")]
    bios = {n: (db[i] if i < len(db) else None) for i, n in enumerate(dn) if n}
    parts = [{**part(c.get("name"), c.get("role")), "_bio": bios.get(c.get("name"))}
             for c in o.get("constituents") or []]
    for n in dn:
        if n and not any(p["name"] == n for p in parts):
            parts.append({**part(n, o.get("artistRole") or None), "_bio": bios.get(n)})
    if not _kept(parts):
        return None
    pd = bool(o.get("isPublicDomain"))
    stmt = "Met Open Access: isPublicDomain=true (CC0)" if pd else None
    img = o.get("primaryImage") or None
    return make_record(
        record_id=f"met:{o['objectID']}", participants=parts, original_title=o.get("title"),
        date_as_stated=o.get("objectDate") or None, technique_as_stated=o.get("medium") or None,
        object_type="print" if "print" in fold(o.get("classification") or o.get("objectName")) else "drawing"
        if "drawing" in fold(o.get("classification") or o.get("objectName")) else None,
        institution="The Metropolitan Museum of Art", accession=o.get("accessionNumber"),
        record_url=o.get("objectURL"), image_url=img, rights_statement=stmt,
        rights_status="open_confirmed" if (pd and img) else ("unknown" if not pd else "rights_pending"),
        country=None, series_text=o.get("title"),
        impression_note=o.get("creditLine"),
    )


def parse_vam_record(rec: dict) -> dict | None:
    parts = []
    for m in rec.get("artistMakerPerson") or []:
        nm = (m.get("name") or {}).get("text")
        parts.append({**part(nm, (m.get("association") or {}).get("text"), m.get("note")),
                      "role_as_stated": ((m.get("association") or {}).get("text") or "") +
                                        (f" ({m['note']})" if m.get("note") else "") or None, "_bio": None})
    for m in rec.get("artistMakerOrganisations") or []:
        parts.append(part((m.get("name") or {}).get("text"), (m.get("association") or {}).get("text"), m.get("note")))
    if not _kept(parts):
        return None
    sn = rec.get("systemNumber")
    titles = [t.get("title") for t in rec.get("titles") or [] if t.get("title")]
    phys = rec.get("physicalDescription") or ""
    brief = rec.get("briefDescription") or ""
    places = [p.get("place", {}).get("text") for p in rec.get("placesOfOrigin") or []]
    dates = [d.get("date", {}).get("text") for d in rec.get("productionDates") or []]
    return make_record(
        record_id=f"vam:{sn}", participants=parts, original_title=titles[0] if titles else None,
        date_as_stated=dates[0] if dates else None, technique_as_stated=phys or None,
        object_type={"print": "print", "drawing": "drawing", "book": "book"}.get(fold(rec.get("objectType"))),
        institution="Victoria and Albert Museum", accession=rec.get("accessionNumber"),
        record_url=f"https://collections.vam.ac.uk/item/{sn}/", country=places[0] if places else None,
        rights_statement=None, rights_status="unknown", series_text=f"{phys} {brief}",
        impression_note=brief or None,
        verification_status="source_record_read",
    )


def _la_notation(types: list[dict] | None) -> str | None:
    for t in types or []:
        for n in t.get("notation") or []:
            if isinstance(n, dict) and n.get("@language") == "en":
                return n.get("@value")
    return None


def _dicts(seq) -> list[dict]:
    return [x for x in seq or [] if isinstance(x, dict)]


def parse_rijks_object(obj: dict, people: dict[str, str]) -> dict | None:
    prod = obj.get("produced_by") or {}
    parts = []
    for p in _dicts(prod.get("part")) or [prod]:
        role = _la_notation(_dicts(p.get("technique")))
        stated = next((r.get("content") for r in _dicts(p.get("referred_to_by"))
                       if r.get("content") and "(mentioned on object)" in r["content"]), None)
        for a in _dicts(p.get("assigned_by")):
            for who in _dicts(a.get("assigned")):
                nm = people.get(who.get("id"), "")
                if nm:
                    parts.append({**part(nm, role), "role_as_stated": stated or role, "_bio": None})
    if not _kept(parts):
        return None
    acc = title = None
    titles = []
    for i in _dicts(obj.get("identified_by")):
        cls = [_la_notation([c]) for c in _dicts(i.get("classified_as"))]
        if i.get("type") == "Identifier" and "object number" in cls:
            acc = i.get("content")
        if i.get("type") == "Name":
            titles.append((("title on object" in cls), i.get("content")))
    on_obj = [t for flag, t in titles if flag]
    title = on_obj[0] if on_obj else (titles[0][1] if titles else None)
    html = iiif = lic = None
    for s in _dicts(obj.get("subject_of")):
        for d in _dicts(s.get("digitally_carried_by")):
            ap = (_dicts(d.get("access_point")) or [{}])[0].get("id")
            if d.get("format") == "text/html":
                html = html or ap
            elif ap and "iiif" in ap:
                iiif = ap
                lic = next((r.get("content") for r in _dicts(d.get("referred_to_by")) if r.get("content")), None)
    ts = (prod.get("timespan") or {})
    date = next((i.get("content") for i in _dicts(ts.get("identified_by")) if i.get("content")), None)
    status = rights_status_for(lic) if iiif else "unknown"
    base = re.sub(r"/full/.*$", "", iiif) if iiif else None
    rec = make_record(
        record_id=f"rijks:{acc}", participants=parts, original_title=title, date_as_stated=date,
        object_type="print" if any(fold(_la_notation([c])) == "print"
                                   for c in _dicts(obj.get("classified_as"))) else None,
        institution="Rijksmuseum", accession=acc, record_url=html or obj.get("id"),
        iiif_manifest=None, image_url=iiif, rights_statement=lic, rights_status=status,
        technique_as_stated=None,
    )
    rec["_iiif_base"] = base
    return rec


def parse_nga_row(obj: dict, role_rows: list[dict], names: dict[str, str], image: dict | None,
                  constituents: list[dict] | None = None) -> dict | None:
    parts = []
    for r in constituents or role_rows:
        nm = names.get(r["constituentid"], r["constituentid"])
        parts.append({**part(nm, r.get("role") or None), "_bio": None})
    if not _kept(parts):
        return None
    open_img = bool(image and image.get("openaccess") == "1")
    w = int(image["width"]) if open_img and (image.get("width") or "").isdigit() else None
    h = int(image["height"]) if open_img and (image.get("height") or "").isdigit() else None
    stmt = "NGA Open Data: published image flagged openaccess=1 (NGA Open Access, CC0)" if open_img else None
    oid = obj["objectid"]
    rec = make_record(
        record_id=f"nga:{oid}", participants=parts, original_title=obj.get("title"),
        date_as_stated=obj.get("displaydate") or None, technique_as_stated=obj.get("medium") or None,
        object_type={"print": "print", "drawing": "drawing", "album": "album", "volume": "volume",
                     "book": "book"}.get(fold(obj.get("classification"))),
        institution="National Gallery of Art, Washington", accession=obj.get("accessionnum"),
        record_url=f"https://www.nga.gov/artworks/{oid}",
        iiif_manifest=None,
        image_url=(image["iiifurl"] + "/full/full/0/default.jpg") if open_img else None,
        image_width=w, image_height=h, rights_statement=stmt,
        rights_status="open_confirmed" if open_img else "unknown",
        volume=obj.get("series") or obj.get("volume") or None,
        series_text=f"{obj.get('portfolio') or ''}",
        impression_note=obj.get("creditline") or None,
    )
    return rec


_BROWN_ROLE = re.compile(r"^(.*?),?\s*(?:\d{4}\??-[^()]*)?\((.+)\)\s*$")


def parse_brown_item(d: dict) -> dict | None:
    parts = []
    for line in d.get("contributor_display") or []:
        m = re.match(r"^(.*?)\s*\(([^()]+)\)\s*$", line)
        nm, role = (m.group(1), m.group(2)) if m else (line, None)
        parts.append({**part(nm, role), "_bio": None})
    if not _kept(parts):
        return None
    links = d.get("links") or {}
    views = links.get("views") or {}
    pk = d.get("pid")
    rights = "; ".join(d.get("mods_access_condition_rights_text_tsim") or []) or None
    rlink = (d.get("mods_access_condition_rights_link_ssim") or [None])[0]
    stmt = f"{rights} ({rlink})" if rights and rlink else rights
    title = d.get("primary_title")
    other = (d.get("other_title") or [None])[0]
    pn = (d.get("mods_related_title_partnumber_ssim") or [None])[0]
    plate = re.sub(r"^no\.?\s*", "", pn, flags=re.I) if pn else None
    prov = d.get("mods_note_provenance_ssim")
    return make_record(
        record_id=f"brown:{pk}", participants=parts, original_title=title, series=detect_series(other) or other,
        plate_number=plate, date_as_stated=(d.get("mods_dateIssued_ssim") or [None])[0],
        technique_as_stated=(d.get("mods_physicalDescription_extent_ssim") or [None])[0],
        object_type="print" if "lithograph" in fold(" ".join(d.get("genre") or [])) or "engraving" in fold(
            " ".join(d.get("genre") or [])) else None,
        institution="Brown University Library (" + "; ".join(d.get("ir_collection_name") or [])[:120] + ")",
        accession=(d.get("mods_id_local_ssim") or [pk])[0],
        record_url=f"https://repository.library.brown.edu/studio/item/{pk}/",
        iiif_manifest=views.get("iiif_manifest"), city=(d.get("publication_place") or [None])[0],
        rights_statement=stmt, rights_status=rights_status_for(stmt, file_level=False) if stmt else "unknown",
        place=(d.get("subject") or [None])[0], impression_note="; ".join(prov) if prov else None,
        series_text=" ".join(d.get("abstract") or []),
    )


def parse_cleveland_row(r: dict) -> dict | None:
    parts = [{**part(c.get("description"), c.get("role")), "_bio": None} for c in r.get("creators") or []]
    if not _kept(parts):
        return None
    cc0 = (r.get("share_license_status") or "").upper() == "CC0"
    web = ((r.get("images") or {}).get("web") or {})
    return make_record(
        record_id=f"cleveland:{r.get('accession_number')}", participants=parts, original_title=r.get("title"),
        date_as_stated=r.get("creation_date"), technique_as_stated=r.get("technique"),
        object_type="print" if "print" in fold(r.get("type")) else None, institution="The Cleveland Museum of Art",
        accession=r.get("accession_number"), record_url=r.get("url"), image_url=web.get("url") if cc0 else None,
        image_width=web.get("width") if cc0 else None, image_height=web.get("height") if cc0 else None,
        rights_statement="CC0" if cc0 else (r.get("share_license_status") or None),
        rights_status="open_confirmed" if (cc0 and web.get("url")) else "unknown",
    )


def parse_aic_row(r: dict) -> dict | None:
    disp = r.get("artist_display") or ""
    parts = [{**part(ln, None), "_bio": ln} for ln in disp.split("\n") if "benoist" in fold(ln)]
    if not _kept(parts):
        return None
    pd = bool(r.get("is_public_domain")) and bool(r.get("image_id"))
    th = r.get("thumbnail") or {}
    return make_record(
        record_id=f"aic:{r.get('id')}", participants=parts, original_title=r.get("title"),
        date_as_stated=r.get("date_display"), technique_as_stated=r.get("medium_display"),
        institution="Art Institute of Chicago", accession=r.get("main_reference_number"),
        record_url=f"https://www.artic.edu/artworks/{r.get('id')}",
        image_url=f"https://www.artic.edu/iiif/2/{r['image_id']}/full/full/0/default.jpg" if pd else None,
        image_width=th.get("width") if pd else None, image_height=th.get("height") if pd else None,
        rights_statement="AIC API: is_public_domain=true (CC0)" if pd else None,
        rights_status="open_confirmed" if pd else "unknown",
    )


def parse_brown_hits(payload: dict) -> list[str]:
    return [d["pid"] for d in (payload.get("response") or {}).get("docs", []) if d.get("pid")]


_FREE_MENTION = re.compile(r"(?:f[eé]lix|philippe|ph\.|f\.)\s*benoist|benoist,\s*(?:f[eé]lix|philippe)", re.I)
_TITLE_ROLES = re.compile(r"lithograph(?:ed)?\s+by\s+(?P<lith>.+?)(?:\s+after\s+(?P<after>.+?))?\.?\s*$", re.I)


def _title_role(title: str, mention: str) -> str | None:
    """'Lithograph by A and Ph. Benoist after F. Benoist' -> role of ``mention`` inside that sentence."""
    m = _TITLE_ROLES.search(title or "")
    if not m:
        return None
    if m.group("after") and mention.lower() in m.group("after").lower():
        return "after (designer)"
    if mention.lower() in m.group("lith").lower():
        return "lithograph by (lithographer)"
    return None


def parse_europeana_item(item: dict) -> dict | None:
    creators = (item.get("dcCreator") or []) + (item.get("dcContributor") or [])
    title = (item.get("title") or [""])[0]
    desc = " ".join(item.get("dcDescription") or [])
    parts, seen = [], set()
    for ctext in creators:
        if ctext in seen or "benoist" not in fold(ctext):
            continue
        seen.add(ctext)
        m = re.match(r"^(.*?\))\.\s*(.+)$", ctext)
        nm, role = (m.group(1), m.group(2)) if m else (ctext, None)
        p = {**part(nm, role), "_bio": None}
        if not any(x["name"] == nm and x["role_normalized"] == p["role_normalized"] for x in parts):
            parts.append(p)
    structured = bool(parts)
    named = {classify_artist(x["name"])[0] for x in parts}
    for text in (title, desc):  # names that only appear in the free-text title/description
        for mm in _FREE_MENTION.finditer(text or ""):
            mention = mm.group(0)
            cid = classify_artist(mention)[0]
            if cid == "uncertain-benoist" and "felix-benoist" in named:
                continue  # initial 'F.' after a Felix creator field: same person per the record itself
            if cid in named or cid in (None, "other") or any(
                    fold(mention) in fold(x["name"]) for x in parts):
                continue
            role = _title_role(title, mention) if text is title else None
            parts.append({"name": mention, "role_as_stated": role or f"free text: {text[:100]}",
                          "role_normalized": normalize_role(role), "_bio": None})
            named.add(cid)
    if not _kept(parts):
        return None
    rights = (item.get("rights") or [None])[0]
    eid = item.get("id")
    is_drawing = bool(re.search(r"\[?dessin\]?", title, re.I))
    place = None
    v = item.get("edmPlaceLabelLangAware") or {}
    if v:
        place = next(iter(v.values()))[0]
    return make_record(
        record_id=f"europeana:{eid}", participants=parts, original_title=title or None,
        date_as_stated=(item.get("year") or [None])[0],
        object_type="drawing" if is_drawing else ("book" if item.get("type") == "TEXT" else "print"),
        institution=(item.get("dataProvider") or [None])[0], accession=eid,
        record_url=(item.get("edmIsShownAt") or [None])[0], image_url=(item.get("edmIsShownBy") or [None])[0],
        rights_statement=rights, rights_status=rights_status_for(rights), place=place, series_text=desc,
        verification_status="search_hit_only",
        attribution_confidence="high" if structured else "low",
        attribution_note=None if structured else "Benoist named only in a free-text title/description field",
        impression_note="Europeana aggregated metadata; holder record page not opened in this run",
    )


_LOC_ROLE = re.compile(r"^(.*?),\s*(artist|lithographer|printer|publisher|engraver|draftsman|designer|etcher|"
                       r"printmaker|creator)\s*$", re.I)


def parse_loc_item(payload: dict) -> dict | None:
    """loc.gov item JSON: new API (``item`` > nested ``item``) or the older pictures API (flat ``item``)."""
    outer = payload.get("item") or {}
    inner = outer.get("item") if isinstance(outer.get("item"), dict) else {}
    it = {**outer, **inner}
    parts = []
    for n in it.get("related_names") or []:
        if isinstance(n, dict):
            parts.append({**part(n.get("title"), n.get("role")), "_bio": n.get("title")})
    for n in it.get("contributor_names") or []:
        m = _LOC_ROLE.match(n.strip())
        nm, role = (m.group(1), m.group(2)) if m else (n.strip(), None)
        if not any(p["name"] == nm for p in parts):
            parts.append({**part(nm, role), "_bio": nm})
    stmt = it.get("stmt_of_responsibility") or ""
    if not _kept(parts) and "benoist" in fold(stmt):
        parts.append({**part(stmt, None), "_bio": None})
    if not _kept(parts):
        return None
    for seg in [x.strip() for x in stmt.split(";") if x.strip()]:  # sheet's own wording gives the roles
        role = normalize_role(seg)
        if "benoist" in fold(seg):
            for p in parts:
                if classify_artist(p["name"])[0] not in (None, "other") and role != "unspecified":
                    p["role_as_stated"] = f"{p['role_as_stated'] or 'named'} / sheet reads: {seg}"
                    p["role_normalized"] = role
        elif role != "unspecified":
            parts.append({"name": seg, "role_as_stated": seg, "role_normalized": role})
    link = outer.get("id") or it.get("link") or ""
    if link.startswith("http://"):
        link = "https://" + link[len("http://"):]
    pk = it.get("control_number") or link.rstrip("/").split("/")[-1]
    if not link and pk:
        link = f"https://www.loc.gov/item/{pk}/"
    rights = it.get("rights_information") or it.get("rights_advisory")
    mediums = " ".join((m.get("medium", "") if isinstance(m, dict) else str(m)) for m in it.get("mediums") or [])
    if not mediums and isinstance(it.get("medium"), list):
        mediums = " ".join(it["medium"])
    return make_record(
        record_id=f"loc:{pk}", participants=parts, original_title=it.get("title"),
        date_as_stated=it.get("created_published_date") or it.get("date"), technique_as_stated=mediums or None,
        object_type="print", institution="Library of Congress, Prints & Photographs Division",
        accession=it.get("reproduction_number") or it.get("call_number") or pk, record_url=link or None,
        rights_statement=rights, rights_status=rights_status_for(rights, file_level=False) if rights else "unknown",
        series_text=f"{stmt} {it.get('call_number') or ''}", impression_note=stmt or None,
        attribution_note="loc.gov 'no known restrictions' is an advisory, not CC0" if rights else None,
    )


def parse_ulan(payload: dict) -> list[dict]:
    out = []
    for b in (payload.get("results") or {}).get("bindings", []):
        out.append({"ulan_uri": b["s"]["value"], "label": b["l"]["value"],
                    "artist_id": classify_artist(b["l"]["value"])[0]})
    return out


def parse_met_search(payload: dict) -> tuple[int, list[int]]:
    return int(payload.get("total") or 0), list(payload.get("objectIDs") or [])


def parse_vam_search(payload: dict) -> tuple[int, int, list[str]]:
    info = payload.get("info") or {}
    return int(info.get("record_count") or 0), int(info.get("pages") or 1), [
        r["systemNumber"] for r in payload.get("records") or []]


def looks_blocked(status: int | None, headers: dict, body: bytes | str) -> str | None:
    """Detect a bot-wall (Cloudflare/AWS WAF challenge) in a non-JSON reply."""
    b = body if isinstance(body, str) else body[:4000].decode("utf-8", "replace")
    h = {k.lower(): str(v) for k, v in (headers or {}).items()}
    if h.get("cf-mitigated") == "challenge" or "Just a moment" in b or "Attention Required" in b:
        return f"HTTP {status} Cloudflare challenge (not bypassed)"
    if h.get("x-amzn-waf-action") == "challenge":
        return f"HTTP {status} AWS WAF challenge (not bypassed)"
    return None


# --------------------------------------------------------------------------------------------------
# Known cross-check
# --------------------------------------------------------------------------------------------------


def build_known(root: Path = ROOT) -> dict:
    urls, accs, hints, ids = {}, {}, set(), {}

    def add(src, url, acc, inst, title, rid=None):
        if url:
            urls.setdefault(norm_url(url), src)
        if acc and inst:
            accs.setdefault((fold(inst)[:12], fold(str(acc))), src)
        if rid:
            ids.setdefault(rid, src)
        h = dup_hint(title, detect_series(title), None)
        if h:
            hints.add(h)

    try:
        for r in json.loads((root / "data/curation/benoist-harvest-v1.json").read_text("utf-8")).get("records", []):
            add("benoist-harvest-v1", r.get("record_url"), r.get("accession_id"), r.get("holder"),
                r.get("title_original"), r.get("id"))
    except (OSError, ValueError):
        pass
    try:
        for r in json.loads((root / "book/benoist-sheets.json").read_text("utf-8")).get("sheets", []):
            add("book/benoist-sheets", r.get("record_url"), r.get("accession"), r.get("holder"),
                r.get("title_original") or r.get("title"), r.get("id"))
    except (OSError, ValueError):
        pass
    return {"urls": urls, "accs": accs, "hints": hints, "ids": ids}


def mark_known(rec: dict, known: dict) -> None:
    src = known["urls"].get(norm_url(rec.get("record_url")))
    how = "record_url" if src else None
    if not src and rec.get("accession"):
        src = known["accs"].get((fold(rec.get("institution"))[:12], fold(str(rec["accession"]))))
        how = "institution+accession" if src else None
    if not src:
        rid = rec["record_id"].split(":", 1)[-1]
        for k, v in known["ids"].items():
            if k and k.endswith(rid) and rec["record_id"].split(":")[0] in fold(k):
                src, how = v, "source id"
                break
    rec["known"] = bool(src)
    rec["known_in"] = src
    rec["known_match"] = how


# --------------------------------------------------------------------------------------------------
# Polite HTTP client
# --------------------------------------------------------------------------------------------------


class Blocked(RuntimeError):
    pass


class Client:
    def __init__(self, loc_pauses=LOC_PAUSES, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir  # development aid: replay JSON replies instead of re-fetching
        self.last: dict[str, float] = {}
        self.n429: dict[str, int] = {}
        self.dead: dict[str, str] = {}
        self.calls: dict[str, int] = {}
        self.loc_pauses = loc_pauses

    def _wait(self, host: str) -> None:
        wait = self.last.get(host, 0) + MIN_GAP.get(host, DEFAULT_GAP) - time.time()
        if wait > 0:
            time.sleep(wait)

    def raw(self, url: str, accept: str = "*/*", retries: int = 2, data: bytes | None = None,
            ctype: str | None = None, timeout: int = 45):
        """-> (status, headers, body bytes). Raises Blocked after repeated refusal."""
        host = urllib.parse.urlsplit(url).netloc
        if host in self.dead:
            raise Blocked(f"{host}: {self.dead[host]}")
        for attempt in range(retries + 1):
            self._wait(host)
            hdr = {"User-Agent": UA, "Accept": accept}
            if ctype:
                hdr["Content-Type"] = ctype
            req = urllib.request.Request(url, headers=hdr, data=data)
            code, headers, body = None, {}, b""
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    code, headers, body = r.status, dict(r.headers), r.read()
            except urllib.error.HTTPError as e:
                code, headers = e.code, dict(e.headers or {})
                try:
                    body = e.read()
                except OSError:
                    body = b""
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                self.last[host] = time.time()
                if attempt == retries:
                    raise Blocked(f"{host}: {type(e).__name__}: {e}"[:220]) from e
                time.sleep(5)
                continue
            self.last[host] = time.time()
            self.calls[host] = self.calls.get(host, 0) + 1
            wall = looks_blocked(code, headers, body)
            if code == 429 or (wall and code in (202, 403, 429, 503)):
                self.n429[host] = self.n429.get(host, 0) + 1
                if self.n429[host] >= MAX_429:
                    self.dead[host] = (wall or "HTTP 429") + f" x{self.n429[host]}"
                    raise Blocked(f"{host}: {self.dead[host]}")
                pauses = self.loc_pauses if host == "www.loc.gov" else (20, 40)
                time.sleep(pauses[min(attempt, len(pauses) - 1)])
                continue
            if code in (401, 403, 410, 451) or wall:
                self.dead[host] = wall or f"HTTP {code}"
                raise Blocked(f"{host}: {self.dead[host]}")
            if code == 404:
                return code, headers, b""
            if code and code >= 500:
                if attempt == retries:
                    raise Blocked(f"{host}: HTTP {code}")
                time.sleep(5)
                continue
            self.n429[host] = 0
            return code, headers, body
        raise Blocked(f"{host}: gave up")

    def json(self, url: str, accept: str = "application/json", **kw):
        key = None
        if self.cache_dir:
            import hashlib
            key = self.cache_dir / (hashlib.sha1((url + repr(kw.get("data"))).encode()).hexdigest() + ".json")
            if key.exists():
                return json.loads(key.read_text("utf-8"))
        out = self._json(url, accept, **kw)
        if key is not None and out:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            key.write_text(json.dumps(out, ensure_ascii=False), "utf-8")
        return out

    def _json(self, url: str, accept: str = "application/json", **kw):
        code, _h, body = self.raw(url, accept=accept, **kw)
        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except ValueError as e:
            raise Blocked(f"{urllib.parse.urlsplit(url).netloc}: non-JSON reply (HTTP {code})") from e

    def probe(self, url: str) -> tuple[int | None, str | None]:
        """One GET; never raises; returns (status, block reason or None)."""
        host = urllib.parse.urlsplit(url).netloc
        self._wait(host)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                code, headers, body = r.status, dict(r.headers), r.read(6000)
        except urllib.error.HTTPError as e:
            code, headers, body = e.code, dict(e.headers or {}), e.read(6000)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            self.last[host] = time.time()
            return None, f"{type(e).__name__}: {e}"[:160]
        self.last[host] = time.time()
        wall = looks_blocked(code, headers, body)
        if wall:
            return code, wall
        if code >= 400:
            return code, f"HTTP {code}"
        return code, None


def q(**kw) -> str:
    return urllib.parse.urlencode(kw)


# --------------------------------------------------------------------------------------------------
# Runners: each returns (records, coverage)  coverage = {queries, pages_walked, hits, blocked[], notes[]}
# --------------------------------------------------------------------------------------------------

def new_cov() -> dict:
    return {"queries": [], "pages_walked": 0, "hits": 0, "blocked": [], "notes": [], "examined": 0, "dropped": 0}


def iiif_dims(c: Client, base: str | None) -> tuple[int | None, int | None]:
    if not base:
        return None, None
    try:
        d = c.json(base.rstrip("/") + "/info.json")
    except Blocked:
        return None, None
    w, h = d.get("width"), d.get("height")
    return (w, h) if isinstance(w, int) and isinstance(h, int) else (None, None)


LOC_START_IDS = ("2016652451", "2016652452", "2013650023", "00652015")


LOC_MAX_FETCH = 120  # item fetches per run (3.2 s apart); further hits are listed, not fetched


def run_loc(c: Client):
    cov, recs = new_cov(), []
    fetched = 0
    pending: list[str] = []
    cov["queries"] = [f"item {i}" for i in LOC_START_IDS] + [
        "pictures/search q='Benoist, Philippe' (name authority heading)", "pictures/search q='Benoist, Felix'"]
    try:
        for i in LOC_START_IDS:
            d = c.json(f"https://www.loc.gov/pictures/item/{i}/?fo=json")
            cov["pages_walked"] += 1
            fetched += 1
            print(f"loc: item {i} ok", file=sys.stderr)
            rec = parse_loc_item(d)
            if rec:
                recs.append(rec)
        have = {r["record_id"].split(":")[1] for r in recs} | set(LOC_START_IDS)
        for who in ("Benoist, Philippe", "Benoist, Felix"):
            sp = 1
            while sp < 40:
                d = c.json("https://www.loc.gov/pictures/search/?" + q(q=who, fo="json", c=100, sp=sp))
                cov["pages_walked"] += 1
                res = d.get("results") or []
                if sp == 1:
                    cov["hits"] += int((d.get("pages") or {}).get("total") or len(res))
                for r in res:
                    link = (r.get("links") or {}).get("item") or r.get("url")
                    pk = (link or "").rstrip("/").split("/")[-1]
                    if not link or pk in have:
                        continue
                    have.add(pk)
                    pending.append(link)
                if len(res) < 100:
                    break
                sp += 1
        for link in pending:
            if fetched >= LOC_MAX_FETCH:
                break
            d = c.json(link.rstrip("/") + "/?fo=json")
            cov["pages_walked"] += 1
            fetched += 1
            rec = parse_loc_item(d)
            if rec:
                recs.append(rec)
            else:
                cov["dropped"] += 1
        if len(pending) + len(LOC_START_IDS) > fetched:
            cov["notes"].append(f"loc: {len(pending) + len(LOC_START_IDS) - fetched} search hits NOT fetched "
                                f"(cap {LOC_MAX_FETCH} item reads per run); re-run to continue")
    except Blocked as e:
        cov["blocked"].append(str(e))
        cov["notes"].append(f"loc: stopped after {fetched} item reads, {len(pending)} hits queued unread")
    return recs, cov


def run_nga(c: Client):
    cov, recs = new_cov(), []
    base = "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/"
    cov["queries"] = ["constituents.csv: preferreddisplayname contains 'Benoist'", "objects_constituents.csv",
                      "objects.csv", "published_images.csv"]

    def stream(name):
        req = urllib.request.Request(base + name, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                yield from csv.DictReader(io.TextIOWrapper(r, encoding="utf-8", newline=""))
        except (urllib.error.URLError, OSError) as e:
            raise Blocked(f"raw.githubusercontent.com: {e}"[:200]) from e

    try:
        cons = {r["constituentid"]: r for r in stream("constituents.csv")
                if "benoist" in fold(r.get("preferreddisplayname"))}
        cov["pages_walked"] += 1
        kinds = {cid: classify_artist(r["preferreddisplayname"], r.get("displaydate") or r.get("visualbrowsertimespan"))
                 for cid, r in cons.items()}
        cov["notes"].append("NGA Benoist constituents: " + "; ".join(
            f"{cid}={r['preferreddisplayname']} ({r.get('displaydate')}) -> {kinds[cid][0]}"
            for cid, r in cons.items()))
        keep_ids = {cid for cid, k in kinds.items() if k[0] != "other"}
        oc: dict[str, list[dict]] = {}
        all_cons: dict[str, list[dict]] = {}
        wanted_obj = set()
        rows = list(stream("objects_constituents.csv"))
        cov["pages_walked"] += 1
        for r in rows:
            if r["constituentid"] in cons:
                wanted_obj.add(r["objectid"])
                if r["constituentid"] in keep_ids:
                    oc.setdefault(r["objectid"], []).append(r)
                else:
                    cov["dropped"] += 1
        cov["hits"] = len(wanted_obj)
        for r in rows:
            if r["objectid"] in oc:
                all_cons.setdefault(r["objectid"], []).append(r)
        need_names = {r["constituentid"] for v in all_cons.values() for r in v}
        names = {cid: r["preferreddisplayname"] for cid, r in cons.items()}
        for r in stream("constituents.csv"):
            if r["constituentid"] in need_names:
                names[r["constituentid"]] = r["preferreddisplayname"]
        objs = {r["objectid"]: r for r in stream("objects.csv") if r["objectid"] in oc}
        cov["pages_walked"] += 1
        imgs: dict[str, dict] = {}
        for r in stream("published_images.csv"):
            oid = r["depictstmsobjectid"]
            if oid in oc and (oid not in imgs or r.get("viewtype") == "primary"):
                imgs[oid] = r
        cov["pages_walked"] += 1
        for oid, o in objs.items():
            if o.get("accessionnum") is None:
                continue
            rec = parse_nga_row(o, oc[oid], names, imgs.get(oid), constituents=all_cons.get(oid))
            if rec:
                recs.append(rec)
    except Blocked as e:
        cov["blocked"].append(str(e))
    return recs, cov


def run_met(c: Client):
    cov, recs = new_cov(), []
    ids: list[int] = []
    totals = []
    queries = [("Benoist", {}), ("Philippe Benoist", {}), ("Felix Benoist", {}), ("Félix Benoist", {}),
               ("Benoist", {"artistOrCulture": "true"}), ("Ph. Benoist", {})]
    try:
        for qq, extra in queries:
            d = c.json("https://collectionapi.metmuseum.org/public/collection/v1.1/search?" + q(q=qq, **extra))
            tot, got = parse_met_search(d)
            cov["queries"].append(qq + (" [artistOrCulture]" if extra else ""))
            cov["pages_walked"] += 1
            totals.append(tot)
            ids += got
        cov["hits"] = max(totals) if totals else 0
        uniq = list(dict.fromkeys(ids))
        cov["notes"].append(f"met: {len(uniq)} distinct object ids fetched individually (search is a full-text match)")
        for oid in uniq:
            o = c.json(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}")
            cov["pages_walked"] += 1
            rec = parse_met_object(o)
            if rec:
                recs.append(rec)
            elif o and "benoist" in fold(json.dumps(o.get("constituents")) + (o.get("artistDisplayName") or "")):
                cov["dropped"] += 1
        cov["notes"].append("Met API gives no pixel dimensions; image_width/height stay null (not guessed)")
    except Blocked as e:
        cov["blocked"].append(str(e))
    return recs, cov


def run_vam(c: Client):
    cov, recs = new_cov(), []
    try:
        sns: list[str] = []
        for qq in ("Benoist", "Felix Benoist"):
            page = 1
            cov["queries"].append(qq)
            while True:
                d = c.json("https://api.vam.ac.uk/v2/objects/search?" + q(q=qq, page_size=100, page=page))
                total, pages, got = parse_vam_search(d)
                cov["pages_walked"] += 1
                if page == 1:
                    cov["hits"] = max(cov["hits"], total)
                sns += got
                if page >= pages:
                    break
                page += 1
        for sn in dict.fromkeys(sns):
            d = c.json(f"https://api.vam.ac.uk/v2/museumobject/{sn}")
            cov["pages_walked"] += 1
            rec = parse_vam_record(d.get("record") or {})
            if rec:
                recs.append(rec)
            else:
                cov["dropped"] += 1
    except Blocked as e:
        cov["blocked"].append(str(e))
    return recs, cov


def run_rijks(c: Client):
    cov, recs = new_cov(), []
    people: dict[str, str] = {}
    try:
        objs: list[str] = []
        for who in ("Benoist", "Philippe Benoist", "Felix Benoist", "Félix Benoist"):
            url = "https://data.rijksmuseum.nl/search/collection?" + q(creator=who)
            cov["queries"].append(f"creator={who}")
            first = True
            while url:
                d = c.json(url, accept="application/ld+json")
                cov["pages_walked"] += 1
                if first:
                    first = False
                    if who == "Benoist":
                        cov["hits"] = (d.get("partOf") or {}).get("totalItems", 0)
                objs += [i["id"] for i in d.get("orderedItems", [])]
                url = (d.get("next") or {}).get("id")
        for oid in dict.fromkeys(objs):
            obj = c.json(oid, accept="application/ld+json")
            cov["pages_walked"] += 1
            for p in _dicts((obj.get("produced_by") or {}).get("part")):
                for a in _dicts(p.get("assigned_by")):
                    for who in _dicts(a.get("assigned")):
                        pid = who.get("id")
                        if pid and pid not in people:
                            pd = c.json(pid, accept="application/ld+json")
                            nm = [i.get("content") for i in _dicts(pd.get("identified_by")) if i.get("type") == "Name"]
                            people[pid] = nm[0] if nm else ""
            rec = parse_rijks_object(obj, people)
            if rec:
                recs.append(rec)
            else:
                cov["dropped"] += 1
        for r in recs:
            base = r.pop("_iiif_base", None)
            if r["rights_status"] == "open_confirmed":
                r["image_width"], r["image_height"] = iiif_dims(c, base)
        cov["notes"].append("Rijks search 'Benoist' is a creator-name search; non-Philippe/Felix creators are dropped")
    except Blocked as e:
        cov["blocked"].append(str(e))
    for r in recs:
        r.pop("_iiif_base", None)
    return recs, cov


def run_aic(c: Client):
    cov, recs = new_cov(), []
    try:
        for phrase in ("Philippe Benoist", "Felix Benoist", "Benoist"):
            body = json.dumps({"query": {"multi_match": {"query": phrase, "type": "phrase",
                                                         "fields": ["artist_display", "artist_title", "title"]}},
                               "limit": 100,
                               "fields": ["id", "title", "artist_display", "date_display", "medium_display",
                                          "is_public_domain", "image_id", "thumbnail",
                                          "main_reference_number"]}).encode()
            d = c.json("https://api.artic.edu/api/v1/artworks/search", data=body, ctype="application/json")
            cov["queries"].append(f"POST multi_match phrase {phrase!r}")
            cov["pages_walked"] += 1
            cov["hits"] = max(cov["hits"], (d.get("pagination") or {}).get("total", 0))
            for r in d.get("data", []):
                rec = parse_aic_row(r)
                if rec:
                    recs.append(rec)
    except Blocked as e:
        cov["blocked"].append(str(e))
    return recs, cov


def run_cleveland(c: Client):
    cov, recs = new_cov(), []
    try:
        for kw in ({"q": "Benoist"}, {"creator": "Benoist"}, {"q": "Felix Benoist"}):
            d = c.json("https://openaccess-api.clevelandart.org/api/artworks/?" + q(limit=100, **kw))
            cov["queries"].append(str(kw))
            cov["pages_walked"] += 1
            cov["hits"] = max(cov["hits"], (d.get("info") or {}).get("total", 0))
            for r in d.get("data", []):
                rec = parse_cleveland_row(r)
                if rec:
                    recs.append(rec)
    except Blocked as e:
        cov["blocked"].append(str(e))
    return recs, cov


def run_brown(c: Client):
    cov, recs = new_cov(), []
    try:
        pids: list[str] = []
        for qq in ("name:Benoist", "Benoist AND object_type:image", "other_title:\"Paris dans sa splendeur\""):
            start = 0
            cov["queries"].append(qq)
            while True:
                d = c.json("https://repository.library.brown.edu/api/search/?" + q(
                    q=qq, rows=100, start=start, fl="pid", wt="json"))
                cov["pages_walked"] += 1
                n = (d.get("response") or {}).get("numFound", 0)
                if start == 0 and qq == "name:Benoist":
                    cov["hits"] = n
                pids += parse_brown_hits(d)
                start += 100
                if start >= n:
                    break
        uniq = list(dict.fromkeys(pids))
        cov["notes"].append(f"Brown: {len(uniq)} distinct pids across queries, each item JSON read")
        for pid in uniq:
            d = c.json(f"https://repository.library.brown.edu/api/items/{pid}/")
            cov["pages_walked"] += 1
            rec = parse_brown_item(d)
            if rec:
                recs.append(rec)
            else:
                cov["dropped"] += 1
        cov["notes"].append("Brown: rightsstatements.org NoC-US ('No Copyright - United States') is an advisory, "
                            "recorded as rights_pending, never open_confirmed")
    except Blocked as e:
        cov["blocked"].append(str(e))
    return recs, cov


def run_europeana(c: Client):
    cov, recs = new_cov(), []
    seen: set[str] = set()
    qs = ['"Philippe Benoist"', '"Benoist, Philippe"', '"Ph. Benoist"', '"Felix Benoist"', '"Félix Benoist"',
          '"Benoist, Félix"', '"F. Benoist"', '"España artística y monumental"', "Benoist lithographe Lemercier",
          "Benoist Paris dans sa splendeur", "Benoist Rome dans sa grandeur", "Benoist Paris et ses environs",
          "Benoist Nice et Savoie", "Benoist Bretagne contemporaine", "Benoist lithograph"]
    try:
        for qq in qs:
            start = 1
            cov["queries"].append(qq)
            while start < 1100:
                d = c.json("https://api.europeana.eu/record/v2/search.json?" + q(
                    wskey="api2demo", query=qq, rows=100, start=start, profile="rich"))
                cov["pages_walked"] += 1
                if start == 1:
                    cov["hits"] += int(d.get("totalResults") or 0)
                items = d.get("items", [])
                for it in items:
                    if it.get("id") in seen:
                        continue
                    seen.add(it.get("id"))
                    rec = parse_europeana_item(it)
                    if rec:
                        recs.append(rec)
                    elif "benoist" in fold(json.dumps(it.get("dcCreator") or "")):
                        cov["dropped"] += 1
                if len(items) < 100:
                    break
                start += 100
        cov["notes"].append("Europeana = aggregator (BnF/Gallica, BNE/Hispana, others); hits are summed over queries "
                            "and overlap; records are search hits, their holder pages were not opened")
    except Blocked as e:
        cov["blocked"].append(str(e))
    return recs, cov


def run_getty(c: Client):
    cov = new_cov()
    cov["queries"] = ["ULAN SPARQL luc:term 'Benoist'"]
    auth = []
    try:
        query = ('select ?s ?l where { ?s luc:term "Benoist" ; skos:inScheme ulan: ; '
                 'gvp:prefLabelGVP/xl:literalForm ?l } limit 100')
        d = c.json("https://vocab.getty.edu/sparql.json?" + q(query=query))
        cov["pages_walked"] = 1
        auth = parse_ulan(d)
        cov["hits"] = len(auth)
        cov["notes"].append("ULAN is an authority file (no works): ULAN uris of Benoist artists are listed in "
                            "coverage.authorities; no work records produced")
    except Blocked as e:
        cov["blocked"].append(str(e))
    cov["authorities"] = auth
    return [], cov


PROBES = {
    "morgan": ["https://www.themorgan.org/printed-books/162671", "https://corsair.themorgan.org/"],
    "british_museum": ["https://www.britishmuseum.org/collection/search?keyword=Philippe&keyword=Benoist"],
    "yale_lux": ["https://lux.collections.yale.edu/api/search/item?" + q(
        q=json.dumps({"AND": [{"text": "Benoist", "_complete": True}]}))],
    "harvard": ["https://api.lib.harvard.edu/v2/items.json?q=Philippe+Benoist&limit=1"],
    "nypl": ["https://api.repo.nypl.org/api/v2/items/search?q=Benoist"],
    "bne": ["https://datos.bne.es/sparql", "https://bdh.bne.es/bnesearch/Search.do?text=Benoist"],
    "hertziana": ["https://digital.biblhertz.it/", "https://www.biblhertz.it/"],
}
PROBE_NOTES = {
    "morgan": "Morgan printed-books record and Corsair catalogue sit behind a Cloudflare bot wall; no public API",
    "british_museum": "BM collection search is behind a Cloudflare challenge; the old SPARQL endpoint is not reachable",
    "yale_lux": "Yale LUX API answers an AWS WAF challenge (HTTP 202, empty body) to non-browser clients",
    "harvard": "Harvard LibraryCloud returns 403 without an API key; HAM needs a key (none stored in repo)",
    "nypl": "NYPL Digital Collections API requires a registered token (HTTP 401); none stored in repo",
    "bne": "BNE: datos.bne.es SPARQL 403, bdh.bne.es serves a request-form shell, catalogue is a JS SPA; "
           "BNE material is reached only through Europeana",
    "hertziana": "Biblioteca Hertziana hosts do not resolve/connect through the egress proxy",
}


def run_probe(c: Client, name: str):
    cov = new_cov()
    ok_any = False
    for u in PROBES[name]:
        code, why = c.probe(u)
        cov["queries"].append(u)
        cov["pages_walked"] += 1
        if why:
            cov["blocked"].append(f"{urllib.parse.urlsplit(u).netloc}: {why}")
        else:
            ok_any = True
            cov["notes"].append(f"{u} reachable (HTTP {code}) but offers no implemented machine-readable Benoist query")
    cov["notes"].append(PROBE_NOTES[name])
    if not ok_any:
        cov["notes"].append("no records produced")
    return [], cov


# Antiquarian leads: titles/series discovered in dealer and auction catalogues. NEVER an image source.
ANTIQUARIAN_LEADS: list[dict] = [
    # Found by web search 2026-11-21; listing pages were NOT opened (search_hit_only). Titles are the listing titles.
    {"id": "1stdibs-a_8706732", "name_as_stated": "Philippe Benoist", "role": "lithographer",
     "title": "Piazza di Monte Cavallo, Rome, Italy. Tinted lithograph by Philippe Benoist",
     "series": "Rome dans sa grandeur", "seller": "1stdibs (dealer listing)",
     "url": "https://www.1stdibs.com/art/prints-works-on-paper/landscape-prints-works-on-paper/"
            "philippe-benoist-piazza-di-monte-cavallo-rome-italy-tinted-lithograph-philippe-benoist/id-a_8706732"},
    {"id": "1stdibs-a_8706812", "name_as_stated": "Felix Benoist", "role": "lithographer",
     "title": "Palazzo e Giardini del Vaticano, Rome Italy. Tinted lithograph, Felix Benoist",
     "series": "Rome dans sa grandeur", "seller": "1stdibs (dealer listing)",
     "url": "https://www.1stdibs.com/art/prints-works-on-paper/landscape-prints-works-on-paper/"
            "felix-benoist-palazzo-e-giardini-del-vaticano-rome-italy-tinted-lithograph-felix-benoist/id-a_8706812"},
    {"id": "1stdibs-a_6360442", "name_as_stated": "Philippe Benoist", "role": None,
     "title": "Paris - Parc de Monceaux, French lithograph, 1861", "series": "Paris dans sa splendeur",
     "date": "1861", "seller": "1stdibs (dealer listing)",
     "url": "https://www.1stdibs.com/art/prints-works-on-paper/landscape-prints-works-on-paper/"
            "philippe-benoist-paris-parc-de-monceaux-french-lithograph-1861/id-a_6360442"},
    {"id": "1stdibs-a_6360462", "name_as_stated": "Philippe Benoist", "role": None,
     "title": "Paris - Fontaine de la Place du Chatelet, French lithograph, 1861", "series": "Paris dans sa splendeur",
     "date": "1861", "seller": "1stdibs (dealer listing)",
     "url": "https://www.1stdibs.com/art/prints-works-on-paper/landscape-prints-works-on-paper/"
            "philippe-benoist-paris-fontaine-de-la-place-du-chatelet-french-lithograph-1861/id-a_6360462"},
    {"id": "1stdibs-a_6360392", "name_as_stated": "Philippe Benoist", "role": None,
     "title": "Paris - Eglise Saint Genevieve (Ancien Pantheon), French lithograph, 1861",
     "series": "Paris dans sa splendeur", "date": "1861", "seller": "1stdibs (dealer listing)",
     "url": "https://www.1stdibs.com/art/prints-works-on-paper/landscape-prints-works-on-paper/"
            "philippe-benoist-paris-eglise-saint-genevieve-ancien-pantheon-french-lithograph-1861/id-a_6360392"},
]

RUNNERS = [("loc", run_loc), ("nga", run_nga), ("met", run_met), ("rijks", run_rijks), ("getty", run_getty),
           ("vam", run_vam), ("aic", run_aic), ("cleveland", run_cleveland), ("brown", run_brown),
           ("europeana", run_europeana)]
ORDER = ["loc", "nga", "met", "morgan", "rijks", "getty", "vam", "british_museum", "aic", "cleveland", "yale_lux",
         "brown", "harvard", "nypl", "bne", "europeana", "hertziana", "antiquarian"]


def antiquarian_records(leads: list[dict]) -> list[dict]:
    out = []
    for L in leads:
        a, _ = classify_artist(L.get("name_as_stated"))
        out.append(make_record(
            record_id=f"antiquarian:{L['id']}", participants=[part(L.get("name_as_stated"), L.get("role"))],
            original_title=L.get("title"), series=L.get("series"), date_as_stated=L.get("date"),
            institution=L.get("seller"), record_url=L.get("url"), rights_status="unknown",
            verification_status="search_hit_only", source_type="antiquarian",
            attribution_note="Antiquarian/auction listing: discovery of a title/series only, never an image source"))
    return out


# --------------------------------------------------------------------------------------------------


def stats_for(recs: list[dict]) -> dict:
    def n(f):
        return sum(1 for r in recs if f(r))

    new = [r for r in recs if not r["known"]]
    return {
        "kept": len(recs),
        "philippe_named": n(lambda r: "philippe-benoist" in r["artist_ids_named"]),
        "felix_named": n(lambda r: "felix-benoist" in r["artist_ids_named"]),
        "philippe_only": n(lambda r: r["artist_id"] == "philippe-benoist"),
        "felix_only": n(lambda r: r["artist_id"] == "felix-benoist"),
        "both_named_or_unclear": n(lambda r: r["artist_id"] == "uncertain-benoist"),
        "known": len(recs) - len(new),
        "new": len(new),
        "open_confirmed": n(lambda r: r["rights_status"] == "open_confirmed"),
        "open_confirmed_with_pixels": n(lambda r: r["rights_status"] == "open_confirmed" and r["image_width"]),
        "rights_pending": n(lambda r: r["rights_status"] == "rights_pending"),
        "link_only": n(lambda r: r["rights_status"] == "link_only"),
        "unknown_rights": n(lambda r: r["rights_status"] == "unknown"),
    }


def assemble(per_source: dict[str, tuple[list[dict], dict]], known: dict, previous: dict | None = None) -> dict:
    all_recs: list[dict] = []
    seen_ids: set[str] = set()
    seen_new_hints: set[str] = set()
    cov_by, per_stats = {}, {}
    for name in ORDER:
        if name not in per_source:
            continue
        recs, cov = per_source[name]
        uniq = []
        for r in recs:
            if r["record_id"] in seen_ids:
                continue
            seen_ids.add(r["record_id"])
            mark_known(r, known)
            uniq.append(r)
        st = stats_for(uniq)
        nu = 0
        for r in uniq:
            h = r["duplicate_hint"]
            if not r["known"] and h and h not in known["hints"] and h not in seen_new_hints:
                seen_new_hints.add(h)
                nu += 1
        st["new_unique_compositions"] = nu
        per_stats[name] = {"hits_reported_by_source": cov["hits"], **st,
                           "examined_records": cov["examined"], "dropped_not_philippe_or_felix": cov["dropped"]}
        cov_by[name] = cov
        all_recs += uniq
    total = stats_for(all_recs)
    total["new_unique_compositions"] = len(seen_new_hints)
    queries = {k: v["queries"] for k, v in cov_by.items()}
    blocked = {k: v["blocked"] for k, v in cov_by.items() if v["blocked"]}
    notes = {k: v["notes"] for k, v in cov_by.items() if v["notes"]}
    return {
        "version": 1,
        "source": "museums-multi",
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "coverage": {
            "queries": queries,
            "pages_walked": {k: v["pages_walked"] for k, v in cov_by.items()},
            "hits_total_reported_by_source": {k: v["hits"] for k, v in cov_by.items()},
            "records_kept": {k: v["kept"] for k, v in per_stats.items()},
            "blocked": blocked,
            "notes": notes,
            "per_source": per_stats,
            "totals": total,
            "authorities": (cov_by.get("getty") or {}).get("authorities", []),
            "cross_checked_against": ["data/curation/benoist-harvest-v1.json", "book/benoist-sheets.json"],
        },
        "records": all_recs,
    }


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    def opt(flag):
        return set(argv[argv.index(flag) + 1].split(",")) if flag in argv else set()

    only, skip = opt("--only"), opt("--skip")
    pause = int(argv[argv.index("--loc-pause") + 1]) if "--loc-pause" in argv else None
    cache = Path(argv[argv.index("--cache") + 1]) if "--cache" in argv else None
    c = Client(loc_pauses=(pause, pause * 2) if pause else LOC_PAUSES, cache_dir=cache)
    per: dict[str, tuple[list[dict], dict]] = {}
    prev = json.loads(OUT.read_text("utf-8")) if only and OUT.exists() else None
    if prev:
        by_src: dict[str, list[dict]] = {}
        for r in prev["records"]:
            by_src.setdefault(r["record_id"].split(":")[0], []).append(r)
        for name in ORDER:
            cov = new_cov()
            cov["queries"] = prev["coverage"]["queries"].get(name, [])
            cov["pages_walked"] = prev["coverage"]["pages_walked"].get(name, 0)
            cov["hits"] = prev["coverage"]["hits_total_reported_by_source"].get(name, 0)
            cov["blocked"] = prev["coverage"]["blocked"].get(name, [])
            cov["notes"] = prev["coverage"]["notes"].get(name, [])
            cov["dropped"] = prev["coverage"]["per_source"].get(name, {}).get("dropped_not_philippe_or_felix", 0)
            cov["examined"] = prev["coverage"]["per_source"].get(name, {}).get("examined_records", 0)
            per[name] = (by_src.get(name, []), cov)
    for name, fn in RUNNERS:
        if (only and name not in only) or name in skip:
            continue
        t0 = time.time()
        try:
            recs, cov = fn(c)
        except (KeyError, TypeError, ValueError, AttributeError) as e:  # a source changed shape: record, go on
            recs, cov = [], new_cov()
            cov["blocked"].append(f"parser error {type(e).__name__}: {e}"[:200])
        per[name] = (recs, cov)
        print(f"{name}: kept {len(recs)} / hits {cov['hits']} blocked={cov['blocked']} ({time.time() - t0:.0f}s)",
              file=sys.stderr)
    for name in PROBES:
        if (only and name not in only) or name in skip:
            continue
        per[name] = run_probe(c, name)
        print(f"{name}: blocked={per[name][1]['blocked']}", file=sys.stderr)
    if not only or "antiquarian" in only:
        cov = new_cov()
        cov["queries"] = ["manual web search of dealer/auction catalogues (see notes)"]
        cov["notes"] = ["source_type=antiquarian: leads for titles/series only; never an image source"]
        per["antiquarian"] = (antiquarian_records(ANTIQUARIAN_LEADS), cov)
    doc = assemble(per, build_known())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps(doc["coverage"]["totals"]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
