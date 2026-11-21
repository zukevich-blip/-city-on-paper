#!/usr/bin/env python3
"""Harvest prints/drawings by Philippe Benoist (1813-1905) from OPEN catalogue APIs into one inventory.

Sources (each reported in ``sources_tried`` with a status, never faked):
  loc         Library of Congress Prints & Photographs (pictures JSON API, name authority + keyword search)
  europeana   Europeana Search API (public demo key by default; override with EUROPEANA_API_KEY)
  met         Metropolitan Museum open access API (v1.1 search)
  aic         Art Institute of Chicago API
  cleveland   Cleveland Museum of Art open access API
  rijks       Rijksmuseum Linked Art search
  internet_archive  Internet Archive advanced search
  parismusees, gallica, commons   probed; failures are recorded (these hosts often block automated clients)

Rules: nothing is invented. Title, date, creator roles, holder, accession, rights text are copied from the
source record. ``image_url`` is set only when the source states an open licence/public-domain mark for the
image. A sheet that merely says "Ph. Benoist" is recorded as written. Records whose only Benoist is a
different person (Guillaume-Philippe Benoist, J. L. Benoist, ...) are excluded and counted.

Polite client: >= 1 s between calls (5 s for loc.gov), custom User-Agent, stops a host after repeated 429.
Output: data/curation/benoist-harvest-v1.json
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "curation" / "benoist-harvest-v1.json"
UA = "CityOnPaperResearch/0.9 (non-commercial museum atlas)"
EUROPEANA_KEY = os.environ.get("EUROPEANA_API_KEY", "api2demo")  # api2demo is Europeana's public demo key
MIN_GAP = {"www.loc.gov": 5.0}
DEFAULT_GAP = 1.2
MAX_429 = 3
LOC_MAX_ITEMS = 80  # loc.gov is slow and rate-limited; keyword hits beyond this are not fetched
LOC_BUDGET_S = 420

# --------------------------------------------------------------------------------------------------
# Pure helpers (unit-tested, no network)
# --------------------------------------------------------------------------------------------------

_PHILIPPE = re.compile(
    r"(benoist,?\s+ph(?:ilippe|\.)?(?!\w)|ph(?:ilippe|\.|\[ilippe\])\s*\(?(?:1813\)?\s*)?benoist|p\[hilippe\]\s+benoist"
    r"|philippe\s*\(1813\)\s*benoist|benoist\s*\(1813)",
    re.I,
)
_OTHER_BENOIST = re.compile(
    r"guillaume[\s-]*philippe\s+benoist|benoist,?\s+guillaume|j\.\s*l\.\s*benoist|benoist,\s*j\.\s*l\.|félix\s+benoist"
    r"|benoist,?\s+f[eé]lix",
    re.I,
)
OPEN_PATTERNS = (
    "publicdomain/zero", "publicdomain/mark", "creativecommons.org/licenses/by/", "creativecommons.org/licenses/by-sa/",
    "cc0", "public domain", "no known restrictions", "pdm",
)
ROLE_WORDS = (
    r"lithograph(?:é|ed|ie|ier)?(?: par| by| von)?|lith\.|lithografie von|dessin(?:é|ateur)(?: par)?|drawn by|"
    r"gezeichnet von|del\.|delin\.|imp\.|imprim(?:é|erie)|printed by|druck von|publi(?:é|shed)(?: par| by)?|"
    r"verlag"
)


def is_philippe_benoist(text: str) -> bool:
    """True when ``text`` names Philippe Benoist (full name, ``Ph.`` initial, dates 1813) and not another Benoist."""
    if not text:
        return False
    t = " ".join(text.split())
    if not _PHILIPPE.search(t):
        return False
    stripped = _OTHER_BENOIST.sub(" ", t)
    return bool(_PHILIPPE.search(stripped))


def rights_class(statement: str | None) -> str:
    """``open`` only for explicit CC0 / PDM / CC BY(-SA) / public domain / 'No known restrictions'; else ``link``."""
    s = (statement or "").lower()
    if not s:
        return "link"
    if any(w in s for w in ("noc-oklr", "inc/1.0", "-nc", "nc-nd", "nc-sa", "noncommercial", "all rights reserved")):
        return "link"
    return "open" if any(p in s for p in OPEN_PATTERNS) else "link"


def norm_url(u: str | None) -> str:
    if not u:
        return ""
    u = u.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.rstrip("/")


def split_roles(creator_strings: list[str]) -> list[dict]:
    """Europeana-style ``Name (dates). Role`` strings -> [{name, role_as_stated, as_written}] (deduplicated)."""
    out, seen = [], set()
    for raw in creator_strings:
        if not raw or raw in seen:
            continue
        seen.add(raw)
        m = re.match(r"^(.*?\))\.\s*(.+)$", raw) or re.match(r"^(.*?)\.\s+([A-Za-zéÉ ]{3,30})$", raw)
        name, role = (m.group(1).strip(), m.group(2).strip()) if m else (raw.strip(), None)
        out.append({"name": name, "role_as_stated": role, "as_written": raw})
    # Europeana repeats FR/EN labels of the same role; keep one entry per name+role-language pair as written.
    return out


def statement_roles(text: str) -> list[dict]:
    """Free-text responsibility statement -> verbatim fragments that mention a role word near a name."""
    frags = []
    for part in re.split(r"\s*;\s*|\s*\.\s+(?=[A-ZÉ])", text or ""):
        part = part.strip()
        if part and re.search(ROLE_WORDS, part, re.I):
            frags.append({"name": None, "role_as_stated": part, "as_written": part})
    return frags


def year_from(text: str | None) -> str | None:
    m = re.search(r"(?<!\d)(1[5-9]\d\d)(?!\d)", text or "")
    return m.group(1) if m else None


def make_record(**kw) -> dict:
    rec = {
        "source": kw["source"],
        "id": kw["id"],
        "title_original": kw.get("title_original"),
        "kind": kw.get("kind", "print"),
        "place_depicted": kw.get("place_depicted"),
        "date_as_stated": kw.get("date_as_stated"),
        "creators": kw.get("creators") or [],
        "statement_of_responsibility": kw.get("statement_of_responsibility"),
        "holder": kw.get("holder"),
        "accession_id": kw.get("accession_id"),
        "record_url": kw.get("record_url"),
        "image_url": None,
        "rights_statement": kw.get("rights_statement"),
        "rights_class": rights_class(kw.get("rights_statement")),
        "image_rights_statement": kw.get("image_rights_statement"),
        "attribution_confidence": kw.get("attribution_confidence", "high"),
        "confidence_note": kw.get("confidence_note", ""),
        "known": False,
        "known_match": None,
    }
    img_rights = kw.get("image_rights_statement") or kw.get("rights_statement")
    if kw.get("image_url") and rights_class(img_rights) == "open":
        rec["image_url"] = kw["image_url"]
        rec["image_rights_statement"] = img_rights
    return rec


def parse_europeana_item(item: dict) -> dict | None:
    creators = item.get("dcCreator") or []
    title = (item.get("title") or [""])[0]
    desc = " ".join(item.get("dcDescription") or [])
    blob = " | ".join(creators)
    in_creator = is_philippe_benoist(blob)
    in_title = is_philippe_benoist(title) or "benoist" in title.lower() and is_philippe_benoist(title + " " + blob)
    in_desc = is_philippe_benoist(desc)
    if not (in_creator or in_title or in_desc):
        return None
    if re.search(r"guillaume[\s-]*philippe\s+benoist", blob, re.I) and not in_desc and not re.search(
        r"1813", blob
    ):
        return None
    rights = (item.get("rights") or [None])[0]
    is_drawing = bool(re.search(r"\[?dessin\]?", title, re.I)) or any("Dessinateur" in c for c in creators)
    kind = "drawing" if is_drawing else ("book" if item.get("type") == "TEXT" else "print")
    structured = in_creator and all(
        len(c) < 120 and ";" not in c for c in creators if is_philippe_benoist(c))
    roles = split_roles([c for c in creators if is_philippe_benoist(c)]) if structured else []
    if not structured:
        roles = statement_roles(blob or desc)
    place = None
    for k in ("edmPlaceLabelLangAware",):
        v = (item.get(k) or {})
        if v:
            place = next(iter(v.values()))[0]
    shown_at = (item.get("edmIsShownAt") or [None])[0]
    shown_by = (item.get("edmIsShownBy") or [None])[0]
    eid = item.get("id")
    year = (item.get("year") or [None])[0]
    note = "Creator field names Philippe Benoist." if structured else (
        "Benoist is named only in a free-text field; role and attribution as written by the holder.")
    if is_drawing:
        note += " Drawing (not a lithograph) per the record."
    return make_record(
        source="europeana", id=f"europeana{eid}", title_original=title, kind=kind, place_depicted=place,
        date_as_stated=year, creators=roles, statement_of_responsibility=None if structured else (blob or desc),
        holder=(item.get("dataProvider") or [None])[0], accession_id=eid, record_url=shown_at,
        image_url=shown_by, rights_statement=rights,
        attribution_confidence="high" if structured else "medium", confidence_note=note,
    )


def _named(t: str) -> bool:
    return is_philippe_benoist(t) or "benoist, philippe" in t.lower()


def parse_loc_item(payload: dict) -> dict | None:
    it = payload.get("item") or {}
    stmt = it.get("stmt_of_responsibility") or ""
    names = it.get("related_names") or []
    title_names = " ".join(n.get("title", "") for n in names)
    notes = " ".join(n.get("note", "") for n in it.get("notes") or [])
    named = is_philippe_benoist(title_names) or "benoist, philippe" in title_names.lower()
    stated = is_philippe_benoist(stmt)
    if not (named or stated):
        return None
    roles = [{"name": n["title"], "role_as_stated": n.get("role"), "as_written": n["title"]}
             for n in names if _named(n.get("title", ""))]
    link = it.get("link") or ""
    pk = link.rstrip("/").split("/")[-1]
    date = it.get("created_published_date") or it.get("date")
    rights = it.get("rights_information")
    img = it.get("service_medium") or it.get("service_low")
    note = ("LoC name-authority heading 'Benoist, Philippe, 1813-approximately 1905'"
            + (f"; sheet reads: {stmt}" if stmt else "") + ".")
    if notes:
        note += f" Notes: {notes[:300]}"
    medium = " ".join(m.get("medium", "") for m in it.get("mediums") or [])
    return make_record(
        source="loc", id=f"loc-{pk}", title_original=it.get("title"),
        kind="print" if "lithograph" in medium.lower() or "print" in medium.lower() else "print",
        place_depicted=None, date_as_stated=date, creators=roles, statement_of_responsibility=stmt or None,
        holder="Library of Congress, Prints & Photographs Division", accession_id=it.get("reproduction_number") or pk,
        record_url=link, image_url=img, rights_statement=rights, image_rights_statement=rights,
        attribution_confidence="high" if named else "medium", confidence_note=note,
    )


def parse_met_object(o: dict) -> dict | None:
    name = o.get("artistDisplayName") or ""
    if not is_philippe_benoist(name) and not re.match(r"^philippe benoist$", name.strip(), re.I):
        return None
    pd = bool(o.get("isPublicDomain"))
    rights = "Public domain (Met Open Access, CC0)" if pd else "Not flagged public domain/Open Access by the Met"
    return make_record(
        source="met", id=f"met-{o.get('objectID')}", title_original=o.get("title"), kind="print",
        date_as_stated=o.get("objectDate"),
        creators=[{"name": name, "role_as_stated": o.get("artistRole") or None, "as_written": name}],
        holder="The Metropolitan Museum of Art", accession_id=o.get("accessionNumber"),
        record_url=o.get("objectURL"), image_url=(o.get("primaryImage") or None) if pd else None,
        rights_statement=rights if pd else None, image_rights_statement=rights if pd else None,
        confidence_note=f"Medium: {o.get('medium')}; credit line: {o.get('creditLine')}.",
    )


def parse_aic_row(r: dict) -> dict | None:
    disp = r.get("artist_display") or ""
    if not is_philippe_benoist(disp):
        return None
    pd = bool(r.get("is_public_domain"))
    iiif = f"https://www.artic.edu/iiif/2/{r.get('image_id')}/full/843,/0/default.jpg"
    img = iiif if pd and r.get("image_id") else None
    rights = "Public domain (Art Institute of Chicago: is_public_domain=true; CC0)" if pd else None
    return make_record(
        source="aic", id=f"aic-{r.get('id')}", title_original=r.get("title"), date_as_stated=r.get("date_display"),
        creators=[{"name": disp.split("\n")[0], "role_as_stated": None, "as_written": disp}],
        holder="Art Institute of Chicago", accession_id=str(r.get("id")),
        record_url=f"https://www.artic.edu/artworks/{r.get('id')}", image_url=img, rights_statement=rights,
        confidence_note=f"artist_display: {disp!r}",
    )


def parse_cleveland_row(r: dict) -> dict | None:
    creators = r.get("creators") or []
    desc = " ".join(c.get("description", "") for c in creators)
    if not is_philippe_benoist(desc):
        return None
    cc0 = (r.get("share_license_status") or "").upper() == "CC0"
    img = ((r.get("images") or {}).get("web") or {}).get("url") if cc0 else None
    return make_record(
        source="cleveland", id=f"cma-{r.get('accession_number')}", title_original=r.get("title"),
        date_as_stated=r.get("creation_date"),
        creators=[{"name": c.get("description"), "role_as_stated": c.get("role"), "as_written": c.get("description")}
                  for c in creators],
        holder="The Cleveland Museum of Art", accession_id=r.get("accession_number"), record_url=r.get("url"),
        image_url=img, rights_statement="CC0" if cc0 else (r.get("share_license_status") or None),
        confidence_note="Cleveland creators[] names Philippe Benoist.",
    )


def _la_text(block: list | None) -> list[str]:
    return [b.get("content", "") for b in block or [] if isinstance(b, dict)]


def _dicts(seq) -> list[dict]:
    return [x for x in seq or [] if isinstance(x, dict)]


def parse_rijks_object(obj: dict, people: dict[str, str]) -> dict | None:
    """Rijksmuseum Linked Art object; ``people`` maps person URIs to resolved names."""
    prod = obj.get("produced_by") or {}
    parts = _dicts(prod.get("part")) or [prod]
    creators = []
    for p in parts:
        role = None
        for t in _dicts(p.get("technique")):
            for n in t.get("notation") or []:
                if isinstance(n, dict) and n.get("@language") == "en":
                    role = n.get("@value")
        for a in _dicts(p.get("assigned_by")):
            for who in _dicts(a.get("assigned")):
                nm = people.get(who.get("id"), "")
                if nm:
                    creators.append({"name": nm, "role_as_stated": role, "as_written": nm})
    if not any(is_philippe_benoist(c["name"]) or re.match(r"^philippe benoist$", c["name"], re.I) for c in creators):
        return None
    ident = _dicts(obj.get("identified_by"))
    def is_objnr(i):
        notes = [n for c in _dicts(i.get("classified_as")) for n in c.get("notation", [])]
        return any(isinstance(n, dict) and n.get("@value") == "object number" for n in notes)

    acc = next((i.get("content") for i in ident if i.get("type") == "Identifier" and is_objnr(i)), None)
    titles = [i.get("content") for i in ident if i.get("type") == "Name"]
    html = img = lic = None
    for s in _dicts(obj.get("subject_of")):
        for d in _dicts(s.get("digitally_carried_by")):
            ap = (_dicts(d.get("access_point")) or [{}])[0].get("id")
            if d.get("format") == "text/html":
                html = ap
            elif ap and "iiif" in ap:
                img = ap
                lic = next((r.get("content") for r in _dicts(d.get("referred_to_by")) if r.get("content")), None)
    return make_record(
        source="rijks", id=f"rijks-{acc}",
        title_original=titles[1] if len(titles) > 1 else (titles[0] if titles else None),
        creators=creators, holder="Rijksmuseum", accession_id=acc, record_url=html or obj.get("id"),
        image_url=img, rights_statement=lic, image_rights_statement=lic,
        confidence_note="Creator resolved from Rijksmuseum person record.",
    )


def parse_ia_doc(d: dict) -> dict | None:
    creators = d.get("creator") or []
    if isinstance(creators, str):
        creators = [creators]
    if not any(is_philippe_benoist(c) or re.search(r"\bbenoist\b", c, re.I) and not _OTHER_BENOIST.search(c)
               for c in creators):
        return None
    ident = d.get("identifier")
    lic = d.get("licenseurl") or d.get("rights")
    if isinstance(lic, list):
        lic = lic[0]
    title = d.get("title")
    if isinstance(title, list):
        title = title[0]
    return make_record(
        source="internet_archive", id=f"ia-{ident}", title_original=title, date_as_stated=d.get("date"),
        creators=[{"name": c, "role_as_stated": None, "as_written": c} for c in creators],
        holder="Internet Archive (uploader's holding; see item)", accession_id=ident,
        record_url=f"https://archive.org/details/{ident}", rights_statement=lic,
        attribution_confidence="medium",
        confidence_note="Creator field lists 'Benoist' without first name or role; verify against the sheet.",
    )


def build_known_index(root: Path = ROOT) -> dict:
    """URLs / ids already present in atlas.json and the two curation files."""
    urls, ids = set(), set()

    def add(u):
        if u:
            urls.add(norm_url(u))

    try:
        atlas = json.loads((root / "eras" / "data" / "atlas.json").read_text("utf-8"))
        for c in atlas.get("cities", []):
            for w in c.get("works", []):
                add(w.get("url"))
                ids.add(str(w.get("wid")))
    except (OSError, json.JSONDecodeError):
        pass
    for name in ("benoist-paris-musees-v1.json", "cc0-gallery-20261103.json"):
        try:
            d = json.loads((root / "data" / "curation" / name).read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for it in d.get("items", []):
            add(it.get("url"))
            for k in ("id", "source_id"):
                if it.get(k):
                    ids.add(str(it[k]))
    return {"urls": urls, "ids": ids}


def mark_known(records: list[dict], idx: dict) -> int:
    n = 0
    for r in records:
        hit = None
        if norm_url(r.get("record_url")) in idx["urls"]:
            hit = "record_url"
        elif r.get("accession_id") and str(r["accession_id"]) in idx["ids"]:
            hit = "accession_id"
        if hit:
            r["known"], r["known_match"] = True, hit
            n += 1
    return n


def dedupe(records: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in records:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        out.append(r)
    return out


# --------------------------------------------------------------------------------------------------
# Polite HTTP client
# --------------------------------------------------------------------------------------------------

class Blocked(RuntimeError):
    """Host keeps refusing (429/403/410/...)."""


class Client:
    def __init__(self) -> None:
        self.last: dict[str, float] = {}
        self.n429: dict[str, int] = {}
        self.dead: dict[str, str] = {}
        self.calls: dict[str, int] = {}

    def get(self, url: str, accept: str = "*/*", retries: int = 2):
        host = urllib.parse.urlsplit(url).netloc
        if host in self.dead:
            raise Blocked(f"{host}: {self.dead[host]}")
        for attempt in range(retries + 1):
            gap = MIN_GAP.get(host, DEFAULT_GAP)
            wait = self.last.get(host, 0) + gap - time.time()
            if wait > 0:
                time.sleep(wait)
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
            try:
                with urllib.request.urlopen(req, timeout=40) as r:
                    body = r.read()
                self.last[host] = time.time()
                self.calls[host] = self.calls.get(host, 0) + 1
                self.n429[host] = 0
                return json.loads(body.decode("utf-8"))
            except urllib.error.HTTPError as e:
                self.last[host] = time.time()
                if e.code == 429:
                    self.n429[host] = self.n429.get(host, 0) + 1
                    if self.n429[host] >= MAX_429:
                        self.dead[host] = "HTTP 429 repeated"
                        raise Blocked(f"{host}: HTTP 429 repeated") from e
                    time.sleep(30 * (attempt + 1))
                    continue
                if e.code in (403, 410, 401, 451):
                    self.dead[host] = f"HTTP {e.code}"
                    raise Blocked(f"{host}: HTTP {e.code}") from e
                if e.code == 404:
                    return {}
                if attempt == retries:
                    raise Blocked(f"{host}: HTTP {e.code}") from e
                time.sleep(5)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
                self.last[host] = time.time()
                if attempt == retries:
                    raise Blocked(f"{host}: {type(e).__name__}: {e}"[:200]) from e
                time.sleep(5)
        raise Blocked(f"{host}: gave up")


# --------------------------------------------------------------------------------------------------
# Source runners
# --------------------------------------------------------------------------------------------------

def q(**kw) -> str:
    return urllib.parse.urlencode(kw)


def run_loc(c: Client) -> list[dict]:
    pks: dict[str, str] = {}
    name = "Benoist, Philippe, 1813-approximately 1905"
    for url in (
        "https://www.loc.gov/pictures/related/?" + q(fi="name", q=name, fo="json", c=100),
        "https://www.loc.gov/pictures/search/?" + q(q="Philippe Benoist", fo="json", c=100),
        "https://www.loc.gov/pictures/search/?" + q(q="Ph. Benoist del. Lemercier", fo="json", c=100),
        "https://www.loc.gov/pictures/search/?" + q(q="Benoist lithographer Paris views", fo="json", c=100),
    ):
        try:
            d = c.get(url)
        except Blocked:
            if c.dead.get("www.loc.gov"):
                break
            continue
        for r in d.get("results", []):
            link = (r.get("links") or {}).get("item")
            if link:
                pks[link] = r.get("title", "")
    out = []
    t0 = time.time()
    for n, link in enumerate(pks):
        if n >= LOC_MAX_ITEMS or time.time() - t0 > LOC_BUDGET_S:
            print(f"loc: stopped item fetches at {n}/{len(pks)} (budget)", file=sys.stderr)
            break
        try:
            d = c.get(link.rstrip("/") + "/?fo=json")
        except Blocked:
            if c.dead.get("www.loc.gov"):
                break
            continue
        rec = parse_loc_item(d)
        if rec:
            out.append(rec)
    if not out and c.dead.get("www.loc.gov"):
        raise Blocked(f"www.loc.gov: {c.dead['www.loc.gov']}")
    return out


def run_europeana(c: Client) -> list[dict]:
    out = []
    for query in (
        '"Philippe Benoist"', '"Benoist, Philippe"', '"Ph. Benoist"', "Benoist lithographe Lemercier",
        "Benoist Paris dans sa splendeur", "Benoist Rome dans sa grandeur", "Benoist Paris et ses environs",
        "Benoist lithograph Paris", "Benoist Jacottet",
    ):
        start = 1
        while start < 300:
            d = c.get("https://api.europeana.eu/record/v2/search.json?" + q(
                wskey=EUROPEANA_KEY, query=query, rows=100, start=start, profile="rich"))
            items = d.get("items", [])
            for it in items:
                rec = parse_europeana_item(it)
                if rec:
                    out.append(rec)
            if len(items) < 100:
                break
            start += 100
    return out


def run_met(c: Client) -> list[dict]:
    ids: list[int] = []
    for query in ("Philippe Benoist", "Benoist lithograph", "Benoist Paris"):
        d = c.get("https://collectionapi.metmuseum.org/public/collection/v1.1/search?" + q(q=query, limit=100))
        ids += d.get("objectIDs") or []
    out = []
    for oid in dict.fromkeys(ids):
        rec = parse_met_object(c.get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}"))
        if rec:
            out.append(rec)
    return out


def run_aic(c: Client) -> list[dict]:
    out = []
    for query in ('"Philippe Benoist"', "Benoist lithograph"):
        d = c.get("https://api.artic.edu/api/v1/artworks/search?" + q(
            q=query, limit=100, fields="id,title,artist_display,date_display,is_public_domain,image_id"))
        for r in d.get("data", []):
            rec = parse_aic_row(r)
            if rec:
                out.append(rec)
    return out


def run_cleveland(c: Client) -> list[dict]:
    d = c.get("https://openaccess-api.clevelandart.org/api/artworks/?" + q(q="Benoist", limit=100, has_image=0))
    return [r for r in (parse_cleveland_row(x) for x in d.get("data", [])) if r]


def run_rijks(c: Client) -> list[dict]:
    d = c.get("https://data.rijksmuseum.nl/search/collection?" + q(creator="Philippe Benoist"),
               accept="application/ld+json")
    out, people = [], {}
    for it in d.get("orderedItems", []):
        obj = c.get(it["id"], accept="application/ld+json")
        for part in _dicts((obj.get("produced_by") or {}).get("part")):
            for a in _dicts(part.get("assigned_by")):
                for who in _dicts(a.get("assigned")):
                    pid = who.get("id")
                    if pid and pid not in people:
                        pd = c.get(pid, accept="application/ld+json")
                        names = [i.get("content") for i in _dicts(pd.get("identified_by")) if i.get("type") == "Name"]
                        people[pid] = names[0] if names else ""
        rec = parse_rijks_object(obj, people)
        if rec:
            out.append(rec)
    return out


def run_ia(c: Client) -> list[dict]:
    out = []
    for query in ("creator:(Benoist) AND mediatype:image", 'creator:("Philippe Benoist")',
                  '"Ph. Benoist" AND mediatype:image'):
        d = c.get("https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
            [("q", query), ("fl[]", "identifier"), ("fl[]", "title"), ("fl[]", "creator"), ("fl[]", "date"),
             ("fl[]", "licenseurl"), ("fl[]", "rights"), ("rows", 100), ("output", "json")]))
        for doc in (d.get("response") or {}).get("docs", []):
            rec = parse_ia_doc(doc)
            if rec:
                out.append(rec)
    return out


NGA_BASE = "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/"
NGA_ID = "3497"  # constituent "Benoist, Philippe" (French, 1813 - in or after 1879) in NGA open data


def stream_csv(url: str):
    """Yield dict rows of a (large) CSV from the NGA open data repository."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            yield from csv.DictReader(io.TextIOWrapper(r, encoding="utf-8", newline=""))
    except (urllib.error.URLError, OSError) as e:
        raise Blocked(f"raw.githubusercontent.com: {e}"[:200]) from e


