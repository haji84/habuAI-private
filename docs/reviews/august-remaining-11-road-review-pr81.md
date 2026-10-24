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
