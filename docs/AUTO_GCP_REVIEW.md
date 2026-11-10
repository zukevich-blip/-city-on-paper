# Research GCP candidate pipeline (not scientific confirmation)

`tools/automated_gcp.py` matches a historic raster to an existing reference raster with ORB, a reciprocal Lowe ratio test, and RANSAC homography. It does **not** prove that the two rasters show the same geography or that individual landmarks remained fixed in the intervening decades.

## Requirements and run

Use Python 3.11+, `opencv-python-headless`, `numpy`, and `pyproj` (the last is needed for georeferenced outputs).

```bash
python -m pip install -r tools/requirements-gcp.txt
python tools/automated_gcp.py \
  --source path/to/original-historical-map.png \
  --reference path/to/exact-georeferenced-reference-raster.png \
  --reference-georef path/to/reference-georef.json \
  --output data/gcp-candidates/paris-candidate.json
```

Example of `reference-georef.json` (replace these **illustrative** values with real measured metadata from the raster; never use the example to claim accuracy):

```json
{
  "crs": "EPSG:32631",
  "geotransform": [500000, 1, 0, 5410000, 0, -1]
}
```

The affine coefficients use GDAL's corner-origin convention: map X = c0+c1*pixel_x+c2*pixel_y; map Y = c3+c4*pixel_x+c5*pixel_y. The reference image must be the **same pixel dimensions and origin** as the georeferenced source. A screenshot of a slippy map or an arbitrary satellite image has no reliable georeferencing without its exact raster metadata.

A run without `--reference-georef` writes matched pixel pairs, not real-world GCPs; `residual_rmse_meters` remains `null`. When georeferencing is provided, it becomes the RMS distance *between the detected and model-predicted reference locations*, based on WGS84 ellipsoidal distances. This is only an in-sample residual, not absolute positioning accuracy. The zero/low residual can still be completely wrong geographically.

Every result remains either `candidate_auto` or `auto_fail`, with `scientific_accuracy_verified: false` and `review_required: true`. The program never emits `verified_auto`. It also does **not** export an Allmaps Georeference Annotation directly. Before such an export, an editor must validate image originality/dimensions, landmark identity, historic transformations and geographical positions, compare withheld independent control points, and confirm rights/IIIF source and quality of reference raster. A reviewer should then publish confirmed control points in the appropriate separate verified dataset and the Allmaps/IIIF annotation format.

## Site/CI audit

`tools/integration_check.py` reuses the existing `tools/release/audit_public_links.py`, validates a supplied catalog's local image assets, and rejects malformed candidate GCP records or false verification claims. It must be pointed at **the actual built public directory**, not source code.

```bash
python tools/integration_check.py --root public \
  --auditor tools/release/audit_public_links.py \
  --report /tmp/city-on-paper-integration.json
```

To also check the candidate inventory and a normalized catalog, add `--gcp-dir data/gcp-candidates` and `--catalog path/to/catalog.json` once those real inputs exist. Missing *requested* inputs must fail. An HTTP image URL is reported as **unverified**, never treated as a successfully downloaded image. JS-generated links, external URLs, historical claims and browser visuals require separate tests.

No new workflow in this patch deploys to the public museum. Feature-branch results require QA before any `main` or production integration.
