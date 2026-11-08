# Constant Poisson diagnostic v1

Design against main `9c06f3d8b059439991f444dee8c7b30f35b2b6bc`, for root review
before implementation. The new standalone pure module is proposed as
`src/models/constant_poisson_diagnostic.py`. Existing count feasibility, selector,
G0 planned-effort restrictions, historical M0-M3 definitions and registries are
unchanged. This is a fitted declared-cohort count baseline, not a new source
forecast API, target generator, parent integration or scientific qualification.

## Interfaces and scope

```python
fit_constant_poisson(selection, count_projection=None, effort_projection=None, *,
                     budget_seconds=30, check=None)

validate_constant_poisson_model(model, *, budget_seconds=30, check=None)

evaluate_constant_poisson_scenario(model, active_search_seconds, *, count=None,
                                   budget_seconds=30, check=None)
```

All interfaces accept/return JSON-compatible values only and perform no file,
network, source parsing, fitting of another model or publication operation.
The validator returns a detached checked model, not a boolean or a refit.
Serialization is ordinary safe JSON; no pickle, executable model object or
third-party numerical backend is used.

The count target is exactly existing count_feasibility.TARGET:
`OWNER_CAPTURED_HABU_INDIVIDUALS_DURING_MEASURED_ACTIVE_SEARCH`.
It is neither capture events nor abundance, detection probability, unmeasured
encounters or all Habu activity. One capture event with two canonical individuals
contributes two. A complete explicitly observed zero contributes zero; UNKNOWN
does not. The model conditions on the same declared owner/observer/method.

## Existing admission gate and whole cohort

Fit owns one bounded snapshot of selection/count/effort inputs, then calls
`assess_count_feasibility` exactly once on that snapshot under its remaining
deadline and guard. Reuse all existing row/unit/source identity, projection
hash, four-stage ancestral chronology, complete-outcome scope, measured active
interval, event/individual and cross-cell observer-overlap checks. Do not clone
or loosen that gate or introduce another row contract.

The cohort is **every selection.accepted row**, each covered once by both
projections. Rejected rows are not converted to zero or effort. Do not drop
incomplete rows, select positives, fill counts from binary labels/event IDs,
normalize by GPX points or fit a complete-looking subset. All supplied known
contradictions are checked even when another projection is missing.

If feasibility is NEED_MORE_DATA, return no model and the exact sealed assessment.
This includes empty accepted cohorts, any missing/UNKNOWN count or complete
scope, missing individual ledger, missing measured effort or any zero-effort
row. Do not calculate a partial rate. Invalid inputs raise; capacity/timeout
never return a partial model.

Fit is permitted numerically only when the existing assessment is
DECLARED_CONSISTENCY_ONLY with a nonempty whole cohort. The selector's binary
class/night readiness is not a Poisson adequacy test: a completely declared
positive-only or all-zero cohort may still produce a diagnostic model even
when selector status is NEED_MORE_DATA. No new minimum support claim is implied.
All statistical adequacy and real scientific qualification remain unassessed.

## Fixed analytic model and arithmetic

For each admitted row, let k_i be its explicit nonnegative individual count and
t_i its explicit positive measured active-search seconds. Freeze one homogeneous
independent Poisson likelihood conditional on those declared exposures:

```text
K_i | t_i ~ Poisson(lambda * t_i)
S = integer sum(k_i)
E = math.fsum(t_i in canonical row_id order)
lambda_hat = S / E
```

There is no prior, smoothing, regularizer, optimizer, seed, tuning, dispersion
fit, feature coefficient or selected-row weighting. Sort model training units
by Unicode row_id order before all floating aggregation. Counts use exact integer
sum. Seconds and rate are serialized as floats; lambda_hat is exactly0.0 when
S=0 and E>0, a valid boundary MLE without a positive floor or pseudocount.

For conditional mean mu=lambda*t and integer k, use the common log-mass core:
`k*math.log(mu) - mu - math.lgamma(k+1)` when mu>0. Training log likelihood is
math.fsum of those terms in the same row order. For mu=0, k=0 has log mass0.0;
k>0 has zero mass, not a finite log mass. A valid fitted training cohort cannot
contain the latter case. All-zero training log likelihood is exactly0.0.

Reject nonfinite E/rate/means/log likelihood, division overflow, or a positive
rate/exposure product that rounds to zero, with ValueError containing
NUMERIC_BLOCKED. This is numerical representation failure, not missing data;
do not clip, floor, impute, truncate or release a partial fit. Retain existing
effort validation rather than inventing a new minimum measured duration.

The feasibility summary's unchanged ordinary seconds sum is not replaced or
resealed. The model's fsum statistic is separately defined by this recipe;
the two aggregates may differ in final floating bits.

## Recipe, fitted model and checked JSON

H means canonical UTF-8 JSON SHA256: sorted keys, compact separators, Unicode
retained, nonfinite values forbidden. Every self-hash excludes only its own
hash field; full-input digests include supplied self-hash fields. Hash equality
is declared content integrity, not source truth or historical fit attestation.

