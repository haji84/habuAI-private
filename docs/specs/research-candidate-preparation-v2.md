# Explicit three-slot research candidate configuration v2

This additive pure interface prepares a configured development candidate set.
It does not compare models, choose a winner, authenticate source/code bytes,
consume confirmation, change the parent adapter, extend Stage1 v1, or activate
production. Historical M0–M3 and every v1 function/constant remain unchanged.

## API and exact configuration

```python
prepare_research_candidates_v2(
    selection, forecast_rows, *, candidate_config, expected_config_sha256,
    cutoff_time, joined_universe_sha256, feature_definition_sha256,
    budget_seconds=30, check=None)
```

The exact config fields are:

| Field | Meaning |
| --- | --- |
| `schema_version` | `habu-research-candidate-config-v2` |
| `mode` | Only `DEVELOPMENT_ONLY` |
| `candidate_ids` | Ordered list: uniform first, then exactly two unique IDs from HB-A0/HB-B1/HB-A1 |
| `hba1_recipe` | Full seven-feature fixed HB-A1 recipe when selected; otherwise null |
| `feature_definition_sha256` | Registered strict definition identity supplied by the caller |

The three possible sets are uniform/A0/B1, uniform/A0/A1, and uniform/B1/A1.
The configured execution order of the final two slots is content-bound; it is
not a learned preference. There is no fourth slot, alias, silent replacement,
automatic fallback or extra ablation candidate. Unknown fields, trust flags,
confirmation modes, duplicate IDs and absence of uniform are rejected.

HB-A1 uses the existing `habu-hba1-fixed-logistic-recipe-v1`, validated by the
standalone module, with all seven mask entries true. An ablated feature recipe
is diagnostic and cannot enter this full-recipe slot. Its implementation SHA map
has the same exact core/model paths as the standalone contract.

The expected config hash binds its canonical contents. The supplied strict
feature-definition SHA must equal the config field. It is distinct from a legacy
feature-name digest, and neither digest authenticates actual source bytes here.

## One common cohort and complete output

Combined inputs are bounded and copied before any model runs. The existing
selector validator checks the exact TRAIN-only envelope; the existing future
validator checks every supplied joined row, feature/source reference, cutoff,
physical cell and aware ten-minute window. A valid insufficient selection still
undergoes complete future validation, so leaking or contradictory future data
cannot hide behind an insufficiency result.

All selected models receive the same owned TRAIN selection and original complete
joined future snapshot. Each candidate wrapper binds the selection SHA, ordered
TRAIN row-ID digest, full accepted-row digest, all raw feature-row digest,
strict definition SHA, config SHA and whole joined-universe SHA. The receipt also
binds held-out night, fit cutoff and forecast cutoff. Output rows must exactly
cover that full universe once, with unchanged night/window/cell identities.

Uniform retains its existing Beta(1,1) formula. HB-A0 retains its existing area
probabilities. HB-B1 retains its native hierarchical diagnostic rank scores and
conditional ranks; they are not relabeled as probabilities. HB-A1 calls the
reviewed standalone fit/predict functions and shared legacy numeric core.
No optimizer, rank aggregation or historical model definition is duplicated.

For a requested HB-A1, a valid common input with another feature schema returns
`NEED_MORE_DATA` with `HB_A1_REQUIRES_EXACT_SEVEN_RAW_FEATURE_SCHEMA`. It is not
filled, projected or imputed. Before that data-block decision, every supplied
known HB-A1 raw field is checked on every accepted TRAIN row and the complete
future set, including partial schemas and insufficient TRAIN support. Existing
legacy bounds remain humidity `[0,100]`, precipitation `[0,300]`, slope `[0,90)`,
road length `>0`, and wind/road proxy `[0,1]`; temperature and TPI require finite
values without additional invented physical bounds. A missing field remains a
data gap, while a supplied contradictory value raises `ValueError`. No missing
field is created just to run these checks. The full seven-feature schema also
retains the standalone learner's existing physical validation.
HB-A1 still needs five prior TRAIN nights, twenty rows and the selector's binary
class conditions. If any selected recipe lacks valid data, the whole set returns
`NEED_MORE_DATA`, `candidates=[]` and concrete blockers; another model is never
substituted. A valid late HB-A1 insufficiency receipt also clears the entire
returned set, including any already computed local candidates.

Each native model and prediction digest is checked. HB-A1 fit/model recipe, code
SHA assertions and all three TRAIN snapshot digests must match the config/common
inputs. Optional native candidate/TRAIN identity assertions may not contradict
the configured identity. Source/model consistency never means source authenticity.

