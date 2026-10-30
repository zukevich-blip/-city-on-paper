# City on Paper | First ECC-lite mission

**Baseline date:** 30 Oct 2026. Official ECC: https://github.com/affaan-m/ECC, MIT, at commit `b38be6a7f6350964d59328b52f0624e1d1d552d1`.

## Current truth
As read from GitHub default branch `main` SHA `1c541f053be3a799263e185c6fbdb2d535b5cdb1`, only two tracked files are present: `README.md` and `MIGRATION.md`. The migration note mentions a historical bundle `city-on-paper-2026-10-29.bundle` and original historic SHAs but this bundle is not in repo. **Migration has not been validated from repository contents.**

## Priorities
1. Restore original working Cities on Paper Sites code and the existing Benoist catalog/pairs, with source preservation. Do not create an unrelated starter template and call it a migration.
2. Inventory historical prints and corresponding modern photographs; separate artist name spelling from machine canonical ID, album/plate, license, image fingerprint and source.
3. Three evidence-backed matching pairs with reversible 4-8 control-point alignment and visible original/warped distinction.
4. Browser and image regression on iPhone/iPad/desktop from real preview, with manual visual review, normal and low bandwidth.
5. Scale to broader European albums and other creators only after source and rights gates.

## ECC components: chosen vs rejected
Chosen ideas: `search-first` for research-before-implementation; `tdd-workflow` for matching and metadata invariants; `verification-loop` for real source and code checks; `browser-qa` for visual comparison. Implemented now: optional `.claude/skills/city-source-and-visual-qa/SKILL.md` instructions.

Not chosen now: global ECC plugin/hooks, automatic continuous-learning transcript mining, generic MCP set, mass repository copying, remote image AI model with unspecified rights, refactoring the app into a new framework. No execution hooks have been installed.

## Acceptance
- Proven original source code and count of preserved assets, maps, pairs.
- Accurate source ledger, source/rights terms and aligned derivatives.
- Three independently confirmed matched pairs; no AI-generated historical facts.
- Measured screenshots at 375px and iPad; if protected Site cannot be accessed, mark NOT TESTED.
- Independent PR review and owner approval before changing published exhibit.

This is a **process skill**, not evidence of recovered app source or a complete ECC deployment.
