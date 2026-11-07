---
name: source-integrity
description: Validate historical artwork metadata, original images, museum links, modern photo licenses, artist identities and provenance before publication.
---
- Identify by stable institution accession/IIIF manifest, artist role, title (original language), date as interval when appropriate.
- Split confidence: attribution, license, historical content, viewpoint, current-city geo, and binary capture checksum.
- Confirm actual reproduction license separately from artwork age. CMA CC0 can be used according to its object record; LoC no-known-restrictions is an advisory, not automatic CC0; Panoramax CC BY-SA requires attribution/license/share-alike for derivatives.
- Unknown/restricted images: link-only metadata, never mirror, watermark-remove, or automatically include a thumbnail.
- Deduplicate by work vs impression vs digitisation. 1019 research candidates are NOT approved public artworks.
- Validate realistic historic/modern pair with visible trust region and no historic-image warp; require original/photo source links beside the slider.
- Save a machine-readable provenance receipt and report HOLD for missing source.
