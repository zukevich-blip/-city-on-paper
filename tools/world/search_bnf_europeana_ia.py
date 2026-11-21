#!/usr/bin/env python3
"""Search BnF, Europeana, Heidelberg, Internet Archive, HathiTrust/Google Books and Commons for works by
Philippe Benoist (1813-1905, BnF authority ark:/12148/cb14962134k, UNIMARC id 14962134) and, separately,
Felix Benoist (1818-1896, UNIMARC id 11891235).  They are different people; so are Guillaume-Philippe
Benoist, Antoine Benoist and other Benoists, who are counted and dropped.

Output: data/research/benoist/bnf-europeana-heidelberg-ia-v1.json (schema: data/research/benoist/SCHEMA.md).
Nothing is downloaded except catalogue metadata (XML/JSON).  No image bytes are fetched.  403 / 429 /
CAPTCHA / bot challenges are NOT bypassed: they are written to coverage.blocked.

Run (re-runnable, stdlib only, ~10-15 minutes because of >= 1.2 s gaps between requests):
    python3 tools/world/search_bnf_europeana_ia.py            # all sources
    python3 tools/world/search_bnf_europeana_ia.py --only bnf,europeana
Environment: EUROPEANA_API_KEY (default: Europeana's public demo key, as in collect_benoist.py).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.world.collect_benoist import Blocked, Client  # noqa: E402  (reuse the project's polite client)

OUT = ROOT / "data" / "research" / "benoist" / "bnf-europeana-heidelberg-ia-v1.json"
UA = "CityOnPaperResearch/0.9 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)"
EUROPEANA_KEY = os.environ.get("EUROPEANA_API_KEY", "api2demo")
MIN_GAP = 1.2
HOST_GAP = {"commons.wikimedia.org": 2.5}

# BnF authority identifiers as they appear in UNIMARC 7xx $3
BNF_AUTH = {"14962134": "philippe-benoist", "11891235": "felix-benoist"}
SERIES = (
    (r"paris dans sa splendeur", "Paris dans sa splendeur"),
    (r"promenade dans paris", "Promenade dans Paris et ses environs"),
    (r"rome dans sa grandeur", "Rome dans sa grandeur"),
    (r"espa[nñ]a art[ií]stica y monumental", "España artística y monumental"),
    (r"vues? de paris", "Vues de Paris"),
    (r"paris et ses environs", "Paris et ses environs"),
    (r"album de (?:varsovie|wilna)", "Album de Varsovie / Wilna"),
)

# --------------------------------------------------------------------------------------------------
# Pure helpers (unit-tested, no network)
# --------------------------------------------------------------------------------------------------


def strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s or "") if unicodedata.category(ch) != "Mn")


_OTHER = re.compile(
    r"guillaume[\s-]*philippe\s+benoist|benoist,?\s+guillaume|antoine\s+benoist|benoist,?\s+antoine|"
    r"j\.\s*l\.\s*benoist|benoist,\s*j\.\s*l\.|raymond\s+benoist|benoist,?\s+charles|charles\s+benoist|"
    r"benoist[- ]m[eé]chin|jean[- ]marie\s+benoist|benoist,?\s+jean|benoist,?\s+[ée]milien",
    re.I,
)
_PH = re.compile(
    r"benoist,?\s+ph(?:ilippe|\.)?(?!\w)|ph(?:ilippe|\.|\[ilippe\])\s*\(?(?:1813\)?\s*)?benoist|p\[hilippe\]\s+benoist"
    r"|ph\.?\s+benoist|benoist\s*\(1813|philippe,?\s+benoist|\bbenoist\s+philippe",
    re.I,
)
_FE = re.compile(r"f[eé]lix\s+benoist|benoist,?\s+f[eé]lix|benoist\s*\(?1818|benoist,?\s+f\.(?!\w)", re.I)
_ANY = re.compile(r"benoi[sc]?t", re.I)


def classify_benoist(text: str) -> tuple[str | None, str]:
    """Return (artist_id, note).  None means no Benoist at all.  'other' = a different Benoist."""
    t = " ".join(strip_accents(text or "").split())
    if not _ANY.search(t):
        return None, ""
    cleaned = _OTHER.sub(" ", t)
    ph = bool(_PH.search(cleaned)) and not re.search(r"benoist\s+philippe\s*,?\s+r[ée]al", cleaned, re.I)
    fe = bool(_FE.search(cleaned))
    if ph and fe:
        return "uncertain-benoist", "Text names both Philippe and Félix Benoist; assign per participant."
    if ph:
        return "philippe-benoist", ""
    if fe:
        return "felix-benoist", ""
    if _OTHER.search(t):
        return "other", "Another Benoist (Guillaume-Philippe / Antoine / other) is named."
    if re.search(r"\bbenoist\b", cleaned, re.I):
        return "uncertain-benoist", "Surname 'Benoist' without a first name or initial."
    return None, ""


def norm_role(text: str | None) -> str:
    s = strip_accents((text or "").lower())
    if re.search(r"\bdel\b|delin|dessin|drawer|drawn|gezeichnet|designer|\bdes\.?\b", s):
        return "designer"
    if re.search(r"lith|lithograph", s):
        return "lithographer"
    if re.search(r"\bimp\b|imprim|printer|printed|druck", s):
        return "printer"
    if re.search(r"editeur|publi|verlag|\bed\.", s):
        return "publisher"
    if re.search(r"grav|engrav|sculp", s):
        return "engraver"
    if re.search(r"auteur du texte|\btexte|\bauthor|\bautor\b|\bpar\b\s+m", s):
        return "author_of_text"
    return "unspecified"


def role_set_from_statement(stmt: str) -> list[str]:
    """Roles named in a responsibility string such as 'Ph. Benoist del. et lith.' (several are possible)."""
    s = strip_accents((stmt or "").lower())
    out = []
    if re.search(r"\bdel\b|delin|dessin|\bdes\b", s):
        out.append("designer")
    if re.search(r"\blith|lithograph", s):
        out.append("lithographer")
    if re.search(r"\bimp\b|imprim", s):
        out.append("printer")
    if re.search(r"\bsc\b|sculp|\bgr\b|grav", s):
        out.append("engraver")
    return out or ["unspecified"]


def rights_status(statement: str | None) -> str:
    """open_confirmed only for explicit CC0/PDM/CC BY/CC BY-SA on the file.  'No known restrictions' is NOT open."""
    s = (statement or "").lower()
    if not s:
        return "unknown"
    if any(
        w in s
        for w in (
            "noc-oklr",
            "noc-nc",
            "/inc/",
            "/cne/",
            "-nc",
            "noncommercial",
            "all rights reserved",
            "no known restrictions",
            "no known copyright",
            "noc-cr",
        )
    ):
        return "link_only"
    if any(
        w in s
        for w in (
            "publicdomain/zero",
            "publicdomain/mark",
            "creativecommons.org/licenses/by/",
            "creativecommons.org/licenses/by-sa/",
            "/by-sa/",
            "cc0",
            "cc-by",
            "pdm",
            "public domain",
            "domaine public",
        )
    ):
        return "open_confirmed"
    return "rights_pending"


def series_of(*texts: str | None) -> str | None:
    blob = strip_accents(" ".join(t for t in texts if t).lower())
    for pat, name in SERIES:
        if re.search(strip_accents(pat), blob):
            return name
    return None


def plate_of(title: str | None) -> str | None:
    m = re.search(r"(?:planches?|pl\.|plate|n[°o]\.?)\s*(\d{1,3})\b", title or "", re.I)
    return m.group(1) if m else None


def duplicate_hint(title: str | None, series: str | None, plate: str | None) -> str:
    t = (title or "").split(" / ")[0]
    t = re.sub(r"\[[^\]]*\]", " ", t)  # [estampe], [dessin], [Paris]
    t = strip_accents(t.lower())
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = re.sub(r"\b(le|la|les|l|de|du|des|d|et|a|au|aux|en|un|une)\b", " ", t)
    t = " ".join(t.split())
    return f"{t}|{(series or '').lower()}|{plate or ''}"


_KEY_PATTERNS = (
    re.compile(r"ark:/12148/([a-z0-9]+)", re.I),
    re.compile(r"ark__12148_([a-z0-9]+)", re.I),
    re.compile(r"(?:node/|pm-|parismusees-)(\d{6,})", re.I),
    re.compile(r"loc\.gov/(?:pictures/item|item)/(\w+)", re.I),
    re.compile(r"(?:archive\.org/details/|\bia-)([A-Za-z0-9_.-]{6,})"),
    re.compile(r"(audiganne1861bd\d/\d{4})"),
)


def extract_keys(text: str) -> set[str]:
    """Stable source-id keys found anywhere in a JSON/markdown text (Gallica/BnF ark ids, node numbers, ...)."""
    keys = set()
    for pat in _KEY_PATTERNS:
        for m in pat.finditer(text or ""):
            keys.add(m.group(1).lower())
    return keys


def record_keys(rec: dict) -> set[str]:
    keys = set()
    for k in ("record_url", "record_id", "iiif_manifest", "accession"):
        keys |= extract_keys(str(rec.get(k) or ""))
    return keys


def mark_known(records: list[dict], known: set[str]) -> int:
    n = 0
    for r in records:
        hit = sorted(record_keys(r) & known)
        r["known_in_repo"] = bool(hit)
        r["known_match"] = hit[0] if hit else None
        n += bool(hit)
    return n


def group_duplicates(records: list[dict]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for r in records:
        groups.setdefault(r["duplicate_hint"], []).append(r["record_id"])
    return groups


def make_record(**kw) -> dict:
    rid = kw["record_id"]
    title = kw.get("original_title")
    series = kw.get("series") or series_of(title)
    plate = kw.get("plate_number") or plate_of(title)
    rs = kw.get("rights_status") or rights_status(kw.get("rights_statement"))
    image_url = kw.get("image_url") if rs == "open_confirmed" else None
    return {
        "record_id": rid,
        "artist_id": kw["artist_id"],
        "participants": kw.get("participants") or [],
        "original_title": title,
        "translated_title_ru": None,
        "series": series,
        "plate_number": plate,
        "volume": kw.get("volume"),
        "city": kw.get("city"),
        "place": kw.get("place"),
        "country": kw.get("country"),
        "geo_confidence": kw.get("geo_confidence") or ("city" if kw.get("city") else "unknown"),
        "date_as_stated": kw.get("date_as_stated"),
        "technique_as_stated": kw.get("technique_as_stated"),
        "object_type": kw.get("object_type", "print"),
        "institution": kw.get("institution"),
        "accession": kw.get("accession"),
        "record_url": kw["record_url"],
        "iiif_manifest": kw.get("iiif_manifest"),
        "image_url": image_url,
        "image_width": kw.get("image_width"),
        "image_height": kw.get("image_height"),
        "rights_statement": kw.get("rights_statement"),
        "rights_status": rs,
        "duplicate_hint": duplicate_hint(title, series, plate),
        "impression_note": kw.get("impression_note"),
        "verification_status": kw.get("verification_status", "source_record_read"),
        "attribution_confidence": kw.get("attribution_confidence", "medium"),
        "attribution_note": kw.get("attribution_note", ""),
        "known_in_repo": False,
        "known_match": None,
        "source_hit_query": kw.get("source_hit_query"),
    }


# ---- BnF (UNIMARC via SRU) -----------------------------------------------------------------------

NS = {"srw": "http://www.loc.gov/zing/srw/", "mxc": "info:lc/xmlns/marcxchange-v2"}


def _sub(df: ET.Element, code: str) -> list[str]:
    return [(s.text or "").strip() for s in df.findall("mxc:subfield", NS) if s.get("code") == code and s.text]


def _fields(rec: ET.Element, tag: str) -> list[ET.Element]:
    return [d for d in rec.findall("mxc:datafield", NS) if d.get("tag") == tag]


def parse_bnf_sru(xml_text: str) -> tuple[int, int | None, list[ET.Element], str | None]:
    """-> (numberOfRecords, nextRecordPosition, marc records, diagnostic message)."""
    root = ET.fromstring(xml_text)
    total = int((root.findtext("srw:numberOfRecords", default="0", namespaces=NS) or "0").strip())
    nxt = root.findtext("srw:nextRecordPosition", namespaces=NS)
    diag = None
    for el in root.iter():
        if el.tag.endswith("}message") and el.text:
            diag = el.text
    recs = [r for r in root.iter("{info:lc/xmlns/marcxchange-v2}record")]
    return total, (int(nxt) if nxt else None), recs, diag


def parse_bnf_record(rec: ET.Element, query: str | None = None) -> tuple[dict | None, str | None]:
    """UNIMARC record -> (record, drop_reason).  Attribution comes from the authority id in 7xx $3 first."""
    ark = (rec.get("id") or "").replace("ark:/12148/", "")
    if not ark:
        return None, "no_ark"
    f200 = (_fields(rec, "200") or [None])[0]
    if f200 is None:
        return None, "no_200"
    title = " : ".join(x for x in (", ".join(_sub(f200, "a")), " ; ".join(_sub(f200, "i"))) if x)
    if _sub(f200, "e"):
        title += " " + " ".join(_sub(f200, "e"))
    stmt = " ; ".join(_sub(f200, "f") + _sub(f200, "g"))
    people = []
    auth_hits = set()
    text_only = False
    other_benoist = False
    for tag in ("700", "701", "702", "710", "711", "712"):
        for df in _fields(rec, tag):
            fam, giv = ", ".join(_sub(df, "a")), ", ".join(_sub(df, "b"))
            auth = (_sub(df, "3") or [None])[0]
            code = (_sub(df, "4") or [None])[0]
            name = ", ".join(x for x in (fam, giv) if x)
            if _sub(df, "f"):
                name += f" ({_sub(df, 'f')[0]})"
            people.append({"name": name, "auth": auth, "code": code, "tag": tag})
            if auth in BNF_AUTH:
                auth_hits.add(BNF_AUTH[auth])
            elif re.search(r"benoi", fam, re.I):
                other_benoist = True
    text_blob = " ".join(
        [title, stmt] + [x for tag in ("300", "304", "305", "320") for d in _fields(rec, tag) for x in _sub(d, "a")]
    )
    text_id, text_note = classify_benoist(text_blob)
    if auth_hits:
        artist = next(iter(auth_hits)) if len(auth_hits) == 1 else "uncertain-benoist"
        conf, note = "high", f"BnF authority id(s) linked in the record: {sorted(auth_hits)}."
        if len(auth_hits) > 1:
            note += " Both Philippe and Félix Benoist are credited on this record."
    elif text_id in ("philippe-benoist", "felix-benoist") and not other_benoist:
        text_only = True
        artist, conf, note = (
            text_id,
            "medium",
            "No authority-linked 7xx for Benoist; attribution read from the title/responsibility text.",
        )
    elif text_id == "uncertain-benoist" and not other_benoist:
        return None, "surname_only_without_authority"
    else:
        return None, "other_benoist" if (other_benoist or text_id == "other") else "no_benoist"
    parts = []
    for p in people:
        if re.search(r"benoi", p["name"], re.I):
            parts.append(
                {
                    "name": p["name"],
                    "role_as_stated": stmt or None,
                    "role_normalized": norm_role(stmt) if stmt else "unspecified",
                }
            )
    if not parts and stmt:
        parts.append(
            {
                "name": "Benoist (from responsibility statement)",
                "role_as_stated": stmt,
                "role_normalized": norm_role(stmt),
            }
        )
    f214 = _fields(rec, "214")
    pub_place = _sub(f214[0], "a")[0] if f214 and _sub(f214[0], "a") else None
    date = next((x for d in f214 for x in _sub(d, "d")), None)
    f215 = (_fields(rec, "215") or [None])[0]
    tech = " ; ".join(_sub(f215, "a") + _sub(f215, "c")) if f215 is not None else None
    leader = rec.findtext("mxc:leader", namespaces=NS) or ""
    tl = (title + " " + (tech or "")).lower()
    if "estampe" in tl:
        otype = "print"
    elif "dessin" in tl:
        otype = "drawing"
    elif len(leader) > 6 and leader[6] == "k":
        otype = "print"
    else:
        otype = "book"
    ym = re.search(r"(\d{4})", date or "")
    if text_only and otype == "book" and not (ym and int(ym.group(1)) <= 1925):
        return None, "text_only_not_nineteenth_century"
    f461 = _fields(rec, "461") + _fields(rec, "225")
    series = (_sub(f461[0], "t") or _sub(f461[0], "a") or [None])[0] if f461 else None
    f607 = _fields(rec, "607")
    city = place = None
    if f607:
        city = (_sub(f607[0], "a") or [None])[0]
        place = (_sub(f607[0], "x") or [None])[0]
    cote = (
        next(((_sub(d, "a") or [None])[0], (_sub(d, "c") or [None])[0]) for d in (_fields(rec, "930") or [rec]))
        if _fields(rec, "930")
        else (None, None)
    )
    accession = " | ".join(x for x in cote if x) or None
    r = make_record(
        record_id=f"bnf:{ark}",
        artist_id=artist,
        participants=parts,
        original_title=title.strip(),
        series=series_of(title, series) or series,
        city=city,
        place=place,
        country="FR" if city and "France" in city else None,
        date_as_stated=date,
        technique_as_stated=tech,
        object_type=otype,
        institution="Bibliothèque nationale de France",
        accession=accession,
        record_url=f"https://catalogue.bnf.fr/ark:/12148/{ark}",
        rights_statement=None,
        rights_status="unknown",
        impression_note=f"Published: {pub_place or '?'}; 200$f/$g: {stmt or '-'}",
        attribution_confidence=conf,
        attribution_note=note,
        source_hit_query=query,
    )
    r["roles_set_from_statement"] = role_set_from_statement(stmt)
    return r, None


# ---- Europeana --------------------------------------------------------------------------------------


def _first(v):
    return v[0] if isinstance(v, list) and v else (v if isinstance(v, str) else None)


def parse_europeana_item(item: dict, query: str | None = None) -> tuple[dict | None, str | None]:
    creators = item.get("dcCreator") or []
    contribs = item.get("dcContributor") or []
    title = _first(item.get("title")) or ""
    desc = " ".join(item.get("dcDescription") or [])
    blob = " | ".join(creators + contribs + [title])
    artist, note = classify_benoist(blob)
    if artist is None:
        a2, n2 = classify_benoist(desc)
        if a2 in ("philippe-benoist", "felix-benoist"):
            artist, note = a2, "Benoist named only in the free-text description. " + n2
        else:
            return None, "no_benoist"
    if artist == "other":
        return None, "other_benoist"
    if artist == "uncertain-benoist" and note.startswith("Surname") and not series_of(title, desc):
        return None, "surname_only_no_series"
    structured = [c for c in creators + contribs if re.search(r"benoi", c, re.I)]
    parts, seen = [], set()
    for c in structured or []:
        m = re.match(r"^(.*?\))\.\s*(.+)$", c) or re.match(r"^(.*?)\.\s+([A-Za-zéÉ ]{3,30})$", c)
        name, role = (m.group(1).strip(), m.group(2).strip()) if m else (c.strip(), None)
        key = (name, norm_role(role))
        if key in seen:
            continue
        seen.add(key)
        parts.append({"name": name, "role_as_stated": role, "role_normalized": norm_role(role)})
    if not parts:
        m = re.search(r"/\s*([^/]*benoi[^/]*)$", title, re.I)
        stmt = m.group(1).strip() if m else None
        parts.append(
            {
                "name": "Benoist (as written in title statement)",
                "role_as_stated": stmt,
                "role_normalized": norm_role(stmt),
            }
        )
    conf = (
        "high"
        if structured and re.search(r"\(\s*18(?:13|18)", " ".join(structured))
        else ("medium" if structured else "low")
    )
    if artist == "uncertain-benoist":
        conf = "low"
    rights = _first(item.get("rights"))
    shown_at = _first(item.get("edmIsShownAt")) or f"https://www.europeana.eu/item{item.get('id')}"
    shown_by = _first(item.get("edmIsShownBy"))
    is_drawing = bool(re.search(r"\[dessin\]", title, re.I))
    typ = item.get("type")
    otype = "drawing" if is_drawing else ("book" if typ == "TEXT" else "print")
    place = None
    for v in (item.get("edmPlaceLabelLangAware") or {}).values():
        place = v[0] if v else None
        break
    holder = _first(item.get("dataProvider"))
    r = make_record(
        record_id=f"europeana:{item.get('id')}",
        artist_id=artist,
        participants=parts,
        original_title=title,
        series=series_of(title, desc, " ".join(item.get("dctermsIsPartOf") or [])),
        city=None,
        place=place,
        date_as_stated=_first(item.get("year")) or _first(item.get("dcDate")),
        technique_as_stated=_first(item.get("dcFormat")) or _first(item.get("dctermsMedium")),
        object_type=otype,
        institution=holder,
        accession=_first(item.get("dcIdentifier")) or item.get("id"),
        record_url=shown_at,
        image_url=shown_by,
        rights_statement=rights,
        impression_note="Europeana re-exposes the holder record; Gallica sheets appear here "
        "when Gallica itself blocks bots.",
        attribution_confidence=conf,
        attribution_note=note or ("Creator field names Benoist." if structured else ""),
        source_hit_query=query,
    )
    r["europeana_item_url"] = f"https://www.europeana.eu/item{item.get('id')}"
    return r, None


# ---- Heidelberg (IIIF manifest + METS; the HTML pages sit behind a bot challenge and are not used) ----


def parse_heidelberg_manifest(man: dict, key: str, volume_label: str) -> list[dict]:
    """Volume record + one record per canvas labelled 'Planche N'.  Plate-level credit is NOT in the manifest."""
    attribution_pd = man.get("license")
    authors = next(
        (
            " ".join(m.get("value") or []) if isinstance(m.get("value"), list) else str(m.get("value"))
            for m in man.get("metadata") or []
            if m.get("label") == "Author"
        ),
        "",
    )
    shelf = next(
        (" ".join(m.get("value") or []) for m in man.get("metadata") or [] if m.get("label") == "Shelfmark"), None
    )
    date = next((" ".join(m.get("value") or []) for m in man.get("metadata") or [] if m.get("label") == "Date"), None)
    out = []
    vol_url = f"https://digi.ub.uni-heidelberg.de/diglit/{key}"
    manifest_url = f"https://digi.ub.uni-heidelberg.de/diglit/iiif/{key}/manifest.json"
    out.append(
        make_record(
            record_id=f"heidelberg:{key}",
            artist_id="philippe-benoist",
            participants=[
                {
                    "name": "Benoist, Philippe",
                    "role_as_stated": "Ill. (Author field: " + authors + ")",
                    "role_normalized": "unspecified",
                }
            ],
            original_title=f"Paris dans sa splendeur {volume_label}",
            series="Paris dans sa splendeur",
            volume=volume_label,
            city="Paris",
            country="FR",
            date_as_stated=date,
            object_type="volume",
            institution="Universitätsbibliothek Heidelberg",
            accession=shelf,
            record_url=vol_url,
            iiif_manifest=manifest_url,
            rights_statement=attribution_pd,
            attribution_confidence="medium",
            attribution_note="Title statement: 'dessins et lithographies par MM. "
            "Philippe Benoist [und 17 weitere]'. Benoist is "
            "one of 18 named illustrators; this is NOT a whole-volume attribution to him.",
            source_hit_query="IIIF manifest",
            impression_note="Volume record; plates listed separately.",
        )
    )
    for cv in (man.get("sequences") or [{}])[0].get("canvases") or []:
        label = cv.get("label") or ""
        if not re.match(r"^Planches?\s*\d", label):
            continue
        cid = cv["@id"].rsplit("/", 1)[-1]
        res = ((cv.get("images") or [{}])[0].get("resource")) or {}
        out.append(
            make_record(
                record_id=f"heidelberg:{key}/{cid}",
                artist_id="uncertain-benoist",
                participants=[],
                original_title=f"{label} (plate in Paris dans sa splendeur, {volume_label})",
                series="Paris dans sa splendeur",
                plate_number=re.sub(r"\D", "", label) or None,
                volume=volume_label,
                city="Paris",
                country="FR",
                date_as_stated=date,
                object_type="page_in_book",
                institution="Universitätsbibliothek Heidelberg",
                accession=f"{shelf} / canvas {cid}",
                record_url=f"{vol_url}/{cid}",
                iiif_manifest=manifest_url,
                image_url=res.get("@id"),
                image_width=cv.get("width"),
                image_height=cv.get("height"),
                rights_statement=attribution_pd,
                verification_status="search_hit_only",
                attribution_confidence="low",
                attribution_note="Plate title and artist credit are printed on the page and are not in the "
                "IIIF manifest/METS; the "
                "page HTML/OCR is behind a bot challenge (not bypassed). Volume names 18 illustrators; "
                "Benoist credit for THIS plate is unverified.",
                source_hit_query="IIIF manifest canvases",
            )
        )
    return out


# ---- Internet Archive -------------------------------------------------------------------------------


def parse_ia_item(meta: dict, query: str | None = None) -> tuple[dict | None, str | None]:
    md = meta.get("metadata") or {}
    ident = md.get("identifier")
    if not ident:
        return None, "no_identifier"

    def flat(v):
        return " ; ".join(v) if isinstance(v, list) else str(v or "")

    title, creators = flat(md.get("title")), flat(md.get("creator"))
    desc = flat(md.get("description")) + " " + flat(md.get("subject")) + " " + flat(md.get("contributor"))
    artist, note = classify_benoist(creators + " | " + title)
    if artist is None:
        a2, _ = classify_benoist(desc)
        if a2 in ("philippe-benoist", "felix-benoist"):
            artist, note = a2, "Benoist named only in description/subject."
    ser = series_of(title)
    if artist == "other":
        return None, "other_benoist"
    date_s = flat(md.get("date")) or flat(md.get("year"))
    if artist is None:
        if not ser:
            return None, "no_benoist"
        artist = "uncertain-benoist"
        note = (
            "Series title only; the IA metadata does not name Benoist. Plate-level credits unchecked "
            "(series membership from the project brief, not from this record)."
        )
        conf = "low"
    else:
        conf = "medium" if artist != "uncertain-benoist" else "low"
    # an authority heading in creator can collide with a modern namesake: flag impossible dates
    ym = re.search(r"(\d{4})", date_s)
    if artist == "philippe-benoist" and ym and int(ym.group(1)) > 1930 and not ser:
        note += (
            f" WARNING: date {ym.group(1)} is after the lifetime of Philippe Benoist (1813-1905); likely a namesake."
        )
        conf = "low"
        artist = "uncertain-benoist"
    lic = flat(md.get("licenseurl")) or flat(md.get("rights")) or None
    parts = [
        {"name": c.strip(), "role_as_stated": None, "role_normalized": "unspecified"}
        for c in creators.split(" ; ")
        if re.search(r"benoi", c, re.I)
    ]
    return make_record(
        record_id=f"internet_archive:{ident}",
        artist_id=artist,
        participants=parts,
        original_title=title,
        series=ser,
        date_as_stated=date_s or None,
        object_type="book",
        institution="Internet Archive (uploader's holding)",
        accession=ident,
        record_url=f"https://archive.org/details/{ident}",
        rights_statement=lic,
        attribution_confidence=conf,
        attribution_note=note,
        source_hit_query=query,
        iiif_manifest=None,
    ), None


# ---- Commons ----------------------------------------------------------------------------------------


def parse_commons_pages(payload: dict, category: str, artist_id: str) -> list[dict]:
    out = []
    for page in (payload.get("query") or {}).get("pages", {}).values():
        ii = (page.get("imageinfo") or [{}])[0]
        em = ii.get("extmetadata") or {}
        title = page.get("title", "")
        lic = (em.get("LicenseShortName") or {}).get("value")
        lic_url = (em.get("LicenseUrl") or {}).get("value")
        stmt = " ".join(x for x in (lic, lic_url) if x) or None
        desc = re.sub(r"<[^>]+>", "", (em.get("ImageDescription") or {}).get("value") or "")
        artist_txt = re.sub(r"<[^>]+>", "", (em.get("Artist") or {}).get("value") or "")
        a2, n2 = classify_benoist(artist_txt + " " + desc + " " + title)
        out.append(
            make_record(
                record_id=f"commons:{title}",
                artist_id=artist_id if a2 in (None, artist_id) else (a2 or artist_id),
                participants=[
                    {
                        "name": artist_txt or "(Commons Artist field empty)",
                        "role_as_stated": None,
                        "role_normalized": "unspecified",
                    }
                ],
                original_title=re.sub(r"^File:|\.\w{3,4}$", "", title),
                object_type="print",
                institution="Wikimedia Commons",
                accession=title,
                record_url=ii.get("descriptionurl")
                or "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
                image_url=ii.get("url"),
                image_width=ii.get("width"),
                image_height=ii.get("height"),
                rights_statement=stmt,
                series=series_of(title, desc),
                attribution_confidence="low",
                attribution_note=f"In Commons category '{category}'. Category membership is not an "
                "attribution; check Artist/description. " + n2,
                source_hit_query=f"Category:{category}",
                date_as_stated=(em.get("DateTimeOriginal") or {}).get("value"),
            )
        )
    return out


def bnf_authority_count(html: str) -> int | None:
    m = re.search(r"auteur\s*\((\d+)\)", html or "")
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------------------------------
# Polite HTTP (reuses collect_benoist.Client bookkeeping: dead hosts, 429 counters)
# --------------------------------------------------------------------------------------------------


class PoliteClient(Client):
    """collect_benoist.Client plus raw-text fetches (BnF SRU is XML) and the project User-Agent."""

    def fetch(self, url: str, accept: str = "*/*", as_json: bool = True, retries: int = 1):
        host = urllib.parse.urlsplit(url).netloc
        if host in self.dead:
            raise Blocked(f"{host}: {self.dead[host]}")
        for attempt in range(retries + 1):
            wait = self.last.get(host, 0) + HOST_GAP.get(host, MIN_GAP) - time.time()
            if wait > 0:
                time.sleep(wait)
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    body = r.read().decode("utf-8", "replace")
                self.last[host] = time.time()
                self.calls[host] = self.calls.get(host, 0) + 1
                if body.lstrip()[:15].lower().startswith("<!doctype html") and re.search(
                    r"not a bot|Just a moment|captcha", body, re.I
                ):
                    self.dead[host + "|html"] = "bot challenge page (HTTP 200)"
                    raise Blocked(f"{host}: bot challenge page (HTTP 200)")
                return json.loads(body) if as_json else body
            except urllib.error.HTTPError as e:
                self.last[host] = time.time()
                if e.code in (429, 403, 401, 410, 451):
                    if e.code == 429 and attempt < retries:
                        time.sleep(20)
                        continue
                    self.dead[host] = f"HTTP {e.code}"
                    raise Blocked(f"{host}: HTTP {e.code}") from e
                if e.code == 404:
                    return {} if as_json else ""
                if attempt == retries:
                    raise Blocked(f"{host}: HTTP {e.code}") from e
                time.sleep(4)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
                self.last[host] = time.time()
                if attempt == retries:
                    raise Blocked(f"{host}: {type(e).__name__}: {e}"[:200]) from e
                time.sleep(4)
        raise Blocked(f"{host}: gave up")


def qs(**kw) -> str:
    return urllib.parse.urlencode(kw)


def new_cov() -> dict:
    return {
        "queries": [],
        "pages_walked": 0,
        "hits_total_reported_by_source": {},
        "records_kept": 0,
        "blocked": [],
        "notes": [],
        "dropped": {},
    }


def drop(cov: dict, reason: str | None) -> None:
    if reason:
        cov["dropped"][reason] = cov["dropped"].get(reason, 0) + 1


# --------------------------------------------------------------------------------------------------
# Source runners
# --------------------------------------------------------------------------------------------------

BNF_QUERIES = (
    'bib.author all "Benoist Philippe 1813"',
    'bib.author all "Ph. Benoist"',
    'bib.author all "Benoist Philippe"',
    'bib.author all "Philippe Benoist"',
    'bib.author all "Benoist Félix"',
    'bib.author all "Félix Benoist"',
    'bib.author all "Benoist" and bib.doctype any "i"',
    'bib.title all "Benoist del lith"',
)
BNF_PAGE = 50
BNF_MAX_PAGES = 30


def run_bnf(c: PoliteClient) -> tuple[list[dict], dict]:
    cov, out, seen = new_cov(), [], set()
    # authority page: linked-notice count as displayed by the catalogue (HTML)
    try:
        html = c.fetch("https://catalogue.bnf.fr/ark:/12148/cb14962134k", "text/html", as_json=False)
        cov["hits_total_reported_by_source"]["authority_cb14962134k_linked_as_auteur"] = bnf_authority_count(html)
        cov["queries"].append("GET https://catalogue.bnf.fr/ark:/12148/cb14962134k")
    except Blocked as e:
        cov["blocked"].append(str(e))
    for query in BNF_QUERIES:
        cov["queries"].append("SRU " + query)
        pos, total = 1, None
        while pos and cov["pages_walked"] < 400:
            url = "https://catalogue.bnf.fr/api/SRU?" + qs(
                version="1.2",
                operation="searchRetrieve",
                query=query,
                maximumRecords=BNF_PAGE,
                startRecord=pos,
                recordSchema="unimarcxchange",
            )
            try:
                body = c.fetch(url, "text/xml", as_json=False, retries=3)
            except Blocked as e:
                cov["blocked"].append(f"SRU '{query}' at startRecord={pos}: {e}")
                break
            cov["pages_walked"] += 1
            try:
                total, nxt, recs, diag = parse_bnf_sru(body)
            except ET.ParseError as e:
                cov["blocked"].append(f"SRU '{query}' unparsable XML: {e}")
                break
            if diag and not recs:
                cov["notes"].append(f"SRU '{query}': {diag}")
            for r in recs:
                rec, why = parse_bnf_record(r, query)
                if rec is None:
                    drop(cov, why)
                elif rec["record_id"] not in seen:
                    seen.add(rec["record_id"])
                    out.append(rec)
            pos = nxt if nxt and recs else 0
        cov["hits_total_reported_by_source"][query] = total
    cov["records_kept"] = len(out)
    cov["notes"].append(
        "Attribution is taken from the BnF authority id in UNIMARC 7xx $3 (14962134 Philippe, 11891235 "
        "Félix); text-only matches are kept as medium/low. Other Benoist authority ids are dropped."
    )
    return out, cov


def run_gallica(c: PoliteClient) -> dict:
    cov = new_cov()
    url = "https://gallica.bnf.fr/SRU?" + qs(
        version="1.2", operation="searchRetrieve", query='dc.creator all "Benoist Philippe"', maximumRecords=1
    )
    cov["queries"].append('SRU dc.creator all "Benoist Philippe"')
    try:
        c.fetch(url, "text/xml", as_json=False)
        cov["notes"].append("Gallica SRU answered; not walked here, BnF/Europeana already re-expose the records.")
    except Blocked as e:
        cov["blocked"].append(
            f"gallica.bnf.fr SRU: {e}; not bypassed. Gallica sheets are covered through Europeana (BnF provider)."
        )
    return cov


EUROPEANA_QUERIES = (
    'who:"Benoist, Philippe"',
    'who:"Benoist, Félix"',
    '"Philippe Benoist"',
    '"Félix Benoist"',
    '"Ph. Benoist"',
    '"F. Benoist"',
    "who:Benoist",
    '"Benoist del"',
    "Benoist AND lithographe",
    "Benoist AND lithographer",
    'Benoist AND "Paris dans sa splendeur"',
    'Benoist AND "Promenade dans Paris"',
    'Benoist AND "Paris et ses environs"',
    'Benoist AND "Vues de Paris"',
    'Benoist AND "Rome dans sa grandeur"',
    'Benoist AND "España artística"',
    "Benoist AND Villaamil",
    "Benoist AND Lemercier",
    "Benoist AND Jacottet",
    "Benoist AND Bayot",
)
EUROPEANA_MAX_PAGES_PER_QUERY = 40


def run_europeana(c: PoliteClient) -> tuple[list[dict], dict]:
    cov, out, seen_ids = new_cov(), [], set()
    cov["unique_items_seen"] = 0
    for query in EUROPEANA_QUERIES:
        cov["queries"].append(query)
        cursor, pages = "*", 0
        while cursor and pages < EUROPEANA_MAX_PAGES_PER_QUERY:
            url = "https://api.europeana.eu/record/v2/search.json?" + qs(
                wskey=EUROPEANA_KEY, query=query, rows=100, cursor=cursor, profile="rich"
            )
            try:
                d = c.fetch(url, "application/json")
            except Blocked as e:
                cov["blocked"].append(f"'{query}' page {pages + 1}: {e}")
                break
            pages += 1
            cov["pages_walked"] += 1
            cov["hits_total_reported_by_source"].setdefault(query, d.get("totalResults"))
            for it in d.get("items", []):
                if it.get("id") in seen_ids:
                    continue
                seen_ids.add(it.get("id"))
                cov["unique_items_seen"] += 1
                rec, why = parse_europeana_item(it, query)
                if rec is None:
                    drop(cov, why)
                else:
                    out.append(rec)
            cursor = d.get("nextCursor") if d.get("items") else None
        if cursor and pages >= EUROPEANA_MAX_PAGES_PER_QUERY:
            cov["notes"].append(f"'{query}': stopped at {pages} pages (cap); more results exist.")
    cov["records_kept"] = len(out)
    cov["notes"].append(
        "Cursor paging (not start=) so results past 1000 are walked. Image URLs are kept only when the "
        "rights URL is CC0/PDM/CC BY(-SA); rightsstatements NoC-OKLR (Gallica) is link_only."
    )
    return out, cov


def run_heidelberg(c: PoliteClient) -> tuple[list[dict], dict]:
    cov, out = new_cov(), []
    for key, label in (("audiganne1861bd1", "Band 1"), ("audiganne1861bd2", "Band 2")):
        for what, url in (("manifest", f"https://digi.ub.uni-heidelberg.de/diglit/iiif/{key}/manifest.json"),):
            cov["queries"].append(f"GET {url}")
            try:
                man = c.fetch(url, "application/json")
            except Blocked as e:
                cov["blocked"].append(f"{key} {what}: {e}")
                continue
            cov["pages_walked"] += 1
            recs = parse_heidelberg_manifest(man, key, label)
            n_canvas = len((man.get("sequences") or [{}])[0].get("canvases") or [])
            cov["hits_total_reported_by_source"][key] = {"canvases": n_canvas, "plates": len(recs) - 1}
            out.extend(recs)
    cov["blocked"].append(
        "digi.ub.uni-heidelberg.de HTML pages (/diglit/<id>/<page>, incl. OCR and page text) answer HTTP 200 "
        "with a bot-challenge ('Making sure you're not a bot!'); not bypassed. Only the published IIIF "
        "manifest was read. Plate-level 'del./lith.' credits therefore could NOT be read."
    )
    cov["records_kept"] = len(out)
    cov["notes"].append(
        "0 plates have a Benoist credit that could be established from page text or metadata; plate records are "
        "enumerated as uncertain-benoist / search_hit_only and must not be promoted."
    )
    return out, cov


IA_QUERIES = (
    (
        "creator",
        '(creator:("Benoist, Philippe") OR creator:("Philippe Benoist") OR creator:("Benoist, Félix") '
        'OR creator:("Félix Benoist") OR creator:("Benoist, Felix") OR creator:("Ph. Benoist"))',
    ),
    ("series-paris", "title:(paris AND splendeur)"),
    ("series-promenade", "title:(promenade AND paris AND environs)"),
    ("series-espana", "title:(espana AND artistica AND monumental)"),
    ("series-rome", "title:(rome AND grandeur AND (dans OR sa))"),
    ("text", 'Benoist AND (lithographies OR "del. et lith." OR "Ph. Benoist") AND mediatype:texts'),
    ("text-villaamil", "Benoist AND Villaamil"),
)


def run_ia(c: PoliteClient) -> tuple[list[dict], dict]:
    cov, out, idents = new_cov(), [], {}
    for name, query in IA_QUERIES:
        cov["queries"].append(f"advancedsearch[{name}] {query}")
        page = 1
        while page <= 5:
            url = "https://archive.org/advancedsearch.php?" + qs(
                q=query, rows=100, page=page, output="json", **{"fl[]": "identifier"}
            )
            try:
                d = c.fetch(url, "application/json")
            except Blocked as e:
                cov["blocked"].append(f"advancedsearch[{name}]: {e}")
                break
            cov["pages_walked"] += 1
            resp = d.get("response") or {}
            cov["hits_total_reported_by_source"][name] = resp.get("numFound")
            docs = resp.get("docs") or []
            for dd in docs:
                idents.setdefault(dd["identifier"], name)
            if page * 100 >= (resp.get("numFound") or 0) or not docs:
                break
            page += 1
    cov["unique_items_seen"] = len(idents)
    # metadata API for every hit; the parser keeps only creator/text hits and known-series titles
    for ident, name in idents.items():
        try:
            meta = c.fetch(f"https://archive.org/metadata/{ident}", "application/json")
        except Blocked as e:
            cov["blocked"].append(f"metadata/{ident}: {e}")
            continue
        cov["pages_walked"] += 1
        rec, why = parse_ia_item(meta, name)
        if rec is None:
            drop(cov, why)
        else:
            out.append(rec)
    cov["records_kept"] = len(out)
    cov["notes"].append(
        "IA metadata API read for each advancedsearch hit; items without Benoist in creator/title/description "
        "are dropped unless the title is one of the known series (then kept as uncertain-benoist)."
    )
    return out, cov


def run_hathi_google(c: PoliteClient) -> dict:
    cov = new_cov()
    tries = (
        (
            "hathitrust catalogue",
            "https://catalog.hathitrust.org/Search/Home?" + qs(lookfor="Benoist Philippe", type="author"),
        ),
        (
            "hathitrust full-text/babel",
            "https://babel.hathitrust.org/cgi/ls?" + qs(q1="Benoist Paris dans sa splendeur", a="srchls"),
        ),
        (
            "google books api",
            "https://www.googleapis.com/books/v1/volumes?" + qs(q='inauthor:"Philippe Benoist"', maxResults=40),
        ),
    )
    for name, url in tries:
        cov["queries"].append(f"{name}: {url}")
        host = urllib.parse.urlsplit(url).netloc
        try:
            c.fetch(url, "application/json", as_json=url.startswith("https://www.googleapis"))
            cov["notes"].append(f"{name}: answered but is not parsed by this script.")
        except Blocked as e:
            cov["blocked"].append(f"{name}: {e}")
            c.dead.pop(host, None)  # let the next probe on the same host be tried independently
    cov["notes"].append("No catalogue records collected from HathiTrust or Google Books in this run; see blocked.")
    return cov


COMMONS_CATEGORIES = (("Philippe Benoist", "philippe-benoist"), ("Félix Benoist", "felix-benoist"))


def run_commons(c: PoliteClient) -> tuple[list[dict], dict]:
    cov, out = new_cov(), []
    for cat, artist in COMMONS_CATEGORIES:
        cov["queries"].append(f"Category:{cat} (file members, then imageinfo|extmetadata)")
        titles, cont = [], None
        while True:
            params = dict(
                action="query",
                list="categorymembers",
                cmtitle=f"Category:{cat}",
                cmlimit=500,
                cmtype="file",
                format="json",
            )
            if cont:
                params["cmcontinue"] = cont
            try:
                d = c.fetch("https://commons.wikimedia.org/w/api.php?" + qs(**params), "application/json")
            except Blocked as e:
                cov["blocked"].append(f"Category:{cat}: {e}")
                break
            cov["pages_walked"] += 1
            titles += [m["title"] for m in (d.get("query") or {}).get("categorymembers", [])]
            cont = (d.get("continue") or {}).get("cmcontinue")
            if not cont:
                break
        cov["hits_total_reported_by_source"][f"Category:{cat}"] = len(titles)
        for i in range(0, len(titles), 40):
            chunk = titles[i : i + 40]
            try:
                d = c.fetch(
                    "https://commons.wikimedia.org/w/api.php?"
                    + qs(
                        action="query",
                        titles="|".join(chunk),
                        prop="imageinfo",
                        iiprop="url|size|extmetadata",
                        format="json",
                    ),
                    "application/json",
                )
            except Blocked as e:
                cov["blocked"].append(f"imageinfo for {cat} [{i}:{i + 40}]: {e}")
                break
            cov["pages_walked"] += 1
            out += parse_commons_pages(d, cat, artist)
    cov["records_kept"] = len(out)
    return out, cov


# --------------------------------------------------------------------------------------------------
# Known index (repo files + other branches) and assembly
# --------------------------------------------------------------------------------------------------

KNOWN_FILES = ("data/curation/benoist-harvest-v1.json", "book/benoist-sheets.json", "book/benoist-registry.json")
KNOWN_GLOBS = ("research/collections/benoist*.json", "data/catalog/works/*benoist*.json")


def build_known(root: Path = ROOT, branches: bool = True) -> tuple[set[str], dict]:
    keys, stats = set(), {}
    paths = [root / p for p in KNOWN_FILES]
    for g in KNOWN_GLOBS:
        paths += sorted(root.glob(g))
    paths += (
        sorted((root / "data" / "research" / "benoist").glob("*.json"))
        if (root / "data/research/benoist").exists()
        else []
    )
    for p in paths:
        if p.name == OUT.name:
            continue
        try:
            ks = extract_keys(p.read_text("utf-8"))
        except OSError:
            continue
        stats[str(p.relative_to(root))] = len(ks)
        keys |= ks
    if branches:
        try:
            refs = subprocess.run(
                ["git", "-C", str(root), "for-each-ref", "--format=%(refname:short)", "refs/remotes/origin"],
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout.split()
            for ref in refs:
                names = subprocess.run(
                    ["git", "-C", str(root), "ls-tree", "-r", "--name-only", ref],
                    capture_output=True,
                    text=True,
                    timeout=30,
                ).stdout.splitlines()
                for n in names:
                    if n == str(OUT.relative_to(root)):
                        continue  # never treat our own earlier output as prior knowledge
                    if re.search(r"benoist|ledger", n, re.I) and n.endswith((".json", ".md", ".csv")):
                        blob = subprocess.run(
                            ["git", "-C", str(root), "show", f"{ref}:{n}"], capture_output=True, text=True, timeout=30
                        ).stdout
                        ks = extract_keys(blob)
                        if ks:
                            stats[f"{ref}:{n}"] = len(ks)
                            keys |= ks
        except (OSError, subprocess.SubprocessError):
            stats["branches"] = "git unavailable"
    return keys, stats


def summarize(records: list[dict], per_source: dict) -> dict:
    """Per-source kept / new / new_unique (first of its duplicate group among unknown records) + artist/type split."""
    first_seen: dict[str, str] = {}
    for r in records:
        if not r["known_in_repo"]:
            first_seen.setdefault(r["duplicate_hint"], r["record_id"])
    by_src: dict[str, dict] = {}
    for r in records:
        s = r["record_id"].split(":", 1)[0]
        d = by_src.setdefault(
            s, {"kept": 0, "known_in_repo": 0, "new": 0, "new_unique": 0, "by_artist": {}, "by_object_type": {}}
        )
        d["kept"] += 1
        d["known_in_repo"] += r["known_in_repo"]
        d["new"] += not r["known_in_repo"]
        d["new_unique"] += (not r["known_in_repo"]) and first_seen.get(r["duplicate_hint"]) == r["record_id"]
        d["by_artist"][r["artist_id"]] = d["by_artist"].get(r["artist_id"], 0) + 1
        d["by_object_type"][r["object_type"]] = d["by_object_type"].get(r["object_type"], 0) + 1
    for s, d in by_src.items():
        per_source.setdefault(s, {})["summary"] = d
    return by_src


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default="bnf,gallica,europeana,heidelberg,ia,hathi_google,commons")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--no-branches", action="store_true", help="do not read other git branches for the known index")
    args = ap.parse_args(argv)
    want = set(args.only.split(","))
    c = PoliteClient()
    records, per_source = [], {}

    def go(name, fn):
        if name not in want:
            return
        t0 = time.time()
        try:
            res = fn(c)
        except Blocked as e:
            per_source[name] = {**new_cov(), "blocked": [str(e)]}
            return
        if isinstance(res, tuple):
            recs, cov = res
            records.extend(recs)
        else:
            cov = res
        cov["seconds"] = round(time.time() - t0)
        per_source[name] = cov
        print(
            f"{name}: kept={cov['records_kept']} pages={cov['pages_walked']} blocked={len(cov['blocked'])}",
            file=sys.stderr,
        )

    go("bnf", run_bnf)
    go("gallica", run_gallica)
    go("europeana", run_europeana)
    go("heidelberg", run_heidelberg)
    go("ia", run_ia)
    go("hathi_google", run_hathi_google)
    go("commons", run_commons)

    # one record per source id
    uniq = {}
    for r in records:
        uniq.setdefault(r["record_id"], r)
    records = list(uniq.values())
    known, known_stats = build_known(branches=not args.no_branches)
    n_known = mark_known(records, known)
    summarize(records, per_source)
    groups = group_duplicates(records)
    doc = {
        "version": 1,
        "source": "bnf+europeana+heidelberg+internet_archive+hathitrust+googlebooks+commons",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "coverage": {
            "queries": [f"{k}: {q}" for k, v in per_source.items() for q in v.get("queries", [])],
            "pages_walked": sum(v.get("pages_walked", 0) for v in per_source.values()),
            "hits_total_reported_by_source": {
                k: v.get("hits_total_reported_by_source", {}) for k, v in per_source.items()
            },
            "records_kept": len(records),
            "blocked": [f"{k}: {b}" for k, v in per_source.items() for b in v.get("blocked", [])],
            "notes": [f"{k}: {n}" for k, v in per_source.items() for n in v.get("notes", [])],
            "per_source": per_source,
            "known_in_repo_count": n_known,
            "known_index_sources": known_stats,
            "duplicate_groups_with_more_than_one_record": sum(1 for v in groups.values() if len(v) > 1),
            "ua": UA,
        },
        "records": records,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(f"wrote {args.out}: {len(records)} records", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
