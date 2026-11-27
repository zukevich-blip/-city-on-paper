/* Geometric morph between a print and a photo from matched control points.
 * Own implementation from textbook mathematics (Bowyer-Watson Delaunay triangulation, piecewise-affine warping,
 * exact quadratic Jacobian check); no third-party code. Idea of the pre-morph gate follows the Gemini v10 notes,
 * the thresholds and rules below are ours and are tested in tests/js/morph_unit.js.
 * A morph is offered ONLY when the same control points that justify the alignment cover enough of the sheet. */
(function (root) {
  const LIM = { minPoints: 6, minHull: 0.06, minCoverage: 0.15, minDist: 0.035, maxShift: 0.35, minAreaRatio: 0.05 };

  const area2 = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);

  function hullArea(pts) { // Andrew monotone chain + shoelace
    const p = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    if (p.length < 3) return 0;
    const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const half = (arr) => { const h = []; for (const q of arr) { while (h.length >= 2 && cross(h[h.length - 2], h[h.length - 1], q) <= 0) h.pop(); h.push(q); } h.pop(); return h; };
    const hull = half(p).concat(half(p.slice().reverse()));
    let s = 0; for (let i = 0; i < hull.length; i++) { const a = hull[i], b = hull[(i + 1) % hull.length]; s += a[0] * b[1] - b[0] * a[1]; }
    return Math.abs(s) / 2;
  }

  function delaunay(P) { // Bowyer-Watson; returns index triples
    const n = P.length, big = 1e4, pts = P.concat([[-big, -big], [big, -big], [0, big]]);
    let tris = [[n, n + 1, n + 2]];
    const circ = (t, q) => {
      const [a, b, c] = t.map((i) => pts[i]);
      const ax = a[0] - q[0], ay = a[1] - q[1], bx = b[0] - q[0], by = b[1] - q[1], cx = c[0] - q[0], cy = c[1] - q[1];
      const det = (ax * ax + ay * ay) * (bx * cy - cx * by) - (bx * bx + by * by) * (ax * cy - cx * ay) + (cx * cx + cy * cy) * (ax * by - bx * ay);
      return area2(a, b, c) > 0 ? det > 0 : det < 0;
    };
    for (let i = 0; i < n; i++) {
      const bad = tris.filter((t) => circ(t, pts[i])), edges = [];
      for (const t of bad) for (const [u, v] of [[t[0], t[1]], [t[1], t[2]], [t[2], t[0]]]) {
        const k = edges.findIndex((e) => (e[0] === v && e[1] === u) || (e[0] === u && e[1] === v));
        if (k >= 0) edges.splice(k, 1); else edges.push([u, v]);
      }
      tris = tris.filter((t) => !bad.includes(t)).concat(edges.map(([u, v]) => [u, v, i]));
    }
    return tris.filter((t) => t.every((i) => i < n));
  }

  /* pair: { historic:{size}, photo:{size}, control_points:[{historic:[x,y],photo:[x,y]}], alignment:{confidence,control_point_coverage} } */
  function buildMesh(pair) {
    const [hw, hh] = pair.historic.size, [pw, ph] = pair.photo.size;
    const A = pair.control_points.map((c) => [c.historic[0] / hw, c.historic[1] / hh]);
    const B = pair.control_points.map((c) => [c.photo[0] / pw, c.photo[1] / ph]);
    for (const [x, y] of [[0, 0], [1, 0], [1, 1], [0, 1]]) { A.push([x, y]); B.push([x, y]); } // frames map to frames
    return { A, B, tris: delaunay(A), n: pair.control_points.length };
  }

  function minAreaOverT(a, b, c, A, B) { // exact: area(t) is quadratic in t
    const f = (t) => area2(...[a, b, c].map((i) => [A[i][0] + t * (B[i][0] - A[i][0]), A[i][1] + t * (B[i][1] - A[i][1])]));
    const f0 = f(0), f1 = f(1), fh = f(0.5), c2 = 2 * (f1 + f0 - 2 * fh), c1 = f1 - f0 - c2;
    const vals = [f0, f1];
    if (Math.abs(c2) > 1e-15) { const t = -c1 / (2 * c2); if (t > 0 && t < 1) vals.push(f0 + c1 * t + c2 * t * t); }
    return { f0, min: Math.min(...vals.map((v) => v * Math.sign(f0))) };
  }

  function gate(pair) {
    const why = [], cp = pair.control_points || [], al = pair.alignment || {};
    if (cp.length < LIM.minPoints) { why.push(`контрольных точек ${cp.length}, нужно не меньше ${LIM.minPoints}`); return { ok: false, why }; }
    if (al.confidence === "viewpoint_mismatch") why.push("ракурсы признаны несовместимыми");
    const m = buildMesh(pair), core = (arr) => arr.slice(0, m.n);
    const dist = (u, v) => Math.hypot(u[0] - v[0], u[1] - v[1]);
    for (const [name, arr] of [["рисунке", core(m.A)], ["фото", core(m.B)]]) {
      for (let i = 0; i < arr.length; i++) for (let j = i + 1; j < arr.length; j++) if (dist(arr[i], arr[j]) < LIM.minDist) { why.push(`на ${name} две точки почти совпадают`); i = arr.length; break; }
      if (hullArea(arr) < LIM.minHull) why.push(`точки на ${name} занимают меньше ${Math.round(LIM.minHull * 100)}% листа`);
    }
    const cov = al.control_point_coverage;
    if (typeof cov === "number" && cov < LIM.minCoverage) why.push(`точки покрывают ${Math.round(cov * 1000) / 10}% листа, нужно не меньше ${LIM.minCoverage * 100}%: за их пределами совмещение не проверено`);
    const shift = core(m.A).reduce((s, a, i) => s + dist(a, m.B[i]), 0) / m.n;
    if (shift > LIM.maxShift) why.push("точки на рисунке и на фото слишком далеко друг от друга: другой ракурс");
    for (const t of m.tris) {
      const r = minAreaOverT(t[0], t[1], t[2], m.A, m.B), a0 = Math.abs(r.f0);
      if (r.min <= 0) { why.push("при перетекании треугольник сетки выворачивается"); break; }
      if (a0 > 0 && r.min / a0 < LIM.minAreaRatio) { why.push("при перетекании треугольник сетки схлопывается"); break; }
    }
    return { ok: why.length === 0, why, mesh: m };
  }

  function affine(s, d) { // maps source triangle s to destination d: [a,b,c,d,e,f] for canvas.setTransform
    const [[x0, y0], [x1, y1], [x2, y2]] = s, [[u0, v0], [u1, v1], [u2, v2]] = d, den = x0 * (y1 - y2) + x1 * (y2 - y0) + x2 * (y0 - y1);
    const a = (u0 * (y1 - y2) + u1 * (y2 - y0) + u2 * (y0 - y1)) / den, c = (u0 * (x2 - x1) + u1 * (x0 - x2) + u2 * (x1 - x0)) / den;
    const e = (u0 * (x1 * y2 - x2 * y1) + u1 * (x2 * y0 - x0 * y2) + u2 * (x0 * y1 - x1 * y0)) / den;
    const b = (v0 * (y1 - y2) + v1 * (y2 - y0) + v2 * (y0 - y1)) / den, d2 = (v0 * (x2 - x1) + v1 * (x0 - x2) + v2 * (x1 - x0)) / den;
    const f = (v0 * (x1 * y2 - x2 * y1) + v1 * (x2 * y0 - x0 * y2) + v2 * (x0 * y1 - x1 * y0)) / den;
    return [a, b, c, d2, e, f];
  }

  function render(ctx, imgA, imgB, mesh, t, W, H) {
    ctx.clearRect(0, 0, W, H);
    const V = mesh.A.map((a, i) => [(a[0] + t * (mesh.B[i][0] - a[0])) * W, (a[1] + t * (mesh.B[i][1] - a[1])) * H]);
    for (const [img, P, alpha] of [[imgA, mesh.A, 1], [imgB, mesh.B, t]]) {
      for (const tr of mesh.tris) {
        const src = tr.map((i) => [P[i][0] * img.naturalWidth, P[i][1] * img.naturalHeight]), dst = tr.map((i) => V[i]);
        ctx.save(); ctx.globalAlpha = alpha; ctx.beginPath(); ctx.moveTo(...dst[0]); ctx.lineTo(...dst[1]); ctx.lineTo(...dst[2]); ctx.closePath(); ctx.clip();
        ctx.setTransform(...affine(src, dst)); ctx.drawImage(img, 0, 0); ctx.restore();
      }
    }
  }

  const api = { LIM, delaunay, buildMesh, gate, affine, hullArea, minAreaOverT, render };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.CoPMorph = api;
})(typeof window !== "undefined" ? window : globalThis);
