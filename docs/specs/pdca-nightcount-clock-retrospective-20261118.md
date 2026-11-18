# Private NightCount / EventClock chronological comparison v1
2026-11-18 JST. Master goal: haji84/AI-#1642. Draft PR #163.

## Purpose
Research and compare **existing private, owner-supplied model snapshots** even when fully qualified 100m/10min Negative units or prospective ORIGINAL P0 are absent. This is independent descriptive/retrospective model research, **not** formal G0 fitting, new official P0, full spatiotemporal scoring, model promotion, or production data ingestion.

## Code and private execution
- `src/research_nightcount_clock.py`: purely in-memory, standard-library evaluation of the existing NightCount v1.2 and EventClock v1.2 stored model shapes; bounded schema/total/chronology validation and non-promotion assertions.
- `scripts/private_count_clock_comparison.py`: owner-only filesystem wrapper; reads JSON from an isolated private directory outside GitHub, verifies source byte hashes, rejects invalid JSON/duplicate keys/path escapes, writes a single immutable/readback research report under the same private root and prints only opaque hashes, sample sizes, and research candidate decisions.
- `tests/test_research_nightcount_clock.py` and `tests/test_private_count_clock_comparison.py` use **synthetic** data. No real owner GPS or night rows are committed here.

Example for an authorized owner-private runtime with local copies of the already-existing research JSON files:
```sh
python scripts/private_count_clock_comparison.py \
  --private-root /owner-only/store \
  --nightcount models/HabuAI_ResearchNightCount_v1.2_to_20261109_PRIVATE.json \
  --eventclock models/HabuAI_2025_2026_ResearchEventClock_v1.2_to_20261109_PRIVATE.json
```
The files and output must physically reside under the access-controlled private root. No hidden GitHub Actions access to connected ChatGPT Library is assumed. This CLI is not an unattended connector.

## NightCount methods
Input: 16 dated owner-research nights in the v1.2 snapshot, including each recorded personal capture count and **elapsed session duration proxy**. No spatial negatives are created. Duplicate/out-of-order nights, count/hour conflicts, invalid types and nonfinite values fail closed.

Use 5 or more earlier nights to forecast the next night. On each chronological evaluation fold compare:
1. **historical_night_mean**: arithmetic mean of past recorded capture counts per night.
2. **assumed_5h_exposure_rate**: past total recorded captures / past total session elapsed hours proxy * assumed 5 hours. The evaluated night’s *actual* elapsed duration is **not** used as a predictor.
3. **recent_5_night_mean**: mean of the last five available prior nights, with no tuning.

Metrics on the **same folds**: capture count MAE, RMSE, mean Poisson negative log-likelihood and paired night-level bootstrap 95% intervals on differences (fixed seed 1642; 2,000 replicates). Lower values are better. The prospective duration assumption of 5h is a research scenario, **not** an owner-supplied planned duration. Posthoc historical source availability and active-search effort remain unverified. Do not treat chronological rows alone as a genuinely sealed future-night study.

`REJECT_EXPLORATORY_CHANGE` is returned when neither candidate improves both MAE and log score against historical_night_mean. A positive diagnostic is only `RESEARCH_HYPOTHESIS_ONLY`, never automatic promotion.

## EventClock methods
Input: saved v1.2 *prior*, *new November* and *combined* six-bin capture **event** histograms. Validate counts add exactly. Evaluate the 8 new November capture records under three fixed probability assignments:
- Uniform six-bin;
- Prior-histogram Laplace smoothing, alpha recorded in source;
- Half-shrinkage toward uniform (50/50), a retrospective **post-selected** counterfactual.

Metric: mean negative log-likelihood per recorded capture event. The percentages are **conditional on a capture having been recorded**; they are not estimates of Habu presence per search hour or unbiased event-time hazards. The 50/50 counterfactual was examined after stored November outcomes were available, so independent validation is **not** claimed.

## Private historical research comparison result (reporting guidance, not stored publicly)
The separately verified owner Library source includes 16 nights / 38 capture individuals through 2026-11-09. An exploratory calculation on 11 chronological folds yielded an ordinary historical per-night average as the lowest MAE of the three fixed models. This public document intentionally omits the private night-by-night evaluation rows and exact GPS/capture locations.

## Remaining original Master Goal
- Real private connection/archival readback in the user’s own verified execution environment. Library tool read is not the same as unattended access for public Actions.
- Safe individual-count and active-search exposure admission into registered models. Capture *event* counts are not inferred as individual counts; unknown GPX passage is never Negative.
- Feature-aware model comparison and weather/wetness/terrain joins, no as-of leakage, properly untouched future-night holdouts.
- Stage1 1km Top10 Recall and formal 100m ±10min scoring before Champion eligibility.
- Trusted promotion/rollback and next real ORIGINAL issuance verification, not code-only test success.

**Authority:** This stage only generates private research diagnostics. Every report has `champion_promotion_allowed=false` (or equivalent) and is neither a replacement for source qualification nor permission to activate a model.
