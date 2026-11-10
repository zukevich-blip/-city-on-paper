# City on Paper · Geography QA patch (2026-11-10)

**Scope:** Candidate historic-map GCPs, scientific status separation, and published-site integration checks. **Status:** local implementation tested; NOT merged, deployed, or validated on Paris/Florence/Naples originals.

This directory can be overlaid onto the root of `zukevich-blip/-city-on-paper` in a new research feature branch. It adds files; it does not overwrite the existing production publication workflow or the trusted `tools/release/audit_public_links.py`.

## Contents

- `tools/automated_gcp.py`: ORB + reciprocal Lowe matching, RANSAC homography, spatial candidate sampling, real reference raster optional CRS+geotransform, SHA-256 provenance and **unverified** GCP candidate output.
- `tools/integration_check.py`: fail-closed built-site link gate reusing existing auditor, optional catalog local asset check and unverified GCP schema validation.
- `tools/requirements-gcp.txt`: research-only test dependencies.
- `tests/test_geo_pipeline.py`: synthetic positive/negative and integration gate tests.
- `.github/workflows/research-georeferencing-ci.yml`: PR QA only, no deployment.
- `docs/AUTO_GCP_REVIEW.md`: use and explicit scientific limitations.

## Installation in an existing git checkout

1. Create a feature branch from the current repository state (not `main` release publication).
2. Copy this archive's files to the repository root, preserving folders.
3. Run:

```bash
python -m pip install -r tools/requirements-gcp.txt
python -m pytest -q tests/test_geo_pipeline.py
python -m compileall -q tools/automated_gcp.py tools/integration_check.py
```

4. Test two **real** images with valid provenance, known pixel sizes and optionally a real CRS/geotransform for the reference raster. Review the generated `data/gcp-candidates/*.json` against historical landmarks and independent survey points before asserting any geographic accuracy.
5. In the actual built-site release job run `python tools/integration_check.py --root public --report /tmp/integration.json`. Include optional `--catalog` and `--gcp-dir` only when those datasets actually exist and are intended for QA. Do not equate `PASS_SCOPED` to browser/IIIF, history, external HTTP or rights verification.
6. Only after results pass on real sources should the publication owners decide whether and how to wire the check into the **pinned** production workflow. Do not change the pinned approved release artifact as part of this patch.

## Acceptance gates

- No output may claim `verified_auto`, survey-grade accuracy, or georeferenced `lon/lat` without a reference raster CRS/geotransform.
- Metric residuals are **in-sample model fitting error**, not an accuracy claim.
- False or missing local links, missing requested input catalogs, and falsely verified GCP statuses must fail the gate.
- Run the repository's existing audit rather than a no-op `pass` and return `PASS_SCOPED` only when verified checks pass.
- Proof of real Paris 1870 / 2023 fit requires authoritative source images, actual recorded CRS/geo metadata, validated stable landmarks and independent control points; the earlier example with 1.85 m must not be repeated as established.

Project live link (unchanged by this patch): https://zukevich-blip.github.io/-city-on-paper/
