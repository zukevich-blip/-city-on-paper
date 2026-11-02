"""Offline, reversible alignment of a MODERN PHOTO onto an immutable HISTORICAL image.

* Reference geometry = the historical image. Its pixels are never transformed or rewritten.
* Output is a 3x3 matrix H (photo px -> historic px) plus its inverse, residuals and a
  confidence verdict. The viewer applies H as a CSS transform to the photo only, so the
  untouched photo is always one toggle away.
* A homography is only valid for one plane (a facade) or a pure camera rotation. Leave-one-out
  error exposes parallax / changed camera position; we then report low confidence or
  viewpoint_mismatch instead of forcing a fake fit.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import cv2
import numpy as np

THRESHOLDS = {  # relative to the historical image diagonal
    "high": {"rms": 0.005, "loo": 0.015},
    "medium": {"rms": 0.015, "loo": 0.04},
}


COVERAGE_MIN = 0.15  # below this the verdict is capped at "low" (local fit only)
RANSAC_MIN_POINTS = 8  # with fewer hand-picked points RANSAC just picks an exact 4-point subset


def _fit(src: np.ndarray, dst: np.ndarray, robust: bool, thresh: float) -> tuple[np.ndarray | None, np.ndarray]:
    if len(src) >= RANSAC_MIN_POINTS and robust:
        H, mask = cv2.findHomography(src, dst, cv2.RANSAC, ransacReprojThreshold=thresh)
    else:
        H, mask = cv2.findHomography(src, dst, 0)
    if mask is None:
        mask = np.ones((len(src), 1), np.uint8)
    return H, mask.ravel().astype(bool)


def project(H: np.ndarray, pts: np.ndarray) -> np.ndarray:
    return cv2.perspectiveTransform(pts.reshape(-1, 1, 2).astype(np.float64), H).reshape(-1, 2)


def estimate(photo_pts, historic_pts, historic_size, photo_size, robust: bool = True) -> dict:
    """photo_pts / historic_pts: lists of [x, y] in each image's own pixel grid."""
    src = np.asarray(photo_pts, np.float64)
    dst = np.asarray(historic_pts, np.float64)
    n = len(src)
    diag = math.hypot(*historic_size)
    out: dict = {"n_points": n, "maps": "photo_px -> historic_px", "historic_size": list(historic_size),
                 "photo_size": list(photo_size)}
    if n < 4:
        return {**out, "confidence": "insufficient_points", "H": None}
    ransac_px = 0.01 * diag
    H, inliers = _fit(src, dst, robust, ransac_px)
    if H is None or not np.isfinite(H).all() or abs(np.linalg.det(H)) < 1e-12:
        return {**out, "confidence": "viewpoint_mismatch", "H": None, "reason": "degenerate fit"}
    H = H / H[2, 2]
    H_inv = np.linalg.inv(H)
    H_inv = H_inv / H_inv[2, 2]
    res = np.linalg.norm(project(H, src) - dst, axis=1)
    rms = float(np.sqrt(np.mean(res[inliers] ** 2)))
    rms_all = float(np.sqrt(np.mean(res ** 2)))
    # leave-one-out: how well does a fit without point i predict point i?  (parallax detector)
    loo = []
    if n >= 5:
        for i in range(n):
            keep = np.arange(n) != i
            Hi, _ = cv2.findHomography(src[keep], dst[keep], 0)
            if Hi is None:
                loo.append(float("inf"))
                continue
            loo.append(float(np.linalg.norm(project(Hi, src[i:i + 1])[0] - dst[i])))
    loo_max = max(loo) if loo else None
    # roundtrip: H_inv(H(p)) == p
    roundtrip = float(np.max(np.linalg.norm(project(H_inv, project(H, src)) - src, axis=1)))
    # orientation / fold check on the photo frame
    w, h = photo_size
    # projective denominator at the photo corners: if it is <= 0 anywhere, the horizon line of the
    # transform crosses the photo frame (part of the photo maps "behind the camera"; CSS matrix3d breaks)
    wc = np.array([[0, 0, 1], [w, 0, 1], [w, h, 1], [0, h, 1]], np.float64) @ H[2]
    corners = project(H, np.array([[0, 0], [w, 0], [w, h], [0, h]], np.float64))
    signed = sum(corners[i][0] * corners[(i + 1) % 4][1] - corners[(i + 1) % 4][0] * corners[i][1]
                 for i in range(4))
    hull = cv2.convexHull(dst.astype(np.float32))
    coverage = float(cv2.contourArea(hull) / (historic_size[0] * historic_size[1]))
    rel_rms, rel_loo = rms / diag, (loo_max / diag if loo_max is not None else None)
    if np.any(wc <= 0):
        conf, reason = "viewpoint_mismatch", "photo frame crosses the horizon line of the transform"
    elif signed <= 0:
        conf, reason = "viewpoint_mismatch", "transform folds or mirrors the photo frame"
    elif inliers.mean() < 0.75:
        conf, reason = "low", "RANSAC rejected >25% of points: off-plane structures / parallax"
    elif rel_loo is None:
        conf, reason = "low", "fewer than 5 points: no leave-one-out check possible"
    elif rel_rms < THRESHOLDS["high"]["rms"] and rel_loo < THRESHOLDS["high"]["loo"]:
        conf, reason = "high", "consistent single-plane / rotation fit"
    elif rel_rms < THRESHOLDS["medium"]["rms"] and rel_loo < THRESHOLDS["medium"]["loo"]:
        conf, reason = "medium", "fit usable; check marked areas"
    elif rel_rms < THRESHOLDS["medium"]["rms"] * 3:
        conf, reason = "low", "points disagree: likely parallax (several depth planes) or drawing licence"
    else:
        conf, reason = "viewpoint_mismatch", "no single homography explains the control points"
    if coverage < COVERAGE_MIN and conf in ("high", "medium"):
        # a good fit on a small patch says nothing about the rest of the sheet
        reason = (f"local fit only ({conf} inside the outlined region): control points cover "
                  f"{coverage:.0%} < {COVERAGE_MIN:.0%} of the historic image")
        conf = "low"
    return {
        **out, "method": "cv2.findHomography " + (f"RANSAC {ransac_px:.1f}px" if robust and n >= RANSAC_MIN_POINTS
                                            else "least squares (all points)"),
        "H": H.round(10).tolist(), "H_inverse": H_inv.round(10).tolist(),
        "residuals_px": [round(float(r), 2) for r in res], "inliers": inliers.tolist(),
        "rms_px": round(rms, 2), "rms_all_points_px": round(rms_all, 2), "rms_rel_diag": round(rel_rms, 5),
        "outlier_fraction": round(1 - float(inliers.mean()), 3),
        "loo_px": [round(x, 2) for x in loo], "loo_max_px": round(loo_max, 2) if loo_max is not None else None,
        "loo_max_rel_diag": round(rel_loo, 5) if rel_loo is not None else None,
        "roundtrip_max_px": round(roundtrip, 6), "control_point_coverage": round(coverage, 4),
        "valid_region_historic": hull.reshape(-1, 2).round(1).tolist(),
        "scope": "global" if coverage >= COVERAGE_MIN else
                 f"local: control points span {coverage:.0%} of the historic image; trust only the outlined region",
        "confidence": conf, "reason": reason, "cv2_version": cv2.__version__,
    }


