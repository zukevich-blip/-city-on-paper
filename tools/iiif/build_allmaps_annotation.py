#!/usr/bin/env python3
"""Convert vetted research GCP pairs into a DRAFT IIIF Georeference Annotation.

No network access; retains research uncertainty. A convex-hull mask excludes
uncontrolled sheet corners and insets rather than pretending whole-map precision.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "data/vision-lab/georef-paris-1878.json"
DEFAULT_DEST = ROOT / "data/research/paris-1878-georeference-draft.json"
DEFAULT_ID = (
    "https://raw.githubusercontent.com/zukevich-blip/-city-on-paper/"
    "feature/iiif-manifest-evidence-20261108/"
    "data/research/paris-1878-georeference-draft.json"
)


def convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Return hull in counterclockwise order, omitting collinear interior points."""
    ordered = sorted(set(points))
    if len(ordered) < 3:
        raise ValueError("At least 3 unique source pixels required")

    def cross(a: tuple, b: tuple, c: tuple) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    lower: list[tuple[float, float]] = []
    upper: list[tuple[float, float]] = []
    for point in ordered:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    for point in reversed(ordered):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        raise ValueError("GCPs are collinear; cannot create a map mask")
    return hull


def build(source: dict, annotation_id: str) -> dict:
    width = source["pixel_space"]["width"]
    height = source["pixel_space"]["height"]
    gcps = source["gcps"]
    service = source["iiif_service"]
    if not (isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0):
        raise ValueError("Invalid image dimensions")
    if not (isinstance(service, str) and service.startswith("https://")):
        raise ValueError("Need a real official https IIIF Image Service")
    if not (isinstance(annotation_id, str) and annotation_id.startswith("https://")):
        raise ValueError("Annotation id must be its absolute source URL")
    if len(gcps) < 6:
        raise ValueError("At least six research GCPs required")

    pixels: list[tuple[float, float]] = []
    features = []
    for gcp in gcps:
        x, y, lon, lat = (gcp[key] for key in ("px", "py", "lon", "lat"))
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (x, y, lon, lat)):
            raise ValueError(f"Invalid GCP numbers: {gcp.get('name')}")
        if not (0 <= x <= width and 0 <= y <= height and -180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError(f"GCP outside image or geographic range: {gcp.get('name')}")
        pixels.append((x, y))
        features.append({
            "type": "Feature",
            "properties": {
                "resourceCoords": [x, y],
                "label": gcp["name"],
                "confidence": gcp["pick_confidence"],
            },
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
        })

    hull = convex_hull(pixels)
    # Match JavaScript Math.round for positive pixel coordinates.
    polygon = " ".join(f"{math.floor(x + 0.5)},{math.floor(y + 0.5)}" for x, y in hull)
    selector = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<polygon points="{polygon}"/></svg>'
    )
    return {
        "@context": [
            "http://iiif.io/api/extension/georef/1/context.json",
            "http://iiif.io/api/presentation/3/context.json",
        ],
        "id": annotation_id,
        "type": "Annotation",
        "motivation": "georeferencing",
        "target": {
            "type": "SpecificResource",
            "source": {"id": service, "type": "ImageService2", "width": width, "height": height},
            "selector": {"type": "SvgSelector", "value": selector},
        },
        "body": {
            "type": "FeatureCollection",
            "transformation": {"type": "polynomial", "options": {"order": 1}},
            "features": features,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--id", default=DEFAULT_ID, help="Public URL of the exact JSON annotation")
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    doc = build(source, args.id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Draft written: {len(doc['body']['features'])} GCPs at {args.output}")


if __name__ == "__main__":
    main()
