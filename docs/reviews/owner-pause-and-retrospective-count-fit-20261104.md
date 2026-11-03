# Owner-confirmed pause and exploratory night-level count fit (2026-11-04)

Status: **PRIVATE_EVIDENCE_ARCHIVED / EXPLORATORY_FIT_COMPLETED / FORMAL_MODEL_FIT_BLOCKED**.
Work item: existing [PR #136](https://github.com/haji84/habuAI-private/pull/136). This is a public-safe receipt only. **No raw GPS, event coordinates, detailed routes, user log, private training rows, or fitted private JSON are included.**

## New evidence: 2026-11-03 operational night

- Owner's direct report: **2 owner-captured Habu**, distinct from fauna sightings or Himehabu.
- Search start/end: 18:17–23:33 JST, elapsed **316 minutes** from owner log.
- GPS point-to-point interval 22:14:53–22:44:05 JST: **29m12s**. Owner explicitly confirmed a deliberate pause for personal errands; do **not** classify as GPS failure, forced telemetry loss or observed noncapture.
- Active exploration proxy after pause: **approximately 286.8 minutes / 4h47m**. Exact real pause boundaries and any other non-search periods are not independently observed; this is a proxy, not a fully qualified measured exposure.
- Historical prior-chat reference count forecast: 2, actual 2; exact count agreement **does not certify** regional/timing skill or an original P0. Never relabel a retrospective fit as the model that issued it.
- Local private-source GPX, derived event CSV, corrected PDCA, receipt, model fit, and reproducing code were archived under the owner's private Library `/ハブAI/{Raw,Derived,Evidence,PDCA}` on 2026-11-04. Uploaded original GPX and candidate model were retrieved and **byte-for-byte SHA-256 matched** against their working-container sources.
- Private raw/source-receipt SHA-256: GPX `e3e2e0809b7fc980bb90d47d1bff65b45e86490b6273eaf218dc5dd62aa778aa`; experiment model `5b95f28aa08c80cb9c2757184aced81ea48196c6a64c2f152b167299cc6dea7b`. Hashes alone are not source authenticity or training approval.

## Actual exploratory numerical fit, explicitly outside official selector

- Retrospective, simple homogeneous **Poisson MLE capture-count rate per elapsed-session-hour proxy**; not a new Habu predictor integration, no official forecast.
- **13** historical owner-night records, **34** owner captures; accumulated proxy exposure **64.46141 hours**; numerical fitted rate **0.527447 owner captures / session proxy hour**.
- Conditional five-hour mean **2.6372** counts under a homogeneous effort assumption. This is *not* a published Habu AI count prediction or a validated interval.
- Strict chronological **post-hoc replay** holding out November 1: trained from 11 older records, conditional mean **2.8132**, observed **2**.
- Strict chronological **post-hoc replay** holding out November 3: trained from 12 older records, conditional mean **2.5629**, observed **2**. Neither post-hoc replay is a preserved prospective prediction, and no official scores are computed.
- Exclude older nights with **unresolved** long GPX gaps instead of fabricating full measured active search. Correct only this owner's verified Nov3 pause; do not assume other gaps were also personal pauses.
- Numerical output was deterministically re-run with identical SHA; private fit contains no geographic coordinates or sensitive place names.
- Owner's proposed day→night temperature decline, wind×terrain, prior-rain wetness, and time-of-night features were **not fitted or validated** because source-bound, as-of environmental joins and qualifying active-search/outcome evidence are missing.

## Non-negotiable gates

1. Existing strict `training_corpus.select_training_rows` → `train_spacetime_candidate.fit_candidate`, G0/100m×10min qualification and prospective freeze rules remain in force. **No source-qualified training fit** took place here.
2. An owner-confirmed pause subtracts only approximate time from a *research effort proxy*. It does **not** grant independent full positive/negative source certification. Unvisited or paused spatial cells remain UNKNOWN.
3. Official 100m±10min metrics, 1km Top10 Recall, model-vs-Champion performance, P0/P1 issuance, Champion promotion and production activation remain **NOT_VALIDATED / BLOCKED**.
4. Do not push the private source or any detailed coordinates to this **PUBLIC** repository. Keep existing PR #136 Draft. Main merge, production activation, billing, permissions or release require separate explicit approval.

This note records *completed* private ingestion and numerical research fitting, while preserving the precise scientific gate between exploratory diagnostics and formal model learning.

## Supplemental private-GPX reproduction and research-only v1.1 (2026-11-04)

The following are **new aggregate-only audits**, not new official prediction training, not a private route upload, and not a replacement for the existing source-bound train/score contracts.

- Original November 1 GPX was recovered privately and byte-hash-verified, resolving the earlier “GPX inaccessible” limitation for source inspection. Nov1 has **18,125 GPS points / one segment**, Nov3 has **17,217 / two segments**. Neither recorded segment has an internal unreviewed gap over 120 seconds. Nov3's 29m12s intersegment gap is an **owner-confirmed voluntary exploration pause**, not a capture-negative window or GPS failure.
- Private 100m × 10min track-presence preprocessing produced **722 Nov1** and **793 Nov3** unique visited grid/time units, **1,515 total**. Two Nov3 observed Habu captures aligned with contemporaneous GPS within 100m and ±10min, which is retrospective event-to-source matching and **not** proof of spatial prediction accuracy. No positive or negative official training labels were generated from these cells; unknown remained unknown.
- The 127-night historical feature readiness snapshot has **zero independently qualified binary training units, verified active-search receipts or complete-outcome scopes**, and does not include Nov3. Full canonical individual-event de-duplication remains unverified, so no DB entry was incremented or overwritten.
- Previously archived exploratory v1 was rerun and byte-identically reproduced. Separate, research-only v1.1 corrected two proxy durations from the original GPX, without adding nights: **13 owner nights, 34 captures, 64.466830 proxy-hours, MLE 0.527403 captures/proxy-hour; 5-hour illustrative mean 2.637015**. Post-hoc leave-future-out diagnostics with *actual post-search effort* yield means **2.811874 (Nov1)** and **2.567214 (Nov3)**, each with observed count 2. These are not frozen prior predictions or official scores.
- Independent [JMA Koniya Nov1 hourly](https://ds.data.jma.go.jp/obd/stats/etrn/view/hourly_a1.php?block_no=0980&day=1&month=11&prec_no=88&view=np0&year=2026) check: 15h **25.4°C**, 18h **23.7°C**, 21h **22.6°C**, 22h **23.1°C**. Cooling was not linear. Rain lags, residual wetness, wind × terrain, road orientation and time-of-night effects were **not fitted or validated**. Later-obtained weather data must not masquerade as original forecast-time inputs.
- **15 local tests passed.** The updated research-only model, private grid with unlabeled cells, weather evidence, private audit and forecast-chat handoff are stored under the owner's private Library /ハブAI/. Existing PR #136 private-model handoff work is preserved; no duplicate adapter was created.

**Formal training, future-night 100m ±10min independent evaluation, Champion comparison, model promotion and production authorization remain blocked or unperformed.** No raw GPS, coordinates or full private rows are published in this note.
