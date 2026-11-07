---
name: release-gate
description: Run post-implementation independent quality assurance on the actual runnable package, with PASS/FAIL/NOT TESTED results.
---
1. Run ruff, pytest, museum catalog validation and all Playwright tests. Include 390px phone, 820px iPad viewport and 1440px desktop captures.
2. Build the SAME package offered to the owner; test it via HTTP server, not just the source checkout. Run tools/release/validate_bundle.py on its root.
3. Verify every route, images loaded or meaningful fallback, swipe/pointer controls, closing dialogs, keyboard focus, personal note privacy, old/new slider and accurate credit/licensing.
4. Run negative scenarios: blocked large image; missing optional external API; invalid rights; missing image, and mismatch viewpoints.
5. Compare actual before/after screenshots; challenge at least five assertions for evidence and reject misleading acceptance language. For real iPad Safari/VoiceOver use NOT TESTED until physically tested.
6. Write docs/consilium/AFTER_RELEASE.md with exact commands, screenshots, sha, CI URLs, defects fixed/held, and result READY TO TRY / PARTIAL / BLOCKED. No automatic merge/deploy to main.
