---
name: city-source-and-visual-qa
description: "ECC-lite quality workflow for City on Paper historical lithography sources, Benoist attribution, photography matching, rights, alignment and mobile museum UI. Use before catalog import, matching, visual changes or releases."
---

# City on Paper | ECC-lite source and visual verification

Project-specific on-demand workflow, **inspired by** the official [Everything Claude Code](https://github.com/affaan-m/ECC) search-first, TDD, verification-loop, and browser-qa processes (MIT). Reference upstream commit `b38be6a7f6350964d59328b52f0624e1d1d552d1`, checked 2026-10-30. No full ECC installation, external hooks, or third-party runtime is included.

## Gate 0: restore before rebuilding
The default `main` on 2026-10-30 contains only `README.md` and `MIGRATION.md`. The latter reports a separately preserved owner checkpoint `city-on-paper-2026-10-29.bundle`; the actual app source is NOT currently in this repo tree. Recover approved source from that bundle or existing Sites export, verify SHAs, then compare screenshots and data inventory against the running exhibit. Do not fake a working app, recreate all images, rewrite history, or merge before comparing.

## Gate 1: research and source attribution
- Before building a catalog parser/image matcher, inspect the existing source and research maintained open-source tools; compare IIIF manifests, museum archives, Europeana/Gallica/public-domain digitization and licensed contemporary photos; record source URLs and reuse constraints.
- Maintain original attribution vs uncertain attribution: Felix Benoist and Philippe Benoist are distinct artists. Check title, album/plate, date, publisher, archival identifier, exact scan source and license/rights per work; never assign artist by similarity alone.
- For each modern candidate record photographer, source, capture date, GPS/geolocation confidence, license, allowable caching/reproduction, viewpoint description; don't bulk download imagery from Google/Yandex map interfaces contrary to terms.
- Historic scan is immutable. Save aligned transformations separately as derivative **presentation geometry** (crop, rotate, perspective, 4–8 reference points, masks). Never invent missing architecture or represent AI inpainting as documentary proof.

## Gate 2: TDD / comparison truth
- Start with 3 source-backed exact-place pairs, offline fixtures and test for place identity, landmark anchors, orientation, true/false matches, transformation round-trip and original-versus-transformed display.
- For same-place mismatches return `uncertain` with clear explanation rather than fabricated high-confidence overlay.
- Compare architectural elements with explicit observations and citations; historical artistic license is an interpretation, not proof of an exact geometric drawing.

## Gate 3: mobile visual QA (ECC browser-qa)
- Mobile 375px and iPad landscape + desktop screenshots on actual protected preview; compare before/after baseline, avoid baseline-free PASS.
- Test slider, alpha overlay, blink, zoom, multiple candidate photos, legend/sources, reduced motion, accessibility and no broken thumbnails.
- Use synthetic/public-domain test fixtures; do not upload private user photos or restricted digitizations to external services. Respect cache/low-bandwidth.

## Gate 4: verification and release
Record recovered source SHA, exact imported work/pair counts, rights ledger, test command/results, screenshot diffs, evidence URLs, actual target-device state (PASS/FAIL/NOT TESTED). Public Sites stays unchanged until owner approves replacement. GitHub PR remains draft until real originals, manual review and device test.
