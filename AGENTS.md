# City on Paper — instructions for Codex and cooperating coding agents

> **Обновление 09.11.2026: правила ниже относятся к историческому релизу. Для текущей серии работ сначала проверьте фактическую базовую ветку.** Новый исследовательский стек: #45 (география) → #46 (историческая картография) → #48 (единый музейный UX) → #50 (консилиум качества, WCAG и PWA). PR #44 (Париж, 15 GCP) идёт **параллельно** и не должен неявно включаться при слиянии стека. Публичный релиз и самостоятельная экспертная атрибуция/GCP всё ещё **НЕ ПРИНЯТЫ**. Прежде чем работать, откройте `docs/consilium/CREATION_AND_POSTBUILD_PROTOCOL.md`, [Issue #49](https://github.com/zukevich-blip/-city-on-paper/issues/49) и зелёные/красные CI по выбранной ветке. Нельзя трактовать роль агента как заключение привлечённого человека. Для новых задач используйте отдельную PR-ветку, не выполняйте работу напрямую на release/main без явного решения владельца.

This is the **same single project**, not a fork. Work on `release/city-on-paper-private-preview-20261104`, the branch of draft PR #31, unless another agent currently owns that file. The canonical brief is GitHub Issue #30. Read `CLAUDE.md`, both `docs/consilium/BEFORE_RELEASE.md` and `docs/consilium/AFTER_RELEASE.md`, plus `docs/consilium/CLOSE_READING_EDITORIAL_REVIEW_20261103.md`. Codex and Claude must use **one design, one dataset contract, one packaged release**; never generate a competing v2 site without a technical migration decision.

## New priority: actual *visible* scale, not inflated records
- Keep the 41 hand-curated CMA originals, 2 explicitly non-CC0 Philippe Benoist LoC works, the existing Then/Now slider, 11 close-reading lessons, and 7-view old Site v7 as an **unrecovered, separate historical source**.
- Expand using `tools/curation/expand_open_archives.py`: Cleveland CC0 API, Art Institute of Chicago public-domain IIIF, Met Museum Open Access CC0 / `/v1.1/search`, machine-labelled discovery. Gallery `salon/index.html` merges the archive into the same museum, filters by institution/quality, pages results by 48. `museum-expansion-v1.json` is produced in the **same release artifact**, not a separate static website. Never call an archive metadata candidate a verified rendered image until actual image loading succeeds.
- Images have legitimate source links, creator roles, copyright/usage labels, original resolution hints and quality tiers: `высокое`, `экранное`, `не измерено`; no upscaling framed as original quality. Keep occasional lower-resolution works with a warning.
- Museum institution source facts are API-verified, **editorial relevance selection is automatic** and must be labelled as such until a human curator reviews it. Do not invent popularity/rating numbers. Source image hotlinking preferred by AIC, rather than bulk scraping their IIIF.
- Preserve all rights warnings, and do not reclassify LoC no-known-restrictions as CC0 or blindly mirror restricted/unknown photos.
- For modern photography, use CC0 or explicitly attributed CC BY/CC BY-SA pictures only with per-image attribution, license and original link. Do not present non-matching camera angles as exact slide transitions.
- The GitHub PR and the primary user-facing zip are the deliverable. No public deploy or premium paid infrastructure before the owner opts in.

## Working arrangement / one source of truth
1. Before touching files, look at PR #31 HEAD SHA and Actions. If another agent modified the file, read latest before modifying.
2. Use `.claude/agents/` as distinct responsibility templates, not imaginary completed agents; use `.claude/skills/` checklists.
3. Implement directly on the same release branch in bounded, reversible commits and review existing tests. Report errors and fix them; don't open 15 parallel speculative PRs.
4. Quality gate: `ruff check tools tests`, `pytest -q tests`, source browser suites, **actual built ZIP** `tools/release/validate_bundle.py`, `tests/browser/qa_packaged.js`. Mobile 390, iPad-like 820, desktop 1440. Real Safari remains NOT TESTED unless genuinely tested.
5. Don't silently modify old native Site v7 (https://city-on-paper-anatolii.tolyaz.chatgpt.site). Its original source/export remains missing from the repo. Do not lose its seven user-visible pairs or pretend exact alignment validation.
6. Favorite next ideas: lost buildings (Les Halles/Tuileries), architectural detail detective, authentic city/restaurant market trails, owner photo fieldwork, original editions/artists' workshops; choose quality of educational encounters, not just a swollen grid.

## Concurrency
Claude/Codex may review in parallel but should coordinate file ownership in PR #31; the integration branch + CI is the shared state. Opening a competing host or codebase is a last resort with documented migration and preservation checks.
