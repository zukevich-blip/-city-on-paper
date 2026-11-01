import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest

from tools.align import synthetic
from tools.align.homography import align_pair, estimate, project

PAIRS = Path(__file__).resolve().parents[1] / "poc" / "compare" / "pairs"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("pairs")
    return {p.stem: json.loads(p.read_text()) for p in synthetic.build(out)}


def run(pair):
    c = pair["control_points"]
    return estimate([x["photo"] for x in c], [x["historic"] for x in c], pair["historic"]["size"], pair["photo"]["size"])


@pytest.mark.parametrize("cid,allowed", [
    ("synthetic-near-identical", {"high"}),
    ("synthetic-rotation-only", {"high"}),
    ("synthetic-parallax", {"low", "viewpoint_mismatch"}),
])
def test_three_viewpoint_conditions(built, cid, allowed):
    assert run(built[cid])["confidence"] in allowed


def test_rotation_only_recovers_ground_truth_homography(built):
    """Pure camera rotation: H = K_hist R_hist R_photo^T K_photo^-1 exactly (any depth)."""
    def K(cam):
        return np.array([[cam["f"], 0, synthetic.W / 2], [0, -cam["f"], synthetic.H / 2], [0, 0, 1]])
    a, b = synthetic.HIST_CAM, synthetic.CASES["synthetic-rotation-only"]
    Ra = synthetic.rot(math.radians(a["yaw"]), math.radians(a["pitch"]))
    Rb = synthetic.rot(math.radians(b["yaw"]), math.radians(b["pitch"]))
    H_true = K(a) @ Ra @ Rb.T @ np.linalg.inv(K(b))
    H_true /= H_true[2, 2]
    H_est = np.array(run(built["synthetic-rotation-only"])["H"])
    grid = np.array([[x, y] for x in range(100, 900, 200) for y in range(100, 600, 200)], float)
    assert np.abs(project(H_est, grid) - project(H_true, grid)).max() < 3.0  # 0.8 px point noise


def test_inverse_roundtrip_and_reversibility(built):
    r = run(built["synthetic-rotation-only"])
    H, Hi = np.array(r["H"]), np.array(r["H_inverse"])
    assert np.allclose(H @ Hi / (H @ Hi)[2, 2], np.eye(3), atol=1e-8)
    assert r["roundtrip_max_px"] < 1e-6


def test_parallax_is_flagged_by_leave_one_out(built):
    r = run(built["synthetic-parallax"])
    assert r["loo_max_rel_diag"] > 0.04


def test_insufficient_points():
    assert estimate([[0, 0], [1, 0], [0, 1]], [[0, 0], [1, 0], [0, 1]], (100, 100), (100, 100))["confidence"] \
        == "insufficient_points"


def test_mirrored_photo_is_a_mismatch():
    pts = [[10, 10], [90, 12], [88, 80], [12, 85], [50, 50]]
    mirrored = [[100 - x, y] for x, y in pts]
    assert estimate(mirrored, pts, (100, 100), (100, 100))["confidence"] == "viewpoint_mismatch"


def test_committed_pairs_keep_original_bytes_and_are_reproducible():
    for f in PAIRS.glob("*.json"):
        if f.name == "index.json":
            continue
        pair = json.loads(f.read_text())
        hist = pair["historic"]
        if "sha256" in hist:  # historic file must be byte-identical to what was downloaded
            assert hashlib.sha256((PAIRS / hist["file"]).read_bytes()).hexdigest() == hist["sha256"]
        photo = pair["photo"]
        if "sha256" in photo:  # stored photo = the recorded re-encode (EXIF/GPS stripped)
            assert hashlib.sha256((PAIRS / photo["file"]).read_bytes()).hexdigest() == photo["sha256"]
        again = align_pair(pair)
        assert again["confidence"] == pair["alignment"]["confidence"]
        if pair["alignment"]["H"] is None:
            assert again["H"] is None
        else:
            assert np.allclose(again["H"], pair["alignment"]["H"], atol=1e-6)


def test_index_lists_every_pair_file():
    idx = json.loads((PAIRS / "index.json").read_text())["pairs"]
    files = {f.stem for f in PAIRS.glob("*.json")} - {"index"}
    assert set(idx) == files


def test_real_photos_carry_no_exif_gps():
    from PIL import Image
    for f in PAIRS.glob("*.json"):
        if f.name == "index.json":
            continue
        pair = json.loads(f.read_text())
        if pair["status"] == "synthetic_test":
            continue
        with Image.open(PAIRS / pair["photo"]["file"]) as im:
            assert len(im.getexif()) == 0 and "exif" not in im.info


def test_reviewed_viewpoint_mismatch_is_never_fitted():
    pair = json.loads((PAIRS / "palais-royal-ph-benoist.json").read_text())
    a = align_pair(pair)
    assert a["confidence"] == "viewpoint_mismatch" and a["H"] is None
    # even if someone adds points later, the review verdict still blocks a forced fit
    pts = [[10, 10], [900, 20], [880, 700], [20, 690], [400, 300]]
    forced = {**pair, "control_points": [{"label": str(i), "photo": p, "historic": p} for i, p in enumerate(pts)]}
    assert align_pair(forced)["H"] is None


def test_horizon_crossing_the_photo_frame_is_a_mismatch():
    """Reviewer repro: exact points, but w <= 0 at two photo corners -> must not be 'high'."""
    H = np.array([[1, 0, 0], [0, 1, 0], [-0.0015, 0, 1]], float)
    photo = np.array([[50, 50], [300, 80], [550, 60], [100, 400], [400, 420], [600, 700], [200, 750], [450, 600]], float)
    hist = project(H, photo)
    r = estimate(photo.tolist(), hist.tolist(), (1000, 800), (1000, 800))
    assert r["confidence"] == "viewpoint_mismatch" and "horizon" in r["reason"]


def test_small_coverage_caps_verdict_at_low():
    rng = np.random.default_rng(1)
    hist = np.array([[480, 330], [540, 335], [545, 390], [478, 392], [510, 360], [500, 345]], float)
    photo = hist * 1.5 + rng.normal(0, 0.2, hist.shape)
    r = estimate(photo.tolist(), hist.tolist(), (1000, 700), (1500, 1050))
    assert r["control_point_coverage"] < 0.15
    assert r["confidence"] == "low" and r["scope"].startswith("local")