def parse_nga(obj_row: dict, role_rows: list[dict], image: dict | None) -> dict:
    oid = obj_row["objectid"]
    roles = [{"name": "Philippe Benoist", "role_as_stated": r.get("role") or None, "as_written": r.get("role", "")}
             for r in role_rows]
    open_img = bool(image and image.get("openaccess") == "1")
    stmt = "NGA Open Data: image flagged openaccess=1 (National Gallery of Art Open Access, CC0)" if open_img else None
    return make_record(
        source="nga", id=f"nga-{oid}", title_original=obj_row.get("title"), date_as_stated=obj_row.get("displaydate"),
        creators=roles, holder="National Gallery of Art, Washington", accession_id=obj_row.get("accessionnum"),
        record_url=f"https://www.nga.gov/artworks/{oid}", rights_statement=stmt,
        image_url=(image["iiifurl"] + "/full/!1200,1200/0/default.jpg") if open_img else None,
        image_rights_statement=stmt,
        confidence_note=f"NGA constituent 3497 'Benoist, Philippe'; medium: {obj_row.get('medium')}; "
                        f"classification: {obj_row.get('classification')}; series/volume: "
                        f"{obj_row.get('series') or '-'} / {obj_row.get('volume') or '-'}.",
    )


def run_nga(c: Client) -> list[dict]:
    roles: dict[str, list[dict]] = {}
    for row in stream_csv(NGA_BASE + "objects_constituents.csv"):
        if row["constituentid"] == NGA_ID:
            roles.setdefault(row["objectid"], []).append(row)
    objs = {}
    for row in stream_csv(NGA_BASE + "objects.csv"):
        if row["objectid"] in roles:
            objs[row["objectid"]] = row
    images: dict[str, dict] = {}
    for row in stream_csv(NGA_BASE + "published_images.csv"):
        oid = row["depictstmsobjectid"]
        if oid in roles and (oid not in images or row.get("viewtype") == "primary"):
            images[oid] = row
    return [parse_nga(o, roles[i], images.get(i)) for i, o in objs.items()]


