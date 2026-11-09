# CITY ON PAPER / Город на бумаге — Claude Code operating instructions

> **Обновление 09.11.2026: правила ниже относятся к историческому релизу. Для текущей серии работ сначала проверьте фактическую базовую ветку.** Новый исследовательский стек: #45 (география) → #46 (историческая картография) → #48 (единый музейный UX) → #50 (консилиум качества, WCAG и PWA). PR #44 (Париж, 15 GCP) идёт **параллельно** и не должен неявно включаться при слиянии стека. Публичный релиз и самостоятельная экспертная атрибуция/GCP всё ещё **НЕ ПРИНЯТЫ**. Прежде чем работать, откройте `docs/consilium/CREATION_AND_POSTBUILD_PROTOCOL.md`, [Issue #49](https://github.com/zukevich-blip/-city-on-paper/issues/49) и зелёные/красные CI по выбранной ветке. Нельзя трактовать роль агента как заключение привлечённого человека. Для новых задач используйте отдельную PR-ветку, не выполняйте работу напрямую на release/main без явного решения владельца.

## Mission (owner-approved)
Build a beautiful, coherent, **working private museum preview**, RU-first, usable on iPhone/iPad/desktop. User wants the finished experience, not repeated permission loops or collections of ideas. No irreversible/public steps without permission. Canonical P0 coordination and double-consilium specification: **GitHub issue #30** (https://github.com/zukevich-blip/-city-on-paper/issues/30).

## Start here, every session
1. Read issue #30 and relevant project history: docs/consilium/MASTER_DIRECTION_20261103.md, EXPERT_AGENTS_EDITORIAL_GATES_20261103.md, CLOSE_READING_EDITORIAL_REVIEW_20261103.md.
2. Check `git branch`, PRs #18–#29, HEAD/parents, CI and the latest standalone preview artifact; do not confuse parallel draft branches with merged changes. Read MIGRATION.md. **Main is not the runnable app.**
3. Audit the available historical artworks and source rights. 1019 candidate records are not 1019 approved images. The 41 CMA CC0 originals are a legitimate art wall; two LoC Philippe Benoist images are "no known restrictions", not CC0.
4. Before coding run /museum-consilium and write `docs/consilium/BEFORE_RELEASE.md`; isolate specialist tasks if subagent tool available.
5. Implement P0: a coherent preview with hero historic/now slider and proper route links. Build artifact and test it through HTTP (not `file://`), across mobile/tablet/desktop; repair actual failures.
6. After coding run /release-gate and a genuinely separate review if available; write `docs/consilium/AFTER_RELEASE.md` with pass/fail/not-tested and evidence.
7. Share one preview artifact link and exact commands (Russian), PR number, tested routes, known limitations. Keep a rollback reference. Do not claim iPad Safari was tested using Chromium.

## Preserve important history
- Original native ChatGPT Site v7 had seven user-visible comparisons and manual alignment, but its owner-held source export/bundle is **NOT** imported into GitHub main. No claim of recovery without actual bytes/SHAs.
- Latest integrated development is stacked from PR #29 and predecessors. Native Site v7 is a separate preservation/migration track.
- `poc/compare/`: Madeleine historic/modern viewpoints differ, at most limited front-portico alignment; Palais-Royal directions opposite, cannot honestly overlay. Never deform the lithograph or mark an unverified pair as perfect.
- Preserve photography attribution, CC BY-SA terms, role of original draughtsman vs lithographer/printer and archive accession.
- Assume private usage, but private is NOT blanket permission to copy/share third-party photos or code.

## Working conventions
- Prefer minimal static web bundle first; avoid rewriting all working modules in a new framework.
- Source of truth for navigation: index.html, salon/, exhibitions/city-as-evidence/, closeup/, journeys/, detective/, discover/, fieldwork/, printlab/, atelier/, ornaments/, poc/compare/.
- Data: data/curation, data/catalog/works, data/candidates. Distinguish source records, verified objects and unapproved discovery candidates.
- CI: `ruff check tools tests`, `pytest -q tests`, Playwright scripts in tests/browser, `python -m tools.catalog.validate`, and package check on **built** artifact.
- Use approved dependency license notices; run automated checks before calling a release ready.
- No tokens/secrets in code. Never upload private user photos or GPS. Use localStorage only for private notes/selection until a privacy policy is approved.
- Merge/deploy production only after explicit owner authorization; create test branches and draft PRs freely.
- Avoid speculative claims like “hundreds of verified matching views,” “every image is open” or “iOS Safari verified” without evidence.

## Consilium specialists
Use these project-specific subagents when available: `archive-curator`, `historical-geometry`, `museum-art-director`, `app-quality-reviewer`, `release-coordinator`. They are instructions for specialist tasks, not a record of independent human experts. Record actual agent runs and artifacts, not fictional parallel completion.

## Externally authored reference tools
Consider official, license-cleared integrations only when justified: OpenSeadragon (BSD-3-Clause), Mirador (Apache 2.0), IIIF APIs, Cleveland CMA Open Access, AIC/Met/LoC/BnF and Panoramax licensing. Document licenses, pinned versions and fallbacks. Don't blindly clone closed sites or services. Product objective always takes priority over installing tools.

## GitHub PR / release gate
P0 means a private downloadable executable preview with functioning interactive routes, accurate credits, and PASS for actual archive. P1 means curated depth and better modern photos. P2 means installable PWA after content quality. Do not schedule unbacked work or promise finishing tomorrow without an actual runner.
