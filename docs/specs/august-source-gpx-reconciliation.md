# August 2026 field-log candidates joined to real GPX (Source-level review)

## Correct inventory scope

`data/raw/gpx/` on main has **13 genuine GPX files: 12 from August (12/13/15/17/19/21/23/24/27/28/29/31) and 1 from September (09/02)**, totaling 243,747 measured track points as inventoried. September 28 is a *separate* 22,990-point byte-exact archive and is not included among the 13.

This project stores partial recovered TXT content:
- `evidence/master-goal-1642/recovered_sources/august-extracted.txt`
- `evidence/master-goal-1642/recovered_sources/overlap-candidate-review.json`

They came from previously saved Library read/extracted representations; their hashes do **not** certify original TXT bytes or contemporaneous observation receipt times. Original native `8:2~8:29ハブ.txt` behind some workbook rows has not yet been recovered or byte-verified.

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

For every raw GPX, this combines timestamp-derived night + SHA with any recovered review candidates and adds independent gaps:
- 4 August nights have matched *candidate events*, still ineligible for training.
- The remaining **9 GPX files** (8 later August + 1 September) have **no fully reconciled primary Habu event/individual/reaction source in the current repository**. A derivative workbook or daily dashboard count is not an independent owner-event ledger. This is a *recovery gap*, not evidence no snake appeared or was captured.
- `Negative=0` means **zero certified training-negative cells**, not observed absence. Unvisited and incomplete search coverage remain UNKNOWN.
- `Positive=0` means **zero confirmed owner-individual training labels** after all gates, not zero Habu capture events. 11 reported candidate events are retained for source review.

Both scripts are read-only for canonical input and only write requested diagnostic output paths. Real GitHub Actions tests capture raw source-SHA and GPX-match errors and upload only diagnostic derived reports, not private 13-GPX copies. No `model_learning.json`, P0, Champion promotion or formal KPI is made.

## Remaining requirement before true walk-forward

Recover byte-verified source logs, reconcile quantity/ownership/duplicate and reaction categorization per event, and align full GPX passage/exposure with **completely accounted observer effort**. Strict Negative requires a verified searched interval with complete outcome and detection quality, not just driving. Historical weather forecast availability and road/DEM ex-ante universe hashes must precede the modeled cutoff. Then build at least 5 research and 2 untouched future confirmation nights with full-outcome denominator, evaluate 1km Top10 Recall≥90% before 100m±10min Stage Gate; any uncertainty remains explicitly BLOCKED.

[Issue #64](https://github.com/haji84/habuAI-private/issues/64) tracks the next canonical learning snapshot and production P0 work.
