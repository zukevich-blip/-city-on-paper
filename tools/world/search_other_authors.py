#!/usr/bin/env python3
"""Search open museum APIs for architectural / city prints by authors OTHER than Philippe/Felix Benoist.

Output: data/research/authors/other-authors-v1.json (record schema: data/research/benoist/SCHEMA.md, plus
`author_name`; artist_id is a slug of the author).  Standard library only, re-runnable, resumable.

Sources: Cleveland Open Access, Art Institute of Chicago, Met Open Access, NGA open data (CSV, metadata
only), Rijksmuseum (Linked Art), Europeana, Library of Congress (rights are NOT cleared: rights_pending),
Wikimedia Commons (429 is recorded, never bypassed), Paris Musees (public site + IIIF manifest, reuses
tools.world.search_parismusees).

Rules: nothing but metadata is requested, never an image file; >= 1.2 s between requests per host; HTTP 403/429
are written to coverage.blocked and the host is abandoned; image_url is kept only when rights_status is
open_confirmed (the source itself states an open licence for the file); unknown is null.  Arnout/Benois/etc. are
matched by exact name forms; every Benoist name is rejected for the Benois family.

    python3 -m tools.world.search_other_authors --cache-dir /tmp/oa-cache --only cleveland,aic,met
    python3 -m tools.world.search_other_authors --cache-dir /tmp/oa-cache --merge     # build the output file
Each source writes <cache-dir>/result-<source>.json when finished (resume: finished sources are skipped,
HTTP responses are cached on disk).
"""
# ruff: noqa: E501

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "research" / "authors" / "other-authors-v1.json"
UA = "CityOnPaperResearch/0.9 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)"
MIN_GAP = 1.2
HOST_GAP = {"commons.wikimedia.org": 2.5, "www.loc.gov": 3.0}
EUROPEANA_KEY = os.environ.get("EUROPEANA_API_KEY", "api2demo")
SOURCES = ("cleveland", "aic", "met", "nga", "rijks", "europeana", "loc", "commons", "parismusees")

# --------------------------------------------------------------------------------------------------
# Authors.  aliases are matched against the accent/punctuation-folded creator string (substring).
# --------------------------------------------------------------------------------------------------


def A(slug, name, aliases, queries=None, role="designer", cities=()):
    return {"slug": slug, "name": name, "aliases": aliases, "queries": queries or [name], "cities": cities}


AUTHORS = [
    A(
        "louis-jules-arnout",
        "Louis-Jules Arnout",
        ["louis jules arnout", "arnout louis jules", "arnout louis"],
        ["Louis-Jules Arnout", "Arnout lithographe Paris"],
    ),
    A(
        "nicolas-marie-joseph-chapuy",
        "Nicolas-Marie-Joseph Chapuy",
        ["chapuy nicolas", "nicolas marie joseph chapuy", "nicolas chapuy", "chapuy n m j", "chapuy"],
        ["Chapuy"],
    ),
    A(
        "thomas-shotter-boys",
        "Thomas Shotter Boys",
        ["shotter boys", "boys thomas shotter", "boys thomas s", "t shotter boys"],
        ["Thomas Shotter Boys", "Shotter Boys"],
    ),
    A(
        "giuseppe-zocchi",
        "Giuseppe Zocchi",
        ["giuseppe zocchi", "zocchi giuseppe"],
        ["Giuseppe Zocchi", "Zocchi Firenze vedute"],
    ),
    A(
        "giovanni-battista-piranesi",
        "Giovanni Battista Piranesi",
        [
            "giovanni battista piranesi",
            "piranesi giovanni battista",
            "giambattista piranesi",
            "piranesi giambattista",
            "gian battista piranesi",
            "giovanni b piranesi",
            "piranesi gian battista",
        ],
        ["Giovanni Battista Piranesi", "Piranesi Vedute di Roma"],
    ),
    A(
        "adolphe-rouargue",
        "Adolphe Rouargue",
        ["adolphe rouargue", "rouargue adolphe", "rouargue freres", "rouargue"],
        ["Adolphe Rouargue", "Rouargue"],
    ),
    A(
        "francois-alexandre-pernot",
        "François-Alexandre Pernot",
        ["francois alexandre pernot", "pernot francois alexandre", "pernot francois", "pernot f a"],
        ["François-Alexandre Pernot", "Pernot"],
    ),
    A(
        "jean-jacques-champin",
        "Jean-Jacques Champin",
        ["jean jacques champin", "champin jean jacques", "champin j j", "champin jean"],
        ["Jean-Jacques Champin", "Champin"],
    ),
    A(
        "eugene-ciceri",
        "Eugène Cicéri",
        ["eugene ciceri", "ciceri eugene", "ciceri e"],
        ["Eugène Cicéri", "Ciceri Eugene"],
    ),
    A("charles-meryon", "Charles Meryon", ["charles meryon", "meryon charles", "meryon"], ["Charles Meryon", "Meryon"]),
    A(
        "canaletto",
        "Canaletto (Giovanni Antonio Canal)",
        ["canaletto", "giovanni antonio canal", "canal giovanni antonio", "antonio canal"],
        ["Canaletto", "Giovanni Antonio Canal"],
    ),
    A(
        "francesco-guardi",
        "Francesco Guardi",
        ["francesco guardi", "guardi francesco"],
        ["Francesco Guardi", "Guardi Venezia"],
    ),
    A("giuseppe-vasi", "Giuseppe Vasi", ["giuseppe vasi", "vasi giuseppe"], ["Giuseppe Vasi", "Vasi Roma"]),
    A(
        "vasily-sadovnikov",
        "Vasily Sadovnikov",
        [
            "sadovnikov",
            "sadovnikov vasily",
            "sadovnikov vasilij",
            "sadovnikov vasili",
            "sadovnikov vasilii",
            "садовников",
        ],
        ["Sadovnikov", "Vasily Sadovnikov"],
    ),
    A("karl-beggrov", "Karl Beggrov", ["beggrov", "begrov", "beggrow", "беггров"], ["Beggrov", "Beggrow Karl"]),
    A(
        "fyodor-alekseev",
        "Fyodor Alekseev",
        [
            "fedor alekseev",
            "fyodor alekseev",
            "feodor alekseev",
            "fedor alexeev",
            "fyodor alexeyev",
            "fedor alekseyev",
            "alekseev fedor",
            "alekseev fyodor",
            "alexeev fedor",
            "alexeyev fedor",
            "алексеев федор",
        ],
        ["Fedor Alekseev", "Fyodor Alekseyev", "Alexeev Fedor"],
    ),
    A(
        "alexandre-benois",
        "Alexandre Benois (Aleksandr Benua)",
        [
            "alexandre benois",
            "benois alexandre",
            "alexander benois",
            "aleksandr benua",
            "benois aleksandr",
            "benois alexandr",
            "alexandre nikolaevich benois",
            "benois alexander",
        ],
        ["Alexandre Benois", "Alexander Benois", "Aleksandr Benua"],
    ),
    A(
        "albert-benois",
        "Albert Benois (Albert Nikolaevich Benois)",
        ["albert benois", "benois albert", "albert nikolaevich benois", "albert benua"],
        ["Albert Benois", "Albert Nikolaevich Benois"],
    ),
    A(
        "nicolas-benois",
        "Nikolai Leontievich Benois (architect)",
        [
            "nicolas benois",
            "nikolai benois",
            "nicolai benois",
            "benois nikolai",
            "benois nicolas",
            "nikolay benois",
            "nikolai leontievich benois",
            "nikolai benua",
        ],
        ["Nikolai Benois architect", "Nicolas Benois"],
    ),
    A(
        "thomas-hosmer-shepherd",
        "Thomas Hosmer Shepherd",
        ["thomas hosmer shepherd", "shepherd thomas hosmer", "shepherd thomas h"],
        ["Thomas Hosmer Shepherd"],
    ),
    A(
        "bernardo-bellotto",
        "Bernardo Bellotto",
        ["bernardo bellotto", "bellotto bernardo", "bellotto"],
        ["Bernardo Bellotto"],
    ),
    A(
        "luca-carlevarijs",
        "Luca Carlevarijs",
        ["luca carlevarijs", "carlevarijs luca", "carlevaris luca", "luca carlevaris"],
        ["Luca Carlevarijs"],
    ),
    A("michele-marieschi", "Michele Marieschi", ["michele marieschi", "marieschi michele"], ["Michele Marieschi"]),
    A(
        "giovanni-battista-falda",
        "Giovanni Battista Falda",
        ["giovanni battista falda", "falda giovanni battista", "giovan battista falda"],
        ["Giovanni Battista Falda"],
    ),
    A("thomas-malton", "Thomas Malton", ["thomas malton", "malton thomas"], ["Thomas Malton"]),
    A("thomas-girtin", "Thomas Girtin", ["thomas girtin", "girtin thomas"], ["Thomas Girtin"]),
    A("hubert-robert", "Hubert Robert", ["hubert robert", "robert hubert"], ["Hubert Robert"]),
    A("israel-silvestre", "Israël Silvestre", ["israel silvestre", "silvestre israel"], ["Israël Silvestre"]),
    A("jacques-rigaud", "Jacques Rigaud", ["jacques rigaud", "rigaud jacques"], ["Jacques Rigaud"]),
]
AUTHOR_BY_SLUG = {a["slug"]: a for a in AUTHORS}
# Disambiguation: names that look like a listed author but are someone else.
EXCLUDE = {
    "giovanni-battista-piranesi": ["francesco piranesi", "pietro piranesi", "piranesi francesco", "laurent piranesi"],
    "canaletto": ["bellotto"],
    "eugene-ciceri": ["pierre luc charles ciceri"],
    "alexandre-benois": ["benoist"],
    "albert-benois": ["benoist"],
    "nicolas-benois": ["benoist"],
}


