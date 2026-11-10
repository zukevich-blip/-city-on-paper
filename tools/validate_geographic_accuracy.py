#!/usr/bin/env python3
"""Research-only geographic accuracy audit. Never grants publication approval.

Two explicitly different assessments:
* legacy-paris: recalculate in-sample and leave-one-out affine fit of research GCPs.
* candidate: evaluate a frozen ORB matrix against SEPARATELY reviewed holdout points.

Neither establishes scientific accuracy by itself. No guessed map scale is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
from pyproj import CRS, Geod, Transformer


class ValidationError(ValueError):
    """Input cannot support the requested assessment."""


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValidationError("Expected a JSON object")
    return data


def number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValidationError(f"{label} must be finite")
    return result


def pair(value: object, label: str) -> np.ndarray:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValidationError(f"{label} must be two numbers")
    return np.array([number(value[0], label), number(value[1], label)], dtype=float)


def rms(errors: np.ndarray) -> float:
    if len(errors) == 0 or not np.isfinite(errors).all():
        raise ValidationError("No finite errors; cannot report zero")
    return float(np.sqrt(np.mean(np.square(errors))))


def standard_report(mode: str, source_file: Path) -> dict:
    return {
        "schema_version": "city-on-paper.geographic-validation.v1",
        "mode": mode,
        "input_file": str(source_file),
        "source_sha256": hashlib.sha256(source_file.read_bytes()).hexdigest(),
        "scientific_accuracy_verified": False,
        "approved_for_publication": False,
        "assessment": "research_only",
    }


def legacy_affine(path: Path) -> dict:
    """Recompute research-set fit, not independent accuracy of historic pixel picks."""
    data = read_json(path)
    points = data.get("gcps")
    space = data.get("pixel_space", {})
    frame = data.get("local_projection", {})
    if not isinstance(points, list) or len(points) < 5:
        raise ValidationError("At least five named historic GCP pairs are required")
    width = number(space.get("width"), "pixel_space.width")
    height = number(space.get("height"), "pixel_space.height")
    lon0 = number(frame.get("lon0"), "lon0")
    lat0 = number(frame.get("lat0"), "lat0")
    radius = number(frame.get("R_m"), "R_m")
    if width <= 0 or height <= 0 or radius <= 0 or not (-90 < lat0 < 90):
        raise ValidationError("Invalid historic pixel space or local projection")
    xys = []
    meter_points = []
    names = []
    for i, p in enumerate(points):
        if not isinstance(p, dict) or not str(p.get("name", "")).strip():
            raise ValidationError(f"Historic point {i} needs an identifiable name")
        px = number(p.get("px"), "px")
        py = number(p.get("py"), "py")
        lon = number(p.get("lon"), "lon")
        lat = number(p.get("lat"), "lat")
        if not (0 <= px <= width and 0 <= py <= height and -180 <= lon <= 180
                and -90 <= lat <= 90):
            raise ValidationError(f"Historic point {i} is outside valid coordinates")
        names.append(p["name"])
        xys.append([1., px / width, py / width])
        meter_points.append([
            (lon - lon0) * math.pi / 180 * radius * math.cos(math.radians(lat0)),
            (lat - lat0) * math.pi / 180 * radius,
        ])
    if len(set(names)) != len(names):
        raise ValidationError("Duplicate historic point names")
    x = np.asarray(xys, dtype=float)
    y = np.asarray(meter_points, dtype=float)
    if np.linalg.matrix_rank(x) != 3:
        raise ValidationError("Historic landmarks are geometrically degenerate")
    coefficients, *_ = np.linalg.lstsq(x, y, rcond=None)
    direct = np.linalg.norm(x @ coefficients - y, axis=1)
    loo = []
    for i in range(len(x)):
        train = np.arange(len(x)) != i
        if np.linalg.matrix_rank(x[train]) != 3:
            raise ValidationError("LOO subset is degenerate; cannot count it as zero")
        local_fit, *_ = np.linalg.lstsq(x[train], y[train], rcond=None)
        loo.append(float(np.linalg.norm(x[i] @ local_fit - y[i])))
    loo = np.asarray(loo)
    result = standard_report("historical_gcps_internal_affine", path)
    result.update({
        "map_id": data.get("map_id"),
        "landmarks": len(points),
        "in_sample_rmse_meters": round(rms(direct), 3),
        "loo_rmse_meters": round(rms(loo), 3),
        "max_in_sample_meters": round(float(np.max(direct)), 3),
        "max_loo_meters": round(float(np.max(loo)), 3),
        "point_errors": [
            {"name": name, "in_sample_meters": round(float(a), 3),
             "loo_meters": round(float(b), 3),
             "historic_point_checked_independently": False}
            for name, a, b in zip(names, direct, loo, strict=True)
        ],
        "interpretation": (
            "Fit and cross-validation of previously selected research landmarks. "
            "They may share systematic identification errors. No new map "
            "measurements, independent check points or survey evidence were used."
        ),
    })
    return result


def validate_candidate(candidate_path: Path, controls_path: Path) -> dict:
    """Evaluate fixed historic->reference-pixel H on independent holdout landmarks."""
    candidate = read_json(candidate_path)
    controls = read_json(controls_path)
    if candidate.get("schema_version") != "city-on-paper.gcp-candidates.v1":
        raise ValidationError("Not a recognized ORB candidate schema")
    if candidate.get("scientific_accuracy_verified") is not False:
        raise ValidationError("Candidate must remain scientifically unverified")
    if candidate.get("status") != "candidate_auto":
        raise ValidationError("Candidate is not usable; no independent accuracy estimate")
    if controls.get("schema_version") != "city-on-paper.independent-gcp-controls.v1":
        raise ValidationError("Explicit independent control-point schema is required")
    source = candidate.get("source", {})
    ref = candidate.get("reference", {})
    if not isinstance(source, dict) or not isinstance(ref, dict):
        raise ValidationError("Missing raster provenance")
    for key, actual in (("historic_sha256", source.get("sha256")),
                        ("reference_sha256", ref.get("sha256"))):
        if not isinstance(actual, str) or len(actual) != 64 or controls.get(key) != actual:
            raise ValidationError(f"{key} does not match the exact input image")
    geo = ref.get("georeferencing")
    if not isinstance(geo, dict) or not geo.get("crs"):
        raise ValidationError("Actual reference raster CRS is required")
    gt = geo.get("geotransform")
    if not isinstance(gt, list) or len(gt) != 6:
        raise ValidationError("Six-term reference raster geotransform required")
    affine = np.array([number(x, "GDAL geotransform") for x in gt], dtype=float)
    if abs(affine[1] * affine[5] - affine[2] * affine[4]) < 1e-12:
        raise ValidationError("Singular reference raster geotransform")
    matrix = candidate.get("homography_original_pixels")
    if matrix is None:
        raise ValidationError("ORB candidate does not contain an historic-to-raster matrix")
    try:
        h = np.array(matrix, dtype=float)
    except (ValueError, TypeError) as exc:
        raise ValidationError("Non-numeric homography") from exc
    if h.shape != (3, 3) or not np.isfinite(h).all() or abs(np.linalg.det(h)) < 1e-12:
        raise ValidationError("Invalid homography")
    source_w, source_h = (number(source.get(k), f"source.{k}") for k in ("width", "height"))
    if source_w <= 0 or source_h <= 0:
        raise ValidationError("Source dimensions must be positive")
    data = controls.get("points")
    if not isinstance(data, list) or len(data) < 6:
        raise ValidationError("At least six separately reviewed holdout landmarks are required")
    ids = set()
    historic = []
    targets = []
    evidence = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValidationError(f"Point {i} must be an object")
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in ids:
            raise ValidationError("Control IDs must be unique and non-empty")
        ids.add(identifier)
        source_xy = pair(item.get("historic_pixel"), f"{identifier}.historic_pixel")
        target = pair(item.get("longitude_latitude"), f"{identifier}.longitude_latitude")
        if not (0 <= source_xy[0] <= source_w and 0 <= source_xy[1] <= source_h
                and -180 <= target[0] <= 180 and -90 <= target[1] <= 90):
            raise ValidationError(f"{identifier} coordinates are outside their coordinate system")
        reviewer = item.get("reviewer")
        url = item.get("evidence_url")
        if (not isinstance(reviewer, str) or not reviewer.strip()
                or not isinstance(url, str) or urlsplit(url).scheme != "https"
                or not urlsplit(url).netloc
                or item.get("historic_landmark_checked") is not True
                or item.get("modern_position_checked") is not True
                or item.get("independent_of_orb") is not True):
            raise ValidationError(f"{identifier} lacks documented independent review")
        historic.append(source_xy)
        targets.append(target)
        evidence.append({"id": identifier, "reviewer": reviewer, "evidence_url": url})
    src = np.asarray(historic, dtype=float)
    dst = np.asarray(targets, dtype=float)
    if np.linalg.matrix_rank(np.c_[src, np.ones(len(src))]) < 3:
        raise ValidationError("Holdout points must not be collinear")
    mapped = np.c_[src, np.ones(len(src))] @ h.T
    if (np.abs(mapped[:, 2]) < 1e-12).any():
        raise ValidationError("Homography crosses the projective horizon")
    pix = mapped[:, :2] / mapped[:, 2, None]
    grid_x = affine[0] + affine[1] * pix[:, 0] + affine[2] * pix[:, 1]
    grid_y = affine[3] + affine[4] * pix[:, 0] + affine[5] * pix[:, 1]
    transformer = Transformer.from_crs(CRS.from_user_input(geo["crs"]),
                                       "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(grid_x, grid_y)
    prediction = np.c_[lon, lat]
    if (not np.isfinite(prediction).all() or (np.abs(prediction[:, 0]) > 180).any()
            or (np.abs(prediction[:, 1]) > 90).any()):
        raise ValidationError("Reference geotransform gives impossible positions")
    _, _, errors_m = Geod(ellps="WGS84").inv(
        prediction[:, 0], prediction[:, 1], dst[:, 0], dst[:, 1]
    )
    errors_m = np.asarray(errors_m, dtype=float)
    result = standard_report("candidate_independent_holdout", candidate_path)
    result.update({
        "controls_file": str(controls_path),
        "controls_sha256": hashlib.sha256(controls_path.read_bytes()).hexdigest(),
        "number_of_holdout_points": len(data),
        "rmse_meters": round(rms(errors_m), 3),
        "mean_error_meters": round(float(np.mean(errors_m)), 3),
        "max_error_meters": round(float(np.max(errors_m)), 3),
        "point_errors": [
            {"id": source["id"], "reviewer": source["reviewer"],
             "evidence_url": source["evidence_url"],
             "error_meters": round(float(error), 3)}
            for source, error in zip(evidence, errors_m, strict=True)
        ],
        "interpretation": (
            "Out-of-sample measured residuals of the FROZEN ORB homography, "
            "conditional on the independently reviewed historic pixel picks "
            "and modern target coordinates. This program cannot authenticate "
            "the reviewers or their evidence; publication remains blocked."
        ),
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--legacy-paris", type=Path)
    group.add_argument("--candidate", type=Path)
    parser.add_argument("--controls", type=Path, help="Required with --candidate")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (args.candidate is None) != (args.controls is None):
        parser.error("--controls is required exactly when --candidate is supplied")
    try:
        result = (legacy_affine(args.legacy_paris) if args.legacy_paris
                  else validate_candidate(args.candidate, args.controls))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(
            result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"VALIDATION REFUSED: {exc}\n")
    print(json.dumps({
        "assessment": result["assessment"],
        "scientific_accuracy_verified": result["scientific_accuracy_verified"],
        "output": str(args.output),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
