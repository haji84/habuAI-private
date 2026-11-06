# Habu AI 100m/10min research training automatic gate (2026-11-04)

## Actual scope

Implemented `scripts/habu_qualified_fit_cycle.py`, a fail-closed coordinator for an **independently qualified** G0 source manifest. It **reuses** `select_g0_training_rows`, `fit_candidate`, and the registered prospective 100m/10min candidate reader. It does not add a new ML architecture, relax the historical evidence gate, or authorize `P0`, Champion promotion or production model activation.

The qualified source manifest must already be source-verified with scoped active-Habu-search evidence, complete owner capture outcomes, independent negatives, row validity, valid as-of features and source hashes. The code cannot infer this from a GPX alone. A manifest for a future heldout night is required. The existing immutable model governance remains authoritative.

## Invocation in a private runtime

```sh
python scripts/habu_qualified_fit_cycle.py \
  --root /private/isolated-source-workspace \
  --private-output /private/models/qualified-research \
  --manifest-path protocols/development/qualified-training.json \
  --manifest-sha256 <sha256_of_manifest_bytes> \
  --feature-sha256 <sha256_of_registered_feature_definition> \
  --heldout-night 2026-11-05 \
  --fit-cutoff 2026-11-04T23:00:00+09:00 \
  --forecast-cutoff 2026-11-05T18:00:00+09:00
```

This is an interface example, **not** a claim that those files or timestamps are certified or that an approved model exists. The private output directory must be outside the source checkout and must never be committed to a public repository.

If the qualified manifest is not available, call with `--heldout-night`, `--fit-cutoff`, `--forecast-cutoff`, `--private-output` and omit all `--manifest-*`/`--feature-*` options; the result is `BLOCKED / MISSING_SOURCE_QUALIFIED_G0_MANIFEST`, not a fit. If the source selector accepts fewer than three prior nights or fewer than two positives and two independently qualified negatives, the result remains `BLOCKED`. **Do not manufacture or auto-certify any training labels.**

## Research-only success behavior

1. Validate exact source manifests and as-of times via the existing G0 source-closure selector.
2. Use the source-bound selector result unchanged. Refuse any unexpected production authority flag.
3. For qualified training data only, fit the existing logistic 100m/10min candidate and verify its `UNVALIDATED_CANDIDATE` status.
4. Round-trip the candidate through the existing `_read_candidate_model` with full payload hash checks before persistence.
5. Store the candidate under private `candidates/<content_sha>.json`, and an immutable matching receipt under private `receipts/<sha>.json`. Rerunning the same model is byte-idempotent; changing an existing payload fails.
6. Report `RESEARCH_CANDIDATE_FITTED`; **do not publish P0, alter the Champion registry, or update main**.

## Real-data gate on November 4

A private 2026-11-01 and 2026-11-03 audit reported 1,515 observed-only 100m/10min GPS grids, but **zero** source-qualified positive/negative 100m/10min training units and no canonical independently certified training manifest. The 11/03 22:14:53–22:44:05 interval was confirmed by the owner as a deliberate pause, not a negative observation or GPS failure. This means the actual formal model training/automatic adoption is **BLOCKED**. NightCount v1.1 is a research-only count model and must not be treated as this spatial model.

## Verification and deployment boundaries

Test fixture is synthetic, with actual G0 gate and candidate reader exercised in CI. Tests cover successful candidate fit, no-op on missing source, source tampering, negative qualification, future data exclusion, idempotency, path confinement and research-only authority. Code and documentation only in existing Draft PR #136. No new PR, paid service, Cloudflare dependency, automatic main merge, or public-private data crossing.

Release/Champion promotion requires independent review, intact previously issued P0 evidence, future untouched scoring, exact-head CI and the owner's explicit approval. This script is intentionally unable to override those gates.

## Additive private source preparation

The no-fit preparation mode preserves retained research artifacts and connects
an explicitly supplied existing G0 declaration to a checked private input
workspace. It does not create `AUDITED_TRAIN_ONLY` from unknown research rows.
The original fit mode and its exact blocked/success reports remain unchanged.

```sh
python scripts/habu_qualified_fit_cycle.py \
  --prepare-only \
  --root /private/research-source-workspace \
  --private-output /private/prepared-source-output \
  --research-sources-path evidence/research-sources.json \
  --research-sources-sha256 <raw_byte_sha256_of_the_reference_array> \
  --prepare-budget-seconds 300 \
  --heldout-night <future_operational_night> \
  --fit-cutoff <actual_fit_boundary_before_that_night_07JST> \
  --forecast-cutoff <future_forecast_cutoff>
```

The reference file is a bounded array of existing `{path,sha256,size_bytes}`
objects. Real available artifact bytes are copied without editing their internal
historic references. Therefore a research-only packet is not claimed to be a
complete formal source closure. Add the existing `--manifest-path`,
`--manifest-sha256` and `--feature-sha256` only when those actual independently
reviewed v1 artifacts are supplied. Both source and copied declarations must
pass the unchanged strict selector; `NOT_ATTESTED` never becomes an authenticity
certificate. Preparation itself never creates a candidate/model directory.

Outputs are private `inputs/<preparation_id>/`, stable
`preparations/<preparation_id>.json`, separate `checks/<content_sha>.json` and,
when blocked, the **unchanged** existing report in `fit-reports/<content_sha>.json`.
The semantic preparation record excludes per-execution counters and child
receipt hashes. The raw child receipts are not resealed to force equality.
The safe console contains fixed statuses/hashes and aggregate read counts;
private paths, event identities, feature values and coordinates stay private.

Actual retained evidence was packaged as 29 payload references (8 original GPX
and 7 nights of manifest/payload/completion), 306,494,694 bytes. The bound ref-list
adds one 4,817-byte inventory input. Three actual CLI executions, including the
final reviewed implementation, preserve identical console/semantic identity.
All 30 input/copy references are verified; the operation accounts
1,532,513,868 actual read bytes each, including repeat scans and output-integrity
reads. This is different from unique input byte size. The real result is
`BLOCKED / MISSING_SOURCE_QUALIFIED_G0_MANIFEST`, total eligibility null,
new qualified/negative rows and real fits zero. Source truth/independent scoped
outcomes, canonical capture assignment, registered feature validity/readiness,
and some latest original handles are still required. Existing GPS processing
was reused; it was not recomputed and no raw or model bytes were overwritten.

These real-data blocked receipts are separate from synthetic passing controls
of the actual G0 selector on a supplied declaration. A positive-only declaration
can retain valid positives without inventing negative search scopes, but it
cannot satisfy the existing 3-night/2-positive/2-independent-negative binary
training minimum. Current code, review and CI are recorded in Issue86/STATE;
software success is not scientific or production approval.
