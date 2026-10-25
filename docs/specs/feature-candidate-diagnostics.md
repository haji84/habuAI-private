# Feature candidate development diagnostics v1

This additive pure module computes descriptive reliability bins, Brier and
log-loss on a complete supplied development observed cohort. It does not fit,
recalibrate, choose, register or promote a model. The three existing candidate
configurations and all existing numerical learners remain unchanged.

`model_evaluation.py` already computes descriptive fixed five-bin calibration
inside legacy evaluation, omitting empty bins. Its numerical behavior and fields
remain unchanged. This interface adds content-bound source-selected unit coverage,
explicit fold declarations, fixed configurable edges with empty-bin nulls,
log-loss, equal-night summaries and a shared cooperative budget.

## Scope and remaining implementation gaps

`prospective_candidate_model.train_candidate` requires the exact seven feature
names and fixes the scaler/coefficient dimensions and 320 optimization epochs.
The legacy public trainer retains its all-seven-feature recipe; the standalone
companion uses the shared masked numeric core and cooperative callback.
The diagnostic module itself does not fit or wrap that learner. The separately
reviewed [standalone HB-A1 implementation](hba1-feature-candidate.md) now supplies
the shared numeric core, column masks and actual same-row retrained ablations.
Zeroing a column at prediction is not an ablation. Remaining result blockers name
the three-slot HB-A1 parent dispatch, retrained-ablation parent dispatch and
source-bound calibration parent dispatch. Those connections remain unimplemented;
the computation must not be reported as missing. No hidden fourth promotion
candidate or scientific calibration approval is introduced.

## Pure API and exact input contract

```python
describe_feature_candidate_development(
    protocol, observed_selection, predictions, *,
    expected_protocol_sha256, budget_seconds=30, check=None)
```

All arguments are in-memory JSON values. No file, network, sealed-label reader,
learner, predictor, parent dispatcher or registry is called. The expected protocol
hash is required and binds canonical supplied content, not the time it was frozen.

The protocol has exactly these fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | `habu-feature-candidate-development-protocol-v1` |
| `phase` | Only `DEVELOPMENT` |
| `target` | `OWNER_CAPTURE_BINARY_ON_AUDITED_OBSERVED_100M_600S_UNITS` |
| `evaluation_selection_sha256` | Exact observed selector identity |
| `predictions_sha256` | Canonical digest of the complete supplied prediction list, in supplied order |
| `bin_edges` | 2–21 finite nonboolean strictly increasing numbers, first exactly 0 and last exactly 1 |
| `log_loss_clip` | Fixed epsilon in `[1e-15, 0.5)` |
| `folds` | One sorted declaration for each observed development night |

Each fold contains exactly `night`, `model_sha256`,
`training_selection_sha256`, `training_cutoff`, and `train_nights`. Train nights
are nonempty, sorted, unique, valid `YYYY-MM-DD` JST operational-night identifiers.
Each train night starts at 07:00 JST and must satisfy
`train_night_start < training_cutoff < evaluation_night_start`.
An entire training night need not have ended at cutoff: partial-night eligibility
and actual row/feature/label readiness belong to the authentic training dependency.
The API does not consume those training rows and does not attest their availability.
Repeated use of one frozen model on multiple later development nights is legal;
the same model hash must carry identical training declarations. An evaluation
selection hash cannot also be its declared training selection hash.

The observed envelope is checked with existing `research_selection.validate_selection`.
Its accepted binary labels, canonical event uniqueness, physical units, source
hash identity, unknown rejection and selector consistency rules are preserved.
It is an **evaluation observation identity**, not the model's training fit input.
This check cannot restore per-row source/readiness receipts discarded by the
selector. Source qualification, actual measurement, complete outcome scope,
training-model bindings and real prediction computation remain caller dependencies.

Each prediction contains exactly `row_id`, `night`, `cell_x`, `cell_y`,
`window_start_jst`, `probability`, `model_sha256`, and `training_selection_sha256`.
It must match one accepted observed row and its fold. The prediction list must
cover **all** accepted rows exactly once: no subset, missing, extra or duplicate
unit is scored. Window comparison normalizes aware timestamps to UTC. Probability
must be finite, nonboolean and in `[0,1]`. Unknown labels cannot be imputed.

## Computation and interpretation

For each operational night, Brier is the mean of `(p-y)^2`, using the original
probability. Log-loss uses `p_clip = min(1-epsilon,max(epsilon,p))` and
`-y*log(p_clip)-(1-y)*log1p(-p_clip)`. The primary descriptive summaries are
equal-night means of those per-night values. Separately named pooled unit metrics
weight each observed unit equally; they must not be confused with equal-night means.

