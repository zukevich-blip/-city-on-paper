# AFTER RELEASE — City on Paper private-preview review
Date: 2026-11-04. Release branch: `release/city-on-paper-private-preview-20261104`, draft PR #31. Canonical Claude task: issue #30.

## Status and honesty
**READY TO TRY as a PRIVATE preview; public/legacy-migration gates remain HOLD.** This is a documented post-implementation multi-role internal review by an assistant using evidence. No independent external humans participated and no authenticated Claude Code agent has confirmed execution. Real iPad Safari and VoiceOver: **NOT TESTED**. Original native ChatGPT Site v7 has **NOT** been migrated into GitHub.

## Before/after review table
| Expert role | Evidence found | Verdict | Outstanding issue |
|---|---|---|---|
| Archival curator | 41 CMA CC0 source works, two LoC Philippe Benoist items with clear source URL, 1,019 candidates not labelled public art | PASS source structure | human verification of captions still needed |
| Art historian | Lessons use direct image observations; viewpoint note says no perfect match | PASS guardrail | manual historical review before public release |
| Historical photo geometry | Working original photo/historic viewer and slider retained from previous verified PR, e.g. PR #8/POC | PASS feature presence | **zero verified exact pair**; site v7 previous seven pairs not individually reverified |
| Copyright | LoC no-known-restrictions != CC0; Panoramax credit preserved; CMA CC0 metadata | PASS metadata classification | further approval before public rights-sensitive release |
| Art direction | Consistent paper-like visual language, large viewer, source links | PARTIAL | typography and visual polish on real iPad untested |
| Accessibility | Responsive Chromium at 390/820/1440, focus and keyboard slider tests added | PARTIAL | VoiceOver and real Safari untested |
| Frontend/mobile | Real packaged browser QA initially revealed `studio/` phone 390, `studio/` iPad 820 and `detective/` iPad 820 overflows | PASS after fixes, GitHub run 41687414198 | physical iPad touch remains NOT TESTED |
| Imagery/media | Package audit from CI run 41686193093: 41/41 cached CMA, 4 cached photos, two LoC images present, no missing files | PASS inventory | image load on every iPad page still being tested |
| Security/privacy | Existing local notes, no commissioned public upload or paid services | PASS design | full external security review not performed |
| QA | Release audit 16 pages, no missing files/links; packaged Playwright passed all 15 visitor routes at 390/820/1440, real image loading and slider/side-by-side. GitHub Actions run 41687414198, commit 3e3748eb | PASS private preview | real device Safari/VoiceOver NOT TESTED |
| DevOps | GitHub Actions builds ZIP + screenshots; release branch and draft PR, production/main untouched | PASS reversible candidate | no cloud-hosted private preview URL; new ZIP awaits green CI |
| Audience/editor | 3 guided city tours and 11 source-led micro-lessons survive integration | PASS scope | user satisfaction not measured, no invented ratings |
| Skeptical challenger | Highlights mismatch of old vs new view, invalid false CC0 and missing original source | PASS guardrails | do not claim a fully unified restoration |

## Defects found and repairs
1. The package JSON image paths from two-level `exhibitions/city-as-evidence/` pointed to the wrong relative location. Fixed by explicit page-depth resolver in that exhibition, commit `7486c16a`.
2. First RC workflow heredoc failed GitHub YAML parsing. Corrected indentation, commit `949445c2`.
3. Ruff found unused import in packaged validator. Corrected, commit `007f4483`.
4. Runtime on 390px found horizontal overflow in the collector Studio. Patched responsive header/rotation/text-wrap, commit `1822bff3`.
5. Runtime on 820px found horizontal overflow in Detective navigation. Patched tablet nav wrap and horizontal scrolling in commit `9e275c99`.
6. The full packaged Playwright run has now **PASS** at 390, 820 and 1440px. Passing GitHub Actions: [41687382687](https://github.com/zukevich-blip/-city-on-paper/actions/runs/41687382687) (functional RC) and [41687414198](https://github.com/zukevich-blip/-city-on-paper/actions/runs/41687414198) (extra overflow diagnostics).

## Minimum release receipt
- Old standalone vNext preview, before RC fixes, successful base commit `2936e3d8`, run 41681342270. Downloadable Actions artifact, but does not include latest package fixes.
- New RC source: PR #31, issue #30; verified CI on commit `3e3748eb`. A downloadable preview ZIP was produced by run 41687382687.
- Parent source: PR #29; original GitHub main and old native Site are preserved.
- User must start the ZIP via Python HTTP server or protected static hosting, not tap index.html from Files.
- At least 41 curated public-domain/CC0 images and 4 CC0 photos in cache; some other sources are links only.
- There are **zero independently verified exact historic-modern alignment pairs** in new vNext. Slider is real and uses distinct authentic sources, but viewpoint fit claims remain conservative.
- Do not publish protected/photos/site v7 copy until real rights and migration review. Cloud deployment and real iPad testing remain separate.

**Release decision: READY TO TRY, privately.** The exact packaged-preview QA and browser test passed with `RELEASE_QA.json`, cached assets and genuine then/now slider interaction. Still **NOT READY for public release** without independent legal/historical review, iOS Safari testing, and authorized legacy Site v7 source preservation. The shared ZIP is not a remotely hosted site. No independent Claude Code agent has acknowledged issue #30; do not claim multi-agent execution.