# --------------------------------------------------------------------------------------------------
# Pure helpers (unit-tested, no network)
# --------------------------------------------------------------------------------------------------


def fold(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9а-яё]+", " ", s).strip()


def match_author(creators: list[str]) -> tuple[dict, str] | None:
    """Return (author, matched creator string) for the first creator that names a listed author, else None.
    Bellotto is tried before Canaletto, 'Benoist' never matches a Benois."""
    folded = [(c, " " + fold(c) + " ") for c in creators if c]
    order = sorted(AUTHORS, key=lambda a: a["slug"] != "bernardo-bellotto")
    for a in order:
        for raw, f in folded:
            if any(x in f for x in EXCLUDE.get(a["slug"], [])):
                continue
            for al in a["aliases"]:
                if (" " + al + " ") in f or (len(al) > 12 and al in f):
                    return a, raw
    return None


CITY_RES = (
    ("Paris", r"\bparis\b|\bparigi\b"),
    ("Rome", r"\brome\b|\broma\b|\brom\b|\broman\b|\bromani?\b|\bromane\b"),
    ("Venice", r"\bvenice\b|\bvenezia\b|\bvenise\b|\bvenedig\b|\bvenetian\b"),
    ("Florence", r"\bflorence\b|\bfirenze\b|\bflorenz\b"),
    ("London", r"\blondon\b|\blondres\b"),
    ("Nantes", r"\bnantes\b"),
    (
        "Saint Petersburg",
        r"\bst\.? petersburg\b|\bsaint petersburg\b|\bsaint petersbourg\b|\bpetersburg\b|\bpetersbourg\b|\bleningrad\b|\bsankt peterburg\b|\bnevsky\b|\bneva\b|петербург|петроград",
    ),
    ("Moscow", r"\bmoscow\b|\bmoscou\b|\bmoskva\b|\bkremlin\b|москв"),
    ("Naples", r"\bnaples\b|\bnapoli\b"),
    ("Pompeii", r"\bpompei\b|\bpompeii\b|\bpompeji\b"),
    ("Dresden", r"\bdresden\b|\bdresde\b"),
    ("Warsaw", r"\bwarsaw\b|\bvarsovie\b|\bwarszawa\b"),
)
BUILDING_RES = (
    r"notre[- ]dame",
    r"\blouvre\b",
    r"tuileries",
    r"palais[- ]royal",
    r"\bmadeleine\b",
    r"pantheon|panthéon",
    r"hôtel de ville|hotel de ville",
    r"sainte[- ]chapelle",
    r"\bpont (?:neuf|royal|des arts|au change|saint[- ]michel|d'iéna|d'austerlitz)\b",
    r"champs[- ]elys[ée]es",
    r"place (?:vend[oô]me|de la concorde|de la bastille)",
    r"colosseo|colosseum|coliseum|colisée",
    r"foro romano|forum romanum|roman forum|campo vaccino",
    r"campidoglio|capitol(?:ine)?",
    r"san pietro|st\.? peter'?s|saint[- ]pierre|vatican|vaticano",
    r"fontana di trevi|trevi",
    r"castel sant'?angelo",
    r"piazza (?:navona|di spagna|del popolo|san marco)",
    r"ponte vecchio",
    r"palazzo (?:pitti|vecchio|ducale)",
    r"santa maria del fiore|duomo",
    r"rialto",
    r"grand canal|canal grande|canalazzo",
    r"san marco|saint[- ]marc",
    r"santa maria della salute|\bsalute\b",
    r"westminster|st\.? paul'?s|tower of london|\bthames\b|london bridge|waterloo bridge",
    r"admiralty|admiralteysk\w+|адмиралтей\w+",
    r"winter palace|зимн\w+ дворец",
    r"hermitage|эрмитаж",
    r"kazan(?:sky)? cathedral|казанск\w+",
    r"isaac'?s? cathedral|исаакиев\w+",
    r"peter and paul|петропавловск\w+",
    r"red square|красн\w+ площад\w+",
    r"pantheon of agrippa",
    r"arch of (?:titus|constantine|septimius severus)",
    r"temple of (?:isis|vesta|saturn|jupiter)",
    r"villa (?:borghese|medici|albani)",
    r"palatine|palatino",
    r"cathédrale|cathedrale|cathedral",
    r"piazza della signoria",
    r"palais du luxembourg|luxembourg",
    r"\binvalides\b",
    r"\bbourse\b",
    r"\bpont\b",
)


def detect_geo(*texts: str | None) -> tuple[str | None, str | None, str]:
    """(city, place, geo_confidence) read from the literal title/series text.  Never inferred from the author."""
    flat = " ".join(t for t in texts if t)
    low = unicodedata.normalize("NFC", flat.lower())
    city = None
    for name, rx in CITY_RES:
        if re.search(rx, low):
            city = name
            break
    place = None
    for rx in BUILDING_RES:
        m = re.search(rx, low)
        if m:
            place = flat[m.start() : m.end()]
            break
    if place:
        return city, place, "building"
    if city:
        return city, None, "city"
    return None, None, "unknown"


