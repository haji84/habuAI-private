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
