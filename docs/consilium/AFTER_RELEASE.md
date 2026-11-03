# AFTER RELEASE — City on Paper private-preview review
Date: 2026-11-04. Release branch: `release/city-on-paper-private-preview-20261104`, draft PR #31. Canonical Claude task: issue #30.

## Status and honesty
**PARTIAL / pending complete packaged-browser signoff.** This is a documented post-implementation multi-role internal review by an assistant using evidence. No independent external humans participated and no authenticated Claude Code agent has confirmed execution. Real iPad Safari and VoiceOver: **NOT TESTED**. Original native ChatGPT Site v7 has **NOT** been migrated into GitHub.

## Before/after review table
| Expert role | Evidence found | Verdict | Outstanding issue |
|---|---|---|---|
| Archival curator | 41 CMA CC0 source works, two LoC Philippe Benoist items with clear source URL, 1,019 candidates not labelled public art | PASS source structure | human verification of captions still needed |
| Art historian | Lessons use direct image observations; viewpoint note says no perfect match | PASS guardrail | manual historical review before public release |
| Historical photo geometry | Working original photo/historic viewer and slider retained from previous verified PR, e.g. PR #8/POC | PASS feature presence | **zero verified exact pair**; site v7 previous seven pairs not individually reverified |
| Copyright | LoC no-known-restrictions != CC0; Panoramax credit preserved; CMA CC0 metadata | PASS metadata classification | further approval before public rights-sensitive release |
| Art direction | Consistent paper-like visual language, large viewer, source links | PARTIAL | typography and visual polish on real iPad untested |
| Accessibility | Responsive Chromium at 390/820/1440, focus and keyboard slider tests added | PARTIAL | VoiceOver and real Safari untested |
| Frontend/mobile | Full packaged test revealed horizontal overflow `studio/` phone 390 and `detective/` iPad 820 | PATCHED, recheck CI | no complete PASS until final artifact browser run |
| Imagery/media | Package audit from CI run 41686193093: 41/41 cached CMA, 4 cached photos, two LoC images present, no missing files | PASS inventory | image load on every iPad page still being tested |
| Security/privacy | Existing local notes, no commissioned public upload or paid services | PASS design | full external security review not performed |
| QA | Python release validator reports 16 pages, no broken static paths; additional Playwright visits 15 user routes and loads images | PARTIAL | release job currently still being repeated after 820px fix |
| DevOps | GitHub Actions builds ZIP + screenshots; release branch and draft PR, production/main untouched | PASS reversible candidate | no cloud-hosted private preview URL; new ZIP awaits green CI |
| Audience/editor | 3 guided city tours and 11 source-led micro-lessons survive integration | PASS scope | user satisfaction not measured, no invented ratings |
| Skeptical challenger | Highlights mismatch of old vs new view, invalid false CC0 and missing original source | PASS guardrails | do not claim a fully unified restoration |

## Defects found and repairs
1. The package JSON image paths from two-level `exhibitions/city-as-evidence/` pointed to the wrong relative location. Fixed by explicit page-depth resolver in that exhibition, commit `7486c16a`.
2. First RC workflow heredoc failed GitHub YAML parsing. Corrected indentation, commit `949445c2`.
3. Ruff found unused import in packaged validator. Corrected, commit `007f4483`.
4. Runtime on 390px found horizontal overflow in the collector Studio. Patched responsive header/rotation/text-wrap, commit `1822bff3`.
5. Runtime on 820px found horizontal overflow in Detective navigation. Patched tablet nav wrap and horizontal scrolling in commit `9e275c99`.
6. Post-fix browser QA is required; earlier P0 package audit PASS is **not** sufficient for whole release. Check current Actions on PR #31 rather than assume.

## Minimum release receipt
- Old standalone vNext preview, before RC fixes, successful base commit `2936e3d8`, run 41681342270. Downloadable Actions artifact, but does not include latest package fixes.
- New RC source: PR #31, issue #30.
- Parent source: PR #29; original GitHub main and old native Site are preserved.
- User must start the ZIP via Python HTTP server or protected static hosting, not tap index.html from Files.
- At least 41 curated public-domain/CC0 images and 4 CC0 photos in cache; some other sources are links only.
- There are **zero independently verified exact historic-modern alignment pairs** in new vNext. Slider is real and uses distinct authentic sources, but viewpoint fit claims remain conservative.
- Do not publish protected/photos/site v7 copy until real rights and migration review. Cloud deployment and real iPad testing remain separate.

**Status transition to READY TO TRY:** when latest PR #31 GitHub Actions run is green including `Audit and browser-test the ACTUAL delivered package`, and the downloadable artifact includes `RELEASE_QA.json`. This is ready as a PRIVATE exploratory product, not a public rights-certified museum nor a port of native Site v7.
