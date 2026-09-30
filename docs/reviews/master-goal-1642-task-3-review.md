# Independent Task 3 review

Scope: Task 3 commit `1277d91` (parent `5851707`), its brief/report and normative spec including independent-review resolutions; also integration test change `ccf18c5`. Read-only implementation review with focused tests/probes, no implementation edits or full-suite rerun.

**Spec compliance: changes required. Code quality: changes required.** No Critical finding. Four Important findings below. Missing feature-aware/scientific/output/confirmation/trusted-production adapters are explicitly reported and are intentionally later-slice work, not defects merely because absent here.

## Important 1 — Provenance roles and coverage can bypass source-availability checks

`src/model_evaluation.py:131–147, 221–237`; `schemas/model-learning.json:28–47`.

Source roles are neither required nor validated at runtime. The only source availability checks are conditional on `role == 'label'` or `role in ('feature', 'universe')`. Rows need some `source_refs`, but observed labels do not need label-source coverage and features do not need feature-source coverage. Omitting the role, supplying an unrecognized role, or assigning only protocol provenance skips the availability guard entirely. The schema also leaves `role` optional. Requiring an enum alone will not fix missing role-specific coverage.

Reproduction: using the three-night fixture, move its sole source's declared availability to `2027-01-01`. With `role='label'`, evaluation correctly returns FAIL and zero folds. Remove `role`, or change it to `protocol` or `unknown`, and it instead produces six folds, model_evaluation NOT_VALIDATED and candidate_generation PASS. Label evidence declared unavailable until the future has entered historical training and evaluation.

The analogous feature-origin gap is present: fixture features reference only label provenance. With that sole label source available at `2026-09-01T22:00+09:00` (after the first forecast cutoff), all six folds and feature associations are still produced using features declared available August 1. There is no declared feature source binding against which those dates can be checked. These models do not fit the features, but the feature-research output still consumes them.

Require explicit recognized roles and adequate source binding for every consumed label/feature (and prevent protocol-only references from standing in for observation provenance). Check declared field availability against the bound source availability. Missing binding should be a specific blocker; contradictory/future binding must fail. Add omitted/invalid/wrong-role and missing-feature-origin regressions. This concerns consistency of declared provenance, not authenticating its issuer or inventing a production trust mechanism.

## Important 2 — A capture event can occur in both training and held-out nights

`src/model_evaluation.py:214–218`.

The deduplication key is `(operational_night, event_id)`. This admits the same canonical capture event under two or more nights, violating the normative no-duplicate-event-IDs-across-rows requirement. It can count the same confirmed captures in training and held-out evaluation and create apparent independent evidence. Neither the schema nor the inference/report contract documents a per-night namespace exception.

Reproduction: replace the positive event ID on each of the fixture's three nights with `same-confirmed-event`. Evaluation produces six folds and candidate_generation PASS, although that event is reused across training/test boundaries.

Reject canonical event IDs repeated anywhere in the learning snapshot; conflicting night assignment must not manufacture new events. Retain the existing same-night collision test and add a cross-night train/test collision test.

## Important 3 — Truly unknown universe units cannot be represented without invented observation metadata

`src/model_evaluation.py:191–194, 219–220`; `schemas/model-learning.json` learningRow `label_available_at` property/requirements.

The validator unconditionally parses a label-availability timestamp and requires an audited observation quality value before differentiating the needs of observed versus unobserved units. An honest unknown forecast-universe row has no observed label to become available and may have quality UNKNOWN. Requiring every universe row while rejecting those attributes blocks the entire dataset or pressures its producer to invent label availability/observation quality.

Reproduction: take one held-out row and set `observed=false`, `label=null`, zero captures, no event IDs, `quality='UNKNOWN'`, `label_available_at=null`. It returns FAIL, zero folds, `availability timestamp must be an ISO string`. Supplying a dummy timestamp instead still returns BLOCKED, zero folds, for unaudited observation quality. The existing unknown-label test misses this because it retains the old observed row's timestamp and AUDITED_OBSERVED quality.