def probe(c: Client, url: str) -> dict:
    try:
        c.get(url)
        return {"status": "reachable", "records": 0, "note": "probe only; no Benoist query implemented for this host"}
    except Blocked as e:
        return {"status": "failed", "records": 0, "error": str(e)}


RUNNERS = [("loc", run_loc), ("europeana", run_europeana), ("met", run_met), ("aic", run_aic),
           ("cleveland", run_cleveland), ("rijks", run_rijks), ("internet_archive", run_ia),
           ("nga", run_nga)]
PROBES = [
    ("parismusees", "https://apicollections.parismusees.paris.fr/jsonapi/node/oeuvre?page%5Blimit%5D=1",
     "Paris Musées JSON:API; the 10 Carnavalet sheets are already curated in benoist-paris-musees-v1.json"),
    ("gallica", "https://gallica.bnf.fr/SRU?operation=searchRetrieve&version=1.2&maximumRecords=1&"
     + q(query='dc.creator all "Benoist"'), "Gallica SRU returns XML, often blocked; BnF items reach us via Europeana"),
    ("commons", "https://commons.wikimedia.org/w/api.php?" + q(
        action="query", format="json", list="search", srsearch="Philippe Benoist lithograph", srnamespace=6, srlimit=1),
     "Wikimedia Commons API"),
]


