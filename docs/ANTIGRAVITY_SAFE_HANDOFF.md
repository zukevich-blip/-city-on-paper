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


## Verified source branches and no-browser handoff (2026-11-21)

The published deployment on `main` uses a pinned artifact and is not the full editable source.

GitHub branch inspection confirms that **`claude/consilium-wander`** contains the editable museum (including `index.html`, `atlas/`, `cities/`, `salon/`, `eras/`, `poc/`, `tests/` and `pyproject.toml`). Its observed HEAD was `d99e11a382ce569e16cc031e9a1f53c708a6b13e` when this note was prepared. Another relevant integration branch is **`codex/consilium-mobile`** (observed HEAD `61d0da3c0775cf5d4a68de8bdf6507edec040892`), which AGENTS.md names as a working integration line. Before editing either branch, verify current PR heads and newer changes: do not assume this information remains current.

**No GitHub/network tool in Gemini Chat?** The owner can download the complete public source ZIP from GitHub using the branch selector on the repository and `Code > Download ZIP`. Direct source-branch page:

https://github.com/zukevich-blip/-city-on-paper/tree/claude/consilium-wander

Related integration line:

https://github.com/zukevich-blip/-city-on-paper/tree/codex/consilium-mobile

Public product brief: https://github.com/zukevich-blip/-city-on-paper/issues/39

Public design review: https://github.com/zukevich-blip/-city-on-paper/issues/40

No remote access is required to inspect an owner-uploaded ZIP. Do not request passwords, OTPs or private access tokens.

On a machine or an execution-capable hosted environment, in the unpacked public source:

```sh
python -m pip install -e '.[dev]'
ruff check tools tests
pytest -q tests
```

For browser testing, inspect `tests/browser/` and `.github/workflows/qa-city-on-paper.yml` for actual dependencies and commands; do not invent test invocations. When the system cannot execute these commands, supply the patch and explicitly mark the tests NOT RUN.

There is no permission to merge or publish, alter repository permissions, or touch private repositories. A ZIP file can be inspected without connecting the entire GitHub account.


## Cross-agent handoff: ChatGPT + Claude + Gemini

All agents must use **GitHub as the shared record**, not private chat memory. This is collaboration by source-controlled changes, not direct connectivity between separate chat sessions.

**Ownership and handoff**
- **Claude**: continue existing museum curation, source research, and design on its current development line. Check `AGENTS.md`, `CLAUDE.md`, live PRs and the latest branch HEAD before modifying.
- **Gemini / Antigravity**: start as an *independent reviewer* of this public repository. Inspect real source under `claude/consilium-wander` and newer `codex/consilium-mobile` work. Pick one concrete non-overlapping bug, make a new branch prefixed `gemini/`, run the defined tests and open a **draft PR** if GitHub access is authorized.
- **ChatGPT / Codex**: verify the proposed patch against the product contracts, check CI and site safety, suggest improvements or prepare independent review. No independent publication or merge.
- **Owner**: reviews tradeoffs, resolves conflicting proposals, approves production merges/publication.

**Shared work anchors:** [Product contract #39](https://github.com/zukevich-blip/-city-on-paper/issues/39), [Design review #40](https://github.com/zukevich-blip/-city-on-paper/issues/40), [Museum expert review #49](https://github.com/zukevich-blip/-city-on-paper/issues/49), [this handoff PR #93](https://github.com/zukevich-blip/-city-on-paper/pull/93).

**Every agent's delivery must include**
1. Read commit SHA, source branch, exact changed paths and reason for changing each.
2. Links to relevant product requirement and upstream art/museum record when applicable.
3. A minimal diff in its *own* branch and a draft PR (if authorized), never a force-push to another agent's branch.
4. Exact checks run and result, or a clear `NOT RUN` marker.
5. Screen sizes tested, with real Safari/browser tests only if actually executed.
6. Known limitations, potential conflicts, what the next agent must review, and an explicit handoff to the owner.

**Conflict control:** One agent owns a given file for the duration of an active change. Before creating work, inspect existing open PRs and issues to avoid duplicating an implemented fix. Do not automatically merge agents' branches, change workflows that control release, or push to `main`.

**Security boundary:** This public repository is the only repository approved for the Gemini pilot. Its instructions do not authorize access to any private repo, personal archive, email, provider account, or secret. Any later private access requires the owner's explicit per-repository decision and separate OAuth authorization with repository-scoped permissions. Do not paste OAuth tokens, passwords or one-time codes into chat.

**No paid automation by default:** No Gemini API / Anthropic API / OpenAI API keys, pay-as-you-go activation, hosted background workers or new subscriptions without an explicit budget approval. Chat subscriptions are not API billing.
