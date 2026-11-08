# Configured pure Stage1 v2

The coordinator approved this concrete contract before implementation. Base is PR107 exact
`5b0d5e090d3addd88dbfe5d8fbec66795f03018d`. This slice only extends the pure
Stage1 evaluator. It does not connect configured candidates to the parent or
change source profiles, issuance, policy, models, thresholds or historical data.

## API and configuration

Add `evaluate_full_ledger_stage1_v2(universe, scores, ledger, *, candidate_config,
expected_config_sha256, feature_definition_sha256, budget_seconds=30, check=None)`.
Reuse the existing pure candidate-config v2 validator in
`research_model_adapter._v2_config`, reached only by the new v2 function.
Its exact config fields remain `schema_version`, `mode`, `candidate_ids`,
`hba1_recipe`, `feature_definition_sha256`. Uniform is first, followed by two
unique choices from HB-A0, HB-B1 and HB-A1. Either optional order is valid.
HB-A1 requires its full seven-column fixed recipe; other configs require null
HB-A1 recipe. No fourth candidate, ablation recipe or model selection is added.

Universe and ledger retain their existing exact v1 projections. Scores have
exact fields `schema_version` (`habu-stage1-scores-v2`), `universe_sha256`,
`candidate_config_sha256`, `feature_definition_sha256`, `candidates`.
Each ordered candidate has exactly `candidate_id`, `score_semantics`,
`model_sha256`, `prediction_sha256`, `candidate_config_sha256`, `recipe_sha256`,
`scores`. Config digest equals the expected keyword and the config canonical
digest at every binding. Feature-definition digest matches the keyword/config.
Recipe digest equals the config HB-A1 recipe canonical digest for HB-A1 and is
null for every other candidate. Model/prediction digests are declared identities,
not authentication of absent serialized models or source files.

## Evaluation and compatibility

Use one private owned-snapshot numeric core for v1 and v2. Public v1 keeps its
current signature, rejects v2 scores/HB-A1, and cannot accept a private registry
or config argument. No mutation of `CANDIDATE_IDS` is permitted. Existing v1
complete results, missing behavior, numerical formulas, output keys, policy
digest and receipt digest remain exact across six frozen full-result oracles.

V2 uses exactly the ordered configured three candidates, common complete
universe and complete individual ledger. All native ranking semantics are
retained. Numerator/denominator, event-two-individual handling, outside-universe
FN, lexical ties, pooled counts, paired NIGHT bootstrap (seed0, 2000 draws),
five-night floor and NOT_ESTABLISHED adequacy remain the same algorithm.

V2 output version is `habu-full-ledger-stage1-diagnostic-v2`. Additional identity
fields are ordered `candidate_ids`, `candidate_config_sha256`,
`feature_definition_sha256`; candidate lineage includes config/recipe digests,
and input digests include config. All existing authority/science flags remain
false/NOT_VALIDATED. Configuration hashes do not establish trusted registration,
exposure accounting, original-issuer authenticity or confirmation permission.

## Resource and missing-input boundaries

Own the combined universe/scores/ledger/config JSON snapshot under the existing
16MiB, depth/node, list/row and scalar limits before copying. The same absolute
deadline and optional parent callback cover config validation, every hash,
projection check, resampling and final sealing. No new deadline reset or larger
resource budget is introduced.

V2 validates known supplied schemas, finite values, digests, candidate identities,
source/ID/time consistency even when a different projection is missing. Only
cross-projection facts that require the absent projection remain unknown. A
contradiction raises ValueError; missing/noncomplete valid inputs return
NEED_MORE_DATA with empty per-night/pooled/uncertainty metrics. No invented
universe is used to validate a partial ledger. V1's existing early missing-input
behavior is unchanged.

The owned paths are `src/evaluation/full_ledger_stage1.py`, its existing test,
the synthetic `tests/fixtures/stage1_v1_pr107_oracle.json`, this new spec and the new review document. Source adapter, parent, configured
preparer, state/freeze, Raw and ORIGINAL are outside this slice.
