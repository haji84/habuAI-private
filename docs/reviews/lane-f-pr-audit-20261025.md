# Lane F: prospective-input PR audit, 2026-10-25

Status: SOURCE_AUDIT_COMPLETE; existing PR #46 needs an eligibility repair before integration. This audit does not certify training data, scientific metrics, production issuance, or historical source availability.

Audited at 2026-10-24 22:37 UTC / 2026-10-25 07:37 JST. Main is pinned to `4981592789f5a6fe01800df85105f2d0c49c0b4a`; the audit worktree started clean on `codex/feature-audit-20261025`. Raw, ORIGINAL, shared state, source receipts, and production authority were not changed. The only initial owned output is this document.

## Exact heads, stack, CI

| PR | Exact fetched head | Base/dependency | Current observed CI |
| --- | --- | --- | --- |
| [#32](https://github.com/haji84/habuAI-private/pull/32) | `123109a630b16f7af4e5cc41482ddd10839351b5` | main; merge-base `27f4832a23f0a3826ce96b87afb4f2f1c58aa936` | [run 39594265389](https://github.com/haji84/habuAI-private/actions/runs/39594265389) success; job `119570614619` test success |
| [#33](https://github.com/haji84/habuAI-private/pull/33) | `cd97e69a2d1cfb160b21f33a3e561be989d5ba8d` | main; same merge-base | [run 39593746339](https://github.com/haji84/habuAI-private/actions/runs/39593746339) success; job `119569725935` test success |
| [#46](https://github.com/haji84/habuAI-private/pull/46) | `179c45b9f58cd46aec8a97a127db713e80540229` | PR #32 branch; #32 head is an ancestor; #33 is related producer, not an ancestor | [run 39614043931](https://github.com/haji84/habuAI-private/actions/runs/39614043931) success; job `119569903439` test success |

All three are open, draft, API `mergeable=true`. Exact-head workflow lookup returned `data-intake-tests` completed/success and combined-status lookup returned CodeRabbit success. Each job reports successful checkout, Python setup, requirements-analysis installation, `python -m unittest discover -s tests -v`, and secret-file rejection. This proves the returned run/job statuses, not the number of tests or current-main integration. The workflow connector returns only its first page and PR-triggered runs. No CI was dispatched by this audit. Old PR body statements that Issue #34 blocks all runner execution are stale relative to these successful runs; no billing/permission changes were made.

Git fetch used `refs/pull/{32,33,46}/head` into `refs/remotes/origin/audit-pr{32,33,46}`. All heads match the supplied SHAs. Main has 31 commits beyond the common merge-base. PR #32 has 8 unique commits, #33 has 7, #46 has 39 versus main (31 commits relative to #32). No proposed path already exists at pinned main, so there is no direct same-file add conflict. Semantic integration still requires fresh-main checks: `src/evidence_audit.py` and `src/prospective_candidate_model.py` changed on main since the common base.

## Implemented scope and overlap

| Work | Source at exact head | What it actually does | Reuse / missing boundary |
| --- | --- | --- | --- |
| #32, 3 files / 763 added lines | `src/prospective_inputs.py`, its tests and `docs/specs/prospective-forecast-input-binding-v2.md` | Read-only v2 snapshot plus v1 universe/feature join; hashes consumed bytes, strictly checks reference availability, normalizes UTC/JST unit identity, rejects known outcome fields recursively, requires complete feature values, bounds bytes/rows/features/join/deadline, rescans | Reuse input loader. Its feature-schema hash covers sorted names only (lines 235-240), so units, valid-time, definition/version and derivation semantics need a separate G0 hash-bound contract. Hash consistency does not authenticate an availability declaration. |
| #33, 3 files / 698 added lines | `scripts/build_osm_prospective_universe.py`, its tests and `docs/specs/verified-osm-prospective-universe.md` | Verifies archived ZIP/CSV bytes, parses 16,990 auxiliary road cells, emits 1-6 future ten-minute windows and road length/axial sin/cos, publishes snapshot last and rejects late completion | Reuse producer. Source class is auxiliary, legal access/current closures UNKNOWN (lines 181-190); no weather, DEM, full night or official road certification. Linux `fcntl`/directory flags make materialization unavailable directly in current Windows runtime. |
| #46, 7 extra files / 1,389 added lines above #32 | `src/prospective_spacetime.py`, `src/training_corpus.py`, `src/train_spacetime_candidate.py`, `src/development_walkforward.py`, 2 test files and bridge spec | Candidate-only logit/time inference consumes actual #32 loader; TRAIN_ONLY selector; L2 logit fitting and retrospective observed-unit development diagnostics | Reuse same PR after safety repair; do not replace with another pipeline. It is not wired into the current orchestrator/registry, has no complete outcome denominator or independent confirmation, and does not implement composite v2. |
| Existing main research candidate | `src/prospective_candidate_model.py` | A separate research-only L2 logistic implementation with fixed seven environmental/terrain/road features and hierarchy IDs | Overlaps #46's fitting/scoring purpose but uses incompatible schema, 7 fixed features, different fit minima/optimizer/serialized state and provenance. Do not silently alias models or duplicate a third fitter. Retain old behavior behind an explicit adapter until a reviewed target/recipe contract replaces its use. |
| Existing main learning path | `src/learning_snapshot.py`, `src/model_evaluation.py`, `schemas/model-learning.json` | v1 historical ex-ante snapshot builder/evaluator with source roles and per-feature source bindings | Preserve this strict v1 contract. TRAIN_ONLY future fitting is a distinct versioned path; no historical cutoff may be moved later to make a row pass. |

## Integration-blocking findings

### P1: #46 accepts passage-only noncapture observations as supervised negatives

`src/training_corpus.py:145-150` permits `search_role` in `('SEARCH','PASSAGE')` with two booleans, without independently hash-bound active-search or complete-outcome coverage receipts. `src/development_walkforward.py:112-116` repeats the same allowance for held-out diagnostics. This contradicts AGENTS rule 4 and current main `src/evidence_audit.py:359-394`, which requires SEARCH plus independently scoped complete capture accounting before a negative is created.

Executed reproduction used the exact PR blob in memory, the unmodified existing `AuditedTrainingTests` fixture class loaded via AST, and temporary fixture files outside the repository. Baseline: 4 accepted units, 3 nights, 2 positives, 2 negatives. Replacing both negative rows' search role with PASSAGE produced `DEVELOPMENT_TRAINING_ELIGIBLE`, all 4 accepted, negatives `row-1` and `row-3`, with no independent search/complete-scope reference. This is an adversarial synthetic probe, not training or actual-data certification.

Minimal repair: require SEARCH, a hash-bound active Habu search scope and a distinct source-bound complete owner-capture-outcome scope covering that night/cell/time. Plain booleans or GPX quality cannot supply either. Use one shared eligibility helper for selector and diagnostic evaluator; absent/insufficient evidence excludes or blocks the row. Regression cases must cover PASSAGE, unknown role, missing/swapped/tampered references and mismatched scope.

### P1: #46's TRAIN_ONLY feature acceptance does not enforce source roles or target exclusion

`src/training_corpus.py:87-99` accepts manifest entries with exactly path/hash/received_at; there is no role. Lines 170-183 accept arbitrary numeric named features using a `feature_valid_for_night` boolean and per-feature timestamp, with no per-feature source binding/valid-time contract. Unlike main `src/model_evaluation.py:145-146,263-278`, this permits outcome-only evidence to be treated as a predictor.

Executed reproduction: replace each fixture's feature with `{'label': row['label']}`, declare `require_features=('label',)`, preserve the outcome-only source and claimed historical-validity boolean. Selector still returns `DEVELOPMENT_TRAINING_ELIGIBLE`, 4 accepted, features `['label']`. #32 later rejects this particular name prospectively, but that does not make the training selector safe or validate its fitted artifact. Minimal repair must reject known target-derived names and bind each selected feature to a declared predictor-role source whose actual readiness precedes feature usability and fit/evaluation cutoff. A name denylist alone cannot prove arbitrary feature semantics.

### P2: per-shard caps do not yet represent a full-night feature universe

#33 lines 35-38,149-203 yield 16,990 cells times at most 6 windows = 101,940 rows and 3 road features. #32 lines 21-27,174-175 cap the join at 400,000 numeric cells; six windows therefore allow at most 3 feature columns, while 7 columns allow at most 3 windows. #46 `MAX_ROWS=120000` (line 23) independently prevents a full-night inference batch. A 24-hour/144-window full domain is 2,446,560 rows, beyond even #32's 2,000,000-row cap; ordinary evening horizons likewise exceed the joined-cell budget.

Keep caps. G0 must declare horizon and complete expected cell/window domain, then bind disjoint shard references and reject gaps, duplicate normalized units, domain/feature-schema mismatch and cutoff/availability disagreement. A six-window shard must never pass as full-night coverage. A new narrow `feature_*_v2.py` coverage-manifest adapter is a useful nonduplicating future slice only after the #32/#33 contracts are reused and ownership is assigned.

### P2: bounded loop counts are not the shared parent wall-clock contract

#46 `fit_candidate` has up to 400 iterations (`src/train_spacetime_candidate.py:20,99`), selector bounds rows/bytes, and diagnostics allow up to 12 folds (`src/development_walkforward.py:19,73`). None of these functions accepts the shared monotonic remaining-budget/check callback required by the feature-model/composite plans. The inference path does have a shared deadline. Before connecting fitting to the parent, bind all source reads, fits and folds to its remaining allowance; do not claim fixed iteration counts prove <=300 seconds.

## Current-main source availability gaps

Inventory is from actual pinned checkout paths, with no network acquisition or data writes. `features/weather_sampling_sites.json` exists. `features/learning_build.json`, `data/processed/model_learning.json`, `protocols/`, `evidence/exante/weather/`, and `evidence/exante/terrain/` are absent. `data/raw/gis/` contains only README/license text, no DEM raster. This does not deny historical successful external/live-source probes reported by other PRs; no equivalent usable source snapshot is present in this audited tree.

| Feature family | Present implementation | Actual availability / remaining work |
| --- | --- | --- |
| Weather | `scripts/acquire_exante_weather.py` obtains six hourly Open-Meteo fields and preserves raw bytes; `scripts/audit_p0_exante_assets.py` checks supplied evidence | No captured snapshot here. Acquisition is 60-minute point samples; exact underlying provider run is not independently certified (lines 163-205). Road-scale spatial mapping, ten-minute semantics, coverage, actual as-issued readiness and typed snapshot adapter remain unverified. Existing audit lines 70,73 use `>` and therefore permit equality; G0 requires strictly before cutoff. |
| DEM/terrain | `src/road_dem_join.py:100-155` hashes road/ASCII DEM inputs, requires EPSG:32652 and strict source-before-cutoff; returns unknown outside coverage | No actual DEM raster/bound per-road terrain artifact here. `scripts/gsi_dem_source_probe.py` is a source probe, not full coverage. Wind-relative-road geometry is a proxy; terrain shielding is explicitly false. |
| Moon/tides | Requested by feature-model plans, arbitrary numeric columns could be passed to #32 | No dedicated source acquisition, ephemeris/tide adapter or hash-bound feature artifact found under `src/`, `scripts/`, `features/`, `data/processed/`, `evidence/` or `artifacts/`. G0 must define source/algorithm/version, site/station geography, physical valid-time, issue/receipt/materialization/readiness and coverage; do not fabricate values or assume a historical source was available. |
| Roads | Archived September-25 auxiliary OSM with verified producer #33 | This is not an official or legal/current road graph and cannot certify August ex-ante inputs. Forecast universe and inference inputs must remain distinct from realized GPX/labels. |
| Existing seven-feature research candidate | `src/prospective_candidate_model.py:19-21,79-104` | No current eligible corpus. It accepts `features_available_at == forecast_cutoff` (line 86) and `GPX_PASSAGE_VALIDATED` for training (line 94), weaker than current main evidence semantics. Integration must not route around the stricter repaired selector. Separate owned repair/review is needed before using that candidate with real rows. |

## G0 interface facts to freeze

1. Preserve current v1 `LearningSnapshot` and pure `predict_model(model, universe_rows)` behavior. Declare TRAIN_ONLY corpus versus label-free prospective universe/feature snapshot as distinct artifact kinds, with explicit adapters and immutable version hashes.
2. Unit identity is EPSG:32652 floor(x/100), floor(y/100), normalized UTC ten-minute instant, plus true 07:00 JST night. Row IDs are transport identifiers. Freeze 1km/500m/250m hierarchy rules from exact coordinates; do not average 100m IDs into 250m cells.
3. An `ArtifactRef` binds path, SHA-256, actual source/receipt and required qualification readiness. `usable_at` is the maximum proven required readiness; all required times are strictly before the fit or forecast boundary. Preserve physical valid-time separately from availability. A digest alone is not authenticity or proof of past access.
4. An `ObservationEligibility` binds target contract, observation state, canonical capture/event identities, independent SEARCH scope receipt, independent complete-outcome scope receipt and exclusions. UNKNOWN has label=null. GPX role/effort and outcome labels never become generic forecast features.
5. A `FeatureDefinition/Value` binds name, units, definition/version/derivation/code hash, role, per-feature source refs, valid-time/window, receipt/materialized/audit/usable times, missingness and deployment semantics. Forecast weather versus retrospective measured weather must remain distinct. Target-derived predictors are forbidden.
6. `ForecastUniverse/ShardSet` binds domain/source class/geometry/horizon, expected cells/windows, snapshot/shard refs, duplicate/coverage checks and feature schema. Full forecast support includes unobserved units. Out-of-universe confirmed events remain evaluation misses through an independent outcome ledger.
7. Candidate output declares target and score semantics. #46's `candidate_probability` is UNVALIDATED and its candidate targets are diagnostic; these are not calibrated biological probabilities, formal production targets or composite/route capability. No compatibility by matching a string list of feature names alone.
8. Pass the common budget callback through all future source/selector/fit/predict/fold calls; persist exact input/code/runtime identities. Confirmation selection, denominator and consumed-night ledger belong to V and must remain inaccessible to fitters.

Suggested contract regressions: PASSAGE and missing completeness cannot create a negative; roles/feature refs cannot be swapped; equality at every readiness boundary rejected; UTC/JST alias duplicates rejected; wrong valid-time rejected; outcome-derived feature rejected; unseen/unobserved forecast cells retained; missing weather/DEM/moon/tide remain explicit blockers; shard gaps/overlaps fail; no changes to Raw/ORIGINAL hashes.

## Next slice and source identity

First repair belongs on existing #46, after G0 review: `src/training_corpus.py`, `src/development_walkforward.py`, existing/new training/development tests. No replacement PR. Independent reviewer and exact new-head CI must follow any change; old green runs do not cover the repair or fresh-main integration. Then integrate/review #32/#33 in dependency order, preserving candidate-only qualification. Keep scientific validation, formal Stage1/100m±10min, production Champion and P0 blocked until genuine inputs and independent evidence exist.

Git blob SHA-256 (avoids Windows checkout CRLF conversion):

| Source at audited head | Bytes | SHA-256 |
| --- | ---: | --- |
| #32 `src/prospective_inputs.py` | 11,314 | `d55bf669dbd5a2595674a13a257490bcd3557347fb826d43a868d19504ba039b` |
| #33 `scripts/build_osm_prospective_universe.py` | 15,218 | `33d4e466ed8720d58d1bb5adc654b1fbbee36c0148e4b81713293cd34321c888` |
| #46 `src/training_corpus.py` | 12,849 | `8e6660925f41618ee20ea069e218d549dc66488d1036ef1833dc02ee41fd538f` |
| #46 `src/development_walkforward.py` | 8,760 | `10c4bf37b3a790ea08ebfe99ee474e9419f548fa74fdba84d5a5d3eb120b7377` |
| #46 `src/train_spacetime_candidate.py` | 7,829 | `b2b18881d20a8aa0ae948526463aa813d3ddf1b17a079e5ef7c5465cfb2f7728` |
| #46 `src/prospective_spacetime.py` | 10,587 | `ebe35e962ac36000e40c9bdbe5f99fb9053a94cb69b5081230a0c49955a9e460` |

Local verification performed: git head/ancestry/path comparisons, actual source/path inventory, API head/status/run/job reads, two successful adversarial demonstrations against exact PR46 selector code. No new actual model fit, scientific evaluation, production E2E or whole-suite PASS is claimed. Current Windows runtime lacks native `fcntl`; Linux CI/fresh-main qualification remains coordinator-owned.
