# Source-consistent calibration parent v1

Development software only. This adds an explicit research request-v5 connection
to the existing pure feature diagnostic, using one existing configured HB-A1
candidate and one operational night. It fits no calibration model, chooses no
winner and grants no scientific, confirmation, issuance or production authority.
Existing source-v2/preparation-v3, HB-A2 and retrained ablation computations are
not missing; their additional parent connections are separate work.

## Request and source profile

`habu-research-model-request-v5` has exactly the existing v4 fields plus a
nonnull `calibration_manifest` byte reference. `stage1_manifest` must be null.
The existing source-v1/cfg-v2 three-slot set must contain HB-A1. v1-v4/default
behavior, source/qualification rules and pure numerical outputs remain unchanged.

The development profile has exactly seven fields:

| Field | Contract |
| --- | --- |
| schema_version | habu-feature-calibration-source-v1 |
| purpose | DEVELOPMENT_EVALUATION_ONLY |
| evaluation_as_of | aware post-forecast assessment time, not a predictor/fit cutoff |
| candidate_id | HB-A1 |
| protocol | existing `{ref, readiness, usable_at}` binding to the unchanged pure protocol |
| observation_manifest | existing strict G0 TRAIN_ONLY source-closure byte reference |
| observation_selector | original `heldout_night, fit_cutoff, forecast_cutoff, exposed_nights` replay arguments |

Refs contain exact path/raw SHA256/size. Existing local path, reserved/reveal
namespace and source role checks apply. A selection-only JSON or caller-written
prediction array cannot replace source replay. Hash/readiness declarations prove
consistency, not historical receipt, origin, prereveal freeze or loaded runtime
authentication. No profile readiness or authenticated timestamp is invented.

The parent performs its unchanged TRAIN selection, strict full forecast load and
one configured three-candidate native preparation before opening observation
corpus/outcome source payloads. Declared protocol/profile/source-manifest metadata
may be preflighted first. Numerical controls are validated before observation
payloads. Native model/config/recipe/TRAIN/fold hashes must match actual preparation.
Actual HB-A1 probabilities are checked against the existing inference primitive;
no second fit or candidate is introduced.

## Separate actual model and later observations

An observation selector envelope is an **evaluation observation identity** under
the existing [pure contract](feature-candidate-diagnostics.md), not the forecasting
model's TRAIN. Its independently declared original source closure and replay
arguments are reproduced unchanged through `select_g0_training_rows`. No later
boundary or observation label enters the fitter. This adapter never fabricates
the original declaration or chooses a rescue cutoff.

For example, the actual model fits at Oct27 18:00 for the Oct28 operational night
and predicts at Oct28 18:00. A positive at Oct28 19:00 and a negative at19:10 may
be qualified by Oct29 09:00. An original retrospective observation selector with
heldout Oct30 and fit/forecast boundary Oct29 10:00 can reproduce those observations
for assessment Oct29 11:00. Oct30 is that selector's exclusion limit; it does not
assert an Oct30 model or forecast existed. The calibration fold retains the actual
Oct27 fit, Oct28 forecast and actual TRAIN/model hashes.

The complete observation corpus, including rejected rows, must describe only the
actual evaluation night. Its existing role/readiness/physical-validity checks
remain enforced. Negatives require separate source-bound independent active Habu
search and complete owner-outcome scope/basis receipts; passage, slowness or other
fauna supply no zero. The adapter never requalifies real sources.

Every accepted observation joins exactly once by its physical100m/600s unit to
the original complete forecast with matching feature definition and values. No
observed mask changes forecast support. Outside-universe observations block
metrics rather than disappear. TRAIN/evaluation event or physical-unit overlap
is invalid. UNKNOWN stays excluded with its original reasons.

One night/two labels remains selector NEED_MORE_DATA. Existing pure behavior can
describe its known labels while calibration is NOT_VALIDATED, adequacy is
NOT_ASSESSED and model selection remains NEED_MORE_DATA. Descriptive Brier is
neither an island occurrence-probability validation nor the formal100m±10min KPI.

## Output and failures

A completed invocation adds `calibration` with the verbatim pure diagnostic and a
source receipt binding original selector arguments/refs, actual TRAIN/fold/model/
prediction/config/forecast identity, all consumed original byte refs and shared
read totals. The envelope resolves only this invocation's
`SOURCE_BOUND_CALIBRATION_PARENT_DISPATCH_NOT_IMPLEMENTED` capability tag.
The nested pure blocker list is retained exactly. Ablation dispatch, trusted
campaign/prereveal/confirmation and scientific support/tolerance gates remain open.

Missing original inputs or an empty/ineligible cohort yield NEED_MORE_DATA.
A completed selector's empty/outside-cohort rejections remain in
`calibration_observation_blockers` without a metric or REPLAY. Known schema/hash/
role/model/fold contradictions remain invalid even when data are insufficient.
Capacity/deadline failures are RUNTIME_BLOCKED. No partial candidates/calibration/
REPLAY are published on failure.

One original `ProspectiveReadContext` covers all reads/reopens, preparation,
calibration, hashes and final original-ref rescans, with its unchanged cumulative
<=300s/byte allowance. No refill, reset or second context is allowed. Profile is
<=256KiB, protocol<=64KiB, corpus<=16MiB/20,000 rows, local JSON depth<=12/nodes<=2M;
existing stricter G0 graph/reader/pure limits also apply. Callback FIRST identity
is preserved through the actual configured-preparation normalization seam,
including falsey caller exceptions. Guards are cooperative, not hard preemption
or hostile-filesystem atomic confinement.

All earlier TRAIN/config/forecast and observation refs are rechecked before the
existing owned content-addressed REPLAY publication. Later stage-construction
source/model mutation or actual expiry cannot release stale calibration metrics.
Outputs remain development exposure, never untouched sealed confirmation.

## Verification boundary

The additive test module uses explicit synthetic TemporaryDirectory data and the
actual native configured fit/predict, original G0 selector and unchanged pure
calculation. It covers post-night labels, direct numerical parity, unchanged
TRAIN/forecast, source/negative/UNKNOWN conflicts, no subset scoring, real caller
FIRST, resource/deadline and late mutation behavior. It introduces no real
captures, GPX, provider calls or scientific evidence.

Pre-edit v1-v4 whole results, REPLAY bytes and account/read ledgers are sealed
privately and compared after implementation; those paths perform no calibration
reads. Windows platform gaps remain disclosed; genuine Linux contracts and normal
exact/fresh CI still belong to integration. No STATE, cycle, policy, raw source,
dependency, trust service or production registry is changed by this slice.

Local author verification on the existing pinned Windows numeric runtime:
35 new tests PASS without skips (53.703s); 35 existing model-adapter tests PASS;
223 other affected existing methods give220 PASS/3 existing platform skips
(two POSIX master/fcntl integrations and one POSIX corpus-symlink regression).
The initial verification harness used one nonexistent module name; its load
ERROR is retained separately and the correct model-adapter module was actually
run. It is not counted as a product PASS. Pre-edit/post-edit v1-v4 whole output,
REPLAY and read/account ledger capture is byte-identical800210B with SHA256
`85f0e375829979c8e89cffee82ecb9a27a1edbd51fa5f2ac23f398ac564c5bc3`.
Source review, refreshed native integration freeze and own Ubuntu exact/fresh CI
remain separate requirements; no full-suite, science or production PASS is claimed.
