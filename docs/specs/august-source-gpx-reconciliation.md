# August 2026 field-log candidates joined to real GPX (Source-level review)

## Source-version scope reconciled on 2026-10-25

This document and its three scripts preserve PR #73's distinct **source version
1**: 111,323 bytes / 10,016 lines, SHA-256
`3c541bcbd994e1da397e083a9b094520926ebc9647879e4b001edbf9471c7eed`.
Its inventories and coverage statements below describe that slice, not all
currently available August evidence. They were compared with main
`09c16fbabf48f4a3fd3429b5681406a344e9abbe` for this documentation repair.

Current main separately preserves the 116,496-byte / 10,506-line
`8月ハブログ(1).txt` source, SHA-256
`130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c`,
with its [independent original-byte review](../reviews/august-native-exact-source-and-review-packets-pr82.md)
and [source proof](../../evidence/recovered_sources/2026-08-native-original-library-byte-proof.json).
The sources and aliases remain separately identified; do not add their
overlapping capture statements as new individuals or replace later source
coverage with this older slice. The owner-confirmed August total of 47 Habu
(46 capture statements, including one two-animal note) remains a separate
count fact, not 47 source-qualified training labels. This repair changes no
source bytes, existing diagnostic result, count or label admission.

## Correct inventory scope

`data/raw/gpx/` on main has **13 genuine GPX files: 12 from August (12/13/15/17/19/21/23/24/27/28/29/31) and 1 from September (09/02)**, totaling 243,747 measured track points as inventoried. September 28 is a *separate* 22,990-point byte-exact archive and is not included among the 13.

This project stores partial recovered TXT content:
- `evidence/master-goal-1642/recovered_sources/august-extracted.txt`
- `evidence/master-goal-1642/recovered_sources/overlap-candidate-review.json`

They came from previously saved Library read/extracted representations; their hashes do **not** certify original TXT bytes or contemporaneous observation receipt times. **The original native `8:2~8:29ハブ.txt` was also recovered for source version 1** (below), and its separate true raw SHA-256 is preserved; the older extracted 11 statements are aliases, not 11 further captures.

## Bounded actual-source linkage

`python scripts/reconcile_august_field_candidates.py --output artifacts/reconciliation/august-candidates.json`

Rejects changed reconstructed TXT content by its declared SHA; checks that all exact historical blocks occur in the preserved extracted text, enforces the native timestamp → 07:00 JST operational night, checks the real GPX content SHA for each of four relevant nights, streams trackpoints with spatial/temporal screening (max 100m and 10 minutes), and retains measured residuals. **This is a source-event linkage, not a formal hit against a prospective prediction.**

| Operational night | Explicit Habu capture statements | Source status |
|---|---:|---|
| Aug 12 | 4 | Source candidate only |
| Aug 13 | 2 | Source candidate only |
| Aug 15 | 3 | Source candidate only |
| Aug 17 | 2 | Source candidate only |
| **Total** | **11 event statements** | **0 verified owner-individual training positives** |

Each block explicitly says `捕獲` and `ハブ捕獲大/中/小`, but `大/中/小` is **size**, not a numeric individual count. Original quantity is null (only a lower bound 1 from the mention), and the owner identity is not explicitly resolved. All 11 corresponding workbook capture rows carry conflicting `target_role=反応`. No count is copied from the derivative workbook without verification.

Separate recovered reactions: **2 Habu roadkills** (Aug 13 20:58; Aug 16 00:39 counted within Aug 15 operational night), **2 Himehabu sightings**, none of which is the owner's own Habu capture. Search start/end markers exist for only some nights, and even present markers do not prove complete encounter recording or Negative exposure.

## All-source review queue

`python scripts/build_real_13_gpx_review_queue.py --output artifacts/reconciliation/real13-review-queue.json`

For every raw GPX, this combines its SHA-verified source night with the **newly recovered native August field log**:
- 11 of 13 GPX nights have native field-log timestamp blocks. 10 of those nights contain **30 explicit Habu capture event statements**, and the 11 earlier extracted statements are proven source aliases, not newly added captures.
- **Aug 21** has original field-log observations but zero explicit Habu capture statement within that source. This is NOT a complete zero-capture assessment. **Aug 31 and Sep 2** fall outside the recovered native file; those two GPX nights still need their primary logs.
- The derived workbook or daily dashboard count is not automatically an independent owner-individual event ledger. Exact per-event quantity and who captured must be checked, despite the raw log byte-level verification.
- `Negative=0` means **zero certified training-negative cells**, not observed absence. Unvisited and incomplete search coverage remain UNKNOWN.
- `Positive=0` means **zero confirmed owner-individual training labels** after all gates, not zero recorded Habu capture events.

