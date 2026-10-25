# 2026 August remaining GPX nights: preserved Library field-log and actual track audit

## Scope and provenance

After PR #75 (Aug 12 plus Sep 2), the **remaining August raw-GPX nights are 11, not 10**:
2026-08-13, 15, 17, 19, 21, 23, 24, 27, 28, 29, 31.
Earlier status "13 August GPX nights" was inaccurate: there are **12 August GPX nights and one September 2 GPX night** in the 13-track set.

The user-provided Library text `8月ハブログ(1).txt` (library ID `libfile_76fd960f5a1481918b03b1b4c9bd9f88`) was read in 11 contiguous windows, lines 1–10506 without gaps or overlaps, and saved at `evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt`. This is **Library extracted/visible text**, NOT byte-verified native TXT. The GitHub file SHA and per-block text hashes are audit pointers to this recovered text, not independent authentication of the earlier original file.

## Runtime: true GPS corroboration

`python scripts/recover_remaining_august_nights.py --output artifacts/august-recovery/event-audit.json`

The script splits the *native dated event blocks* and assigns exploration nights using the **07:00 JST** rollover (Sep 1 before 07:00 belongs to Aug 31). It preserves each block's source line, full text, sha256, literal animal names/quantity tokens, coordinates and native reported time. It separately categorizes capture statements, sightings, roadkill, context and session markers. Ambiguous capture animal and multi-animal sightings are not converted into Habu captures.

Each target night binds the exact `data/raw/gpx/YYYY-MM-DD__legacy.gpx` bytes to the independent `evidence/legacy/habuAI-public/v2_actual_gpx_13night_qc.csv` hash and expected point count. Exact GPS proximity is checked against raw capture and sighting events with 100m/±10min source tolerance, GPS anomaly filtering and HDOP guard. **This is observation/source GPS corroboration, NOT actual pre-departure prediction accuracy.**

All source blocks are event **candidates** only. A mention of `ハブ捕獲小/中/大` describes size, not a validated number of snakes. The archived dashboard monthly tally is never silently rewritten; if count differs or a day is missing, the audit flags this and preserves both values. Missing explicit exploration start/end and species/coordinate mismatches are recorded.

## Science gate

- All reconstructed events are historical. No retroactive P0 is created.
- GPX passage without verified effort and complete owner outcome evidence stays UNKNOWN, not Negative.
- These recovered event blocks alone cannot yield individually identified owner Habu Positive labels. Positive and Negative formal training rows both remain **0** until independent individual capture/ownership, event duplication and complete search/outcome certification.
- To build `data/processed/model_learning.json`, the project still requires authentic source availability timestamps for the forecast-era road/terrain/weather features, audited forecast universe, valid exposure/evaluation protocol and untouched walk-forward confirmation folds.
- Keep all original Library source texts and original GPX unchanged; audit evidence is separate. The full per-event review JSON is retained as a private CI artifact (30-day retention) and can be regenerated from these immutable GitHub references. Private capture coordinates should never be published to public dashboards.

Related: Issue #64, PR #70 / #71 (Sep 28 5 events to six individuals), PR #74 (GPX coverage matrix), PR #75 (Aug12 and Sep2 restoration).
