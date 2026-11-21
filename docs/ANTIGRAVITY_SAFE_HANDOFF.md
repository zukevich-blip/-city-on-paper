# Google Antigravity: safe project handoff

This document describes a **limited pilot** for the public City on Paper project. It does not grant access to any other repositories or accounts.

## Source of truth

- Repository README and published-site workflow on `main`.
- Core product contract: [Issue #39](https://github.com/zukevich-blip/-city-on-paper/issues/39).
- Open design review: [Issue #40](https://github.com/zukevich-blip/-city-on-paper/issues/40).
- Publication workflow: `.github/workflows/publish-museum.yml`.
- Public website: https://zukevich-blip.github.io/-city-on-paper/

The public `main` branch may contain **release tooling and metadata** rather than the entire editable museum source. Published pages are built from an explicitly pinned, tested artifact. Do not assume that the deployment artifact is editable source in `main`.

## First agent task (read-first)

1. Inspect README, Issues #39 and #40, the publishing workflow, and applicable QA workflows.
2. Identify the **actual source branch and path** for a single candidate improvement.
3. Report which elements are already implemented, missing, blocked, or merely proposed. Cite file paths and commit/PR identifiers.
4. Select one small, independently testable issue aligned with Issue #39: historical atlas navigation, licensed artwork metadata, verified view comparison, or mobile usability.
5. If source is present, prepare a **minimal patch in a separate branch**. If the source is missing from the attached resources, stop and report precisely what is missing. Never fabricate files.
6. Run existing automated checks and publish a short report with commands, results and any known gaps. Do not substitute a passed CI job for manual visual confirmation.
7. Return changes for owner review. Do not merge or deploy automatically.

## Non-negotiable rules

- Preserve the unified path: world map > country > city > place > artwork > comparison > original source.
- No competing new homepages, duplicated atlases or replacement website.
- Preserve canonical URLs and existing routes.
- Preserve original media; never present an AI-generated reconstruction as an archival original.
- Verify author, date, institution, source record, image rights and scope of license; never equate “No known restrictions” with CC0.
- Never claim exact viewpoint match without geometric evidence.
- Do not add external credentials, personal data, commercial information or files from other projects.
- Request human review for commands changing repository state. Do not push to `main`, merge PRs, publish releases or change CI/security settings without explicit authorization.

## Acceptance for the pilot

Provide (a) a confirmed source path, (b) a minimal diff or documented blocker, (c) exact validation steps and results, (d) screenshots only if actually captured, (e) remaining risks and (f) proposed PR link if a PR is created.

**Note:** This public file is a working brief, not permission to access other repositories.
