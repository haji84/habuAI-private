# Task 3 bounded implementation report

Status: foundation implementation complete locally; independent review pending. Whole Master Goal #1642 remains incomplete and no production/scientific completion is claimed.

Commit: `1277d91dec6142c5c8d7ff59be11e790f7c7d183` — Add bounded audited model evaluation and diagnostic replay.

Owned changes only: `src/model_evaluation.py`, `tests/test_model_evaluation.py`, `schemas/model-learning.json`. Parent documentation and integration test commits were not staged. No remote writes or subagents.

## Implemented computations and guards

- Canonical four-stage `evaluate_models(root, night, budget_seconds=300)` envelope with separate implementation/data blockers, decision, candidate/fold/replay evidence, research questions and output completion ledger.
- Explicit LearningSnapshot, hashed ForecastUniverse and hashed frozen protocol; all source references hashed and restricted to declared local input namespaces. Missing audited snapshot is BLOCKED, never silently synthesized from legacy diagnostics.
- Exact UTM52N coordinates or checked latitude/longitude, ten-minute windows and 07:00 JST operational-night alignment. Unique universe rows and learning units, all universe rows retained including unknown/unobserved rows, explicit capture counts/event IDs, nonfinite rejection, observation quality, label/feature/source availability checks and input rehash before completion.
- Features at or after cutoff invalidate evidence. Training rows and labels must precede held-out operational-night start/cutoff. Test labels unavailable by the requested evaluation boundary are excluded from evaluation/research. Confirmation nights are excluded from fitting, metrics and descriptive associations; overlap with research nights fails.
- At most three protocol-registered candidates. Fixed family registry: uniform smoothed observed probability; historical capture prior (spatial score only); Beta(1,1) smoothed observed-unit prevalence; optional duration-normalized area rate requires measured duration, method/observer metadata and fixed ex-ante reference effort. Only three may be registered together. Common-fold eligibility applies to every registered family.
- Stage1 Top10 1km individual-count recall, distinct-event recall separately, null recall on zero-positive nights. Coordinate-based 500/250/100m diagnostics. Formal 100m +/-10min output is NOT_PRODUCED because these models emit no actual time targets.
- Brier and descriptive calibration bins only for probability families. Capture prior and measured-duration rate emit `probability: null`; neither is falsely Brier-scored. Descriptive univariate associations and distribution drift are calculated, not called causal/adjusted research.
- Paired night Brier comparison against explicit uniform baseline and deterministic 2,000-draw night-cluster bootstrap. This uses research nights and is explicitly RESEARCH_DIAGNOSTIC / NOT_VALIDATED, never independent confirmation. Fixed smoothing was retained when sparse fixtures did worse than uniform; the independently calculated per-area Brier is 1/9.
- Actual fixed-model `predict_model` inference, model content hashes and lineage, immutable content-addressed REPLAY files. ORIGINAL is never written. Replay tampering, consumed-source mutation, invalid model hash/family or training after forecast cutoff fail closed.

## Exact inference contract for Task 4

`predict_model(model: dict, universe_rows: list[dict]) -> list[dict]` executes the exact serialized `fold['model']` object.

Model fields: `schema_version`, `family`, `implementation_version`, `parameters` (`area_values`, `default`, `smoothing`), `hyperparameters` (`smoothing`, `area_size_m`, optional `effort_reference_seconds`), `status: CANDIDATE`, `evidence_refs`, `training_cutoff`, `training_data_sha256`, `feature_schema_sha256`, `protocol_sha256`, `code_sha256`, `produced_outputs`, `model_id`, `model_sha256`.

Both `model_id` and `model_sha256` equal the canonical digest of all remaining model fields (exclude exactly those two identifier fields). Parameters are fitted state, not arbitrary source code. Feature schema is empty for these non-feature-aware baselines. Hash consistency does not grant registry/production authority.

Universe inference rows require `row_id`, `operational_night`, `cutoff_time`, and exact `utm_x_m`/`utm_y_m` or validated latitude/longitude. Evaluation additionally validates the explicit referenced universe schema, window, availability and geographic domain.

Returned rows, sorted by universe row ID: `universe_row_id`, `operational_night`, `utm_x_m`, `utm_y_m`, `spatial_score`, `probability`. Uniform/prevalence families return real computed probabilities; capture-prior/duration-rate return null probability and spatial ranking scores. These are not formal time-target forecasts. Different fitted models demonstrably change outputs.

## Decision semantics

- Invalid evidence: `REJECT_CANDIDATE`, stages FAIL, reason prefixed `INVALID_MODEL_EVIDENCE`.
- Computed nonimprovement: `REJECT_CANDIDATE`, reason identifies no paired research Brier improvement over uniform; does not imply independent scientific validation.
- Missing evidence, insufficient folds/cross-year coverage, positive but unconfirmed research comparison or budget exhaustion: `NEED_MORE_DATA` with required conditions.
- No code path returns `ACCEPT_CANDIDATE`. Missing formal targets, feature-aware ablation, confirmation consumption lock, trusted runner and other mandatory gates cannot be omitted to gain acceptance.

## TDD and verification

Initial 11 tests failed for the missing module. Added adversarial regressions before fixes for source-availability contradictions, future test labels, explicit nonimprovement rejection, bootstrap comparison/drift, upstream FAIL, unknown quality, future-trained inference, output ledger, required manifest lineage and identical eligible folds. The sparse-data test's initial improvement expectation was corrected to its independently derived Brier (1/9), retaining the fixed preregistered formula rather than tuning it to force a win.