Recipe has exactly:
`{schema_version, family, target, count_units, exposure_units, estimator,
row_order, zero_count_rule}`. Values are respectively
`habu-constant-poisson-recipe-v1`, `POISSON`, the fixed target, `individuals`,
`active_search_seconds`, `SUM_COUNT_OVER_FSUM_SECONDS`, `ROW_ID_ASCENDING`,
`EXACT_ZERO_RATE_BOUNDARY`. Each model contains these exact fixed bytes and
recipe_sha256=H(recipe); caller mutation or a rehashed alternate recipe rejects.

The model has exactly these fields:

```text
schema_version, phase, target, recipe, recipe_sha256, fit_cutoff, heldout_night,
owner_id, observer_id, method_version, input_digests, lineage, training_units,
cohort_sha256, sufficient_statistics, parameters,
source_authenticity, source_authentication, statistical_adequacy,
fit_authorized, scientific_execution_authorized, official_issuance_authorized,
confirmation_authorized, selection_authorized, production_authorized, model_sha256
```

schema_version=`habu-constant-poisson-model-v1`; phase=`DEVELOPMENT`.
Copy fit_cutoff/heldout_night from the admitted selection and owner/observer/
method from the matching admitted projection headers.

input_digests is exactly `{selection, count_projection, effort_projection}`:
H of each complete owned input, all nonnull for a model. lineage is exactly
`{selection_sha256, corpus_sha256, count_projection_sha256,
effort_projection_sha256, feasibility_assessment_sha256}`, preserving each
existing identity/self-hash without changing its scope.

Each training_units entry is exactly the existing five UNIT fields
`{row_id, night, cell_x, cell_y, window_start_jst}` plus
`{count, active_search_seconds}`. Copy physical identity from the selection,
count from its joined count row and seconds as a float from its joined effort
row. Store all rows in row_id order. No raw source content or new observation
label is exported. cohort_sha256=H of exactly
`{target, owner_id, observer_id, method_version, fit_cutoff, heldout_night,
training_units}`.

sufficient_statistics is exactly `{rows, nights, total_individuals,
total_active_search_seconds}`: counts are exact ints; seconds is the canonical
fsum float. parameters is exactly `{lambda_per_active_search_second}` with
a nonnegative finite float. model_sha256=H(all model fields except itself).

The validator bounds/owns the entire JSON model, enforces exact schemas, fixed
recipe/flags and typed hashes, unique row IDs/physical cell-window identities,
aware aligned night/window chronology, earlier training nights and window<fit
cutoff<heldout-night07:00. Each stored count is an exact int in [0,100000]; its
cohort total is <=100000. Each stored exposure is a finite float in (0,600];
retain the selector's existing text, cell and timestamp bounds. It recomputes
cohort digest, all sufficient statistics and rate from the stored table. Compare computed numeric
fields with exact canonical typed representations, including zero sign/type;
no rounding tolerance repairs a changed serialized parameter. Unknown fields,
bool counts/seconds/rates, rehashed inconsistent totals/rate/cohort and bad
dimensions reject. Final model self-hash and checked export must agree.

Do not cache log, lgamma, training likelihood or runtime platform values in the
model. The checked model's identity depends on the core cohort/rate recipe,
not a portable promise about libm final bits. Likelihoods are computed afresh
as diagnostics on the actual runtime; full fit/scenario receipts need not be
byte-identical across Windows/Ubuntu. No cross-libm whole-artifact golden,
platform hash allowlist or regenerated expected hash is permitted.

The checked model cannot re-attest discarded source scopes, exposure history or
original input hashes from this compact table. A coherently reconstructed new
model is a new declaration, not a cryptographic proof of a historical fit.
Stored input/assessment digests remain caller/source dependencies.

## Fit result

The fit result has exactly:

```text
schema_version, status, phase, target, recipe_sha256, feasibility, model,
input_digests, training_log_likelihood, source_authenticity, source_authentication, statistical_adequacy,
fit_authorized, scientific_execution_authorized, official_issuance_authorized,
confirmation_authorized, selection_authorized, production_authorized, receipt_sha256
```

schema_version=`habu-constant-poisson-fit-v1`; phase=`DEVELOPMENT`.
status is NEED_MORE_DATA with model=null, or DECLARED_COHORT_FITTED with a checked
model. feasibility is the exact sealed assessment; never mutate its fields or
reseal it to grant fit permission. input_digests hashes complete supplied owned
inputs; missing count/effort projections have null digests. training_log_likelihood
is null for NEED, otherwise the finite actual-runtime training diagnostic above;
it is not a held-out score, a cached model parameter or a portable bitwise oracle.
receipt_sha256 seals
the complete result excluding only itself.

## Scalar conditional scenario only

