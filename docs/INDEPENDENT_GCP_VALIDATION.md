# City on Paper: geographic accuracy audit (research only)

This validator intentionally **does not** use an assumed paper scale, guessed satellite
metres per pixel, or the ORB RANSAC inlier residual as evidence of map accuracy.

## 1. Recompute the existing Paris 1878 research model

Run from the repository root:

```bash
python tools/validate_geographic_accuracy.py   --legacy-paris data/vision-lab/georef-paris-1878.json   --output /tmp/paris-1878-affine-research-audit.json
```

This re-fits the six-parameter affine model to the **same 15 provisional landmarks**
and calculates correct Euclidean RMS and leave-one-out RMS in the explicitly stated
local metric frame. Expected approximate results are 25.94 m in-sample and
34.90 m leave-one-out. This is NOT external validation; the same historical
pixel selections and modern object coordinates can share systematic errors.

## 2. Evaluate a frozen ORB transform using NEW holdout landmarks

Prerequisites:
- A real historic raster (same exact bytes as in the ORB candidate JSON).
- A real authorized, georeferenced modern reference raster; its actual EPSG CRS
  and **six-term GDAL geotransform** must be recorded in the ORB candidate.
- A JSON file of six or more **independently selected and visually reviewed**
  historic/source-image pixel positions and WGS84 coordinates of the exact same
  fixed landmarks. These must NOT be copied from the ORB's matched keypoints
  or its fit outputs. Prefer points distributed over multiple map regions.
- A named reviewer and a genuine https evidence URL for each point. The program
  can check whether those fields are present but **cannot authenticate the evidence**.

Minimal expected format (placeholders, NOT actual Paris control points):

```json
{
  "schema_version": "city-on-paper.independent-gcp-controls.v1",
  "historic_sha256": "64-character historical raster sha256 from candidate",
  "reference_sha256": "64-character reference raster sha256 from candidate",
  "points": [
    {
      "id": "landmark-a",
      "historic_pixel": [1234.5, 2345.6],
      "longitude_latitude": [2.3, 48.85],
      "reviewer": "Actual independent reviewer",
      "evidence_url": "https://example.org/actual-primary-source",
      "historic_landmark_checked": true,
      "modern_position_checked": true,
      "independent_of_orb": true
    }
  ]
}
```

The above is a shape illustration with only **one invented placeholder point**:
it is not valid evidence and will fail the six-point minimum. Supply true
independent records before attempting a scientific review.

```bash
python tools/validate_geographic_accuracy.py   --candidate /path/to/genuine-paris-orb-candidate.json   --controls /path/to/independent-reviewed-holdout.json   --output /tmp/independent-holdout-research-report.json
```

The fixed ORB homography maps historic full-resolution pixels to modern reference
pixels. The real GDAL raster geotransform and pyproj then map reference pixels
to WGS84. `pyproj.Geod.inv` measures geodesic errors against reviewer-provided
WGS84 points, yielding `sqrt(mean(error_m ** 2))` (not `mean(error_m)`).
It does **not** refit the ORB model on holdout landmarks, avoiding test leakage.

## What the validator deliberately refuses

- No missing CRS / raster geotransform, missing evidence or assumed paper scales.
- No zero-RMSE result when test subsets cannot be computed.
- No automatic claims of ±5 m, ±10 m or ±15 m based solely on internal fit.
- No scientific certification or `approved_for_publication=true` from code.
- No merging map georeferencing with lithograph-to-photograph viewpoint matching.

The existing PR #44 historic Paris 1878 GCP dataset does not yet supply
independently reviewed holdout points for the ORB raster. At present, **only
the internal affine reproduction in section 1 is executable without new data**.
Keep the public GitHub Pages museum pinned to its approved source.

Tests: `pytest -q tests/test_validate_geographic_accuracy.py`.
