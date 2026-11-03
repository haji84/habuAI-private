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
