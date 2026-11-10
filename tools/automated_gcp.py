#!/usr/bin/env python3
"""Research-only candidate GCPs from a historic map and a georeferenced raster.

A match is NEVER a verified landmark, viewpoint or world-position measurement.
Pixel residuals measure internal model fit; they do not measure historical accuracy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class GeoreferenceError(ValueError):
    """Invalid or insufficient georeferencing input."""


def load_greyscale(path: Path, max_dimension: int) -> tuple[np.ndarray, tuple[int, int], float, float]:
    original = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if original is None:
        raise GeoreferenceError(f"Image missing or unreadable: {path}")
    h, w = original.shape
    scale = min(1.0, max_dimension / max(h, w))
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    if (nw, nh) != (w, h):
        original = cv2.resize(original, (nw, nh), interpolation=cv2.INTER_AREA)
    # Individual X/Y ratios protect image coordinates after rounding.
    return original, (w, h), w / nw, h / nh


def extract_matches(source: np.ndarray, reference: np.ndarray, ratio: float) -> tuple[np.ndarray, np.ndarray, int]:
    orb = cv2.ORB_create(nfeatures=5000, scaleFactor=1.2, nlevels=8,
                         edgeThreshold=31, patchSize=31, fastThreshold=15)
    ks, ds = orb.detectAndCompute(source, None)
    kr, dr = orb.detectAndCompute(reference, None)
    if ds is None or dr is None or len(ds) < 2 or len(dr) < 2:
        return np.empty((0, 2), dtype=np.float32), np.empty((0, 2), dtype=np.float32), 0

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    forward = matcher.knnMatch(ds, dr, k=2)
    backward = matcher.knnMatch(dr, ds, k=2)
    reciprocal: dict[tuple[int, int], float] = {}
    reverse_ok = { (m.trainIdx, m.queryIdx) for pair in backward if len(pair) == 2
                   for m, n in [pair] if m.distance < ratio * n.distance }
    for pair in forward:
        if len(pair) != 2:
            continue
        m, n = pair
        if m.distance < ratio * n.distance and (m.queryIdx, m.trainIdx) in reverse_ok:
            reciprocal[(m.queryIdx, m.trainIdx)] = m.distance
    ordered = sorted(reciprocal.items(), key=lambda pair: pair[1])
    # Keep keypoint index pairs distinct; do not compare numeric indices as locations.
    return (np.asarray([ks[a].pt for (a, b), _ in ordered], dtype=np.float32).reshape(-1, 2),
            np.asarray([kr[b].pt for (a, b), _ in ordered], dtype=np.float32).reshape(-1, 2),
            len(ordered))


def coverage(points: np.ndarray, shape: tuple[int, int]) -> float:
    if len(points) < 3:
        return 0.0
    hull = cv2.convexHull(points.astype(np.float32))
    return float(cv2.contourArea(hull)) / float(shape[0] * shape[1])


def select_spread_points(points: np.ndarray, max_points: int, shape: tuple[int, int]) -> np.ndarray:
    """Farthest-point sampling avoids flooding reviewers with clustered keypoints."""
    if len(points) <= max_points:
        return np.arange(len(points), dtype=int)
    norm = points / np.asarray(shape, dtype=float)
    centre = norm.mean(axis=0)
    first = int(np.argmax(np.sum((norm - centre) ** 2, axis=1)))
    picked = [first]
    nearest = np.sum((norm - norm[first]) ** 2, axis=1)
    nearest[first] = -1.0
    for _ in range(max_points - 1):
        j = int(np.argmax(nearest))
        picked.append(j)
        nearest = np.minimum(nearest, np.sum((norm - norm[j]) ** 2, axis=1))
        nearest[picked] = -1.0
    return np.asarray(picked, dtype=int)


def get_geo_reference(path: Path | None) -> tuple[dict[str, Any] | None, Any, Any]:
    if path is None:
        return None, None, None
    try:
        from pyproj import CRS, Geod, Transformer
    except ImportError as exc:
        raise GeoreferenceError("pyproj is required when --reference-georef is provided") from exc
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("crs"):
        raise GeoreferenceError("Reference georeferencing requires an explicit CRS")
    affine = data.get("geotransform")
    if not isinstance(affine, list) or len(affine) != 6 or not all(
        isinstance(x, (int, float)) and math.isfinite(x) for x in affine
    ):
        raise GeoreferenceError("geotransform must contain 6 finite GDAL affine coefficients")
    if abs(affine[1] * affine[5] - affine[2] * affine[4]) < 1e-15:
        raise GeoreferenceError("Singular reference geotransform")
    crs = CRS.from_user_input(data["crs"])
    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    geod = Geod(ellps="WGS84")
    # Caller must document that the image pixels align to this exact raster.
    return {"crs": crs.to_string(), "geotransform": affine, "source": str(path)}, transformer, geod


def pixels_to_lonlat(points: np.ndarray, reference_georef: dict, transformer: Any) -> np.ndarray:
    gt = reference_georef["geotransform"]
    x = gt[0] + gt[1] * points[:, 0] + gt[2] * points[:, 1]
    y = gt[3] + gt[4] * points[:, 0] + gt[5] * points[:, 1]
    lons, lats = transformer.transform(x, y)
    result = np.column_stack([lons, lats])
    if not np.isfinite(result).all() or (np.abs(result[:, 1]) > 90).any() or (np.abs(result[:, 0]) > 180).any():
        raise GeoreferenceError("Reference geotransform produced invalid WGS84 coordinates")
    return result


def fit_candidates(source_points: np.ndarray, reference_points: np.ndarray,
                   source_shape: tuple[int, int], reference_shape: tuple[int, int],
                   ransac_px: float = 4.0, min_inliers: int = 12,
                   min_coverage: float = 0.035) -> dict[str, Any]:
    base = {"status": "auto_fail", "reason": None, "matches": int(len(source_points)),
            "inliers": 0, "inlier_ratio": 0.0, "coverage_source": 0.0,
            "coverage_reference": 0.0, "rmse_reference_pixels": None,
            "matrix": None, "source_points": [], "reference_points": [],
            "predicted_reference_points": []}
    if len(source_points) < max(4, min_inliers):
        base["reason"] = "insufficient_correspondences"
        return base
    H, mask = cv2.findHomography(source_points, reference_points, cv2.RANSAC,
                                 ransacReprojThreshold=ransac_px,
                                 maxIters=5000, confidence=0.995)
    if H is None or mask is None or not np.isfinite(H).all() or abs(float(np.linalg.det(H))) < 1e-12:
        base["reason"] = "degenerate_homography"
        return base
    inliers = mask.ravel().astype(bool)
    count = int(inliers.sum())
    base["inliers"] = count
    base["inlier_ratio"] = round(count / len(source_points), 5)
    if count < 4:
        base["reason"] = "insufficient_inliers"
        return base
    ss, rr = source_points[inliers], reference_points[inliers]
    projected = cv2.perspectiveTransform(ss.reshape(-1, 1, 2), H).reshape(-1, 2)
    if not np.isfinite(projected).all():
        base["reason"] = "nonfinite_projection"
        return base
    errors = np.linalg.norm(projected - rr, axis=1)
    base["rmse_reference_pixels"] = round(float(np.sqrt(np.mean(errors ** 2))), 5)
    base["coverage_source"] = round(coverage(ss, source_shape), 5)
    base["coverage_reference"] = round(coverage(rr, reference_shape), 5)
    base["matrix"] = H.tolist()
    base["source_points"] = ss.astype(float).tolist()
    base["reference_points"] = rr.astype(float).tolist()
    base["predicted_reference_points"] = projected.astype(float).tolist()
    if count < min_inliers:
        base["reason"] = "insufficient_inliers"
    elif base["inlier_ratio"] < 0.3:
        base["reason"] = "low_inlier_ratio"
    elif min(base["coverage_source"], base["coverage_reference"]) < min_coverage:
        base["reason"] = "poor_spatial_coverage"
    elif base["rmse_reference_pixels"] > ransac_px:
        base["reason"] = "high_fit_residual"
    else:
        base["status"] = "candidate_auto"
        base["reason"] = "pending_landmark_and_historical_review"
    return base


def run(source_path: Path, reference_path: Path, output_path: Path,
        georef_path: Path | None = None, max_dimension: int = 2400,
        ratio: float = 0.76, ransac_px: float = 4.0,
        min_inliers: int = 12, min_coverage: float = 0.035) -> dict[str, Any]:
    if max_dimension < 128 or not 0.1 < ratio < 1.0 or ransac_px <= 0 or min_inliers < 4:
        raise GeoreferenceError("Invalid matching parameters")
    # Stable random seed keeps RANSAC sampling reproducible in a pinned OpenCV runtime.
    cv2.setRNGSeed(0)
    source, source_size, sx, sy = load_greyscale(source_path, max_dimension)
    reference, reference_size, rx, ry = load_greyscale(reference_path, max_dimension)
    geo, transformer, geod = get_geo_reference(georef_path)
    pts_src, pts_ref, _ = extract_matches(source, reference, ratio)
    fit = fit_candidates(pts_src, pts_ref, (source.shape[1], source.shape[0]),
                         (reference.shape[1], reference.shape[0]),
                         ransac_px, min_inliers, min_coverage)
    entries = []
    residual_meters = None
    if fit["matrix"] is not None:
        # Matched pixels in resized rasters must be mapped to ORIGINAL pixel coordinates.
        all_s = np.asarray(fit["source_points"], dtype=float) * [sx, sy]
        all_r = np.asarray(fit["reference_points"], dtype=float) * [rx, ry]
        all_predicted = np.asarray(fit["predicted_reference_points"], dtype=float) * [rx, ry]
        if geo:
            # Residual is calculated on *all* RANSAC inliers, not only sampled candidates.
            all_lonlat = pixels_to_lonlat(all_r, geo, transformer)
            pred_lonlat = pixels_to_lonlat(all_predicted, geo, transformer)
            _, _, errors_m = geod.inv(pred_lonlat[:, 0], pred_lonlat[:, 1],
                                       all_lonlat[:, 0], all_lonlat[:, 1])
            residual_meters = round(float(np.sqrt(np.mean(np.asarray(errors_m) ** 2))), 5)
        selected = select_spread_points(all_s, max_points=48, shape=source_size)
        s = all_s[selected]
        r = all_r[selected]
        lonlat = pixels_to_lonlat(r, geo, transformer) if geo else None
        for i, (sp, rp) in enumerate(zip(s, r, strict=True)):
            entry = {"id": i + 1, "source_pixel": [round(float(z), 3) for z in sp],
                     "reference_pixel": [round(float(z), 3) for z in rp],
                     "status": "unverified_machine_match"}
            if geo:
                entry["longitude_latitude"] = [round(float(z), 8) for z in lonlat[i]]
            entries.append(entry)
        # Homography on original pixels, not reduced images.
        Ssrc = np.diag([1 / sx, 1 / sy, 1.0])
        Sref = np.diag([rx, ry, 1.0])
        H_original = Sref @ np.asarray(fit["matrix"]) @ Ssrc
        fit["matrix_original_pixels"] = (H_original / H_original[2, 2]).tolist()
    output = {
        "schema_version": "city-on-paper.gcp-candidates.v1",
        "status": fit["status"], "review_required": True,
        "scientific_accuracy_verified": False,
        "notes": "Automatic visual correspondences only; residuals are not geolocation accuracy.",
        "source": {"path": str(source_path), "width": source_size[0], "height": source_size[1],
                   "sha256": sha256_file(source_path)},
        "reference": {"path": str(reference_path), "width": reference_size[0], "height": reference_size[1],
                      "sha256": sha256_file(reference_path), "georeferencing": geo,
                      "georef_sha256": sha256_file(georef_path) if georef_path else None},
        "method": {"detector": "ORB", "matcher": "reciprocal_Lowe_ratio",
                   "transform": "RANSAC_homography", "opencv_version": cv2.__version__,
                   "max_dimension": max_dimension, "ratio": ratio, "ransac_preview_px": ransac_px},
        "metrics": {k: fit[k] for k in ("reason", "matches", "inliers", "inlier_ratio",
                    "coverage_source", "coverage_reference", "rmse_reference_pixels")},
        "residual_rmse_meters": residual_meters,
        "pixel_rmse_units": "reference_preview_pixels (post-resize)",
        "homography_original_pixels": fit.get("matrix_original_pixels"),
        "gcp_pairs": entries,
        "review_points_emitted": len(entries),
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                           encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Original historic map raster")
    parser.add_argument("--reference", type=Path, required=True, help="Modern reference raster")
    parser.add_argument("--output", type=Path, required=True, help="Candidate GCP JSON")
    parser.add_argument("--reference-georef", type=Path, help="JSON: CRS + 6-term GDAL geotransform")
    parser.add_argument("--max-dimension", type=int, default=2400)
    parser.add_argument("--ratio", type=float, default=0.76)
    parser.add_argument("--ransac-px", type=float, default=4.0)
    parser.add_argument("--min-inliers", type=int, default=12)
    parser.add_argument("--min-coverage", type=float, default=0.035)
    args = parser.parse_args()
    try:
        result = run(args.source, args.reference, args.output, args.reference_georef,
                     args.max_dimension, args.ratio, args.ransac_px,
                     args.min_inliers, args.min_coverage)
    except (OSError, ValueError, cv2.error) as err:
        parser.exit(2, f"GCP ERROR: {err}\n")
    print(json.dumps({"status": result["status"], "metrics": result["metrics"],
                      "residual_rmse_meters": result["residual_rmse_meters"],
                      "output": str(args.output)}, ensure_ascii=False))
    return 0 if result["status"] == "candidate_auto" else 1


if __name__ == "__main__":
    raise SystemExit(main())
