# Grand Museum V3 — independent GPT review

Artifact: city-on-paper-grand-museum-full-v3.zip, 350956 bytes, 73 entries. SHA-256: fc8ce1dc3de3f8bc550e3a6ed10a4704206db17e605c1c51a32b2b640bc48f86. All 72 root manifest entries verified. Original archive retained outside this repository.

Base: 141c3724e2. Existing GPT QA fix e399ff877251f0845a4fe4642640bf938471ff0d passed Actions run 45721282260. PR #102 remains draft; no merge or deployment authorized.

## Verified in uploaded snapshot
- 262 distinct curated IDs, 25 city labels. City coordinates are not landmark/viewpoint evidence: all 16 Rome records share 41.8902,12.4922; all 32 Venice records share 45.4342,12.3388. Preserve source metadata and classify coordinate granularity before ingestion.
- Real pixel CV implementation, KMZ exporter, MCP and 12 skill files exist. Saved vision report explicitly says geminiKeyPresentInRun=false; no live Gemini recognition demonstrated.
- Local npm test without installed dependencies: 10 passes, 4 failures (one suite failed to import jpeg-js, three remote fixture fetch failures). This is not a full 22-test result. No lockfile supplied; full build remains unverified.

## Required integration gates
1. Pin dependency versions and generate lockfile; use offline SHA-pinned fixtures rather than /tmp or moving GitHub branches.
2. Import collections as research candidates first, deduplicate against existing museum and verify source, license, depicted subject and coordinate granularity; preserve historical originals and current pairs.
3. Image fetch: reject redirects or validate each hop; stream with hard byte cap rather than arrayBuffer before checking size; enforce MIME, decode dimension and pixel limits, timeout and concurrency bounds. No public Gemini endpoints before explicit enablement, quotas and spending controls. Verify model ID via supported API before use.
4. KMZ: reject null/empty/out-of-range coordinates, distinguish straight-line schematic path from walking directions, verify XML and Google Earth client compatibility.
5. Validate MCP with actual client handshake and notification handling; tools remain read-only. Skills are prepared files, not installed integrations.
6. Port selected UI and data to existing static Pages architecture rather than replacing museum with Express prototype. Preserve release allowlist, run packaged browser QA and mobile tests.

Do not force-push, merge, deploy, activate billing, or publish unreviewed candidates. No claims of exact historical viewpoints based on CV score alone.
