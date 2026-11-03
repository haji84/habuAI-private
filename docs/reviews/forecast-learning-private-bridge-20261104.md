# Private prediction / learning bridge: implemented boundary (2026-11-04)

Repository: haji84/habuAI-private (currently public). Reuse existing PR #136.

## Completed and reproducible

`python scripts/habu_private_model_link.py --pdca /private/<night>-pdca.json --model /private/model.json --gpx /private/original.gpx --private-output /private/handoffs/<night>-model-link.json`

- Reads only explicit private files, verifies PDCA and research-model internal hashes, bound Habu capture counts, confirmed pause and (when provided) the original GPX bytes' SHA-256.
- Writes an append-only local private handoff with idempotent same-byte reruns and conflict rejection. No coordinates, routes or GPX contents are written to the public repository.
- Marks existing-night model linkage `ALREADY_IN_RESEARCH_MODEL`, or stages a future/new night `STAGED_FOR_PRIVATE_EVIDENCE_REVIEW`.
- Rejects unconfirmed GPS gaps, unknown pause treatment, changed captures, duplicated night training records and promotion/production flags disguised as a research artifact.
- Emits `PROVISIONAL_NOT_FREEZABLE` for the next prediction, does not create P0, does not grant source qualification or train an official model. Existing authoritative pipeline / strict selector are not bypassed.
- Synthetic tests: 10 PASS in local Python unittest. The 2026-11-03 actual private model/PDCA/GPX was linked successfully; the resulting handoff and code were archived in private Library `/ハブAI/Evidence/2026/11/`.

## Not yet functioning as production end-to-end

This code is a source-bound **handoff adapter**, not a new model engine or a public-data connector. Automated invocation requires a private ChatGPT Library agent or an authorized private executor. GitHub Actions cannot read the user's private Library directly, and must not copy it to this public repository. Existing `scripts/private_pdca_runner.py`, `scripts/run_pdca.py`, `training_corpus.select_training_rows`, `train_spacetime_candidate.fit_candidate` and registered-authority checks remain the only formal scientific processing paths. Eligible training corpus with independent active-search and complete-capture-outcome proofs, valid ex-ante features/universe and a trusted Champion authority are not yet established.

Workflow target: after a new exploration original appears in the private Library, a periodic private agent checks revisions and freezes evidence; only authentic older ORIGINALs are scored, and replay/casual estimates remain noncanonical. A verified PDCA handoff can stage an updated private research candidate. A qualified candidate must pass source/readiness gates, chronological backtesting and independent review before the forecast path may adopt it. No automatic main merge, paid services, secret changes, production model activation or publication of private locations.

## 2026-11-04: NightCount v1.1 integration verified

- Existing `scripts/habu_private_model_link.py` now validates the separate `habu-research-nightcount-poisson-v1.1` internal payload digest, explicit research-only rights and private GPX-source lineage. The original v1 format stays supported.
- Against the actual private **November 3** GPX, pause-corrected PDCA and source-hash-checked NightCount v1.1, the revised adapter generated a new **private append-only v3 handoff** (file SHA-256 `99a3c994ca251c999d54bf1a75d81745aa9ffc9c9cb73b8b219b5b10e7700349`). This file remains in the private Library under `/ハブAI/Evidence/2026/11/`; no GPS content or detailed capture locations were committed to GitHub.
- Existing and additional synthetic checks: **15/15 PASS locally**, including illegal promotion via a rehashed model, mismatching original GPX lineage, mutated model, and new-night UNKNOWN cases. Not evidence of field model skill.
- The output explicitly remains `PROVISIONAL_NOT_FREEZABLE`: **no** eligible 100m×10min TRAIN_ONLY model, approved production Champion, immutable P0 or automatic production adoption. Source qualification and independent future-night evaluation are still prerequisites.
- Frozen code closure updated in `protocols/development/cycles/20261104-private-forecast-learning-118-02.json` without modifying previous frozen cycles; the full GitHub Actions test suite and independent review still require their exact-head results.