Permit genuinely unobserved units with unknown observation metadata/null label availability while retaining their required ex-ante universe/feature provenance. Keep them in inference/ranking and out of label fitting, associations and scored-label denominators. Continue requiring valid label availability and audited observation eligibility for observed rows. Align the schema and add a genuine unknown-row regression.

## Important 4 — Malformed LearningSnapshot root escapes the adapter's result contract

`src/model_evaluation.py:99–103, 533–539`.

The JSON root is used with `.get()` before an object-shape check. Valid JSON roots `[]`, `null` and `42` raise uncaught AttributeError, so `evaluate_models` returns none of its four canonical stage records or its specific invalid-evidence reason. The parent currently catches the exception and prevents aggregate success, but direct adapter callers and the stated Task 3 result contract are broken.

All three roots were reproduced. In contrast, a list-valued referenced universe/protocol and a null source-manifest element already return FAIL envelopes through caught TypeError. Validate root/nested envelope shapes before field access; add root-shape tests asserting all four stages and a concrete invalid-evidence status. Preserve missing-file/missing-contract BLOCKED handling as appropriate.

## What was verified and what remains outside this approval

The implementation provides real bounded computations and sensible conservative claims: observed-only labels, earlier-night training, separate individual/event recall, coordinate-based 250m aggregation, score-only families excluded from Brier, actual parameter-driven inference, immutable content-addressed REPLAY, explicit confirmation/production blockers and no ACCEPT_CANDIDATE path. Six selected existing tests passed: unknown label exclusion, held-out-label independence of fitted parameters, exact 250m coordinates, individual versus event recall, common candidate fold eligibility, and positive research comparison remaining ineligible for promotion. An initial invocation from the repository root could not import the test module; rerunning from `tests/` passed all six. Adversarial probe outcomes are recorded above. The reported 26-model/130-total suite is implementer/parent evidence, not a suite repeated by this reviewer.

`ccf18c5` is justified fixture isolation: it explicitly mocks absent adapters and asserts model-adapter discovery, preserving the original orchestration regression after the real model module became available. It does not weaken a scientific or governance gate.

Future confirmation consumption locking, feature-aware retraining, formal time targets, optional requested product executors and trusted production persistence remain explicit integration requirements. No production/scientific/whole-Master completion or remote Actions validation is granted by this review.

## Narrow addendum — Important 5: Stage1 denominator coverage is not established

Assessment requested by the parent after the initial four-finding review. This is a separate bounded-contract finding, not a request to implement the later full data builder.

`src/model_evaluation.py:179–181, 245–246, 325–342` at reviewed commit `1277d91`; normative spec `docs/specs/master-goal-1642.md:106`.

Every learning row must refer to an existing forecast-universe row. `_metrics` sums `capture_count` only over observed learning rows in that universe and labels this `confirmed_individuals` / Stage1 `individual_recall`. No independent outcome ledger or coverage check establishes that these rows contain every confirmed capture in the evaluation domain/night. An outcome outside the candidate universe cannot be represented as an additional learning row; omitting it silently removes a miss from the denominator. For example, three included captures in Top10 and three excluded captures outside the universe yield the reported restricted recall 1.0 rather than full recall 0.5.

The existing NOT_VALIDATED/research-diagnostic qualifiers correctly withhold production acceptance, but do not adequately qualify this denominator: the Stage1 metric still emits `gate_outcome: PASS` for restricted recall >=0.90 and calls the included count `confirmed_individuals`. The normative primary recall is over confirmed individuals whose 1km cell occurs in Top10; the forecast universe must remain ex ante and must not be expanded from held-out captures to hide this issue.

A minimal bounded fix is sufficient: explicitly name and document this as recall restricted to observed units in the supplied forecast universe, record missing full-capture denominator coverage, and leave the formal Stage1 gate NOT_EVALUATED until a hash-bound complete outcome ledger/coverage contract is available. Later builder/evaluator integration must retain confirmed outcomes outside the candidate universe as denominator misses within the approved evaluation domain and time scope. Add a regression that lack of full outcome coverage cannot produce Stage1 gate PASS. No immediate full builder implementation is required.