SERIES_RES = (
    (r"vedute di roma", "Vedute di Roma"),
    (r"antichit[aà] romane", "Le Antichità Romane"),
    (r"carceri", "Carceri d'invenzione"),
    (r"vedute di firenze|vedute delle principali contrade|scelta di xxiv vedute", "Scelta di XXIV vedute (Firenze)"),
    (r"magnificenze di roma|vedute di roma antica", "Magnificenze di Roma"),
    (r"picturesque views (?:in|of) paris|\bboys\b.*paris", "Picturesque Views in Paris"),
    (r"original views of london", "Original Views of London as it is"),
    (r"eaux[- ]fortes sur paris|etchings of paris", "Eaux-fortes sur Paris"),
    (r"paris dans sa splendeur", "Paris dans sa splendeur"),
    (r"vues pittoresques", "Vues pittoresques"),
    (r"monuments? de paris|paris moderne|paris historique|paris pittoresque", "Paris (monuments)"),
    (r"la france monumentale|voyages pittoresques", "Voyages pittoresques"),
    (r"vedute di venezia|prospectus magni canalis|vedute altre prese da i luoghi", "Vedute di Venezia"),
    (r"l'architecture moderne|architecture moderne", "Architecture moderne"),
    (r"views of paris", "Views of Paris"),
    (r"sketches? (?:in|of) st\.? petersburg|vues de saint[- ]p[eé]tersbourg", "Views of St Petersburg"),
)


def detect_series(*texts: str | None) -> str | None:
    low = " ".join(t for t in texts if t).lower()
    for rx, name in SERIES_RES:
        if re.search(rx, low):
            return name
    return None


def duplicate_hint(title: str | None, series: str | None, plate: str | None, author_slug: str) -> str | None:
    t = fold(title)
    t = re.sub(r"\b(?:plate|pl|tav|tavola|no|n)\s*\d+\b", "", t).strip()
    if not t:
        return None
    return f"{author_slug}|{t}|{fold(series)}|{plate or ''}"


OPEN_RIGHTS_RE = re.compile(
    r"publicdomain/(?:zero|mark)|creativecommons\.org/licenses/by(?:-sa)?/|rightsstatements.org/vocab/NoC-OKLR/?$|^cc0|\bcc0\b|public domain|\bcc by(?:-sa)?\b",
    re.I,
)
NOT_OPEN_RE = re.compile(r"-nc|-nd|InC|all rights|no known|NoC-US|NoC-CR|NoC-NC|UND|CNE", re.I)


def open_by_statement(statement: str | None) -> bool:
    """True only for a stated open licence (CC0 / PDM / CC BY / CC BY-SA).  'No known restrictions' is NOT open."""
    if not statement:
        return False
    if re.search(r"/licenses/by-n[cd]|/by-nc|/by-nd|InC/|NoC-|all rights|no known restrictions", statement, re.I):
        return False
    return bool(OPEN_RIGHTS_RE.search(statement))


def role_normalize(role: str | None) -> str:
    r = fold(role)
    for words, norm in (
        (("lithograph", "litograf", "lithographe"), "lithographer"),
        (("engrav", "graveur", "incis", "etch", "radier", "gravé", "etched", "intagli"), "engraver"),
        (("print", "imprim", "stamp"), "printer"),
        (("publish", "edit", "verlag", "uitgever", "excud", "formis"), "publisher"),
        (
            (
                "drawn",
                "design",
                "draft",
                "dessin",
                "delineavit",
                "disegn",
                "painter",
                "artist",
                "inventor",
                "invenit",
                "after",
                "tekenaar",
                "pinx",
                "architect",
            ),
            "designer",
        ),
        (("text", "author", "writer"), "author_of_text"),
    ):
        if any(w in r for w in words):
            return norm
    return "unspecified"


def parse_year(s: str | None) -> tuple[int | None, int | None]:
    yrs = [int(y) for y in re.findall(r"(?<!\d)(1[5-9]\d\d)(?!\d)", s or "")]
    return (min(yrs), max(yrs)) if yrs else (None, None)


def in_period(s: str | None, lo: int = 1700, hi: int = 1900) -> bool:
    """18th-19th c. check on a stated date; unknown dates are kept (judged by the curator)."""
    a, b = parse_year(s)
    if a is None:
        return True
    return not (b < 1700 or a > 1925)


def base_record(source: str, source_id: str, author: dict) -> dict:
    return {
        "record_id": f"{source}:{source_id}",
        "artist_id": author["slug"],
        "author_name": author["name"],
        "participants": [],
        "original_title": None,
        "translated_title_ru": None,
        "series": None,
        "plate_number": None,
        "volume": None,
        "city": None,
        "place": None,
        "country": None,
        "geo_confidence": "unknown",
        "date_as_stated": None,
        "technique_as_stated": None,
        "object_type": "print",
        "institution": None,
        "accession": None,
        "record_url": None,
        "iiif_manifest": None,
        "image_url": None,
        "image_width": None,
        "image_height": None,
        "rights_statement": None,
        "rights_status": "unknown",
        "duplicate_hint": None,
        "impression_note": None,
        "verification_status": "source_record_read",
        "attribution_confidence": "high",
        "attribution_note": None,
    }


def finish(rec: dict, author: dict, matched: str) -> dict:
    """Common post-processing: geo from the literal title, series, hint; drop image_url unless open."""
    geo = detect_geo(rec["original_title"], rec["series"])
    rec["city"], rec["place"], rec["geo_confidence"] = geo
    rec["series"] = rec["series"] or detect_series(rec["original_title"])
    rec["duplicate_hint"] = duplicate_hint(rec["original_title"], rec["series"], rec["plate_number"], author["slug"])
    rec["attribution_note"] = (
        rec["attribution_note"] or f"Creator string in source matched the exact name form: «{matched}»."
    )
    if rec["rights_status"] != "open_confirmed":
        rec["image_url"] = None
        rec["image_width"] = rec["image_height"] = None
    return rec


# ---- source parsers ----------------------------------------------------------------------------


def parse_cleveland(item: dict) -> dict | None:
    creators = [c.get("description") or "" for c in item.get("creators") or []]
    m = match_author(creators)
    if not m:
        return None
    author, matched = m
    r = base_record("cleveland", str(item["id"]), author)
    r["participants"] = [
        {
            "name": c.get("description"),
            "role_as_stated": c.get("role"),
            "role_normalized": role_normalize(c.get("role")),
        }
        for c in item.get("creators") or []
    ]
    r["original_title"] = item.get("title")
    r["date_as_stated"] = item.get("creation_date")
    r["technique_as_stated"] = item.get("technique")
    r["object_type"] = "drawing" if (item.get("type") or "").lower() == "drawing" else "print"
    r["institution"] = "The Cleveland Museum of Art"
    r["accession"] = item.get("accession_number")
    r["record_url"] = item.get("url")
    r["country"] = (item.get("culture") or [None])[0]
    imgs = item.get("images") or {}
    pick = imgs.get("print") or imgs.get("web") or {}
    if pick.get("url"):
        r["image_url"] = pick["url"]
        r["image_width"] = int(pick["width"]) if str(pick.get("width", "")).isdigit() else None
        r["image_height"] = int(pick["height"]) if str(pick.get("height", "")).isdigit() else None
    lic = item.get("share_license_status")
    r["rights_statement"] = f"share_license_status: {lic}" if lic else None
    r["rights_status"] = (
        "open_confirmed" if lic == "CC0" and r["image_url"] else ("rights_pending" if lic else "unknown")
    )
    r["impression_note"] = item.get("state_of_the_work")
    return finish(r, author, matched)


