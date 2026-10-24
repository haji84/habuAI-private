# PR #81: 11 remaining August GPX nights road-search diagnostic

## Sourced inputs
After the Aug31 PR #80 real-data E2E, the remaining nights are Aug12, Aug13, Aug15, Aug17, Aug19, Aug21, Aug23, Aug24, Aug27, Aug28 and Aug29.
The 11 original archived GPX sources contain 213,809 measurement points, 208,239 retained GPS QC samples and 8,277 observed 100m x 10min bins under the frozen PR #77 source receipt.
The original 10506-line recovered Library text is an extracted-read representation, NOT authenticated native TXT bytes. OSM road centerlines are the September 25 SHA-verified auxiliary archive, NOT an ex-ante August prediction road universe.

## Method
The implementation reuses PR #80 RoadMatcher, archive hashes and movement review heuristics. It tests original GPX hashes, QC point counts, 07:00 JST dates, event source timestamps and all capture-statement GPS proximities before any review candidate is produced.
Aug12, Aug13 and Aug29 lack a paired start/end session. All points on those nights remain UNCERTAIN for search activity and no no-capture review candidate is generated from them.
Slow vehicle motion and OSM road colocation do not independently certify active searching. A no-capture statement means no captured individual is recorded in a nearby source block; it never proves a Habu was absent.
Aug19's five capture statements indicate a candidate quantity of six because of one explicit two-snake note. Aug21 has zero capture mentions but no proven complete zero-capture outcome ledger.

## Evidence storage and safety
The source check produces per-night summary JSON and a private Actions artifact with cell-level diagnostics. Only a compact aggregate may be preserved in the repository. Do not publish original capture coordinates, routes, source texts or individual GPS cells.
All review rows keep observation UNKNOWN and a null training label. Certified active search road segments and formally eligible Positive/Negative labels remain zero until independent search/transport and outcome-completeness evidence has been reviewed.
August 2026 owner-confirmed 47 and through-October20 total 243 remain unchanged; no original P0 or model_learning file is generated.

## CI acceptance
11 actual GPX SHA/point-count checks, 28 of 28 captured-source proximity matches, 8,277 observed bins, no fabricated session on three incomplete nights, no Positive/Negative training rows, and private artifact output.
Use the successful actual GitHub Actions run as the authoritative numerical record for road-match and noncapture-review candidate counts rather than inventing totals.

## Verified real-data CI result (2026-10-24)

- Actual GitHub Actions audit run: https://github.com/haji84/habuAI-private/actions/runs/40058026378 . The source algorithm ran and CI assertions passed.
- 11 GPX nights: 213,809 raw points; 208,239 retained QC samples; 189,710 OSM-nearby GPS points; 8,277 100m x 10min sampled bins.
- After excluding Habu roadkill/sighting/capture context, **3,065 review-only noncapture candidates** across eight nights with paired session boundaries. Three nights without paired start/end have zero such candidates.
- All 30 native-text capture statements match actual archived GPX in time/place under the existing source-proximity tolerance. This means statements are GPX corroborated, NOT 30 independently identified snakes.
- 8/21 has 229 review candidates despite zero Habu capture statements, but no source-certified complete outcome ledger; these are not evidence of Habu absence.
- Together with Aug31 PR #80 (426 review candidates), the complete 12-night historic sampled corpus has 3,491 review-only noncapture candidates. This is **not** 3,491 validated Negative labels.
- Verified permanent compact receipt with no private cells: evidence/recovered_sources/2026-08-remaining-11-road-search-review-ci-receipt.json .
- Zero formal training positives, zero formal training negatives, zero officially certified actual searched roads. For scientific training and formal 100m±10min scoring, all review candidates remain UNKNOWN.
