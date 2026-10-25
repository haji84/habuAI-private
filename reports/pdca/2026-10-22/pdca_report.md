# Habu AI PDCA | 2026-10-22 operational night

**Status: PARTIAL / official ORIGINAL P0 scoring BLOCKED / ACT = NEED_MORE_DATA**

This is a post-hoc **manual evidence audit**, not a successful run of the canonical automated PDCA pipeline. It does not Freeze P0 retroactively, authorize Champion promotion, or establish official 100m±10min accuracy.

## PLAN (prior provisional estimate only)

- Prior conversation summary at approximately **2026-10-22 17:45 JST**: if searching ~5h, provisional point estimate **2 personal captures** (range **0–3**); not an issued / immutable P0 (`PROVISIONAL_NOT_FREEZABLE`).
- Informal key time candidate: **20:00–22:30**. Short 2–3h scenario estimated **1 capture**. Later advice also considered postponement due to weather risk. This was not a formally validated model score.
- Suggested options: A=手安〜久根津〜阿鉄, B=清水〜嘉鉄〜伊須, C=節子〜嘉徳; A initially preferred, later modified. These were **narrative suggestions, not scored spatial predictions**.
- `predictions/original/2026-10-22/P0/prediction.json` was **not found on main** when audited 2026-10-23. No valid Freeze SHA-256, P0 spatial targets, cutoff bundle or P1+ proof was established. Count agreement cannot be official P0 success.

## DO: Observed facts from user log and uploaded GPX

- Operational night: **2026-10-22 20:16 – 2026-10-23 01:15 JST** (day boundary 07:00 JST).
- GPX coverage: **20:16:52.610 – 01:15:33.999** (~298.69 min); **17,731 points**, **1 segment**.
- GPS path length: **~91.30 km raw**; **~90.20 km approximate after removing obvious location jumps and sparse transitions**. Neither is a road-matched odometer truth. Several raw coordinate jumps imply impossible instantaneous speed.
- User-reported rainfall event **20:26 JST**; rain amounts, true start/end, hourly humidity, lunar and tide measurements not present in the supplied session evidence.
- **Personal captures = 2**, both juvenile **≤90 cm**, both marked **Wet**:
  - **00:02**: 県道612号 / road centre / moving; contemporaneous GPX ~**9.8 m** from logged point.
  - **00:48**: fence / moving, near 久根津; contemporaneous GPX ~**1.3 m** from logged point.
- **Roadkill Habu = 1**, **01:02**, 県道79号, Wet; GPX at time ~**10.5 m** from logged point. **Never counted among personal captures.**
- All three observations match the GPX within a minute of their logged times and within ~11m horizontally. **This validates observation-track coincidence, not the prediction KPI or GPS instrument accuracy**.
- Prior to **00:02**, **0 captured during approximately 3h45m of logged GPX exploration**. At least two genuine late-night positives occurred.
- Exposure exploration only (NOT formal dataset): UTM52N 100m grid x 10-minute JST buckets from GPS samples produced **1,123 distinct location-time units** and **914 distinct 100m spatial cells**; **1,046 units** had at least one point with HDOP≤10. This is a raw GPS-grid diagnostic, not road-segment-confirmed Negative labels. GPS quality, actual searching and repeat passage need further QA.

## CHECK: scoring separation

| Evaluation | Result | Notes |
|---|---|---|
| Provisional 5-hour count | 2 predicted vs 2 observed, absolute error **0** | **Diagnostic only**; no frozen P0 |
| Provisional 2–3 hour count | 1 estimated; 0 captures during first ~3 hours | **Mismatch**, contingent on comparable effort |
| Time priority 20:00–22:30 | 0 personal captures during that focus | No formal time-target probability, sample size one |
| Capture position/time vs GPX | 2 of 2 observations align; roadkill 1 of 1 | Observation integrity, **not forecasting accuracy** |
| Official P0 integrity and scoring | **BLOCKED** | Missing ORIGINAL P0/cutoff/freeze evidence |
| P1+ adaptive scoring | **BLOCKED** | No independently verified P1+ |
| Stage1 1km Top10 Recall | **NOT_PRODUCED** | No frozen region ranking / corresponding formal target universe |
| Final 100m±10min hit rate | **NOT_PRODUCED** | No frozen time-space candidate predictions |
| Formal road-matched Negative / Exposure | **PARTIAL/BLOCKED** | Raw GPS bins ≠ road-universe visit proof; unvisited cells are Unknown |
| Causal rain / Wet / lunar / tide conclusions | **NOT_VALIDATED** | Need comparable search exposure, independent weather, multi-night tests |
| Walk-forward / ablation / Champion promotion | **BLOCKED** | No scorable original targets or independent model candidate |

### Main diagnostic findings

1. **The count estimate happened to match**, but the peak-time narrative did not: the two captures occurred **00:02/00:48**, not in the 20:00–22:30 focus. A model may get count right while getting route/time wrong.
2. **User searched C-type areas first**, then travelled beyond the initial shortlist and made captures later on the return/southern-route portion. Do not claim A/B predictions succeeded or failed without actual route exposure matching. Whether the alternate A route would have been better is unknown.
3. **All three Habu reactions were Wet**, after an observed rain note, but they do not establish a rainfall causal effect. GPX shows travelled roads; denominator by Wet/Dry/road type/time remains incomplete.
4. **Juvenile movement**: both captured Habu are juveniles, with distinct substrates (road centre and fence). Size and microhabitat are worth separate analysis as descriptive categorical features, not single-night predictive weights.

## ACT: decision NEED_MORE_DATA, no model promotion

- **P0 contract / storage**: enforce capture-before-exploration P0 issuance with model + universe + scores + spatial grid + cutoff + SHA, or mark strict scoring BLOCKED. Never backdate the 17:45 chat prediction.
- **Ingestion**: archive byte-exact log/GPX and event IDs in private raw storage and match source checksum, while keeping a distinction between uploaded GPX and GitHub canonical archive. The SHA-256 of the uploaded GPX is included in `evidence_summary.json`; GPX bytes themselves were **not** committed with this report.
- **Exposure**: map-match the track to road zones, bound GPS jumps/HDOP/speed/stops and time-local passage before marking observed no-capture passes; never label unvisited areas Negative.
- **Diagnostics, not immediate retraining**: test the 20:00–22:30 heuristic vs later intervals using effort-normalized captures, paired region and road categories, observed wetness and rain timing. Compare against count-only and uniform-time baselines with chronological holdouts.
- **Champion**: freeze current model; no candidate accepted or rollback justified from this night alone. Keep hypotheses tagged `NOT_VALIDATED`.

## Traceability

- Primary session log: user-pasted Habu log spanning multiple dates, analyzed for the Oct 22 operational night; **not an exact-byte raw log file**.
- GPX: `2026-10-22-0816 タイトルのないトラック(1).gpx` from current conversation upload.
- GPX SHA-256: `7ee4f005cc27fb3d680bd05b7de19d5e9d33241b906c545bbb356c885a2849aa`
- Machine-readable evidence and stage status: `reports/pdca/2026-10-22/evidence_summary.json`
- This audit is a manual diagnostic and is **not an official automated PDCA pipeline success**. Stored separately from immutable ORIGINAL P0/P1+ predictions. No weather or biological causal relationship was asserted.