def parse_aic(item: dict, iiif_base: str = "https://www.artic.edu/iiif/2") -> dict | None:
    lines = [x.strip() for x in (item.get("artist_display") or "").split("\n") if x.strip()]
    m = match_author([item.get("artist_title") or ""] + lines)
    if not m:
        return None
    author, matched = m
    r = base_record("aic", str(item["id"]), author)
    r["participants"] = [{"name": item.get("artist_title"), "role_as_stated": None, "role_normalized": "unspecified"}]
    for line in lines[1:]:
        r["participants"].append({"name": line, "role_as_stated": line, "role_normalized": role_normalize(line)})
    r["original_title"] = item.get("title")
    r["series"] = "; ".join(item.get("series_titles") or []) or None
    r["date_as_stated"] = item.get("date_display")
    r["technique_as_stated"] = item.get("medium_display")
    r["institution"] = "Art Institute of Chicago"
    r["accession"] = item.get("main_reference_number")
    r["record_url"] = f"https://www.artic.edu/artworks/{item['id']}"
    r["country"] = item.get("place_of_origin")
    r["iiif_manifest"] = f"https://api.artic.edu/api/v1/artworks/{item['id']}/manifest.json"
    th = item.get("thumbnail") or {}
    if item.get("image_id"):
        r["image_url"] = f"{iiif_base}/{item['image_id']}/full/843,/0/default.jpg"
        r["image_width"], r["image_height"] = th.get("width"), th.get("height")
        r["impression_note"] = (
            "image_width/height are the source image size stated by the API (thumbnail block); image_url is the 843 px IIIF derivative."
        )
    if item.get("is_public_domain") and item.get("image_id"):
        r["rights_status"] = "open_confirmed"
        r["rights_statement"] = (
            "is_public_domain: true (AIC API); AIC Open Access images of public-domain works are CC0 (https://www.artic.edu/open-access/open-access-images)"
        )
    else:
        r["rights_status"] = "link_only" if item.get("image_id") else "unknown"
        r["rights_statement"] = f"is_public_domain: {item.get('is_public_domain')} (AIC API)"
    return finish(r, author, matched)


def parse_met(obj: dict) -> dict | None:
    names = [obj.get("artistDisplayName") or ""]
    for c in obj.get("constituents") or []:
        names.append(c.get("name") or "")
    m = match_author(names)
    if not m:
        return None
    author, matched = m
    r = base_record("met", str(obj["objectID"]), author)
    r["participants"] = [
        {"name": c.get("name"), "role_as_stated": c.get("role"), "role_normalized": role_normalize(c.get("role"))}
        for c in obj.get("constituents") or []
    ] or [
        {
            "name": obj.get("artistDisplayName"),
            "role_as_stated": obj.get("artistRole") or None,
            "role_normalized": role_normalize(obj.get("artistRole")),
        }
    ]
    r["original_title"] = obj.get("title")
    r["series"] = obj.get("portfolio") or None
    r["date_as_stated"] = obj.get("objectDate")
    r["technique_as_stated"] = obj.get("medium")
    r["object_type"] = "drawing" if "drawing" in (obj.get("classification") or "").lower() else "print"
    r["institution"] = "The Metropolitan Museum of Art"
    r["accession"] = obj.get("accessionNumber")
    r["record_url"] = obj.get("objectURL") or f"https://www.metmuseum.org/art/collection/search/{obj['objectID']}"
    r["country"] = obj.get("country") or None
    if obj.get("primaryImage"):
        r["image_url"] = obj["primaryImage"]
    pd = obj.get("isPublicDomain")
    r["rights_statement"] = (
        f"isPublicDomain: {pd}; rightsAndReproduction: {obj.get('rightsAndReproduction') or ''}".strip()
    )
    r["rights_status"] = "open_confirmed" if pd and r["image_url"] else ("link_only" if r["image_url"] else "unknown")
    return finish(r, author, matched)


def _nots(x: dict) -> list[dict]:
    """Linked Art `notation` entries as dicts ({"@language","@value"}); bare strings become language-less."""
    out = []
    for n in x.get("notation") or []:
        out.append(n if isinstance(n, dict) else {"@value": str(n)})
    return out


def parse_rijks(obj: dict) -> dict | None:
    names, parts = [], []
    prod = obj.get("produced_by") or {}
    for part in prod.get("part") or []:
        nm = None
        for p in part.get("carried_out_by") or []:
            for n in _nots(p):
                if n.get("@language") == "en" or nm is None:
                    nm = n.get("@value")
        role = None
        for t in part.get("referred_to_by") or []:
            txt = t.get("content") or ""
            if ":" in txt and (t.get("language") or [{}])[0].get("id", "").endswith("300388277"):
                role = txt.split(":", 1)[0].strip()
        for tq in part.get("technique") or []:
            for n in _nots(tq):
                if n.get("@language") == "en" and not role:
                    role = n.get("@value")
        if nm:
            names.append(nm)
            parts.append({"name": nm, "role_as_stated": role, "role_normalized": role_normalize(role)})
    m = match_author(names)
    if not m:
        return None
    author, matched = m
    oid = obj["id"].rsplit("/", 1)[-1]
    r = base_record("rijks", oid, author)
    r["participants"] = parts
    title = None
    accession = None
    for ident in obj.get("identified_by") or []:
        cls = [c.get("id", "") for c in ident.get("classified_as") or []]
        if ident.get("type") == "Name" and any(c.endswith("300404670") for c in cls):
            lang = (ident.get("language") or [{}])[0].get("id", "")
            if title is None or lang.endswith("300388277"):
                title = ident.get("content")
        if ident.get("type") == "Identifier" and any(c.endswith("300312355") for c in cls):
            accession = ident.get("content")
    r["original_title"] = title
    r["accession"] = accession
    r["institution"] = "Rijksmuseum"
    ts = prod.get("timespan") or {}
    if isinstance(ts, list):
        ts = ts[0] if ts else {}
    r["date_as_stated"] = next((i.get("content") for i in ts.get("identified_by") or [] if i.get("content")), None)
    techs = [n.get("@value") for mm in obj.get("made_of") or [] for n in _nots(mm) if n.get("@language") == "en"]
    r["technique_as_stated"] = ", ".join(techs) or None
    cls = [n.get("@value") for c in obj.get("classified_as") or [] for n in _nots(c) if n.get("@language") == "en"]
    r["object_type"] = "drawing" if "drawing" in cls else "print"
    rights = None
    page = None
    for so in obj.get("subject_of") or []:
        for dc in so.get("digitally_carried_by") or []:
            ap = [a.get("id") for a in dc.get("access_point") or []]
            if dc.get("format") == "text/html" and ap:
                page = ap[0]
            for rt in dc.get("referred_to_by") or []:
                if "creativecommons.org" in (rt.get("content") or ""):
                    rights = rt["content"]
                    r["image_url"] = next((a for a in ap if "iiif" in a), None)
    r["record_url"] = page or obj["id"]
    r["rights_statement"] = rights
    r["rights_status"] = (
        "open_confirmed"
        if open_by_statement(rights) and r["image_url"]
        else ("unknown" if not rights else "rights_pending")
    )
    return finish(r, author, matched)


def parse_europeana(item: dict) -> dict | None:
    creators = item.get("dcCreator") or []
    m = match_author(creators)
    if not m:
        return None
    author, matched = m
    r = base_record("europeana", item["id"].strip("/").replace("/", "_"), author)
    r["participants"] = []
    for c in dict.fromkeys(creators):
        role = c.rsplit(".", 1)[-1].strip() if re.search(r"\.\s*\w+$", c) else None
        r["participants"].append({"name": c, "role_as_stated": role, "role_normalized": role_normalize(role)})
    titles = item.get("title") or []
    r["original_title"] = titles[0] if titles else None
    r["date_as_stated"] = (item.get("year") or [None])[0]
    r["institution"] = (item.get("dataProvider") or [None])[0]
    r["country"] = (item.get("country") or [None])[0]
    r["record_url"] = "https://www.europeana.eu/item" + item["id"]
    descr = " ".join(item.get("dcDescription") or [])
    r["technique_as_stated"] = None
    mm = re.search(r"(?:cote|shelfmark|call number)\s*:?\s*([^;|]+)", descr, re.I)
    r["accession"] = mm.group(1).strip() if mm else None
    rights = (item.get("rights") or [None])[0]
    shown = (item.get("edmIsShownBy") or [None])[0]
    r["image_url"] = shown
    r["rights_statement"] = rights
    r["rights_status"] = (
        "open_confirmed" if open_by_statement(rights) and shown else ("rights_pending" if rights else "unknown")
    )
    return finish(r, author, matched)