Final commands:
- `python -m unittest discover -s tests -p test_model_evaluation.py`: 26 tests pass.
- `python -m unittest discover -s tests`: 130 tests pass.
- `git diff --check` and staged diff check: pass.
- Historical availability audit `evaluate_models(repository_root, '2026-09-28')`: all four stages BLOCKED, zero folds, NEED_MORE_DATA; exact missing artifact is `data/processed/model_learning.json`. No legacy conversion or artifacts generated.

Schema is stdlib-generated JSON with referenced universe/protocol definitions; no dependency or permission changes. A transient schema-generation script syntax error was corrected before writing the schema; subsequent full test suite passed.

## Remaining limitations

This is a bounded diagnostic foundation. Feature-aware models, adjusted multivariate/interactions, true retraining ablation, independent confirmation selection/consumption locking, formal temporal targets, count/activity/detection/routes/rerouting executors and trusted production evaluation/persistence remain explicit implementation blockers. No supplied synthetic flag or summary metrics can grant production eligibility. Source hashes and declared availability provide consistency checks, not issuer authenticity. Runtime budget is cooperative between validation rows, folds, candidates and bootstrap batches.

The existing historical dataset still lacks the explicit audited learning/universe contract. Parent's separate data audit indicates intake receipt timestamps cannot be retrospectively relabeled as ex-ante availability; this implementation does not attempt that inference. Independent review and remote Actions evidence remain separate from this local test result.

## Independent review round 1: five Important findings remediated

Review: `/workspace/scratch/fb45a4f31791/task-3-review.md`, including the denominator-coverage addendum.

Commit: `856f8bb6be9495428a46420680806aa72867d1d9` — Close model provenance gaps and scope incomplete recall evidence.

Only the three Task 3 owned paths were staged. No remote writes, data mutations, parent documentation changes or subagents.

### Provenance contract changes for Task 4 / Task 6a

- Every `source_manifest` entry now requires a recognized `role`: `label`, `feature`, `universe` or `protocol`. Missing roles are explicit missing-contract blockers; invalid roles fail. Changing a label source to protocol does not substitute for observation provenance.
- Every observed learning row needs at least one label-role source in `source_refs`. Its `label_available_at` must be no earlier than every bound label source's availability.
- New required row field `feature_source_refs` is an object mapping each feature name to a nonempty list of source paths. Its feature keys must exactly match `features` / `feature_available_at`. Each bound path must also occur in row `source_refs`, exist in the source manifest and have role `feature`. Declared feature availability must be at least the bound source availability and strictly before forecast cutoff. Missing binding is BLOCKED; wrong-role/unknown binding or contradictory/future availability is FAIL.
- These are consistency checks on declared, hash-bound provenance; no new issuer-authenticity or production-trust claim is made.

### Unknown rows and events

- Genuinely unobserved universe rows may use `label: null`, `label_available_at: null`, `quality: UNKNOWN`, zero capture count and no event IDs. They do not require a label-role source or invented audited-observation metadata. Ex-ante universe and feature provenance remains required.
- Unknown rows remain in inference/ranking and out of fitting, associations and scored-label denominators. Observed rows still require valid label timestamps and audited observation eligibility.
- Canonical capture event IDs must now be unique across the entire learning snapshot, including across different operational nights. No implicit per-night event namespace remains.
- LearningSnapshot and nested envelope shapes are checked before object field access. JSON roots `[]`, `null` and `42` return four FAIL stage records with `INVALID_MODEL_EVIDENCE`, not escaped AttributeError.

### Metric contract change: incomplete Stage1 denominator

The former unqualified keys `individual_recall`, `event_recall`, `confirmed_individuals`, `distinct_events` were replaced by:

- `restricted_individual_recall`
- `restricted_event_recall`
- `included_confirmed_individuals`
- `included_distinct_events`

Every spatial recall record includes `scope: OBSERVED_UNITS_WITHIN_FORECAST_UNIVERSE`, `denominator_coverage: NOT_ESTABLISHED`, and the concrete missing complete-outcome-ledger reason. All Stage1 `gate_outcome` values are now `NOT_EVALUATED`, even if the restricted diagnostic recall is 1.0. The actual included-universe recall arithmetic remains tested, including distinct individual/event weighting and exact 250m coordinates.

No complete hash-bound outcome ledger or outside-universe capture builder was added. Later evaluator work must retain all confirmed captures in the approved domain/time denominator, including outside-universe misses. Task 4 must not treat these restricted metrics as evidence that the full Stage1 gate passed.

### TDD / verification

Six regression methods were added before implementation. The initial run reproduced all findings: seven failing subcases and three escaped AttributeError cases. Existing numeric tests were updated only for the explicitly scoped metric names; their independent expected values remain unchanged. The fixture now supplies a separate early feature source and explicit bindings, rather than using label-only provenance as a feature source.

- Model test suite: 32 pass.
- Full repository suite: 136 pass (`python -m unittest discover -s tests`).
- Working/staged diff checks: pass.
- Additional coverage checks missing/invalid/protocol-only provenance, backdated feature availability against an earlier-than-cutoff but later-than-declared source, global event reuse, unknown rows without label refs, malformed roots, and denial of a Stage1 gate when denominator coverage is unknown.

Independent re-review remains pending. Whole Master remains incomplete; all earlier scientific, executor, confirmation and production limitations remain in force.
