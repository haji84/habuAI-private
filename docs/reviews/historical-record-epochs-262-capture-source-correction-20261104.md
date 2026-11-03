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
- The private exploratory conditional-clock model retains its 251 event sample. **No invented event times were added, posterior coefficients were not changed, and there is no new scientific fit.** This is a correction to the understanding/eligibility of existing data, not a model performance improvement claim.
- Existing 13-night/34-capture research effort-proxy model is a different cohort and must not be combined additively with the year total.
- Formal 100m × 10min labels newly qualified: **0**. GPS-missing, pause, unsearched, unknown coverage are never false negatives. Field-log capture coordinates before August 12 are not reconstructed GPX search tracks.
- No prospective P0/P1 or 100m±10min evaluation was performed. No Champion promotion, production activation, main merge, or public release is authorized.

Next work: reconcile identity-level 2026 April–August corrections, 2026 September's additional owner-confirmed capture, October 22–30 event times, then November nights in the private source register. Feed the existing formal selector only source-qualified observation units and ex-ante weather/geography features; keep future-night confirmation untouched.