def parse_loc(item: dict) -> dict | None:
    m = match_author([item.get("creator") or ""])
    if not m:
        return None
    author, matched = m
    r = base_record("loc", item["pk"], author)
    r["participants"] = [
        {
            "name": item["creator"],
            "role_as_stated": item["creator"].rsplit(",", 1)[-1].strip() or None,
            "role_normalized": role_normalize(item["creator"]),
        }
    ]
    r["original_title"] = item.get("title")
    r["date_as_stated"] = item.get("created_published_date")
    r["technique_as_stated"] = item.get("medium")
    r["institution"] = "Library of Congress, Prints & Photographs Division"
    r["accession"] = item.get("call_number")
    r["record_url"] = (item.get("links") or {}).get("item")
    r["rights_status"] = "rights_pending"
    r["rights_statement"] = (
        "Rights advisory not read in the search result; LoC 'no known restrictions' is NOT CC0 and is not treated as open."
    )
    r["verification_status"] = "search_hit_only"
    return finish(r, author, matched)


def parse_commons(page: dict) -> dict | None:
    ii = (page.get("imageinfo") or [{}])[0]
    ext = ii.get("extmetadata") or {}
    artist = re.sub(r"<[^>]+>", "", (ext.get("Artist") or {}).get("value", ""))
    m = match_author([artist])
    if not m:
        return None
    author, matched = m
    r = base_record("commons", str(page["pageid"]), author)
    r["participants"] = [{"name": artist, "role_as_stated": None, "role_normalized": "unspecified"}]
    r["original_title"] = re.sub(r"<[^>]+>", "", (ext.get("ObjectName") or {}).get("value", "")) or page.get("title")
    r["date_as_stated"] = re.sub(r"<[^>]+>", "", (ext.get("DateTimeOriginal") or {}).get("value", "")) or None
    r["institution"] = "Wikimedia Commons"
    r["record_url"] = ii.get("descriptionurl")
    r["image_url"] = ii.get("url")
    r["image_width"], r["image_height"] = ii.get("width"), ii.get("height")
    lic = (ext.get("LicenseShortName") or {}).get("value")
    r["rights_statement"] = f"{lic} {(ext.get('LicenseUrl') or {}).get('value', '')}".strip() if lic else None
    ok = bool(
        lic
        and re.match(r"(?i)(cc0|public domain|pd|cc[- ]by(?:[- ]sa)?\b)", lic)
        and not re.search(r"(?i)-nc|-nd", lic)
    )
    r["rights_status"] = "open_confirmed" if ok and r["image_url"] else "rights_pending"
    return finish(r, author, matched)


# ---- NGA CSV -----------------------------------------------------------------------------------


def nga_author_for(names: list[str]):
    return match_author(names)


def parse_nga(row: dict, participants: list[dict], image: dict | None, matched: tuple) -> dict:
    author, mname = matched
    r = base_record("nga", row["objectid"], author)
    r["participants"] = participants
    r["original_title"] = row.get("title")
    r["series"] = row.get("series") or row.get("portfolio") or None
    r["volume"] = row.get("volume") or None
    r["date_as_stated"] = row.get("displaydate") or None
    r["technique_as_stated"] = row.get("medium") or None
    r["object_type"] = "drawing" if (row.get("classification") or "").lower() == "drawing" else "print"
    r["institution"] = "National Gallery of Art, Washington"
    r["accession"] = row.get("accessionnum")
    r["record_url"] = f"https://www.nga.gov/collection/art-object-page.{row['objectid']}.html"
    if image:
        r["iiif_manifest"] = None
        r["image_url"] = image["iiifurl"] + "/full/full/0/default.jpg"
        r["image_width"] = int(image["width"]) if str(image.get("width", "")).isdigit() else None
        r["image_height"] = int(image["height"]) if str(image.get("height", "")).isdigit() else None
        if image.get("openaccess") == "1":
            r["rights_status"] = "open_confirmed"
            r["rights_statement"] = "openaccess=1 in NGA opendata published_images.csv (NGA Open Access, CC0)"
        else:
            r["rights_status"] = "link_only"
            r["rights_statement"] = "openaccess=0 in published_images.csv"
    return finish(r, author, mname)


# --------------------------------------------------------------------------------------------------
# HTTP (polite, cached, breaker)
# --------------------------------------------------------------------------------------------------


def safe(fn, *args):
    """Run a parser; one malformed source record must not abort a long run (counted as not kept)."""
    try:
        return fn(*args)
    except (KeyError, TypeError, AttributeError, ValueError, IndexError):
        return None


class Blocked(Exception):
    pass


class Fetcher:
    def __init__(self, cache_dir: Path, max429: int = 2):
        self.cache = cache_dir
        self.cache.mkdir(parents=True, exist_ok=True)
        self.last: dict[str, float] = {}
        self.dead: dict[str, str] = {}
        self.n429: dict[str, int] = {}
        self.max429 = max429
        self.blocked: list[dict] = []
        self.requests = 0

    def _cp(self, url: str, accept: str) -> Path:
        return self.cache / (hashlib.sha1((url + "|" + accept).encode()).hexdigest() + ".json")

    def _wait(self, host: str) -> None:
        gap = HOST_GAP.get(host, MIN_GAP)
        wait = self.last.get(host, 0) + gap - time.time()
        if wait > 0:
            time.sleep(wait)

    def text(self, url: str, accept: str = "application/json", retries: int = 2) -> str | None:
        cp = self._cp(url, accept)
        if cp.exists():
            return cp.read_text(encoding="utf-8")
        host = urllib.parse.urlsplit(url).netloc
        if host in self.dead:
            return None
        for attempt in range(retries + 1):
            self._wait(host)
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
            try:
                self.requests += 1
                self.last[host] = time.time()
                with urllib.request.urlopen(req, timeout=60) as resp:
                    body = resp.read().decode("utf-8", "replace")
                self.n429[host] = 0
                cp.write_text(body, encoding="utf-8")
                return body
            except urllib.error.HTTPError as e:
                self.last[host] = time.time()
                if e.code == 429:
                    self.n429[host] = self.n429.get(host, 0) + 1
                    if self.n429[host] >= self.max429:
                        self.dead[host] = "HTTP 429 repeated"
                        self.blocked.append(
                            {"host": host, "url": url, "http": 429, "why": "rate limited; host abandoned, not bypassed"}
                        )
                        return None
                    time.sleep(30 * (attempt + 1))
                    continue
                if e.code in (401, 403, 451):
                    self.dead[host] = f"HTTP {e.code}"
                    self.blocked.append(
                        {"host": host, "url": url, "http": e.code, "why": "access refused; not bypassed"}
                    )
                    return None
                if e.code in (404, 410):
                    self.blocked.append({"host": host, "url": url, "http": e.code, "why": "not found / gone"})
                    return None
                if attempt == retries:
                    self.blocked.append(
                        {"host": host, "url": url, "http": e.code, "why": f"HTTP {e.code} after retries"}
                    )
                    return None
                time.sleep(5)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                self.last[host] = time.time()
                if attempt == retries:
                    self.blocked.append(
                        {"host": host, "url": url, "http": None, "why": f"{type(e).__name__}: {e}"[:200]}
                    )
                    return None
                time.sleep(5)
        return None

    def json(self, url: str, accept: str = "application/json"):
        t = self.text(url, accept)
        if t is None:
            return None
        try:
            return json.loads(t)
        except json.JSONDecodeError:
            self.blocked.append(
                {
                    "host": urllib.parse.urlsplit(url).netloc,
                    "url": url,
                    "http": 200,
                    "why": "non-JSON body (challenge page?)",
                }
            )
            return None

    def download(self, url: str, dest: Path) -> bool:
        """Stream a (metadata) CSV to disk once."""
        if dest.exists() and dest.stat().st_size > 0:
            return True
        host = urllib.parse.urlsplit(url).netloc
        self._wait(host)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            self.requests += 1
            with urllib.request.urlopen(req, timeout=300) as resp, open(dest.with_suffix(".part"), "wb") as fh:
                while chunk := resp.read(1 << 20):
                    fh.write(chunk)
            dest.with_suffix(".part").rename(dest)
            self.last[host] = time.time()
            return True
        except (urllib.error.URLError, OSError) as e:
            self.blocked.append(
                {"host": host, "url": url, "http": getattr(e, "code", None), "why": f"{type(e).__name__}: {e}"[:200]}
            )
            return False


