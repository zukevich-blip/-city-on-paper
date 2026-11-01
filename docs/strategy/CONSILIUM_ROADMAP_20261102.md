# CONSILIUM: City on Paper product and engineering plan — 02.11.2026

Decision: treat the already active Site v7 as the product baseline, not empty GitHub main. Build a museum-quality, bilingual then/now travel and urban-life atlas, preserving original historic images and image provenance. Scope includes Benoist and comparable lithographs/prints/photographs, architecture, historic markets/cafes/menus and actual walking viewpoints.

### Expert-review roles and responsible streams (role review performed in this conversation; does not claim separate live external agents were invoked)

1. **Preservation / migration**: Site v7 with 38 records, 7 ready comparisons, 22 Paris Musees CC0-labelled entries, and existing user 4-point photo alignment. Owner export of code/bundle is P0 blocker. Preserve original source, 7 pair states, current art, notes, image license, and compare screenshots.
2. **Curatorial / museum identity**: PR #7 = 333 candidate metadata records; PR #11 = 27 holder-crosschecked records, 22 with recorded author confirmation and 5 uncertain; PR #10 fixes Antoine Benoist collision and fail-closed rights thumbnails. Curator must check the art and source links before displaying it. Do not merge PR #10 and PR #11 blindly: both target PR #7 independently.
3. **Rights and provenance**: 119 preliminary open, 165 restricted, 49 unknown. Restricted/unknown = metadata + source link only, no thumbnails. Existing Site Paris Musees CC0 works to be reconciled by individual image license. No public download/upload of user photos; no unconsented geolocation.
4. **Computer vision / QA**: PR #8 contains independent reversible viewer and Playwright Chromium checks. Review PR #12: low coverage (<15%) does not auto-warp a whole modern photograph; preserve historic pixels immutable, photo original one tap away. Evaluate Site's existing seven pairs, select >=3 independently verified and geometrically defensible matches. Real Safari tests required.
5. **Museum UX / narrative**: PR #9 has three ideas. Adopt Archive paper A as main experience, map and routes from B, culinary story ideas from C in same design. Initial Paris tour: Madeleine, Parc Monceau, Saint-Sulpice with one verified old market/cafe story. Then Vilnius/Album de Wilna, Naples, Rome, other cities. Pin only geographically verified viewpoints.
6. **Release engineering / agent coordination**: PR #7, #8, #9, #10, #11, #12 must remain draft until independent clean-checkout tests, human research confirmation, migration and owner approval. GitHub Issue #1 tracks recovery; Issue #6 tracks product scope. Claude should maintain a single dependency/status board, not create competing rebuilds.

### Executable order

P0A: Verify and recover original site source. If owner export unavailable, record BLOCKED precisely, while maintaining independent research branches.
P0B: Rebase curated data into a clean review branch from PR #7 + PR #10 + PR #11, preserve evidence of attributions and resolve conflicts. Run complete pytest/ruff. Keep old Site IDs for dedup.
P0C: Review photo viewer PR #8 + PR #12; demonstrate unchanged old artwork and explicit low-coverage opt-in. Test on 375/390/820/1440 Chromium and real Safari before release.
P1: Develop a *single* complete Paris experience using source-approved scans and photo rights, 3 honest pairs and 1 historic gastronomy story, with city page, atlas, deep zoom, credits.
P2: Scale via Europeana, LoC, Rijksmuseum, Paris Musees API with account/token, BnF/Gallica (conditions), INHA for author identities, other institutional IIIF endpoints. No bypass of 403/429, no unverified license assumption.

### Release gates / definitions of done

- Site v7 art inventory, seven published pairs, manual 4-point tool, notes and export do not regress.
- At least 20 well-described artworks for first release, at least 10 images licensed for display, no auto-thumbnail for restricted/unknown rights.
- Three visually/archivally confirmed historical/current pairings; each holds a photo source, creator/date/license, control points, uncertainty/coverage and original toggle. Publishing a 7%-coverage transform as a whole-frame match is forbidden.
- At least one sourced food-market/cafe/menu historical story, NOT keyword false positives from Market Street, still life or slave-market works.
- iPhone/iPad/desktop responsive, keyboard, accessibility, browser Safari QA, source credits and reliable no-key fallback.
- No automatic merges or publication; explicit owner review of final release.

Related: Issue #1, Issue #6, PRs #7–#12. Full existing-Site summary in docs/migration/SITES_BASELINE_20261102.md.