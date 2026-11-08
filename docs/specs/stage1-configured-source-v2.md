# Configured source-bound Stage1 v2

This additive development API consumes an already prepared, explicit three-slot
candidate set. It does not connect a new parent request, fit models, register a
campaign, authenticate an issuer, select a winner, or authorize confirmation or
production. The existing parent request v3 continues to block nonlegacy Stage1
dispatch until a separate explicit integration is reviewed.

```python
evaluate_stage1_sources_v2(
    root, manifest_ref, forecast, prepared, *, candidate_config,
    expected_config_sha256, feature_definition_sha256, context
)
```

`context` must be the parent's existing `ProspectiveReadContext`. There is no new
source-read counter or absolute deadline. `forecast` is the complete strict G0
loader result, and `prepared` is the hash-bound
`habu-research-candidates-prepared-v2` output. The API owns one combined JSON
snapshot of config, forecast and prepared before reading the evaluation manifest.
The existing 16 MiB/2,000,000-node/depth-12 limits apply to the combined object;
forecast/prediction row caps and exactly three candidates are checked before copy.

## Candidate identity before evaluation reads

The existing candidate-config v2 validator requires uniform first and two unique
IDs from HB-A0, HB-B1 and HB-A1 in their explicit order. It requires the full
seven-feature HB-A1 recipe when selected. This API cannot reorder the candidates,
silently add a fourth, accept an ablation in a configured candidate slot, or mutate
the global v1 registry.

Config digest, strict feature-definition digest, ordered IDs, prepared receipt,
joined forecast digest, complete unit count, held-out night and fit chronology
must agree. Every candidate wrapper binds the same config, feature definition,
TRAIN selection, selected-row digest, row-ID digest and raw-feature-row digest.
The existing native candidate binder checks actual model and prediction digests,
all forecast row IDs, physical units, windows, night and cutoff. Native prediction
candidate/TRAIN assertions cannot contradict this binding.

HB-A0 and HB-B1 additionally pass their existing native serialized-model
validators before evaluation I/O. Actual native fit cutoff must equal the common
prepared fit cutoff for every candidate; native held-out nights must equal the
common night wherever the native schema contains that field. Uniform has no
separate native validator or held-out field: it must retain its exact existing
schema/recipe/research-only envelope, finite typed support and the exact fixed
Beta(1,1) probability implied by its counts. Its native training cutoff is bound
to the same common fit cutoff. Rehashing a future or different native fit cannot
be hidden behind an otherwise valid outer prepared receipt.

For HB-A1, the actual validated model's full recipe and recipe digest, prediction
recipe digest, TRAIN row identities and fit chronology must match the configured
recipe and prepared lineage. A stale hash or a rehashed conflicting claim fails
before any evaluation source is opened. Native authority assertions must remain
false. The model validator also preserves HB-A1's existing dimensions, finite
vectors, positive scales, numerical recipe and research-only status.

HB-B1 retains its existing native model recipe and its non-null recipe digest.
That digest and the recipe bytes are checked against the existing fixed native
recipe. Only the new configured-score
projection's `recipe_sha256` is null for non-A1 candidates; no native recipe is
erased. HB-B1 uses native `rank_score_diagnostic`. The other candidates use their
native `spatial_score`. All candidates use `statistics.mean` over the same complete
forecast units within each area, with no conversion to calibrated probabilities.

## Versioned source manifest and projections

`habu-stage1-source-contract-v2` has exactly the v1 thirteen fields plus
`candidate_config_sha256` and `feature_definition_sha256`. These must match the
explicit API arguments, owned config and actual prepared/forecast lineage before
any declared evaluation payload is read. A v1 manifest cannot silently downgrade
this API. Node, scope, coverage, CSV and reference schemas are unchanged.

The shared source implementation preserves all v1 safeguards: guarded snapshot
namespaces only; preflight every ancestor/reference before payload reads; ex-ante
full EPSG:32652 scope and horizon; typed readiness DAG; observational RAW/derived
causality at all four stages; whole supplied CSV validation; exact canonical
event-to-existing-individual links and counts; duplicate rejection; full-scope
coverage binding; and final rereading of every consumed source. UNKNOWN and
INCOMPLETE do not suppress known contradictions or pre-event lineage claims.

The owned projection calls `evaluate_full_ledger_stage1_v2`. Its scores header is
`habu-stage1-scores-v2`, with universe/config/feature-definition digests and exactly
the ordered three candidates. Each candidate includes its native model/prediction
digests, config digest and A1 recipe digest (null for others). Universe and ledger
remain their existing v1 schemas. Same-universe area Top10, individual denominator,
outside-universe FN, seed-0 2,000-draw paired-night bootstrap and numerical behavior
remain the existing pure implementation.

Null roots, unavailable referenced files, UNKNOWN or incomplete coverage yield
`NEED_MORE_DATA` with all Stage1 metrics empty. Supplied structural/hash/identity/
causal contradictions raise `ValueError`; exhausted shared resources raise the
existing capacity/timeout errors and release no result. No placeholder universe
or ledger is manufactured. All reads, hashes, projection loops, bootstrap, rescan
and final result sealing cooperate with the same parent check. Native binding
calls are bracketed by shared checks as well as guarded chunked content hashes.

## Receipt and limits of the claim

The result retains pure v2 config/feature/candidate lineage and adds source
contract v2, the prepared receipt digest, guarded consumed references/digests,
projection digests, missing-input list and cumulative actual-read bytes. Source
authentication remains `NOT_ATTESTED`; consistency is
`DECLARED_CONSISTENCY_ONLY`. Completeness is an issuer declaration whose world
truth this software does not establish. Formal recall, independent confirmation,
selection, promotion, scientific fit and production remain unauthorized or not
validated. This is not a standalone preregistered campaign or a trusted cumulative
candidate/exposure/freeze ledger.

Actual stored September-28 CSVs still parse as five events and six capture
occurrences. Without a predeclared full scope and complete denominator, they
produce no Stage1 metrics. They do not establish Negative/search evidence.

`evaluate_stage1_sources` retains its original public signature and registry.
Four whole-receipt/projection hashes and exact cumulative read-byte counts were
collected from the unedited merged Git archive before this change; regressions
pin all four. No model, pure evaluator, parent request, G0 schema, Raw/ORIGINAL,
evidence policy, STATE or historical serialized receipt changes in this slice.
