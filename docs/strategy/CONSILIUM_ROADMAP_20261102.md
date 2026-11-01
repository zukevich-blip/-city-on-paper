# CONSILIUM: City on Paper product and engineering plan — 02.11.2026

Decision: treat the already active Site v7 as the product baseline, not empty GitHub main. Build a museum-quality, bilingual then/now travel and urban-life atlas, preserving original historic images and image provenance. Scope includes Benoist and comparable lithographs/prints/photographs, architecture, historic markets/cafes/menus and actual walking viewpoints.

### Expert-review roles and responsible streams (role review performed in this conversation; does not claim separate live external agents were invoked)

1. **Preservation / migration**: Site v7 with 38 records, 7 ready comparisons, 22 Paris Musees CC0-labelled entries, and existing user 4-point photo alignment. Owner export of code/bundle is P0 blocker. Preserve original source, 7 pair states, current art, notes, image license, and compare screenshots.
2. **Curatorial / museum identity**: PR #7 first produced 333 candidate records; its 01 Nov late update reports 1019 candidate records from 117 contributing institutions via eight providers plus Commons category discovery (NOT 117 distinct APIs). PR #11 = 27 holder-crosschecked records, 22 with recorded author confirmation and 5 uncertain; PR #10 independently reviewed Antoine Benoist collision and fail-closed rights thumbnails. Claude has already brought core fixes into PR #7. Historical PR #10 needs selective reconciliation, not blind merge. Curator must check the art and source links before displaying it. Do not merge PR #10 and PR #11 blindly: both target PR #7 independently.
3. **Rights and provenance**: 119 preliminary open, 165 restricted, 49 unknown. Restricted/unknown = metadata + source link only, no thumbnails. Existing Site Paris Musees CC0 works to be reconciled by individual image license. No public download/upload of user photos; no unconsented geolocation.
4. **Computer vision / QA**: PR #8 now contains a control-point editor, RU/EN toggle, a second real comparison (Palais-Royal, viewpoint mismatch), cap on low coverage (<15%) and 187/187 Chromium QA checks; preserve historic pixels immutable, photo original one tap away. Review PR #12 was superseded by these changes and closed WITHOUT merge. Evaluate Site's existing seven pairs, select >=3 independently verified and geometrically defensible matches. Real Safari tests required.
5. **Museum UX / narrative**: PR #9 has three ideas. Adopt Archive paper A as main experience, map and routes from B, culinary story ideas from C in same design. Initial Paris tour: Madeleine, Parc Monceau, Saint-Sulpice with one verified old market/cafe story. Then Vilnius/Album de Wilna, Naples, Rome, other cities. Pin only geographically verified viewpoints.
6. **Release engineering / agent coordination**: PR #7, #8, #9, #10, #11 and strategy PR #13 remain draft until independent clean-checkout tests, human research confirmation, migration and owner approval. PR #12 has been closed as superseded, not merged. GitHub Issue #1 tracks recovery; Issue #6 tracks product scope. Claude should maintain a single dependency/status board, not create competing rebuilds.

### Executable order

P0A: Verify and recover original site source. If owner export unavailable, record BLOCKED precisely, while maintaining independent research branches.
P0B: Build a clean integration plan for latest PR #7 (1019 candidates) plus source-backed PR #11 (27 works), selectively carrying any additional valid review findings from older PR #10; preserve evidence of attributions and resolve conflicts. Run complete pytest/ruff. Keep old Site IDs for dedup.
P0C: Review the LATEST PR #8 and its now-built-in <15% coverage cap; PR #12 is superseded/closed. Demonstrate unchanged old artwork and explicit low-coverage opt-in. Test on 375/390/820/1440 Chromium and real Safari before release.
P1: Develop a *single* complete Paris experience using source-approved scans and photo rights, 3 honest pairs and 1 historic gastronomy story, with city page, atlas, deep zoom, credits.
P2: Scale via Europeana, LoC, Rijksmuseum, Paris Musees API with account/token, BnF/Gallica (conditions), INHA for author identities, other institutional IIIF endpoints. No bypass of 403/429, no unverified license assumption.

### Release gates / definitions of done

- Site v7 art inventory, seven published pairs, manual 4-point tool, notes and export do not regress.
- At least 20 well-described artworks for first release, at least 10 images licensed for display, no auto-thumbnail for restricted/unknown rights.
- Three visually/archivally confirmed historical/current pairings; each holds a photo source, creator/date/license, control points, uncertainty/coverage and original toggle. Publishing a 7%-coverage transform as a whole-frame match is forbidden.
- At least one sourced food-market/cafe/menu historical story, NOT keyword false positives from Market Street, still life or slave-market works.
- iPhone/iPad/desktop responsive, keyboard, accessibility, browser Safari QA, source credits and reliable no-key fallback.
- No automatic merges or publication; explicit owner review of final release.

Related: Issue #1, Issue #6, stream Issues #14–#17, PRs #7–#13. Note Claude's four-agent consilium update under #6 with 1019/117 metadata records and 187/187 Chromium checks; claims need independent release verification. Full existing-Site summary in docs/migration/SITES_BASELINE_20261102.md.