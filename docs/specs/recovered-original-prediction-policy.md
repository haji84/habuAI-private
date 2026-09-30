# Recovered Original Prediction Policy

Historical predictions that were genuinely issued before an exploration but were not frozen in GitHub/SHA before label reveal may be preserved under:

`predictions/recovered_original/<operational_night>/P<n>/prediction.json`

Rules:
- the content must be recoverable from a dated prior source;
- the recovered record must state its source timestamp and provenance;
- `freeze_status` must state retrospective recovery;
- `strict_official_score_eligible` must be false;
- absent 100m ±10-minute targets must remain absent and must not be reconstructed from later knowledge;
- the recovered payload receives a SHA-256 only to make the recovered record immutable from recovery onward;
- recovered results may support historical diagnostics and count/area comparisons, but may not be mixed into the strict ORIGINAL leaderboard.

If a strict ORIGINAL Freeze exists, it always takes precedence over any recovered copy.