All three reconciliation scripts and the review queue are read-only for canonical input and only write requested diagnostic output paths. Real GitHub Actions tests capture raw source-SHA and GPX-match errors and upload only diagnostic derived reports, not private 13-GPX copies. No `model_learning.json`, P0, Champion promotion or formal KPI is made.

## Remaining requirement before true walk-forward

Aug 31 and Sep 2 are outside this source version's coverage. Later main has
separate [Aug 31 review](../reviews/aug31-road-search-noncapture-pr80.md) and
[Aug 12 / Sep 2 source recovery](../reviews/aug12-sep02-field-log-gpx-recovery.md);
consult those evidence scopes rather than asserting that no later source was
recovered. Resolve quantity/ownership/duplicates and reaction categorization
per event, and align full GPX passage/exposure with **completely accounted
observer effort**. Strict Negative requires independently corroborated active
Habu search in the applicable time/road scope and source-bound complete owner
capture-outcome recording, not just driving. Historical weather forecast
availability and road/DEM ex-ante universe hashes must precede the modeled
cutoff. Retain at least 5 research nights and require **at least 5 untouched
future confirmation nights**, as the [normative Master contract](master-goal-1642.md)
specifies. Five confirmation nights is an engineering floor, not proof of
adequate coverage, independence or uncertainty. Freeze the selection before
reveal, preserve prior exposure, and use the full-outcome denominator and all
mandatory gates for 1km Top10 Recall≥90% and 100m±10min. Scientific validation
remains BLOCKED / NOT_VALIDATED until those requirements are actually met.

[Issue #64](https://github.com/haji84/habuAI-private/issues/64) tracks the next canonical learning snapshot and production P0 work.


## 2026-10-24 original native August source version 1 recovered and archived

**Original Library user file:** `8:2~8:29ハブ.txt` (source version 1), directly materialized as original bytes then transferred to private GitHub. Exact bytes: **111,323**; lines: **10,016**; SHA-256 **`3c541bcbd994e1da397e083a9b094520926ebc9647879e4b001edbf9471c7eed`**. Unlike the earlier `august-extracted.txt`, this hash is the original native file's byte identity. GitHub verification is enforced by `tests/test_reconcile_native_august_habu_gpx.py`. Original path: `data/raw/habu_logs/2026/2026-08-02_to_2026-08-30.owner-raw.txt`, source receipt `evidence/raw_intake/august-2026-native-habu-log-recovery.json`.

This recovered original contains observation entries from Aug 2 00:27 through Aug 30 02:53 JST; after-midnight observations fall under the preceding 07:00-JST operational night. Capture words `ハブ捕獲小2匹` at 2026-08-20 01:44 (Aug 19 operational night) establish **explicit event quantity 2**, and `大/中/小/極小` otherwise are size descriptors and never numeric count. The original log has exactly 30 Habu capture **event statements on nights represented by the 13 GPX files** (4 on Aug12, 2 on Aug13, 3 on Aug15, 2 on Aug17, 5 on Aug19, 3 on Aug23, 3 on Aug24, 3 on Aug27, 4 on Aug28, 1 on Aug29). Aug21 has 0 capture statements in this source; Aug31 and Sep2 lack source coverage. Neither missing statement nor missing source is a verified zero-capture result.

`python scripts/reconcile_native_august_habu_gpx.py --output artifacts/reconciliation/native-august-13-tracks.json`

The matcher validates each of the 13 actual GPX against the independently retained original-GPX SHA list, streams measured waypoints and checks reported captures (and separately Habu roadkill/sightings) against 100m/10min observational proximity. Matching only establishes spatiotemporal source alignment, **not** 100m±10min prediction accuracy or proven search detection effort. It links all 11 earlier extracted-statement aliases by native time+coordinates, instead of double-counting.

Training status remains **BLOCKED**: capture-event statements have still-unreviewed individual ownership/quantity and complete-outcome recording; a personal log file proves its recorded statements but not an exhaustive nightly detection ledger. Road passage from GPX is not verified Negative. Historical ex-ante forecast weather, terrain/road universe, and availability receipts still require independent validation.

**Source-version improvement recorded by this slice:** the original version 1
log was recovered and incorporated into its 13-GPX review queue; two GPX nights
remain outside **this version's** coverage. Later source versions and reviews
retain their own coverage and identities. All training evidence is still gated
separately.
