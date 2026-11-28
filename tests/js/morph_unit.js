const assert = require("assert");
const M = require("../../poc/compare/morph.js");
const mk = (cp, conf = "high", cov = 0.4) => ({ historic: { size: [1000, 700] }, photo: { size: [1000, 700] }, control_points: cp, alignment: { confidence: conf, control_point_coverage: cov } });
const grid = [[100, 100], [500, 80], [900, 120], [150, 400], [600, 380], [880, 420], [200, 640], [700, 620]];
const near = grid.map(([x, y]) => ({ historic: [x, y], photo: [x + 12, y + 8] }));
// 1. a good, covering pair passes and the mesh covers the unit square
const ok = M.gate(mk(near));
assert.ok(ok.ok, ok.why && ok.why.join("; "));
const total = ok.mesh.tris.reduce((s, t) => s + Math.abs(M.hullArea(t.map((i) => ok.mesh.A[i]))), 0);
assert.ok(Math.abs(total - 1) < 1e-6, "Delaunay mesh must tile the frame, area=" + total);
// 2. too few points
assert.ok(!M.gate(mk(near.slice(0, 4))).ok);
// 3. small coverage (local fit only) is refused with the reason
const low = M.gate(mk(near, "low", 0.02));
assert.ok(!low.ok && /покрывают/.test(low.why.join()));
// 4. a fold (two points swapped between images) is detected through the exact Jacobian check
const fold = near.map((c) => ({ ...c })); [fold[1].photo, fold[4].photo] = [fold[4].photo, fold[1].photo];
const f = M.gate(mk(fold));
assert.ok(!f.ok && /выворач|схлоп|далеко/.test(f.why.join()), f.why.join());
// 5. viewpoint mismatch is refused
assert.ok(!M.gate(mk(near, "viewpoint_mismatch")).ok);
// 6. the affine map really sends the source triangle onto the destination
const [a, b, c, d, e, g] = M.affine([[0, 0], [1, 0], [0, 1]], [[2, 3], [4, 3], [2, 7]]);
assert.deepStrictEqual([a, b, c, d, e, g].map((v) => Math.round(v * 1e9) / 1e9), [2, 0, 0, 4, 2, 3]);
// 7. exact minimum of the quadratic area: a triangle that flips has min <= 0
const A = [[0, 0], [1, 0], [0, 1]], B = [[0, 0], [1, 0], [0, -1]];
assert.ok(M.minAreaOverT(0, 1, 2, A, B).min <= 0);
// 8. local morph: the documented Notre-Dame pair passes with the same error limits as a "high" fit, madeleine-ph-benoist does not
const fs = require("fs"), pr = (n) => JSON.parse(fs.readFileSync(__dirname + "/../../poc/compare/pairs/" + n + ".json", "utf8"));
const nd = M.gateLocal(pr("notre-dame-benoist-carnavalet"));
assert.ok(nd.ok, nd.why.join("; "));
assert.ok(nd.local.hullPrint > 0.04 && nd.local.hullPrint < 0.5, "trust region share " + nd.local.hullPrint);
const bad = M.gateLocal(pr("madeleine-ph-benoist"));
assert.ok(!bad.ok && /допустимо/.test(bad.why.join()));
for (const n of ["madeleine-benoist-carnavalet", "louvre-colonnade-benoist-carnavalet"]) assert.ok(M.gateLocal(pr(n)).ok, n);
assert.ok(!M.gateLocal(pr("synthetic-parallax")).ok, "parallax synthetic must fail the leave-one-out limit");
console.log("morph unit: ok");
