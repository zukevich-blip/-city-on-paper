#!/usr/bin/env python3
"""Propose duplicate groups of Benoist records across catalogues WITHOUT merging uncertain pairs.

The registry's strict key (artist | series | plate | normalised title) only merges records whose key is identical.
This module adds a fuzzy step: normalised title tokens, place, series, plate number and date are compared across
catalogues (BnF ``cb`` notices, Gallica ``btv1b`` arks, Europeana, Paris Musees, Rijksmuseum, ...).

Output (data/research/benoist/duplicate-groups-v1.json) is a PROPOSAL:
* ``high``   - same identifier (ark / record page), or the same distinctive title with corroborating facts and
  no conflict;
* ``medium`` - very similar title, nothing conflicting, but not enough to say it is the same sheet.
Medium groups are never merged by this module; they only feed the "likely" estimate. Nothing is assigned to
Philippe or Felix here: two records with different known artist_id never match, and a record that names Guillaume
Philippe Benoist or Antoine Benoist is kept out of every group.

Usage: python3 -m tools.world.benoist_dedupe
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "data" / "research" / "benoist"
OUT = RESEARCH / "duplicate-groups-v1.json"
SKIP_FILES = {"registry-v1.json", "duplicate-groups-v1.json", "photo-pairs-report-v1.json"}

STOPWORDS = frozenset(
    "a au aux de des du d l la le les et en sur sous dans par pour un une the of and view views vue vues estampe "
    "lithographie lith litho print plate planche pl del dessine dessin nature apres ansicht".split()
)
# Words that flag a different composition of the same building (an interior is not the exterior, north is not south).
DISTINCTIVE = frozenset(
    "interieur exterieur interior exterior nord sud est ouest nord-est cote facade portail choeur nef plan carte "
    "portrait jardin cour escalier coupe detail details vue-generale".split()
)
OTHER_BENOIST = re.compile(r"\b(guillaume|antoine)\b.{0,20}\bbenoist\b|\bbenoist\b.{0,3}\b(guillaume|antoine)\b", re.I)
ARK_BTV = re.compile(r"btv1b[0-9a-z]+", re.I)
ARK_CB = re.compile(r"\bcb\d{8}[0-9a-z]\b", re.I)
YEAR = re.compile(r"\b(1[5-9]\d{2})\b")


INSTITUTION_ALIAS = {
    "national library of france": "bibliotheque nationale de france",
    "bnf": "bibliotheque nationale de france",
    "bibliotheque nationale de france departement estampes et photographie": "bibliotheque nationale de france",
}

# ---------------------------------------------------------------- normalisation (pure)


def fold(text: str | None) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


RESPONSIBILITY = re.compile(
    r"benoist|\bdess|\blith|\bdel\b|\bpar\b|d'apr|\btexte\b|\bsc\b|\bimp\b|\bed\b|\bsculps", re.I
)
SERIES_PHRASES = tuple(
    re.compile(p)
    for p in (
        r"paris dans sa splendeur",
        r"promenade dans paris et (?:ses )?environs",
        r"vues? de paris",
        r"rome dans sa grandeur",
        r"nice et savoie",
    )
)
VOLUME = re.compile(r"\b(?:volume|vol|tome|band|bd)\s*\.?\s*([ivx]+|\d+)\b")


def title_core(title: str | None) -> str:
    """Title without statement-of-responsibility segments; ' / ' inside a title (series / subtitle) is kept."""
    parts = re.split(r"\s/\s|\s\|\s", re.sub(r"\[[^\]]*\]", " ", title or ""))
    keep = [p for i, p in enumerate(parts) if i == 0 or not RESPONSIBILITY.search(p)]
    return " ".join(keep)


def volume_of(title: str | None) -> str | None:
    m = VOLUME.search(fold(title))
    return m.group(1) if m else None


def title_tokens(title: str | None) -> frozenset[str]:
    """Distinctive tokens of the title: no articles, genre words, series phrase or volume marker; light plural strip."""
    flat = fold(title_core(title))
    for pat in SERIES_PHRASES:
        flat = pat.sub(" ", flat)
    flat = VOLUME.sub(" ", flat)
    out = set()
    for tok in flat.split():
        if tok in STOPWORDS or (len(tok) < 2 and not tok.isdigit()):
            continue
        if len(tok) > 4 and tok[-1] in "sx":
            tok = tok[:-1]
        out.add(tok)
    return frozenset(out)


def years(text: str | None) -> tuple[int, int] | None:
    ys = [int(y) for y in YEAR.findall(text or "")]
    return (min(ys), max(ys)) if ys else None


def arks(rec: dict) -> set[str]:
    blob = " ".join(str(rec.get(k) or "") for k in ("record_id", "record_url", "image_url", "iiif_manifest"))
    return {m.lower() for m in ARK_BTV.findall(blob)} | {m.lower() for m in ARK_CB.findall(blob)}


def norm_url(url: str | None) -> str:
    u = re.sub(r"^https?://(www\.)?", "", (url or "").lower()).split("?")[0].rstrip("/")
    return re.sub(r"^(parismuseescollections\.paris\.fr)/(fr|en|de|ru|zh-hans)/", r"\1/", u)


def family(rec: dict) -> str:
    """Catalogue family. BnF cb notices, Gallica btv1b arks and Europeana stay different families."""
    rid = rec.get("record_id") or ""
    if rid.startswith("europeana:") and "btv1b" in rid:
        return "europeana-bnf"
    head = rid.split(":", 1)[0]
    if head == "legacy":
        inst = fold(rec.get("institution"))
        return "legacy-" + (inst.split(" ")[0] if inst else "unknown")
    return head or "unknown"


def mentions_other_benoist(rec: dict) -> bool:
    names = [str(p.get("name") or "") for p in rec.get("participants") or []]
    names.append(str(rec.get("attribution_note") or ""))
    return any(OTHER_BENOIST.search(n) for n in names)


def is_plate_placeholder(rec: dict) -> bool:
    """Heidelberg 'Planche N' canvases carry no title of the composition: they cannot be matched by title."""
    rid = rec.get("record_id") or ""
    return fold(rec.get("original_title")).startswith("planche ") and rid.startswith("heidelberg:")


def features(rec: dict) -> dict:
    series = fold(rec.get("series")) or None
    plate = re.sub(r"\D", "", str(rec.get("plate_number") or "")) or None
    place = frozenset(t for t in fold(rec.get("place")).split() if t not in STOPWORDS)
    return {
        "id": rec["record_id"],
        "artist": rec.get("artist_id") or "uncertain-benoist",
        "tokens": title_tokens(rec.get("original_title")),
        "series": series,
        "volume": volume_of(rec.get("original_title")) or volume_of(rec.get("volume")),
        "plate": plate,
        "place": place,
        "years": years(rec.get("date_as_stated")),
        "family": family(rec),
        "institution": INSTITUTION_ALIAS.get(fold(rec.get("institution")), fold(rec.get("institution"))),
        "arks": arks(rec),
        "url": norm_url(rec.get("record_url")),
        "bookish": rec.get("object_type") in {"book", "volume", "album"},
        "excluded": mentions_other_benoist(rec) or is_plate_placeholder(rec),
    }


# ---------------------------------------------------------------- pair comparison (pure)


def years_conflict(a: tuple[int, int] | None, b: tuple[int, int] | None, slack: int = 3) -> bool:
    if not a or not b:
        return False
    return a[0] - slack > b[1] or b[0] - slack > a[1]


def compare(fa: dict, fb: dict) -> dict | None:
    """Return {confidence, rules, evidence} for a pair, or None when it must not be proposed."""
    if fa["excluded"] or fb["excluded"]:
        return None
    known = {fa["artist"], fb["artist"]} - {"uncertain-benoist"}
    if len(known) > 1:  # Philippe vs Felix (or vs 'other'): never
        return None
    evidence: list[str] = []
    same_ark = fa["arks"] & fb["arks"]
    if same_ark:
        evidence.append("same ark identifier: " + ", ".join(sorted(same_ark)))
    if fa["url"] and fa["url"] == fb["url"]:
        evidence.append("same record page after URL normalisation")
    if evidence:
        return {"confidence": "high", "rules": ["identifier"], "evidence": evidence}
    ta, tb = fa["tokens"], fb["tokens"]
    if not ta or not tb:
        return None
    if fa["plate"] and fb["plate"] and fa["plate"] != fb["plate"]:
        return None
    if fa["series"] and fb["series"] and fa["series"] != fb["series"]:
        return None
    if fa["volume"] and fb["volume"] and fa["volume"] != fb["volume"]:
        return None
    if years_conflict(fa["years"], fb["years"]):
        return None
    if (ta ^ tb) & DISTINCTIVE:
        return None
    if fa["place"] and fb["place"] and not (fa["place"] & fb["place"]):
        return None
    inter = ta & tb
    if len(inter) < 3:
        return None
    jaccard = len(inter) / len(ta | tb)
    contained = (ta <= tb or tb <= ta) and len(inter) >= 4 and abs(len(ta) - len(tb)) <= 2
    exact = ta == tb
    if not exact and jaccard < 0.75 and not contained:
        return None
    corroborators = []
    if fa["plate"] and fa["plate"] == fb["plate"] and fa["series"] and fa["series"] == fb["series"]:
        corroborators.append(f"same series '{fa['series']}' and plate {fa['plate']}")
    if fa["years"] and fb["years"]:
        corroborators.append(f"compatible dates {fa['years']} / {fb['years']}")
    if fa["place"] and fb["place"]:
        corroborators.append("shared place tokens: " + ", ".join(sorted(fa["place"] & fb["place"])))
    if fa["series"] and fa["series"] == fb["series"]:
        corroborators.append(f"same series '{fa['series']}'")
    evidence = [
        f"title tokens {'identical' if exact else f'jaccard {jaccard:.2f}'}: {' '.join(sorted(inter))}",
        f"{len(inter)} shared tokens",
        *corroborators,
    ]
    same_inst = bool(fa["institution"]) and fa["institution"] == fb["institution"]
    if same_inst and not exact:  # one museum with two differently worded titles: different compositions until proven
        return None
    if exact and len(ta) >= 4 and (same_inst or corroborators):
        conf = "high"
    elif exact and len(ta) >= 3 and corroborators:
        conf = "high"
    else:
        conf = "medium"
    if fa["bookish"] or fb["bookish"]:
        conf = "medium"
        evidence.append("book/volume/album record: editions and printings differ, capped at medium")
    if "uncertain-benoist" in (fa["artist"], fb["artist"]) and known:
        conf = "medium"
        evidence.append("one record is uncertain-benoist: capped at medium")
    return {"confidence": conf, "rules": ["title-tokens"], "evidence": evidence}


# ---------------------------------------------------------------- grouping (pure)


class UnionFind:
    def __init__(self, items):
        self.parent = {i: i for i in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra

    def components(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = defaultdict(list)
        for i in self.parent:
            out[self.find(i)].append(i)
        return out


def candidate_pairs(feats: list[dict]):
    """Pairs sharing an ark, a URL or at least two title tokens (inverted index, no O(n^2) scan of the rest)."""
    by_token: dict[str, list[int]] = defaultdict(list)
    by_key: dict[str, list[int]] = defaultdict(list)
    for i, f in enumerate(feats):
        for t in f["tokens"]:
            by_token[t].append(i)
        for k in f["arks"] | ({f["url"]} if f["url"] else set()):
            by_key[k].append(i)
    seen: set[tuple[int, int]] = set()
    counts: Counter = Counter()
    for idxs in by_token.values():
        if len(idxs) > 400:
            continue
        for pair in combinations(idxs, 2):
            counts[pair] += 1
    for pair, n in counts.items():
        if n >= 2:
            seen.add(pair)
    for idxs in by_key.values():
        seen.update(combinations(idxs, 2))
    return sorted(seen)


def strict_key(rec: dict) -> str:
    """Same rule as tools.world.build_benoist_registry.group_key (kept local so this module stays pure)."""
    hint = rec.get("duplicate_hint")
    artist = rec.get("artist_id") or "uncertain-benoist"
    if hint:
        return f"{artist}|{hint}"
    series = fold(rec.get("series") or "")
    title = fold(
        re.sub(
            r"\(\s*\d+\s*\)|\bviews of paris\b|\bvues de paris\b", " ", (rec.get("original_title") or "").split("/")[0]
        )
    )
    return f"{artist}|{series}|{rec.get('plate_number') or ''}|{title}"


def propose_groups(records: list[dict]) -> dict:
    feats = [features(r) for r in records]
    by_id = {f["id"]: f for f in feats}
    rec_by_id = {r["record_id"]: r for r in records}
    edges: list[tuple[str, str, dict]] = []
    for i, j in candidate_pairs(feats):
        res = compare(feats[i], feats[j])
        if res:
            edges.append((feats[i]["id"], feats[j]["id"], res))
    strict = UnionFind(by_id)
    first_by_key: dict[str, str] = {}
    for r in records:
        k = strict_key(r)
        if k in first_by_key:
            strict.union(first_by_key[k], r["record_id"])
        else:
            first_by_key[k] = r["record_id"]
    high = UnionFind(by_id)
    for rid in by_id:
        high.union(strict.find(rid), rid)
    for a, b, res in edges:
        if res["confidence"] == "high":
            high.union(a, b)
    likely = UnionFind(by_id)
    for rid in by_id:
        likely.union(high.find(rid), rid)
    # medium: complete linkage over high clusters, so a chain of weak pairs cannot drift into one group
    high_comp = high.components()
    cluster_of = {rid: root for root, ids in high_comp.items() for rid in ids}
    pair_ok: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    for a, b, _res in edges:
        ca, cb = cluster_of[a], cluster_of[b]
        if ca != cb:
            pair_ok[tuple(sorted((ca, cb)))].add(tuple(sorted((a, b))))
    for (ca, cb), ok in sorted(pair_ok.items()):
        need = {tuple(sorted(p)) for p in ((x, y) for x in high_comp[ca] for y in high_comp[cb])}
        usable = {p for p in need if not (by_id[p[0]]["excluded"] or by_id[p[1]]["excluded"])}
        if usable and usable <= ok:
            likely.union(ca, cb)
    edge_by_pair = {tuple(sorted((a, b))): res for a, b, res in edges}

    def build(components: dict[str, list[str]], level: str) -> list[dict]:
        groups = []
        for ids in components.values():
            if len(ids) < 2 or any(by_id[i]["excluded"] for i in ids):
                continue
            ids = sorted(ids)
            evidence = []
            for a, b in combinations(ids, 2):
                res = edge_by_pair.get((a, b))
                if res:
                    evidence.append({"pair": [a, b], "confidence": res["confidence"], "evidence": res["evidence"]})
            strict_roots = {strict.find(i) for i in ids}
            groups.append(
                {
                    "confidence": level,
                    "members": [
                        {
                            "record_id": i,
                            "catalogue": by_id[i]["family"],
                            "institution": rec_by_id[i].get("institution"),
                            "artist_id": by_id[i]["artist"],
                            "title": rec_by_id[i].get("original_title"),
                            "record_url": rec_by_id[i].get("record_url"),
                        }
                        for i in ids
                    ],
                    "catalogues": sorted({by_id[i]["family"] for i in ids}),
                    "artist_ids": sorted({by_id[i]["artist"] for i in ids}),
                    "already_one_strict_work": len(strict_roots) == 1,
                    "merges_strict_works": len(strict_roots),
                    "evidence": evidence,
                    "auto_merge": False,
                }
            )
        return groups

    high_groups = build(high.components(), "high")
    high_roots = {high.find(m["record_id"]) for g in high_groups for m in g["members"]}
    likely_groups = [
        g
        for g in build(likely.components(), "medium")
        if len({high.find(m["record_id"]) for m in g["members"]}) > 1
    ]
    del high_roots
    strict_n = len(strict.components())
    high_n = len(high.components())
    likely_n = len(likely.components())
    excluded = [i for i, f in by_id.items() if f["excluded"]]
    for n, g in enumerate(high_groups, 1):
        g["group_id"] = f"dg-high-{n:04d}"
    for n, g in enumerate(likely_groups, 1):
        g["group_id"] = f"dg-medium-{n:04d}"
    return {
        "summary": {
            "records": len(records),
            "unique_works_strict": strict_n,
            "unique_works_after_high": high_n,
            "unique_works_likely": likely_n,
            "high_groups": len(high_groups),
            "high_groups_new_vs_strict": sum(1 for g in high_groups if not g["already_one_strict_work"]),
            "medium_groups": len(likely_groups),
            "excluded_records": len(excluded),
        },
        "excluded_record_ids": sorted(excluded),
        "high_groups": high_groups,
        "medium_groups": likely_groups,
    }


# ---------------------------------------------------------------- IO


def load_raw() -> list[dict]:
    """Every record of every research file plus the legacy harvest, exactly as the registry reads them."""
    records: list[dict] = []
    legacy = ROOT / "data" / "curation" / "benoist-harvest-v1.json"
    if legacy.exists():
        from tools.world.build_benoist_registry import legacy_to_schema  # read-only reuse of the legacy mapping

        records += [legacy_to_schema(r) for r in json.loads(legacy.read_text(encoding="utf-8"))["records"]]
    for f in sorted(RESEARCH.glob("*.json")):
        if f.name in SKIP_FILES:
            continue
        records += json.loads(f.read_text(encoding="utf-8")).get("records", [])
    return records


def unique_by_record_id(records: list[dict]) -> list[dict]:
    """The same record_id arrives from several files (e.g. Europeana in two harvests): identity, keep the first."""
    seen, out = set(), []
    for r in records:
        if r["record_id"] not in seen:
            seen.add(r["record_id"])
            out.append(r)
    return out


def main() -> int:
    raw = load_raw()
    records = unique_by_record_id(raw)
    result = propose_groups(records)
    result["summary"]["raw_records_read"] = len(raw)
    result["summary"]["duplicate_record_id_rows"] = len(raw) - len(records)
    result["summary"]["unique_works_registry_strict"] = len({strict_key(r) for r in raw})
    doc = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy": (
            "Proposal only. auto_merge is false everywhere. high = identifier or distinctive identical title with "
            "corroboration and no conflict; medium = similar title, no conflict, needs curator review. Philippe and "
            "Felix never share a group; Guillaume Philippe / Antoine Benoist records are excluded. "
            "unique_works_registry_strict is what build_benoist_registry.py counts today (same record_id read twice "
            "with different hints counts twice); unique_works_strict already treats an equal record_id as one record."
        ),
        **result,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
