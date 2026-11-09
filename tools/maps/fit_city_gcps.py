#!/usr/bin/env python3
"""Research-only affine georeferencing for any city with separately recorded GCPs.

Input is a local JSON with 4+ *review candidates* and optional 1+ hold-outs.
Nothing here independently validates that the pixels designate real landmarks.
For polar, dateline-crossing or heavily distorted maps use qualified GIS tooling.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

R = 6_378_137.0


def solve3(matrix: list[list[float]], vector: list[float]) -> list[float]:
    a = [list(matrix[i]) + [vector[i]] for i in range(3)]
    for i in range(3):
        piv = max(range(i, 3), key=lambda j: abs(a[j][i]))
        if abs(a[piv][i]) < 1e-10:
            raise ValueError("Degenerate GCP geometry: collinear or duplicate points")
        a[i], a[piv] = a[piv], a[i]
        v = a[i][i]
        for k in range(i, 4):
            a[i][k] /= v
        for j in range(3):
            if j != i:
                mult = a[j][i]
                for k in range(i, 4):
                    a[j][k] -= mult * a[i][k]
    return [a[i][3] for i in range(3)]


def fit3(features: list[tuple[float, float, float]], targets: list[float]) -> list[float]:
    matrix = [[sum(x[i] * x[j] for x in features) for j in range(3)]
              for i in range(3)]
    vector = [sum(x[i] * y for x, y in zip(features, targets, strict=True))
              for i in range(3)]
    return solve3(matrix, vector)


def validate_point(p: dict, w: int, h: int) -> None:
    for field in ("px", "py", "lon", "lat"):
        if not isinstance(p.get(field), (int, float)) or not math.isfinite(p[field]):
            raise ValueError("Missing/nonfinite GCP " + field)
    if not (0 <= p["px"] <= w and 0 <= p["py"] <= h):
        raise ValueError("GCP falls outside archival raster")
    if not (-180 < p["lon"] < 180 and -75 < p["lat"] < 75):
        raise ValueError("GCP location outside supported local tangent range")


def convert(p: dict, w: int, lon0: float, lat0: float) -> tuple[tuple[float, float, float], tuple[float, float]]:
    b = (1.0, p["px"] / w, p["py"] / w)
    x = math.radians(p["lon"] - lon0) * R * math.cos(math.radians(lat0))
    y = math.radians(p["lat"] - lat0) * R
    return b, (x, y)


def project(p: dict, w: int, lon0: float, lat0: float,
            coef_x: list[float], coef_y: list[float]) -> float:
    b, (x, y) = convert(p, w, lon0, lat0)
    px = sum(a * v for a, v in zip(coef_x, b, strict=True))
    py = sum(a * v for a, v in zip(coef_y, b, strict=True))
    return math.hypot(px - x, py - y)


def compute(doc: dict) -> dict:
    if not isinstance(doc.get("city_id"), str) or not doc["city_id"].strip():
        raise ValueError("Missing city ID")
    if not isinstance(doc.get("map_id"), str) or not doc["map_id"].strip():
        raise ValueError("Missing archival map ID")
    image = doc.get("image") or {}
    w, h = image.get("width"), image.get("height")
    if not isinstance(w, int) or not isinstance(h, int) or w < 200 or h < 200:
        raise ValueError("Original image pixel dimensions are required")
    control = doc.get("gcps") or []
    holdouts = doc.get("holdouts") or []
    if len(control) < 4:
        raise ValueError("Require at least 4 non-collinear GCPs for an overdetermined affine fit")
    for p in [*control, *holdouts]:
        validate_point(p, w, h)
    if len({(p["px"], p["py"]) for p in control}) != len(control):
        raise ValueError("Duplicate historical pixel control")
    longitudes = [p["lon"] for p in control]
    latitudes = [p["lat"] for p in control]
    if max(longitudes) - min(longitudes) > 2 or max(latitudes) - min(latitudes) > 2:
        raise ValueError("Affine local approximation unsuitable for large-area or dateline maps")
    lon0 = sum(longitudes) / len(longitudes)
    lat0 = sum(latitudes) / len(latitudes)
    pairs = [convert(p, w, lon0, lat0) for p in control]
    basis = [x for x, _ in pairs]
    xvals = [p[0] for _, p in pairs]
    yvals = [p[1] for _, p in pairs]
    coef_x, coef_y = fit3(basis, xvals), fit3(basis, yvals)
    res = [project(p, w, lon0, lat0, coef_x, coef_y) for p in control]
    rms = math.sqrt(sum(v * v for v in res) / len(res))
    loo = []
    if len(control) >= 5:
        for i, p in enumerate(control):
            subset = [pair for j, pair in enumerate(pairs) if j != i]
            feats = [b for b, _ in subset]
            xs = [q[0] for _, q in subset]
            ys = [q[1] for _, q in subset]
            try:
                co_x, co_y = fit3(feats, xs), fit3(feats, ys)
                loo.append(project(p, w, lon0, lat0, co_x, co_y))
            except ValueError:
                loo = []
                break
    hold_res = [project(p, w, lon0, lat0, coef_x, coef_y) for p in holdouts]
    return {
        "schema": "city-on-paper/affine-georef-research/v1",
        "city_id": doc["city_id"], "map_id": doc["map_id"],
        "source_url": image.get("source_url"),
        "image_size_px": [w, h],
        "method": "local_equirectangular_affine_wgs84",
        "earth_radius_m": R, "reference_lonlat": [lon0, lat0],
        "pixel_to_local_metres": {
            "basis": ["1", "px / image_width", "py / image_width"],
            "east": coef_x, "north": coef_y,
        },
        "control_points_used": len(control),
        "holdout_points_not_used_in_fit": len(holdouts),
        "internal_rms_m": rms,
        "loo_rms_m": math.sqrt(sum(e * e for e in loo) / len(loo)) if loo else None,
        "holdout_rms_m": (
            math.sqrt(sum(e * e for e in hold_res) / len(hold_res))
            if hold_res else None
        ),
        "georeference_status": "research_only_manual_landmark_review_required",
        "independent_expert_review": False,
        "warnings": [
            "Residual and holdout error are mathematical fits, not independent evidence of correct landmarks.",
            "Affine model cannot account for local nonlinear distortion, terrain perspective, paper stretching.",
            "Do not apply this transformation to perspective lithographs or aerial photographs.",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    data = json.loads(args.input.read_text("utf-8"))
    result = compute(data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({
        "city_id": result["city_id"], "map_id": result["map_id"],
        "control_points_used": result["control_points_used"],
        "rms_m": result["internal_rms_m"],
        "holdout_rms_m": result["holdout_rms_m"],
        "independent_expert_review": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