def align_pair(pair: dict) -> dict:
    """Alignment block for a pair dict. A human/visual review that already found the views
    incompatible (``viewpoint_review.status == "viewpoint_mismatch"``) wins over any fit: we never
    force a homography onto views that do not share a plane."""
    cps = pair.get("control_points") or []
    review = (pair.get("viewpoint_review") or {}).get("status")
    if review == "viewpoint_mismatch":
        result = {"n_points": len(cps), "maps": "photo_px -> historic_px",
                  "historic_size": list(pair["historic"]["size"]), "photo_size": list(pair["photo"]["size"]),
                  "confidence": "viewpoint_mismatch", "H": None,
                  "reason": "viewpoint review: no common plane / different camera position; no fit attempted"}
    else:
        result = estimate([c["photo"] for c in cps], [c["historic"] for c in cps],
                          pair["historic"]["size"], pair["photo"]["size"])
    return {**result, "derived_label": "Photo geometry adjusted (reversible, display only)"}


def align_pair_file(path: Path) -> dict:
    pair = json.loads(path.read_text("utf-8"))
    pair["alignment"] = align_pair(pair)
    path.write_text(json.dumps(pair, ensure_ascii=False, indent=1) + "\n", "utf-8")
    return pair


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        a = align_pair_file(Path(p))["alignment"]
        print(f"{p}: {a['confidence']}  rms={a.get('rms_px')}px  loo_max={a.get('loo_max_px')}px  ({a.get('reason')})")
