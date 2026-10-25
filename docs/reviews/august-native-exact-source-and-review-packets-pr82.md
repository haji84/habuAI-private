# PR #82: August native-original bytes and evidence packets for 3491 observation candidates

## Native TXT source byte proof: a resolved blocker
The user-uploaded Library raw file `8月ハブログ(1).txt` was directly materialized and its original 116,496 bytes SHA-256 hashed independently on 2026-10-24. Native SHA-256: `130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c`. Source has 10,506 UTF-8 lines. Both size and native SHA exactly match the earlier copied GitHub text `evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt` (same SHA). Therefore this earlier GitHub source copy is byte-identical to the user-uploaded original, not merely a lossy transcript. This proves byte identity *to the Library upload*, not authenticity of a field device's unsigned recording.

Reproducible native proof receipt: `evidence/recovered_sources/2026-08-native-original-library-byte-proof.json`. No fresh copy of the 116 KB source is needed in GitHub and no raw material is overwritten.

## August month-level capture reconciliation
Using `recover_remaining_august_nights.index_events` and 07:00 JST night assignment over ALL 10,506 source lines, the native text contains **46 explicit Habu capture statements** across **17 operational nights**. Exactly one statement (the Aug19 night, native clock Aug20 01:44) explicitly says two Habu. Under a source-statement quantity audit, the total is **47**, matching both user-confirmed August aggregate and each of the 17 day-level entries. The Aug31 night has two capture statements; their original source block hashes are distinct and source locations are approximately 8.4 km apart. No artificial event/individual IDs are assigned, and the record separation does not constitute physical identity proof.

Receipt, source-line selectors and count evidence are produced by `scripts/audit_august_native_capture_original.py` and unit tested. All original logs, models, freeze records and existing PR77/PR80/PR81 evidence remain unchanged.

## Reviewed, but NOT certified search effort
PR80 and PR81 established 231,715 GPS points and 8,965 100m x 10min sampled cells. OSM proximity and low-speed heuristics identified 3,491 review-only noncapture candidates across the 12 real-GPX nights. The source-native match means the 47-capture log is trustworthy as the uploaded text. It does NOT prove the uploader recorded every encountered Habu, that a low-speed car was actually scanning for Habu, that another passenger did not capture an animal, or that a specific road segment was consistently searched.

`scripts/build_august_source_evidence_packets.py` reuses, never duplicates, the existing code from PR80/PR81 to group the **same 3,491 candidates** into deterministic review packets by *same 10-minute window, same OSM auxiliary way and spatially adjacent sampled cells*. This is a review organization, NOT a GPS-interpolated route or proof of a continuously driven road. It never changes UNKNOWN to Negative.

All private UTM grid cells / road IDs / time windows / candidate IDs are only stored inside the private 7-day CI artifact `review_packets_private.json` and `review_cells_private.csv`. A compact coordinate-free `summary.json` includes aggregates, top review group IDs and the precise unresolved evidence needed. Do not publicize the full trajectory or unredacted field log.

## Scientific qualification gates not yet supported by this historical data
1. Independently verified per-road **active search vs transit** intervals, with a source hash, time span and spatial scope, not just general exploration start/end or slow vehicle movement.
2. Scope-bounded **complete capture outcome** accounting (owner captured / Habu sighted / other-person captured / roadkill must remain distinct); missing capture events must not be treated as verified zero.
3. Per-individual canonical IDs or traceable individual capture evidence, with conflicts and duplicates resolved. Monthly owner confirmation alone cannot generate individual labels.
4. Ex-ante road/feature/universe availability and cutoff integrity for formal historical prediction scoring. September 25 OSM auxiliary centerlines cannot become a pre-Aug31 frozen universe.

Until independent proof for a particular unit is present, certified search segments=0 and both official Positive and Negative training rows=0. Treat zero as `NOT_CERTIFIED`, not evidence of no Habu. No historical P0 is fabricated.

## Execute / acceptance
`python scripts/audit_august_native_capture_original.py --output artifacts/august-exposure/native-source`
`python scripts/build_august_source_evidence_packets.py --output artifacts/august-exposure/review-packets`
`python -m unittest discover -s tests -p test_august_native_evidence_packets.py -v`

Full GitHub Actions validates all source digests, 46 statements/47 quantity, 17 matching days, 3,491 review candidates, no learner labels, and saves the detailed private artifact. The user is not required to upload the same August log again.

## Verified CI result and remaining individual review
- Verified native-byte audit and grouping run: https://github.com/haji84/habuAI-private/actions/runs/40059538823
- All 46 source capture-event statements total 47 from native user Library TXT. One unresolved August 19 pair of capture statements occurs 5 minutes and approximately 90m apart. Treat as **individual identification review priority**, not a proven duplicate and not a reason to silently reduce the owner-confirmed 47.
- The 3,491 already observed GPS/OSM review candidates were grouped into **774 review packets**. Grouping reduces independent review units, not total sampled evidence, and never certifies actual travelled/actively searched routes.
- Coordinate-free permanent summary receipt: `evidence/recovered_sources/2026-08-native-source-and-review-packets-ci-receipt.json`.
- User log exact original bytes are verified, while road-by-road active search, per-domain complete capture ledger and physically distinct individual IDs remain unresolved.
