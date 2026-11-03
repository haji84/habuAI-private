# Source epochs and 2026 capture-total reconciliation (2026-11-04)

Status: **PUBLIC-SAFE AGGREGATE RECEIPT / PRIVATE HANDOFF STORED / FORMAL SPACETIME FIT NOT DONE**.
Scope: reuse existing Draft PR #136. This note contains no GPS coordinates, route segments, exact capture-event timestamps, village names, private individual records or raw data.

## Corrected total versus model sample
- The owner's verified **2026 capture tally through October 30 is 262 Habu** from **101 operating nights**. Monthly aggregate April–October: **10, 23, 60, 35, 47, 51, 36**; sum = **262**.
- Separate personally reported capture nights November 1 and November 3 have **two each**, so the arithmetic would give **266 through November 3** if the two new nights are unique and were not included in the October frozen tally. **266 is provisional**, pending canonical individual-event reconciliation; it is not a frozen canonical DB total.
- The previous **251** is not the year's capture total. It is the count of events with exactly parseable clock times used by the private exploratory six-bin conditional capture-event-time model: **16 from 2025**, **168 from 2026 April–August**, **67 from 2026 September–October 20**.
- Of those 251, only **235 are from 2026**. Their difference from 262 is **27 sample/coverage units**: four in the owner-corrected April–August count relative to the original baseline, three time-unknown April–August records, one revised September count, and nineteen later October 22–30 captures. These represent **different input versions and selection scopes**, not permission to manufacture 27 individual events or timestamps.
- Earlier owner source `dashboard/owner_effort_2026-10-26.json` is a historical **249**-capture checkpoint through October 24. Its frozen values must not be overwritten with 262.

## Actual recording practice and source epochs
- **September–November 2025**: owner describes keeping capture times and approximate settlement names. The inspected original historical workbook has no event latitude/longitude pairs for that period. Its nine `capture_or_sighting` legacy records remain unresolved until item-level corroboration; coarse settlements cannot make 100m point labels or GPS routes.
- **April–May 2026 transition**: a separate capture-log period. Original workbook shows no coordinate pairs in April, with some per-capture longitude/latitude pairs in May.
- **May–August 11, 2026**: owner reports GPS coordinates were saved **inside capture logs**. Some original workbook event rows confirm paired coordinates. GPS event coordinates are **not the same as continuous route GPX**; these points may be candidate positive observations after source/individual audit.
- **August 12, 2026 onward**: earliest retained GPX in the inspected `data/raw/gpx` directory is dated August 12. Earlier absence of GPX does not imply the owner did not explore, and does not provide negative labels or search exposure; do not interpolate routes.
- Days/nights use a **07:00 JST operational-night boundary**. Owner corrections and month-boundary rollover must be reconciled by event identity before canonical counts or training rows are replaced.

## Action and model gates
- Completed a private source-provenance, record-era and owner-total audit with SHA-bound original April–August workbook; stored versioned JSON, new handoff, and seven focused source-coverage tests in private Library `/ハブAI/{Evidence,PDCA}/2026/11`.
- Initial source-provenance correction left the 251-event conditional-clock model unchanged. A **separate subsequent research-only v1.1 fit** admitted 19 source-verified late-October captured-event times, producing a **270-event** sample. It does not change the original immutable 251-event version, does not establish a qualified scientific fit and is not a model performance improvement claim.
- Existing 13-night/34-capture research effort-proxy model is a different cohort and must not be combined additively with the year total.
- Formal 100m × 10min labels newly qualified: **0**. GPS-missing, pause, unsearched, unknown coverage are never false negatives. Field-log capture coordinates before August 12 are not reconstructed GPX search tracks.
- No prospective P0/P1 or 100m±10min evaluation was performed. No Champion promotion, production activation, main merge, or public release is authorized.

Next work: reconcile identity-level 2026 April–August corrections, 2026 September's additional owner-confirmed capture, October 22–30 event times, then November nights in the private source register. Feed the existing formal selector only source-qualified observation units and ex-ante weather/geography features; keep future-night confirmation untouched.
## Subsequent source-verified October event-clock refit (research-only)

- Existing October original Habu log SHA-256 independently matches the previously audited October raw source. Derived CSV contains 36 owner capture events across October; all 17 earlier October events agree exactly on operational night and capture time with the frozen October 20 merged view. The remaining **19 events dated October 22–30** each have a distinct ID, exact clock time and matching raw source lines. The earlier 17 were **not added twice**.
- Private research-only fit now uses **270 exact-time capture-event units**: **16 from 2025 and 254 from 2026**. Original 251-event model is retained immutably. The 2026 private model sample is still **8 fewer units** than the October 30 owner tally of 262 because four baseline-vs-owner month corrections, three time-unknown records and one revised September capture are not silently given new event times.
- For transparency, prior 251-event conditional clock model had **mean negative log probability 2.353** on the 19 later October capture clock bins. A uniform six-bin reference had **1.792**, so the older model was **worse than uniform** on this retrospective time-separated diagnostic. This is not a preserved past prediction; the newly refitted 270-event model must not be evaluated on its own included 19 training examples as if it were an independent future trial.
- Local private refit: **12 focused regression tests PASS** (raw tamper, parent model tamper, duplicate event, 07:00 boundary, prior 17-event overlap, invented timestamp and privacy guards). Source, script, model and detailed audit remain exclusively in private Library.
- Model remains **EXPLORATORY / NOT FORECAST VALIDATED**. No official 100m × 10min candidate fit, new Negative, P0/P1 freeze, Champion promotion, main merge or deployment occurred. No raw capture coordinates, individual event clocks/IDs or GPS routes are part of this public receipt.