def q(**kw) -> str:
    return urllib.parse.urlencode(kw)


# --------------------------------------------------------------------------------------------------
# Source runners.  Each returns {"records": [...], "queries": [...], "dropped_other": n}
# query entry: {source, author, query, url, hits_reported, pages, examined, kept}
# --------------------------------------------------------------------------------------------------


def qentry(source, author, query, url):
    return {
        "source": source,
        "author": author,
        "query": query,
        "url": url,
        "hits_reported": None,
        "pages": 0,
        "examined": 0,
        "kept": 0,
    }


def run_cleveland(f: Fetcher, authors, max_pages=6) -> dict:
    recs, qs = {}, []
    for a in authors:
        for term in a["queries"]:
            url0 = "https://openaccess-api.clevelandart.org/api/artworks/?" + q(q=term, has_image=1, limit=100, skip=0)
            e = qentry("cleveland", a["slug"], term, url0)
            qs.append(e)
            for p in range(max_pages):
                url = "https://openaccess-api.clevelandart.org/api/artworks/?" + q(
                    q=term, has_image=1, limit=100, skip=p * 100
                )
                d = f.json(url)
                if not d:
                    break
                e["pages"] += 1
                e["hits_reported"] = d["info"]["total"]
                for item in d["data"]:
                    e["examined"] += 1
                    r = safe(parse_cleveland, item)
                    if r and r["artist_id"] == a["slug"] and in_period(r["date_as_stated"]):
                        recs.setdefault(r["record_id"], r)
                        e["kept"] += 1
                if (p + 1) * 100 >= d["info"]["total"]:
                    break
    return {"records": list(recs.values()), "queries": qs}


def run_aic(f: Fetcher, authors, max_pages=6) -> dict:
    fields = "id,title,artist_title,artist_display,date_display,date_start,place_of_origin,medium_display,artwork_type_title,is_public_domain,image_id,thumbnail,main_reference_number,series_titles"
    recs, qs = {}, []
    for a in authors:
        for term in a["queries"]:
            e = qentry(
                "aic",
                a["slug"],
                term,
                "https://api.artic.edu/api/v1/artworks/search?" + q(q=term, fields=fields, limit=100, page=1),
            )
            qs.append(e)
            for p in range(1, max_pages + 1):
                d = f.json(
                    "https://api.artic.edu/api/v1/artworks/search?" + q(q=term, fields=fields, limit=100, page=p)
                )
                if not d:
                    break
                e["pages"] += 1
                e["hits_reported"] = d["pagination"]["total"]
                for item in d["data"]:
                    e["examined"] += 1
                    r = safe(parse_aic, item, (d.get("config") or {}).get("iiif_url", "https://www.artic.edu/iiif/2"))
                    if r and r["artist_id"] == a["slug"] and in_period(r["date_as_stated"]):
                        recs.setdefault(r["record_id"], r)
                        e["kept"] += 1
                if p >= d["pagination"]["total_pages"] or p * 100 >= 600:
                    break
    return {"records": list(recs.values()), "queries": qs}


def run_met(f: Fetcher, authors, max_objects=450) -> dict:
    recs, qs = {}, []
    for a in authors:
        term = a["queries"][0]
        url = "https://collectionapi.metmuseum.org/public/collection/v1.1/search?" + q(
            q=term, artistOrCulture="true", hasImages="true", limit=max_objects, offset=0
        )
        e = qentry("met", a["slug"], term, url)
        qs.append(e)
        d = f.json(url)
        if not d:
            continue
        e["pages"] = 1
        e["hits_reported"] = d.get("total")
        for oid in (d.get("objectIDs") or [])[:max_objects]:
            obj = f.json(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}")
            if not obj:
                continue
            e["examined"] += 1
            r = safe(parse_met, obj)
            if r and r["artist_id"] == a["slug"] and in_period(r["date_as_stated"]):
                recs.setdefault(r["record_id"], r)
                e["kept"] += 1
            if e["examined"] >= 40 and e["kept"] == 0:
                e["stopped_early"] = "0 kept in the first 40 examined (name matches other people); remaining IDs not fetched"
                break
    return {"records": list(recs.values()), "queries": qs}


