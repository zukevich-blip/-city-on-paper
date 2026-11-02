// Browser-side homography PREVIEW for poc/compare (no dependencies, no network).
// Maps photo px -> historic px, like tools/align/homography.py. The authoritative result is always
// the offline OpenCV run; this file only gives the editor live feedback.
// Method: normalised DLT (Hartley) as the initial guess, then Levenberg-Marquardt on the forward
// reprojection error, which is what cv2.findHomography(method=0) minimises as well.
(function (root) {
  "use strict";

  function normaliser(pts) {
    const n = pts.length;
    let cx = 0, cy = 0;
    for (const [x, y] of pts) { cx += x; cy += y; }
    cx /= n; cy /= n;
    let d = 0;
    for (const [x, y] of pts) d += Math.hypot(x - cx, y - cy);
    d /= n;
    const s = d > 0 ? Math.SQRT2 / d : 1;
    return [[s, 0, -s * cx], [0, s, -s * cy], [0, 0, 1]];
  }

  function mul(A, B) {
    const C = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
    for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) for (let k = 0; k < 3; k++) C[i][j] += A[i][k] * B[k][j];
    return C;
  }

  function inv3(M) {
    const [[a, b, c], [d, e, f], [g, h, i]] = M;
    const A = e * i - f * h, B = -(d * i - f * g), C = d * h - e * g;
    const det = a * A + b * B + c * C;
    if (!isFinite(det) || Math.abs(det) < 1e-15) return null;
    return [[A / det, -(b * i - c * h) / det, (b * f - c * e) / det],
            [B / det, (a * i - c * g) / det, -(a * f - c * d) / det],
            [C / det, -(a * h - b * g) / det, (a * e - b * d) / det]];
  }

  function scaleTo1(H) {
    const k = H[2][2];
    if (!k || !isFinite(k)) return null;
    return H.map(r => r.map(v => v / k));
  }

  function project(H, p) {
    const w = H[2][0] * p[0] + H[2][1] * p[1] + H[2][2];
    return [(H[0][0] * p[0] + H[0][1] * p[1] + H[0][2]) / w, (H[1][0] * p[0] + H[1][1] * p[1] + H[1][2]) / w];
  }

  // eigenvector of the smallest eigenvalue of a symmetric matrix (cyclic Jacobi)
  function smallestEigenvector(S) {
    const n = S.length, A = S.map(r => r.slice()), V = [];
    for (let i = 0; i < n; i++) { V.push(new Array(n).fill(0)); V[i][i] = 1; }
    for (let sweep = 0; sweep < 100; sweep++) {
      let off = 0;
      for (let p = 0; p < n; p++) for (let q = p + 1; q < n; q++) off += A[p][q] * A[p][q];
      if (off < 1e-30) break;
      for (let p = 0; p < n; p++) for (let q = p + 1; q < n; q++) {
        if (Math.abs(A[p][q]) < 1e-300) continue;
        const theta = (A[q][q] - A[p][p]) / (2 * A[p][q]);
        const t = Math.sign(theta || 1) / (Math.abs(theta) + Math.sqrt(theta * theta + 1));
        const c = 1 / Math.sqrt(t * t + 1), s = t * c;
        for (let k = 0; k < n; k++) {
          const akp = A[k][p], akq = A[k][q];
          A[k][p] = c * akp - s * akq; A[k][q] = s * akp + c * akq;
        }
        for (let k = 0; k < n; k++) {
          const apk = A[p][k], aqk = A[q][k];
          A[p][k] = c * apk - s * aqk; A[q][k] = s * apk + c * aqk;
        }
        for (let k = 0; k < n; k++) {
          const vkp = V[k][p], vkq = V[k][q];
          V[k][p] = c * vkp - s * vkq; V[k][q] = s * vkp + c * vkq;
        }
      }
    }
    let best = 0;
    for (let i = 1; i < n; i++) if (A[i][i] < A[best][best]) best = i;
    return V.map(r => r[best]);
  }

  // solve (n x n) M x = b with partial pivoting; returns null when singular
  function solve(M, b) {
    const n = b.length, A = M.map((r, i) => [...r, b[i]]);
    for (let c = 0; c < n; c++) {
      let piv = c;
      for (let r = c + 1; r < n; r++) if (Math.abs(A[r][c]) > Math.abs(A[piv][c])) piv = r;
      if (Math.abs(A[piv][c]) < 1e-14) return null;
      [A[c], A[piv]] = [A[piv], A[c]];
      for (let r = c + 1; r < n; r++) {
        const f = A[r][c] / A[c][c];
        for (let k = c; k <= n; k++) A[r][k] -= f * A[c][k];
      }
    }
    const x = new Array(n).fill(0);
    for (let r = n - 1; r >= 0; r--) {
      let s = A[r][n];
      for (let k = r + 1; k < n; k++) s -= A[r][k] * x[k];
      x[r] = s / A[r][r];
    }
    return x;
  }

  function dlt(src, dst) {
    const T1 = normaliser(src), T2 = normaliser(dst);
    const S = Array.from({ length: 9 }, () => new Array(9).fill(0));
    for (let i = 0; i < src.length; i++) {
      const [x, y] = project(T1, src[i]), [u, v] = project(T2, dst[i]);
      const rows = [[-x, -y, -1, 0, 0, 0, u * x, u * y, u], [0, 0, 0, -x, -y, -1, v * x, v * y, v]];
      for (const r of rows) for (let a = 0; a < 9; a++) for (let b = 0; b < 9; b++) S[a][b] += r[a] * r[b];
    }
    const h = smallestEigenvector(S);
    const Hn = [h.slice(0, 3), h.slice(3, 6), h.slice(6, 9)];
    const T2i = inv3(T2);
    if (!T2i) return null;
    return scaleTo1(mul(T2i, mul(Hn, T1)));
  }

  function sse(H, src, dst) {
    let e = 0;
    for (let i = 0; i < src.length; i++) {
      const [u, v] = project(H, src[i]);
      e += (u - dst[i][0]) ** 2 + (v - dst[i][1]) ** 2;
    }
    return e;
  }

  // Levenberg-Marquardt on h0..h7 (h8 = 1), minimising sum |dst - H(src)|^2
  function refine(H, src, dst, iters = 100) {
    let h = [H[0][0], H[0][1], H[0][2], H[1][0], H[1][1], H[1][2], H[2][0], H[2][1]];
    const toH = (p) => [[p[0], p[1], p[2]], [p[3], p[4], p[5]], [p[6], p[7], 1]];
    let err = sse(toH(h), src, dst), lambda = 1e-3;
    for (let it = 0; it < iters; it++) {
      const JtJ = Array.from({ length: 8 }, () => new Array(8).fill(0)), Jtr = new Array(8).fill(0);
      for (let i = 0; i < src.length; i++) {
        const [x, y] = src[i];
        const w = h[6] * x + h[7] * y + 1;
        const u = (h[0] * x + h[1] * y + h[2]) / w, v = (h[3] * x + h[4] * y + h[5]) / w;
        const Ju = [x / w, y / w, 1 / w, 0, 0, 0, -u * x / w, -u * y / w];
        const Jv = [0, 0, 0, x / w, y / w, 1 / w, -v * x / w, -v * y / w];
        const ru = dst[i][0] - u, rv = dst[i][1] - v;
        for (let a = 0; a < 8; a++) {
          Jtr[a] += Ju[a] * ru + Jv[a] * rv;
          for (let b = 0; b < 8; b++) JtJ[a][b] += Ju[a] * Ju[b] + Jv[a] * Jv[b];
        }
      }
      let improved = false;
      for (let tries = 0; tries < 10 && !improved; tries++) {
        const M = JtJ.map((r, a) => r.map((v, b) => (a === b ? v * (1 + lambda) + 1e-12 : v)));
        const d = solve(M, Jtr);
        if (!d) { lambda *= 10; continue; }
        const cand = h.map((v, k) => v + d[k]);
        const e2 = sse(toH(cand), src, dst);
        if (e2 < err) {
          const rel = (err - e2) / Math.max(err, 1e-30);
          h = cand; err = e2; lambda = Math.max(lambda / 10, 1e-12); improved = true;
          if (rel < 1e-14) return toH(h);
        } else lambda *= 10;
      }
      if (!improved) break;
    }
    return toH(h);
  }

  function fitHomography(src, dst) {
    if (src.length < 4 || src.length !== dst.length) return null;
    const H0 = dlt(src, dst);
    if (!H0 || !H0.flat().every(isFinite)) return null;
    const H = src.length > 4 ? refine(H0, src, dst) : H0;
    return H.flat().every(isFinite) ? H : null;
  }

  function hullArea(pts) {
    const p = pts.map(q => q.slice()).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    if (p.length < 3) return 0;
    const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const lo = [], up = [];
    for (const q of p) { while (lo.length >= 2 && cross(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop(); lo.push(q); }
    for (const q of p.reverse()) { while (up.length >= 2 && cross(up[up.length - 2], up[up.length - 1], q) <= 0) up.pop(); up.push(q); }
    const h = lo.slice(0, -1).concat(up.slice(0, -1));
    let a = 0;
    for (let i = 0; i < h.length; i++) { const j = (i + 1) % h.length; a += h[i][0] * h[j][1] - h[j][0] * h[i][1]; }
    return Math.abs(a) / 2;
  }

  // Same thresholds as tools/align/homography.py (relative to the historic diagonal). Preview only.
  const COVERAGE_MIN = 0.15;
  const THRESHOLDS = { high: { rms: 0.005, loo: 0.015 }, medium: { rms: 0.015, loo: 0.04 } };

  function evaluate(photoPts, histPts, histSize, photoSize) {
    const n = photoPts.length, diag = Math.hypot(histSize[0], histSize[1]);
    if (n < 4) return { n_points: n, H: null, confidence: "insufficient_points" };
    const H = fitHomography(photoPts, histPts);
    if (!H) return { n_points: n, H: null, confidence: "viewpoint_mismatch", reason: "degenerate fit" };
    const residuals = photoPts.map((p, i) => { const q = project(H, p); return Math.hypot(q[0] - histPts[i][0], q[1] - histPts[i][1]); });
    const rms = Math.sqrt(residuals.reduce((s, r) => s + r * r, 0) / n);
    const loo = [];
    if (n >= 5) for (let i = 0; i < n; i++) {
      const Hi = fitHomography(photoPts.filter((_, k) => k !== i), histPts.filter((_, k) => k !== i));
      if (!Hi) { loo.push(Infinity); continue; }
      const q = project(Hi, photoPts[i]);
      loo.push(Math.hypot(q[0] - histPts[i][0], q[1] - histPts[i][1]));
    }
    const looMax = loo.length ? Math.max(...loo) : null;
    const [w, h] = photoSize;
    const c = [[0, 0], [w, 0], [w, h], [0, h]].map(p => project(H, p));
    const wc = [[0, 0], [w, 0], [w, h], [0, h]].map(([x, y]) => H[2][0] * x + H[2][1] * y + H[2][2]);
    let signed = 0;
    for (let i = 0; i < 4; i++) { const j = (i + 1) % 4; signed += c[i][0] * c[j][1] - c[j][0] * c[i][1]; }
    const coverage = hullArea(histPts) / (histSize[0] * histSize[1]);
    const relRms = rms / diag, relLoo = looMax === null ? null : looMax / diag;
    let confidence, reason;
    if (wc.some(v => v <= 0)) { confidence = "viewpoint_mismatch"; reason = "photo frame crosses the horizon line of the transform"; }
    else if (signed <= 0) { confidence = "viewpoint_mismatch"; reason = "transform folds or mirrors the photo frame"; }
    else if (relLoo === null) { confidence = "low"; reason = "fewer than 5 points: no leave-one-out check possible"; }
    else if (relRms < THRESHOLDS.high.rms && relLoo < THRESHOLDS.high.loo) { confidence = "high"; reason = "consistent single-plane / rotation fit"; }
    else if (relRms < THRESHOLDS.medium.rms && relLoo < THRESHOLDS.medium.loo) { confidence = "medium"; reason = "fit usable; check marked areas"; }
    else if (relRms < THRESHOLDS.medium.rms * 3) { confidence = "low"; reason = "points disagree: likely parallax or drawing licence"; }
    else { confidence = "viewpoint_mismatch"; reason = "no single homography explains the control points"; }
    if (coverage < COVERAGE_MIN && (confidence === "high" || confidence === "medium")) {
      reason = `local fit only (${confidence} inside the outlined region): points cover ${Math.round(coverage * 100)}% < 15% of the historic image`;
      confidence = "low";
    }
    return { n_points: n, H, residuals_px: residuals, rms_px: rms, loo_px: loo, loo_max_px: looMax,
             control_point_coverage: coverage, confidence, reason, method: "JS preview: normalised DLT + Levenberg-Marquardt (all points)" };
  }

  root.CoPHomography = { fitHomography, project, evaluate, inv3, THRESHOLDS };
})(typeof window !== "undefined" ? window : globalThis);