def main(argv: list[str] | None = None) -> int:
    """``--only loc,met`` re-runs just those sources and merges them into the existing output file."""
    argv = sys.argv[1:] if argv is None else argv
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else set()
    c = Client()
    sources, records = {}, []
    if only and OUT.exists():
        prev = json.loads(OUT.read_text("utf-8"))
        sources = dict(prev.get("sources_tried", {}))
        records = [r for r in prev.get("records", []) if r["source"] not in only]
    for name, fn in RUNNERS:
        if only and name not in only:
            continue
        t0 = time.time()
        try:
            recs = fn(c)
            sources[name] = {"status": "ok", "records": len(recs), "seconds": round(time.time() - t0)}
            records += recs
            print(f"{name}: {len(recs)}", file=sys.stderr)
        except (Blocked, KeyError, TypeError, AttributeError, ValueError) as e:
            sources[name] = {"status": "failed", "records": 0, "error": f"{type(e).__name__}: {e}"[:200]}
            print(f"{name}: FAILED {e}", file=sys.stderr)
    for name, url, note in PROBES:
        if only:
            break
        res = probe(c, url)
        res["note"] = res.get("note") or note
        if res["status"] == "failed":
            res["note"] = note
        sources[name] = res
        print(f"{name}: {res['status']}", file=sys.stderr)
    records = dedupe(records)
    idx = build_known_index()
    known = mark_known(records, idx)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "version": "2026-11-21",
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "Prints and drawings attributed to Philippe Benoist (1813-1905) in open catalogue APIs.",
        "policy": "Fields copied from source records; image_url only where the source states an open licence "
                  "for the image; rights_class open|link.",
        "sources_tried": sources,
        "summary": {
            "records": len(records), "known": known, "new": len(records) - known,
            "open_image_rights": sum(1 for r in records if r["image_url"]),
        },
        "records": records,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps(doc["summary"]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
