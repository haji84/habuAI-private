# Independent review — recovered September sources and 07:00 display candidate

Date: 2026-10-21 UTC. Reviewed local candidate: `data-audit-repair/`, intended for existing Draft PR #43; receipt baseline head `415837c3713a167794149770f1228190fa158fe6`.

**Verdict: PASS for staging the received originals plus the explicitly limited derived display candidate. The final builder safety fix passes independent checks; no additional blocking defect was established in the final eight candidate files. This does not approve canonical data promotion, historical relabeling, main merge, or a model/Champion change.** Exact pushed-head CI remains a separate gate.

## Important source defect and its bounded repair

Independently reproduced that the quantity-corrected workbook `ead12d…7054` reintroduces **101 incorrect operational-night values** in its 314-row historical capture display. The companion ZIP's historical display CSV has the same 101 errors. This source must remain an incoming original, rather than being designated the latest authoritative view. The final receipt marks `BLOCKED_SOURCE_WORKBOOK_REINTRODUCES_101_07H_DISPLAY_ERRORS`, keeps `canonical_promotion=false`, and links the separate derivative receipt. The report describes the defect explicitly.

Independent scope check:

| Projection in received workbook | Rows | Wrong 07:00 nights among strictly parseable times | Times not strictly parseable |
| --- | ---: | ---: | ---: |
| Historical capture display | 314 | 101 | 23 |
| Selected new events | 1,117 | 0 | 0 |
| Selected owner capture events | 67 | 0 | 0 |
| Selected owner capture individuals | 68 | 0 | 0 |
| All-period event projection | 3,853 | 0 | 19 |

Thus 3,834 parseable all-period rows passed; no exact-night validation is claimed for the other 19. The earlier statement of 24 unparseable historical display times is not reproduced by this strict parser; the final report correctly says 23.

The derivative `data/processed/reconciliation_candidates/2026-10-21/historical_capture_display_september51_07h.csv` has SHA-256 **`979ba7f96259c9202d084e302d08cd8f72f04017b80d4d23cc465242ca26ad07`**. Independent row-by-row comparison against the original packed CSV confirms:

- all 314 source IDs, row order and 16 fields are retained;
- only `night` changes in exactly 101 rows, each equal to `(original local date/time − 7 hours).date()`;
- 91 changed rows retain `BASE_LABELED_CAPTURE_NEEDS_SOURCE_VALIDATION`, and 10 retain `NON_CAPTURE`;
- all 23 strictly unparseable rows remain identical, including their unresolved date/time text and night;
- quantities, classification, coordinates at full CSV precision, notes and every other field value stay unchanged;
- the derived receipt's exact ID/old-night/new-night list and classification totals agree with the independent comparison.

Ran `scripts/build_september51_07h_view.py` against copies of the receipt and two binaries in a disposable root. It reproduced the exact derivative SHA-256 above. All copied original/receipt bytes remained unchanged. Final script reviewed SHA-256: `9e9530b38b616706b6ec260bfedcf20ad9cee5b3930c15199de0560c6dd8022f`.

The final builder opens path components through directory descriptors with `O_NOFOLLOW`, reads receipt/source regular-file snapshots, restricts source references to relative `incoming/` paths and rechecks source/receipt bytes before publication. Output creation uses `O_EXCL`; identical existing bytes are reused without rewriting, while different existing content is rejected. Independently exercised **19 disposable safety cases**: unchanged inode/mtime for identical output, different-output preservation, target/four output-ancestor symlinks, receipt/incoming/source symlinks, absolute/traversal/non-incoming references, root alias and FIFO source/existing-output rejection. A FIFO blocking defect was reproduced during rereview and is resolved by `O_NONBLOCK` plus the regular-file check. No received original was changed.

## Original bytes and event grain

| Received original | Bytes | SHA-256 | Git blob SHA-1 |
| --- | ---: | --- | --- |
| Corrected workbook | 820,713 | `ead12df59799d607a93814d91e5ed719bbc955cda3a8cf2410f22d42214d7054` | `d42c5ad30919114a7b8de7d3cb3d7be70ea0c3b7` |
| Validation ZIP | 1,220,188 | `ee803478c0a1ec574591fc219fa585afad101539b5ddfaebae966e41c5b60aee` | `a926ee5b290ab890fb077b7e2c625d83f3490367` |