def run_nga(f: Fetcher, authors) -> dict:
    base = "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/"
    d = f.cache / "nga"
    d.mkdir(exist_ok=True)
    for n in ("objects", "constituents", "objects_constituents", "published_images"):
        if not f.download(base + n + ".csv", d / f"{n}.csv"):
            return {"records": [], "queries": [], "blocked_all": True}
    cons: dict[str, str] = {}
    author_of_cons: dict[str, tuple] = {}
    with open(d / "constituents.csv", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            names = [row["preferreddisplayname"], row["forwarddisplayname"]]
            cons[row["constituentid"]] = row["forwarddisplayname"] or row["preferreddisplayname"]
            m = match_author(names)
            if m:
                author_of_cons[row["constituentid"]] = m
    obj_authors: dict[str, tuple] = {}
    obj_parts: dict[str, list] = {}
    with open(d / "objects_constituents.csv", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        if row["constituentid"] in author_of_cons and row["roletype"] == "artist":
            obj_authors[row["objectid"]] = author_of_cons[row["constituentid"]]
    for row in rows:
        if row["objectid"] in obj_authors and row["roletype"] in ("artist", "publisher", "printer"):
            role = row["role"] or row["roletype"]
            obj_parts.setdefault(row["objectid"], []).append(
                {
                    "name": cons.get(row["constituentid"]),
                    "role_as_stated": role,
                    "role_normalized": role_normalize(role),
                }
            )
    images: dict[str, dict] = {}
    with open(d / "published_images.csv", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            oid = row["depictstmsobjectid"]
            if oid in obj_authors and row["viewtype"] == "primary":
                images.setdefault(oid, row)
    counts: dict[str, dict] = {}
    recs = {}
    with open(d / "objects.csv", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            oid = row["objectid"]
            if oid not in obj_authors:
                continue
            slug = obj_authors[oid][0]["slug"]
            c = counts.setdefault(slug, {"reported": 0, "no_image": 0, "kept": 0})
            c["reported"] += 1
            if row.get("classification", "").lower() not in ("print", "drawing", "volume", "illustrated book", "book"):
                continue
            img = images.get(oid)
            if not img:
                c["no_image"] += 1
                continue
            if not in_period(row.get("displaydate")):
                continue
            r = parse_nga(row, obj_parts.get(oid, []), img, obj_authors[oid])
            recs[r["record_id"]] = r
            c["kept"] += 1
    qs = []
    for a in authors:
        c = counts.get(a["slug"], {"reported": 0, "kept": 0, "no_image": 0})
        e = qentry(
            "nga",
            a["slug"],
            "constituents.csv name match -> objects_constituents(artist) -> objects/published_images",
            base,
        )
        e.update(
            {
                "pages": 4,
                "hits_reported": c["reported"],
                "examined": c["reported"],
                "kept": c["kept"],
                "dropped_no_published_image": c["no_image"],
            }
        )
        qs.append(e)
    return {"records": list(recs.values()), "queries": qs}


def run_rijks(f: Fetcher, authors, max_objects=30) -> dict:
    recs, qs = {}, []
    for a in authors:
        term = a["queries"][0]
        url = "https://data.rijksmuseum.nl/search/collection?" + q(creator=term, imageAvailable="true")
        e = qentry("rijks", a["slug"], f"creator={term}", url)
        qs.append(e)
        d = f.json(url)
        if not d:
            continue
        e["pages"] = 1
        e["hits_reported"] = (d.get("partOf") or {}).get("totalItems")
        for it in (d.get("orderedItems") or [])[:max_objects]:
            obj = f.json(it["id"], accept="application/ld+json")
            if not obj:
                continue
            e["examined"] += 1
            r = safe(parse_rijks, obj)
            if r and r["artist_id"] == a["slug"] and in_period(r["date_as_stated"]):
                recs.setdefault(r["record_id"], r)
                e["kept"] += 1
    return {"records": list(recs.values()), "queries": qs}


def run_europeana(f: Fetcher, authors, max_pages=3) -> dict:
    recs, qs = {}, []
    for a in authors:
        term = a["queries"][0]
        for reuse in ("open",):
            url0 = "https://api.europeana.eu/record/v2/search.json?" + q(
                wskey=EUROPEANA_KEY,
                query=f'who:"{term}"',
                qf="TYPE:IMAGE",
                reusability=reuse,
                rows=100,
                start=1,
                profile="standard",
            )
            e = qentry(
                "europeana",
                a["slug"],
                f'who:"{term}" TYPE:IMAGE reusability={reuse}',
                url0.replace(EUROPEANA_KEY, "<key>"),
            )
            qs.append(e)
            for p in range(max_pages):
                d = f.json(
                    "https://api.europeana.eu/record/v2/search.json?"
                    + q(
                        wskey=EUROPEANA_KEY,
                        query=f'who:"{term}"',
                        qf="TYPE:IMAGE",
                        reusability=reuse,
                        rows=100,
                        start=1 + p * 100,
                        profile="standard",
                    )
                )
                if not d or not d.get("success"):
                    break
                e["pages"] += 1
                e["hits_reported"] = d.get("totalResults")
                for item in d.get("items") or []:
                    e["examined"] += 1
                    r = safe(parse_europeana, item)
                    if r and r["artist_id"] == a["slug"] and in_period(r["date_as_stated"]):
                        recs.setdefault(r["record_id"], r)
                        e["kept"] += 1
                if (p + 1) * 100 >= (d.get("totalResults") or 0):
                    break
    return {"records": list(recs.values()), "queries": qs}


def run_loc(f: Fetcher, authors, max_pages=2) -> dict:
    recs, qs = {}, []
    for a in authors:
        term = a["queries"][0]
        e = qentry("loc", a["slug"], term, "https://www.loc.gov/pictures/search/?" + q(q=term, fo="json", c=100, sp=1))
        qs.append(e)
        for p in range(1, max_pages + 1):
            d = f.json("https://www.loc.gov/pictures/search/?" + q(q=term, fo="json", c=100, sp=p))
            if not d:
                break
            e["pages"] += 1
            e["hits_reported"] = (d.get("search") or {}).get("hits")
            for item in d.get("results") or []:
                e["examined"] += 1
                r = safe(parse_loc, item)
                if r and r["artist_id"] == a["slug"] and in_period(r["date_as_stated"]):
                    recs.setdefault(r["record_id"], r)
                    e["kept"] += 1
            if not (d.get("pages") or {}).get("next"):
                break
    return {"records": list(recs.values()), "queries": qs}


def run_commons(f: Fetcher, authors) -> dict:
    recs, qs = {}, []
    f.max429 = 1  # one 429 is final for Commons
    for a in authors:
        term = a["queries"][0]
        url = "https://commons.wikimedia.org/w/api.php?" + q(
            action="query",
            format="json",
            generator="search",
            gsrsearch=f"{term} filetype:bitmap",
            gsrnamespace=6,
            gsrlimit=50,
            prop="imageinfo",
            iiprop="url|size|extmetadata",
        )
        e = qentry("commons", a["slug"], term, url)
        qs.append(e)
        d = f.json(url)
        if not d:
            continue
        e["pages"] = 1
        e["hits_reported"] = ((d.get("query") or {}).get("searchinfo") or {}).get("totalhits")
        for page in ((d.get("query") or {}).get("pages") or {}).values():
            e["examined"] += 1
            r = safe(parse_commons, page)
            if r and r["artist_id"] == a["slug"] and in_period(r["date_as_stated"]):
                recs.setdefault(r["record_id"], r)
                e["kept"] += 1
    return {"records": list(recs.values()), "queries": qs}


# Paris Musees authority search: the free-text path ignores the query (454055 hits), the author path works.
PM_PATH = "/fr/recherche/AND/auteur/"
PM_FORMS = {
    "thomas-shotter-boys": "Boys, Thomas Shotter",
    "canaletto": "Canaletto",
    "alexandre-benois": "Benois",
    "albert-benois": "Benois",
    "nicolas-benois": "Benois",
    "thomas-hosmer-shepherd": "Shepherd, Thomas Hosmer",
    "eugene-ciceri": "Cicéri",
    "israel-silvestre": "Silvestre",
}


def run_parismusees(f: Fetcher, authors, max_pages=2, max_records=25) -> dict:
    from tools.world import search_parismusees as pm

    fetch = pm.Fetcher(f.cache / "pm", delay=1.5)
    recs, qs = {}, []
    fails = 0
    for a in authors:
        term = PM_FORMS.get(a["slug"]) or a["name"].split("(")[0].split()[-1]
        e = qentry("parismusees", a["slug"], f"auteur:{term}", pm.SITE + PM_PATH + urllib.parse.quote(term, safe=""))
        qs.append(e)
        cards = []
        for p in range(1, max_pages + 1):
            html = fetch.get(pm.SITE + PM_PATH + urllib.parse.quote(term, safe="") + (f"?page={p}" if p > 1 else ""))
            if not html:
                fails += 1
                break
            page = pm.parse_search_page(html)
            e["pages"] += 1
            e["hits_reported"] = page["total"]
            cards += page["cards"]
            if not page["cards"]:
                break
        for card in cards:
            e["examined"] += 1
            m = match_author(card.get("authors") or [])
            if not m or m[0]["slug"] != a["slug"] or e["kept"] >= max_records or fails >= 4:
                continue
            html = fetch.get(pm.SITE + card["path"])
            if not html:
                fails += 1
                continue
            rec = pm.parse_record_page(html)
            author, matched = m
            r = base_record("parismusees", card["node"], author)
            r["participants"] = [
                {
                    "name": x.get("name"),
                    "role_as_stated": x.get("role"),
                    "role_normalized": role_normalize(x.get("role")),
                }
                for x in rec["authors"]
            ]
            r["original_title"] = rec["title"]
            r["date_as_stated"] = rec["date"]
            r["technique_as_stated"] = "; ".join(rec["techniques"]) or None
            r["institution"] = rec["institution"]
            r["accession"] = rec["inventory"]
            r["record_url"] = rec["record_url"]
            r["iiif_manifest"] = rec["manifest"]
            if rec["manifest"]:
                man = f.json(rec["manifest"])
                if man:
                    cv = pm.parse_manifest(man)["canvases"]
                    status, stmt = pm.rights_from_canvases(cv)
                    r["rights_status"], r["rights_statement"] = status, stmt
                    if cv:
                        r["image_url"], r["image_width"], r["image_height"] = (
                            cv[0]["image_url"],
                            cv[0]["width"],
                            cv[0]["height"],
                        )
            if in_period(r["date_as_stated"]):
                recs.setdefault(r["record_id"], finish(r, author, matched))
                e["kept"] += 1
    f.blocked += [{"host": "www.parismuseescollections.paris.fr", **b} for b in fetch.blocked]
    return {"records": list(recs.values()), "queries": qs}


RUNNERS = {
    "cleveland": run_cleveland,
    "aic": run_aic,
    "met": run_met,
    "nga": run_nga,
    "rijks": run_rijks,
    "europeana": run_europeana,
    "loc": run_loc,
    "commons": run_commons,
    "parismusees": run_parismusees,
}


# --------------------------------------------------------------------------------------------------
# Merge / coverage
# --------------------------------------------------------------------------------------------------


def known_ids(roots=("data/curation", "data/catalog", "data/candidates", "data/research/benoist")) -> str:
    chunks = []
    for r in roots:
        for p in (ROOT / r).rglob("*.json"):
            try:
                chunks.append(p.read_text(encoding="utf-8"))
            except OSError:
                pass
    return "\n".join(chunks)


def build_output(results: dict[str, dict], blocked: list[dict]) -> dict:
    recs = [r for res in results.values() for r in res["records"] if in_period(r["date_as_stated"])]
    qs = [e for res in results.values() for e in res["queries"]]
    corpus = known_ids()
    for r in recs:
        r["known_before"] = bool(r["record_url"] and r["record_url"] in corpus)
    groups: dict[str, list[str]] = {}
    for r in recs:
        if r["duplicate_hint"]:
            groups.setdefault(r["duplicate_hint"], []).append(r["record_id"])
    for r in recs:
        g = groups.get(r["duplicate_hint"] or "", [])
        r["impression_group_size"] = len(g) if g else 1
    per: dict[str, dict] = {}
    for r in recs:
        c = per.setdefault(
            r["artist_id"],
            {
                "author_name": r["author_name"],
                "kept": 0,
                "open_confirmed": 0,
                "by_source": {},
                "cities": set(),
                "buildings": set(),
            },
        )
        c["kept"] += 1
        c["open_confirmed"] += r["rights_status"] == "open_confirmed"
        c["by_source"][r["record_id"].split(":")[0]] = c["by_source"].get(r["record_id"].split(":")[0], 0) + 1
        if r["city"]:
            c["cities"].add(r["city"])
        if r["place"]:
            c["buildings"].add(r["place"])
    hits: dict[str, dict] = {}
    for e in qs:
        h = hits.setdefault(
            f"{e['source']}|{e['author']}",
            {
                "source": e["source"],
                "author": e["author"],
                "hits_reported_max": 0,
                "examined": 0,
                "kept_query_hits": 0,
                "pages": 0,
            },
        )
        h["hits_reported_max"] = max(h["hits_reported_max"], e["hits_reported"] or 0)
        h["examined"] += e["examined"]
        h["kept_query_hits"] += e["kept"]
        h["pages"] += e["pages"]
    for h in hits.values():
        h["records_kept_unique"] = sum(
            1 for r in recs if r["artist_id"] == h["author"] and r["record_id"].startswith(h["source"] + ":")
        )
    open_sized = [r for r in recs if r["rights_status"] == "open_confirmed" and r["image_width"] and r["image_height"]]
    return {
        "version": 1,
        "source": "other-authors (cleveland, aic, met, nga, rijks, europeana, loc, commons, parismusees)",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "coverage": {
            "queries": qs,
            "pages_walked": sum(e["pages"] for e in qs),
            "hits_total_reported_by_source": {
                s: sum(h["hits_reported_max"] for h in hits.values() if h["source"] == s) for s in SOURCES
            },
            "per_author_source": sorted(hits.values(), key=lambda h: (h["author"], h["source"])),
            "records_kept": len(recs),
            "records_by_artist_id": {
                k: {**v, "cities": sorted(v["cities"]), "buildings": sorted(v["buildings"])}
                for k, v in sorted(per.items())
            },
            "unique_compositions": len({r["duplicate_hint"] or r["record_id"] for r in recs}),
            "open_confirmed": sum(r["rights_status"] == "open_confirmed" for r in recs),
            "open_confirmed_with_pixel_size": len(open_sized),
            "records_with_city": sum(1 for r in recs if r["city"]),
            "records_with_building": sum(1 for r in recs if r["geo_confidence"] == "building"),
            "known_before_count": sum(r["known_before"] for r in recs),
            "blocked": blocked,
            "notes": [
                "No images were downloaded; image_url is kept only for rights_status open_confirmed.",
                "hits_reported is the figure the source gives for the free-text/name query; records are kept only when a creator string matches the exact name forms of a listed author (other Piranesi/Benoist/Cicéri/Guardi family members are dropped).",
                "image_width/height only where the source states them (Cleveland, AIC, NGA, Commons, Paris Musées manifest canvas, which is a capped derivative); Met, Rijksmuseum and Europeana do not state pixel size.",
                "AIC/Met 'public domain' flags are the museums' own open-access statements (CC0), not independent verification. LoC 'no known restrictions' is NOT treated as open (rights_pending).",
                "City/place are read literally from title/series text, never inferred from the author; geo_confidence=unknown when the title names no city.",
                "Nantes, Moscow and some Russian authors are thinly covered because the open-API sources hold few such objects; see per_author_source.",
                "Compare known_before with previous branch source IDs: it is true when the record_url already appears in data/curation, data/catalog, data/candidates or data/research/benoist.",
            ],
        },
        "records": sorted(recs, key=lambda r: (r["artist_id"], r["duplicate_hint"] or "", r["record_id"])),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", type=Path, default=Path(os.environ.get("TMPDIR", "/tmp")) / "cop-other-authors")
    ap.add_argument("--only", default=",".join(SOURCES))
    ap.add_argument("--authors", default="", help="comma-separated author slugs (default all)")
    ap.add_argument(
        "--merge", action="store_true", help="only merge finished result-<source>.json files into the output"
    )
    ap.add_argument("--force", action="store_true", help="re-run sources whose result file exists")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    f = Fetcher(args.cache_dir)
    authors = [a for a in AUTHORS if not args.authors or a["slug"] in args.authors.split(",")]
    if not args.merge:
        for s in [x for x in args.only.split(",") if x]:
            rp = args.cache_dir / f"result-{s}.json"
            if rp.exists() and not args.force:
                print(f"{s}: result exists, skip", file=sys.stderr)
                continue
            f.blocked = []
            print(f"== {s}", file=sys.stderr)
            res = RUNNERS[s](f, authors)
            res["blocked"] = f.blocked
            res["requests"] = f.requests
            rp.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
            print(f"{s}: {len(res['records'])} records, {len(f.blocked)} blocked", file=sys.stderr)
    results, blocked = {}, []
    for s in SOURCES:
        rp = args.cache_dir / f"result-{s}.json"
        if rp.exists():
            res = json.loads(rp.read_text(encoding="utf-8"))
            results[s] = res
            blocked += [{"source": s, **b} for b in res.get("blocked", [])]
    out = build_output(results, blocked)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(
        f"wrote {args.out}: {out['coverage']['records_kept']} records, {out['coverage']['open_confirmed']} open_confirmed",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