The complete schema is `habu-research-candidates-prepared-v2`, with
`DIAGNOSTIC_CANDIDATES_PREPARED` or `NEED_MORE_DATA`, `candidate_config_sha256`,
ordered `candidate_ids`, common lineage fields, candidates/blockers, limitations
and `receipt_sha256`. There is no metric, winner, selection decision or promotion.

## Shared guard, capacity and ownership

One deadline covers the whole call: default 30 seconds, maximum 300. The optional
parent `check` is invoked by the same guard throughout snapshotting, preflight,
HB-A1 optimization/prediction, hashing and immediately before return. HB-A1
receives only remaining seconds plus that guard, so a nested call cannot extend
the outer or parent deadline. A real `ProspectiveReadContext.check` can be used;
pure preparation itself charges no source bytes because it opens no files.

Uniform already checks its row loop. Existing HB-A0/HB-B1 bounded APIs have no
callback parameter and are checked before/after; shared validators, bounded JSON
parse/sort/aggregations and legacy digest calls are likewise cooperative
boundaries. This is not a process-preemption or hard CPU deadline guarantee.
No returned candidates survive an expired final receipt hash/guard.

Limits are combined 16 MiB canonical UTF-8 inputs before Python owned copies,
2,000,000 JSON nodes, depth 12, 4096-character values, 512-character keys,
1024-bit integers, 20,000 selection rows including rejected summaries and
120,000 complete future rows. Final canonical output/hash is also bounded to
16 MiB. Effective capacity is the minimum of these limits, not a guarantee that
120,000 large seven-feature rows or three prediction artifacts fit. There is no
subsampling, truncation, partial-publication or independent-chunk rank concat.

Malformed/conflicting evidence raises `ValueError`; capacity raises
`ResearchCapacityBlocked`; own deadline raises `ResearchBudgetExhausted`.
Parent callback exceptions, including its `TimeoutError`, propagate. Canonical
seals use sorted keys, compact separators, UTF-8, no NaN and no own hash field.
The final guard runs after sealing for both success and insufficiency. Mutations
to caller objects after the snapshot cannot change computation or returned data.

## Authority and unimplemented integration

All results retain `source_authentication=CALLER_DEPENDENCY_REQUIRED`,
`source_authenticity=NOT_ATTESTED`, `scientific_status=NOT_VALIDATED`, and false
fit, scientific execution, selection, promotion, official issuance and production
activation authorization. `preregistration=CALLER_DEPENDENCY_REQUIRED` applies
even when all declared hashes agree. All-zero declared code hashes can be
internally consistent; they do not prove that those bytes ran. Actual model/core
source verification belongs to the separately reviewed source-bound parent loader.

A pure function has no trusted state across calls. Different config IDs cannot
legitimately reset a campaign's three-slot limit, consumed research/confirmation
cohort or cumulative 300-second/two-round budget. The required trusted campaign
budget/slot/exposure/freeze/consumption ledger is **not implemented** here. An
expected config hash or local trust flag cannot substitute for that authority.
No held-out outcome/evaluation/confirmation payload is accepted by this API;
its result never authorizes reselection after reveal.

The separately reviewed request v3 now loads config/code refs through the shared
actual-byte reader and binds them to the source profile/request/REPLAY and final
rescans. The pure Stage1 v2 evaluator also supports the exact configured registry.
The remaining integration blocker is
`CONFIGURED_STAGE1_SOURCE_PARENT_NOT_CONNECTED`: configured Stage1 source-v2
evaluation is not connected to the parent. These capability metadata changes
produce fresh content-bound receipts; existing historical artifacts stay intact.

Stage1 `habu-stage1-scores-v1` and its registry remain exactly uniform/A0/B1.
Request v3 can use the source-bound v1 Stage1 path only for that exact ordered
triplet. Every A1-containing or reordered set remains blocked before evaluation
payload reads, without reducing or reordering the configured set. Connecting
source-v2 evaluation to the parent requires separate review of exact configured
IDs/recipe/model/prediction lineage. Comparison, winner selection and trusted
independent pre-reveal freezing remain absent regardless of preparation success.

## Synthetic regression evidence

The first new tests failed because the v2 API did not exist. Tests freeze all five
v1 function bodies (combined SHA
`8a0350421d84a39c781fdc78eb3c0abb23c40f1fb91022759efea44837e111e8`)
and the full existing fixture receipt SHA
`a8c59d499d8fa8d132cbb05876469596c5c365755b05397f80ae06cc808184e0`.
They cover all three legal sets, all-or-none data blocks, typed/schema/digest
conflicts, whole row/source/cutoff coverage, native semantics and identity,
declared code consistency without file authentication, real parent context expiry
inside the optimizer, owned snapshots, combined caps before parse, no I/O and
expiry after final seals. No raw CSV, actual capture or confirmation evidence is used.