Both received files passed independent size/SHA-256/Git-blob checks and their ZIP CRC checks. The validation pack embeds byte-identical workbook content. No unsafe member path was found in either ZIP container. No bundled Python script was executed. The workbook was read through XML without edits or re-export.

Confirmed 1,117 unique selected event IDs and dedup keys, 3,853 unique all-period event IDs, and inclusion of selected IDs in the all-period projection. Confirmed **67 owner capture encounters and 68 individuals**: September 50/51, October selected seven nights 17/17. Every individual links to exactly one of the 67 encounters, per-event individual indexes are contiguous and the repeated `event_count` agrees with that encounter's multiplicity. Counts are not calculated by summing that repeated field. The 2026-09-29 00:00 encounter has two individuals and belongs to operational night 2026-09-28.

Verified all relevant workbook projection keys/time/night/class/count/coordinate fields against the packed CSVs for 67 capture rows, 68 individual rows, 1,117 selected events and 3,853 all-period events. The selected source keeps owner capture 67, sighting 4, roadkill 4 and another person's capture 1 in separate event classes. Unresolved historical capture/sighting labels are not certified by this repair. The existing-overlap section correctly requires identity linking before later ingestion; this staged candidate does not append its selected observations to canonical capture tables.

Compared corrected and preceding source projections independently: only two selected event rows change, both remain `CAPTURE_HABU`. The September 6 01:59 mixed-species note correction changes raw/maximum quantity and derived identity while retaining a minimum of one; the September 29 midnight correction changes multiplicity to two. Across all 67 GPX-report rows, only those two derived IDs change; geometry, timestamps and metrics remain identical. This supports preserving canonical IDs and linking the corrected source evidence rather than appending new captures.

## GPX and test evidence

Independently recomputed the corrected pack's 67 encounter-to-GPX checks from actual trackpoints in **20 original GPX hashes**, rehashing each original against the pack's SHA-256. Encounter IDs, timestamps and coordinates agree with the corrected capture table. All 67 have an actual point within 100 m and absolute time difference ≤600 s; the largest distance was 5.040633 m and largest absolute time difference 237.001 s. Recomputed nearest distances agree with the archived report within 0.005 m. The two-individual encounter remains one encounter check.

These are post-observation track consistency results. They establish no prediction hit rate, forecast recall, calibration or Champion eligibility. The final candidate report preserves that distinction.

Fresh command: `env PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_habu_september_corrected_sources.py' -v` in `data-audit-repair/`: **15/15 tests pass** (four data tests and eleven write-protection tests). The suite uses the standard library only. Independent comparison and the disposable rebuild add checks beyond that suite.

## Evidence and review limits

The final eight candidate files and their byte hashes are recorded in `data-audit-evidence/independent-final-candidate-manifest.json`. The reviewed binaries stayed unchanged throughout this read-only review. No existing raw/ORIGINAL or canonical model/prediction file was modified; only separate review evidence was created. This review did not write GitHub or update a branch.

Reproducible evidence:

- `data-audit-evidence/independent_intake_review.py`
- `data-audit-evidence/independent-intake-review-evidence.json`
- `data-audit-evidence/independent_07h_review.py`
- `data-audit-evidence/independent-07h-view-check.json`
- `data-audit-evidence/independent-overlay-review-evidence.json`
- `data-audit-evidence/independent-overlay-rebuild-evidence.json`
- `data-audit-evidence/independent-corrected-identity-difference.json`
- `data-audit-evidence/independent_builder_safety_review.py`
- `data-audit-evidence/independent-builder-safety-evidence.json`
- `data-audit-evidence/independent-final-candidate-manifest.json`

Remaining controls are the exact pushed-head diff/CI, canonical identity reconciliation, qualified historical evidence and explicit future promotion. The receipt's current retrieval timestamp does not prove historical forecast-time availability.
