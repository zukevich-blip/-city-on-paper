# City on Paper — broad-source collection discovery (draft)

This PR adds **only a read-only, standard-library Python metadata discovery tool**. It does not restore the old site, modify production, fetch bulk image bytes, create verified then/now pairs, or merge into main.

## Why
The older site has 43 historical catalog records, with 30 local images, 13 source cards and 7 then/now pairs (inventory from prior work, **not rechecked**). GitHub main currently contains just README/MIGRATION. Work on expanding the European historic-view collection may proceed as **candidate research** while migration is blocked, but not as a claim that images are already visible in the app.

## Included sources and API handling
- **Wikimedia Commons:** imageinfo/extmetadata and file page. Import only declared PD/CC0/CC BY/CC BY-SA candidates, with all attribution needing human review. Do not ingest entire Philippe Benoist category unexamined: it includes works of the different artist Guillaume Philippe Benoist.
- **Metropolitan Museum:** use current **v1.1/search** (older /v1/search retired 01.10.2026), then /v1/objects; require isPublicDomain and primaryImage. 
- **Art Institute of Chicago:** query public-domain-only works, require image_id, use museum's IIIF image service at 843px.
- **Cleveland Museum of Art:** require share_license_status=CC0 and an image; retain credit and source.
- **Library of Congress, Gallica/BnF, Europeana, Rijksmuseum, Smithsonian, British Library, other IIIF collections:** secondary discovery and provenance sources. Do not treat all digital files as openly licensed. Europeana/Smithsonian may need own API credentials; BnF may apply reuse conditions and Gallica can be technically blocked. No bypasses.
- **Modern images:** Wikimedia Commons and Panoramax only after explicit creator/licence/date/coordinates/heading checks; historical works cannot be auto-paired to photos.

Official docs:
- https://metmuseum.github.io/
- https://api.artic.edu/docs/
- https://www.clevelandart.org/open-access-api
- https://www.mediawiki.org/wiki/API:Imageinfo
- https://www.loc.gov/apis/json-and-yaml/
- https://www.data.gouv.fr/dataservices/api-gallica-iiif
- https://pro.europeana.eu/page/get-api

## Commands (run locally only after reviewing)
Python 3.10+, no packages required:
```sh
python3 tools/discover_open_art.py --query "Félix Benoist" --query "Philippe Benoist" \
  --sources commons met artic cleveland --per-source 10 \
  --request-budget 70 --delay 1.5 --output candidates.json
```
Other prioritized searches: *Paris panorama, Paris lithograph, Venice lithograph, Napoli veduta, Rome veduta, Florence panorama, London engraving, Petersburg lithograph, Moscow veduta, Vilnius University, Prague city view, Lisbon old city, Constantinople view, Bretagne 1860, Nantes lithograph, Chateaubriant castle.*

## Data rules
1. All items start as **candidate_unverified**. Museum API responses and Commons metadata do not prove an exact match for a site or author, and licences need human review. No unapproved image is auto-published.
2. Preserve original author and co-authors/printmaker in a further curatorial enrichment step. Differentiate Félix Benoist, Philippe Benoist, Guillaume Philippe Benoist; never default unknown author to Benoist.
3. Distinguish source artwork, physical print, archive scan, and derivative web thumbnail. Prefer institution record with IIIF manifest or a verifiable original scan; store license and page URL.
4. Deduplicate by provider:item id first. Cross-institution near-duplicates need a separate reviewed identity resolver.
5. Before addition to the live collection: human source/license/attribution review, date/place, title translations, visual QA and copyright review for modern photos. Track precise viewpoint confidence separately.
6. Never erase, reprocess, edit or "restore" historical originals by AI. Geometric alignment is a labelled, reversible presentation layer only.
7. Respect API throttling and errors. No cloud workarounds for 403/429, paywalls, blocked archives, or rights restrictions.

## Validation / release gate
This code is **not yet live-tested against providers**, only prepared from official docs. Run offline unit tests, then a bounded smoke run from an authorized network and inspect 20 candidate entries for rights and author quality. Source migration gate remains GitHub Issue #1. No merge, production deploy, or rehosting until owner decision and actual source recovery.