The scenario function validates the model, then accepts only one explicit
non-bool finite numeric active_search_seconds in [0,12000000] (the existing
20000-row by600-second engineering ceiling). This scalar is caller supplied
counterfactual exposure, not measured or ex-ante planned future effort. There
are no futureRows, dates, locations, source refs or automatic exposure estimates.
count is null or an exact nonnegative integer<=100000, a numerical scenario
count rather than an authenticated observation or held-out evaluation ledger.

Return mu=lambda*seconds, probability_zero=math.exp(-mu), and, when count is
supplied, its conditional Poisson log mass and probability. Do not return a
rounded count, simulated capture, forecast interval, route or observed accuracy.
Numerical representation failures follow NUMERIC_BLOCKED above.

The scenario result has exactly:

```text
schema_version, status, target, model_sha256, scenario_active_search_seconds,
scenario_count, conditional_mean, probability_zero, log_probability, probability,
likelihood_status, source_authenticity, source_authentication, statistical_adequacy,
fit_authorized, scientific_execution_authorized, official_issuance_authorized,
confirmation_authorized, selection_authorized, production_authorized, receipt_sha256
```

schema_version=`habu-constant-poisson-scenario-v1`; status=`SCENARIO_ONLY`.
Normalize scenario seconds to float. likelihood_status is NOT_REQUESTED with
both probability/log_probability null when count is null; ZERO_MASS with
probability0.0/log_probability=null when mu=0 and count>0; otherwise FINITE_LOG_MASS
with finite log_probability<=0 and probability=math.exp(log_probability).
For mu=0/count=0 return log_probability0.0/probability1.0. Never encode Infinity,
NaN or -Infinity. A finite log mass may exponentiate to0.0 through underflow;
this is distinct from the structural ZERO_MASS case and is not clipped.
probability_zero/probability must be finite in [0,1]. Hash the exact result.

## Limits, authority and required evidence

Use one absolute deadline at each public API entry: finite non-bool
0<budget_seconds<=30; optional check is callable. Child feasibility/model
validation receives only remaining time and the same guard. Preserve caller
exception identity, check controlled copy/validation/aggregation/math/hash loops
and immediately before/after final seals. Do not reset allowances between stages
or return after expiry. Sorting/standard-library arithmetic are cooperative,
not hard-preemptive guarantees.

Retain16MiB combined input/output JSON,2M nodes/depth12, existing string/key/integer
limits,20000 rows/events,100000 individuals,16384 source nodes/32768 edges,
depth32 and1M ancestry memberships. Check width/count caps before growth/copy;
use bounded streaming encoding/hashing, no unbounded pre-cap dumps. Map named
capacity failures to a ValueError subclass containing CAPACITY_BLOCKED; timeout
raises TimeoutError. Do not normalize capacity/numerical failures into NEED.

Every result/model retains source_authenticity=NOT_ATTESTED,
source_authentication=CALLER_DEPENDENCY_REQUIRED, statistical_adequacy=NOT_ASSESSED
and all six listed authorization fields exactly false. A numerical diagnostic
fit does not authorize a real scientific fit. Constant-rate independence,
homogeneity, ascertainment and generalization from the selected cohort are not
established. G0 planned_effort remains CAPABILITY_BLOCKED; this module adds no
public source forecast, registry, parent, provider, permission or legacy M3 change.

Required RED and independent controls:

- Whole accepted cohort admission: explicit two-individual events, complete zero,
  all-zero boundary and positive-only cohorts; missing/UNKNOWN/effort0 returns
  no model; malformed-plus-missing and duplicate/overlapping evidence reject.
- True analytic fit: six fixture individuals/1800seconds gives rate1/300;
  each300second mean is1, training log likelihood=-6-3*log(2). Compare fixed
  alternative rates to verify the likelihood maximum, not only copied totals.
- Checked JSON round trip, exact recipe/cohort/input hashes and deterministic
  repeated input; rehashed rate/totals/cohort/flags/schema tampering rejects.
  Canonical row aggregation is deterministic; changed input/provenance hashes
  may change model identity even when fitted numbers agree.
- Likelihood tests use independent analytic closed cases with explicit justified
  numerical tolerances, not cross-platform whole-receipt hashes. Models contain
  no cached likelihood/lgamma value; same-runtime repetition remains exact.
- Scenario scalar controls: Poisson mean1 gives p0=exp(-1), count2 gives
  log mass=-1-log(2); zero rate/exposure and impossible positive count, finite
  probability underflow, nonfinite/overflow/positive-product-underflow and bools.
- Caps before copy, no partial subset, caller mutation ownership, exception
  identity, shared remaining deadline and expiry during/after model/receipt seals.
- Existing count/selection/G0 tests unchanged; no filesystem/network/pickle,
  future-effort inference, actual data fit, source qualification or forecast claim.

Implementation is limited to new model/test/review files after root approves
this spec. Real qualified TRAIN currently remains0; synthetic arithmetic and
JSON mechanics cannot close data, confirmation or production gates.
