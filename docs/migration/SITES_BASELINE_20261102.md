# City on Paper: baseline existing Site v7, 02.11.2026

Source: user's Library record of the active ChatGPT Site (extracted published TEXT, not original HTML/JS/CSS or a backup of image binaries).

- Project ID: appgprj_6adcd6535e808191920e5f4586eb06ae; slug: city-on-paper-anatolii; status active; source version 7; projection revision 12.
- Existing live URL: https://city-on-paper-anatolii.tolyaz.chatgpt.site (cannot confirm accessibility via independent web fetch; owner access may differ).
- Site lists 38 Benoist-related catalogue entries; a visible filter count says 25 with images; a different homepage counter reports 30 images including comparison. These metrics have different grains and should not be summed.
- Published page names 7 ready comparisons: La Madeleine, Opera Garnier, Saint-Sulpice, Ecole Militaire, Pantheon, La Trinite, Parc Monceau.
- Site already offers user-photo matching with FOUR manually chosen correspondences and in-browser transformation, plus export/import of favorites/notes and JSON catalog export. Favorites are only stored in the local browser.
- Site also lists 22 Paris Musees/Carnavalet records with CC0-labelled images and includes non-Benoist artists and cities: Paris, Moscow, Naples, Rome, Amsterdam, Brussels, Bologna etc.

IMPORTANT distinctions:
- Seven PUBLISHED comparisons are not seven INDEPENDENTLY VERIFIED matches. PR #8 says zero independently confirmed matching pairs; real Madeleine candidate covers only 7% of the sheet.
- PR #7 contains 333 CANDIDATES and PR #11 has 27 HOLDER-CROSSCHECKED metadata records, not 360 additional unique artworks. Deduplicate these against Site v7.
- Main on GitHub contains only README/MIGRATION. The owner-held city-on-paper-2026-10-29.bundle is not in GitHub. This Library Site text is not the missing source code.

Required migration protocol:
1. Preserve the currently published Site unchanged. Recover the authorized Sites source/export and/or owner-held Git bundle, confirm checksum and inspect source history.
2. Export the existing Site JSON, capture screenshots at mobile/tablet/desktop, inventory artwork IDs, original scans, albums, 7 pair image sources/matrices, user-alignment tools, browser export functions, credits, favorites/notes.
3. Audit licenses for each of the 22 Paris Musees images. Paris Musees permits reuse for images whose individual rights/credits are CC0; others require authorization. Official terms https://apicollections.parismusees.paris.fr/cgu .
4. Import into separate restore branch and open draft PR with before/after diff and PASS/FAIL/NOT TESTED. Never overwrite main history, rewrite artwork or redeploy without owner decision.

URL access failure in an external tool does not establish deletion of the Site; Library status is active.