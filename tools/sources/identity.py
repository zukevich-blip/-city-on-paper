"""Rule-based Benoist disambiguation hints. Output is a *hint* for a curator, never an attribution.

Wikidata checked 2026-11-01 (wbgetentities / wbsearchentities):
  Q277187   Félix Benoist      1818-04-15 – 1896-09-20  ULAN 500104203  BnF 118912350
  Q26309223 Philippe Benoist   1813 – 1896-11-01        ULAN 500009717  BnF 14962134k
            (LoC and Commons give "approximately 1905"; BnF via Europeana gives 1813-1905: CONFLICT)
  Q5616064  Guillaume Philippe Benoist, engraver, 1725 – 1770 per Wikidata (Met says 1725–1800: CONFLICT)
  Q18526511 Antoine Benoist, draughtsman/engraver 1721–1770 (different person)
  Q117312510 is a Renaissance composer, NOT a duplicate of Philippe Benoist (PR #3 said otherwise).
"""

from __future__ import annotations

import re

from tools.sources.connectors import fold

IDENTITIES = {
    "felix": {"label": "Félix Benoist", "wikidata": "Q277187"},
    "philippe": {"label": "Philippe Benoist", "wikidata": "Q26309223"},
    "guillaume_philippe": {"label": "Guillaume Philippe Benoist", "wikidata": "Q5616064"},
    "antoine": {"label": "Antoine Benoist (1721–1770)", "wikidata": "Q18526511"},
}


def _year(date: str) -> int | None:
    m = re.search(r"(1[5-9]\d\d)", date or "")
    return int(m.group(1)) if m else None


def benoist_hint(creator: str, date: str = "") -> dict:
    c = fold(creator)
    if "benoist" not in c:
        return {"hint": "not_benoist", "reason": "no 'Benoist' in creator field"}
    found = []
    if "guillaume" in c:
        found.append("guillaume_philippe")
    if "felix" in c:
        found.append("felix")
    if "antoine" in c:
        found.append("antoine")
    if "guillaume" not in c and re.search(r"philippe|phillipe|\bph\b|\bp\b", c):
        y = _year(date)
        if (y and y < 1800) or "18th century" in c:
            return {"hint": "uncertain", "reason": f"'Philippe' with date {y} < 1800: check Guillaume Philippe Benoist"}
        found.append("philippe")
    if not found:
        return {"hint": "unresolved_other_benoist", "reason": "Benoist without a resolvable forename/role"}
    return {"hint": "+".join(found), "candidates": [IDENTITIES[f] for f in found],
            "reason": "forename match in provider creator field; confirm against holding institution"}