Reliability bins pool units and expose count, mean original probability and observed
fraction. Every bin is `[lower,upper)` except the final `[lower,1]`; an internal
edge belongs to the bin on its right, 0 to the first and 1 to the final bin.
Empty bins have count 0 and null mean/observed fraction. No smoothing, calibration
fit, confidence claim, recalibration or probability correction is performed.

Known accepted labels may be described even if the selector reports
`NEED_MORE_DATA`; that original status and its blockers are retained. Its binary
training thresholds are not calibration adequacy rules. A zero-row envelope returns
`NEED_MORE_DATA`, empty per-night results and null averages. Neither path grants
statistical sufficiency: `statistical_adequacy=NOT_ASSESSED` and
`calibration_status=NOT_VALIDATED` always.

## Authority and confirmation boundary

The output schema is `habu-feature-candidate-development-diagnostic-v1`, with
`DESCRIPTIVE_DEVELOPMENT_DIAGNOSTIC_ONLY` for nonempty cohorts. It has no serialized
model, coefficients, candidate list, ranks, selection score or promotion decision.
Existing strict learner model validators reject this shape. Every result has
`fit_authorized`, `selection_authorized`, `promotion_authorized`,
`scientific_execution_authorized`, `official_issuance_authorized` and
`production_authorized` set to false.

`source_authentication=CALLER_DEPENDENCY_REQUIRED`,
`source_authenticity=NOT_ATTESTED`, `preregistration=CALLER_DEPENDENCY_REQUIRED`
and `model_training_binding=CALLER_ASSERTED_NOT_ATTESTED` apply even to a complete
fixture. A caller-provided SHA or DEVELOPMENT declaration does not authenticate
the source/model or prove that confirmation labels were not already revealed.
Trusted pre-reveal protocol freezing, label-consumption tracking and source/model
authentication require the parent controller. The API accepts no confirmation
mode or trust-flag shortcut. Results cannot authorize selection or reselection,
including after reveal. No confirmation gate or implementation blocker is removed.

These are observational descriptions on selected observed units, not island-wide
calibration, causal effects, biological presence, detection correction or count
models. Empty/unobserved units never become negatives. Unit dependence, geographic
quality, observation-selection bias and calibration tolerance/support remain
unresolved upstream scientific issues.

## Bounded execution and digest semantics

Combined protocol + observed envelope + predictions are bounded to 16 MiB canonical
UTF-8 JSON **before** creating owned Python copies; complexity is capped at
2,000,000 nodes, depth 12, 4096-character values, 512-character keys and 1024-bit
integers. At most 20,000 observed/predicted rows, 64 evaluation folds, 64 declared
training nights per fold and 20 bins are allowed. Overflow is explicit
`DiagnosticCapacityBlocked` (`CAPACITY_BLOCKED`), not invalid scientific evidence
or silent truncation. Malformed/conflicting contracts raise `ValueError`.

One monotonic deadline covers preflight, snapshot encoding/parsing, validation,
hashing, accumulation and final seal. Default budget is 30 seconds; it may be
set up to 300. A supplied `check` callback shares the parent's remaining budget
and its exception propagates. New loops and encoder chunks check cooperatively.
The existing selector validator has no callback parameter and is bracketed by
checks; bounded JSON parsing, sorting and numeric aggregation are likewise
cooperative boundaries, not hard OS/process preemption. Expiry raises
`TimeoutError` (`RUNTIME_BLOCKED`), returning no partial success.

Canonical digests use sorted object keys, compact separators, UTF-8,
`ensure_ascii=False`, and `allow_nan=False`. `diagnostic_sha256` covers the entire
result except itself. A final deadline/callback check occurs **after** sealing and
immediately before return. All calculations use owned snapshots; input mutation
after snapshot does not change the result, and result lists do not alias inputs.

## Synthetic verification

Tests first failed because the diagnostic module did not exist. The synthetic
suite checks exact Brier/log-loss, endpoint placement, empty bins, unequal-night
weighting, single-class/empty cohorts, all-unit binding, timezone aliases, strict
fold boundaries, fixed-model reuse, digest mismatches, UNKNOWN/NaN/bool rejection,
selector duplicate rules, no I/O/fitting/ranking, owned snapshots, capacity and
deadline rejection after the final digest. No actual CSV, capture, GPX or
confirmation data are consumed.
