# 2025-2026 private historical research fit receipt (2026-11-04)

Scope: existing Draft PR #136. **PUBLIC-SAFE RECEIPT ONLY.** This file contains no private event rows, timestamps, precise geography, GPS traces, routes, raw log text, or model output.

## Work completed in private Library
- Reopened the verified 2026-08-29 2025–2026 baseline workbook and its 2026-10-21 merged manifest. Baseline workbook SHA-256 matches the original merge manifest.
- Compared conflicting 2025 source versions; the later master conservatively retains **9 historical capture-or-sighting unknown records** and does not promote them to owner captures. Quarantined **4 additional inferred/duplicate-suspect labeled capture units** from research fitting.
- Retained **24 historical 2025 capture-labeled units as research candidates** (only **16 have exact clock times**), without treating them as source-certified positives.
- Extracted 2026 April–August exact-clock events (168 captured units) and 67 unique 2026 September–October 20 captures from the merged source's 67-event tab. 2026 October 6–20 overlaps the existing 13-night count research model's 17 captures and was not added twice.
- Built a research-only six-bin (two-hour) smoothed **conditional capture-event-clock distribution** on 251 recorded captured units with exact clock times. Research outputs and reproducibility scripts were stored **only in the user's private Library** under `/ハブAI/{Derived,Evidence,PDCA}/2026/11`.
- Retrospective development diagnostic on 2026 September–October 20 captured events: older 2026-only fit conditional clock NLL 1.61491; adding 2025 research candidate times NLL 1.50747. Lower is better. This is **NOT** a prospective forecast score or evidence that spatial accuracy improved. 2025-only fitting on 2026 April–August performed worse than uniform (2.00437 vs 1.79176).
- Deterministic research model rerun gave identical bytes. 14 focused local tests PASS. No event count was incremented in the canonical database and no false negatives generated.

## Quality / privacy gates remain
- Public repo remains public. Do not publish private raw GPS, exact capture coordinates, per-event time/point sequences, private derived data, or owner route.
- 2025 exact active-search coverage / complete outcome scopes and provenance are not established. Research-clock probabilities are conditional on recorded positive events and are **not search-exposure-normalized capture probabilities**.
- The 2026 October 20 snapshot's September event count may not include a later owner-corrected additional capture; retain as a versioned historical source rather than silently add an unverified timestamp.
- Official `training_corpus` / `train_spacetime_candidate` fit: **0 newly eligible rows**, not attempted with these source-incomplete events. 100m ±10min, Champion comparison, future P0/P1 freeze remain **NOT_VALIDATED**.
- Earlier model v1.1 night-count proxy (13 nights/34 captures) remains unchanged, including the owner's confirmed November 3 intentional pause. No new negative from pause or missing GPX.
- PR remains Draft, no main merge, model promotion or production deployment. Separate human authorization remains required.

This record intentionally provides no private downloadable model path to the public Git repository. The private Library archive is the source of truth for the experiment and its source lineage.