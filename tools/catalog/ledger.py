"""Writes the one-line-per-work curatorial ledger CSV from data/catalog/works/*.json (stdlib only).

Usage: python3 -m tools.catalog.ledger [out.csv]
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from tools.catalog.validate import DEFAULT_WORKS, ROOT

FIELDS = ["id", "title", "artists_roles", "date", "institution", "object_url",
          "attribution_status", "licensing_status", "redistribution", "series"]


def rows(works_dir: Path = DEFAULT_WORKS) -> list[dict]:
    out = []
    for f in sorted(works_dir.glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        agents = "; ".join(f"{a['name']} ({a['role']}, {a['certainty']})" for a in r["agents"])
        series = r.get("series") or {}
        out.append({
            "id": r["id"],
            "title": r["titles"][0]["text"],
            "artists_roles": agents,
            "date": (r.get("date") or {}).get("display", ""),
            "institution": r["holding"]["institution"],
            "object_url": r["holding"]["object_url"],
            "attribution_status": r["review"]["attribution"]["status"],
            "licensing_status": r["review"]["licensing"]["status"],
            "redistribution": r["rights"].get("redistribution", ""),
            "series": " / ".join(v for v in (series.get("title"), series.get("volume"), series.get("plate")) if v),
        })
    return out


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    out = Path(args[0]) if args else ROOT / "data" / "catalog" / "ledger-2026-11-01.csv"
    data = rows()
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(data)
    print(f"{len(data)} rows -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
