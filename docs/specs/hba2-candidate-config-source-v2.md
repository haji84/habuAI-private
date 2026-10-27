# HB-A2 fixed candidate configuration source v2

DESIGN ONLY, based on verified main `7b04d4ed40fd61b4987de6e51b11f4ee5a763872`. This document authorizes no loader implementation, candidate fit, source registration or parent dispatch. That base has the existing source-v1/cfgv2 loader and no `research_candidate_preparation_v3.py`.

The separate reviewed preparation checkpoint `8654a1c6737699127b445d92b227f24ccb5f5549` and author release `0f8eb13902c75a2623b09a891c0cdc1f3d32f495` are historical helper references. Independent scoped code acceptance does not substitute for its genuine pinned numerical test, exact CI, fresh-main verification and actual-main integration. Implementation requires all those gates plus independent review of this design and explicit ROOT dispatch on a then-verified base. Do not invent future commits, acceptance, code counts or CI results from these references. If later numerical CI or review repairs a helper, pin the accepted new bytes before implementation.

## Choice, scope and future ownership

Add a separate opt-in module `research_candidate_config_source_v2.py`. It reads an explicit source-v2 profile containing only cfgv3, returning owned configuration and a declared-consistency receipt. Keep the existing source-v1 loader, its helpers/constants/defaults, cfgv2 acceptance and old callers byte-for-byte unchanged. Refactoring a common orchestration function into the old loader would alter its pinned body and risks old callback/read order; it is unnecessary. Reuse its unchanged path/readiness/membership helpers and the existing guarded reader. Do not generalize the old loader, substitute validators, monkeypatch or dynamically execute source.

Future implementation AllowedPaths are exactly:

- NEW `src/research_candidate_config_source_v2.py`
- NEW `tests/test_research_candidate_config_source_v2.py`
- NEW `docs/reviews/hba2_candidate_config_source_v2_20261026.md`
- This spec only for evidence-driven clarification recorded in that review.

No existing loader/model/preparation/source/summary/Stage1/parent function, test or golden, registry, requirements, policy, Raw/incoming/ORIGINAL, STATE, cycle or workflow is edited by that implementation. ROOT separately owns the later complete code freeze. With the separately integrated preparation module plus this loader, the expected conservative closure is 103 files under the known current dependency context; the contract is exact current `code_paths(root)` membership within its existing 256-reference cap, not an inferred fixed count after unrelated development.

The slice does not call any preparer, fitter, backend probe, inference, learner/scalar extraction, target/evaluation/outcome/confirmation reader, metric/winner selector, publisher or persistent ledger. It does not create a request/parent version or enable source/summary/Stage1/registry use of A2. Those remain separate blocked adapters.

## Public interfaces and exact profile

```python
load_research_candidate_config_v2(root, manifest_ref, *, heldout_night,
    fit_cutoff, forecast_cutoff, expected_feature_definition_sha256, context)
```

Return exactly `{config, receipt}` after the complete first read and rescan. No optional fallback, automatic version detection, ambient current-cycle pointer, default config or new budget argument is accepted. `manifest_ref` and every byte ref have exactly `{path, sha256, size_bytes}`. SHA is lowerhex SHA256 of physical bytes; size is an exact positive nonboolean integer under the existing shared ref contract. Own the outer ref's primitive fields before the first caller-controlled check, preserving the existing borrowed-ref mutation protection.

Profile has exactly eight fields:

| Field | Exact requirement |
| --- | --- |
| `schema_version` | `habu-research-candidate-config-source-v2` |
| `kind` | `DEVELOPMENT_CANDIDATE_CONFIG_SOURCE` |
| `feature_definition_sha256` | strict SHA equal to the explicit expected definition argument |
| `candidate_config` | exact `{ref, config_sha256, readiness, usable_at}` |
| `cycle` | exact `{ref, policy, readiness, usable_at}` |
| `code_availability` | exact bounded list of `{path, size_bytes, readiness, usable_at}` |
| `readiness` | exact four shared readiness fields |
| `usable_at` | declared effective maximum described below |

The config is exactly the approved six-field `habu-research-candidate-config-v3`: `schema_version`, `mode`, `candidate_ids`, `hba1_recipe`, `hba2_recipe`, `feature_definition_sha256`. Mode is DEVELOPMENT_ONLY; IDs are exactly ordered `[uniform, HB-A1, HB-A2]`; recipes are nonnull and their unchanged complete native schemas/parameters/order/maps apply, with all seven A1 mask booleans True. This source version rejects source-v1/cfgv2 and every alternate set/order/fourth candidate, missing/extra field, null/ablated recipe and mismatched definition. It never silently upgrades a legacy profile.

`candidate_config.ref.sha256` binds raw JSON bytes, including formatting; `candidate_config.config_sha256` binds the whole canonical parsed config. Preserve both, never substitute one for the other. The same distinction applies to manifest/cycle/policy physical and canonical hashes. Parsing retains existing duplicate-key/nonfinite rejection at every nested depth.

## Immutable cycle, actual bytes and recipe cross-binding

Reuse unchanged `research_candidate_config_source` helpers:

```text
input_ref(value, *, purpose='profile')
_runtime_path(path)
_fields(value, fields)
_sha(value)
_stamps(node, check)
_ready(node, check, *, parents=())
_membership(root, expected, check)
```

Use only `g0_forecast_contract.G0ArtifactReader(root, context)`, `read(ref, *, small=False, parse=True)` and `rescan()` for actual payload/code bytes. A local subclass may bracket each unchanged `read` with the new invocation's phase check, as the old loader does. No direct `Path.read_bytes`, metadata-derived unbound sizes or alternate reader is permitted. Do not invoke the standalone cycle validator, whose separate file-opening implementation bypasses this ledger.

The explicit cycle ref is under `protocols/development/cycles/*.json`. Its envelope is exactly current `codex_cycle_contract.MANIFEST_FIELDS`, version/kind/valid cycle ID/base-main SHA/frozen timestamp. Policy path is exactly the existing fixed POLICY_PATH, raw SHA comes from the cycle's exact `{path,sha256}` ref, and original size/readiness come from `cycle.policy`'s exact `{size_bytes,readiness,usable_at}`. The parsed policy must retain the existing POLICY_DIGEST. No policy choice, namespace or authority is widened.

Code manifest entries have exact `{path,sha256}`; availability paths/sizes are unique and exactly equal the full current guarded `code_paths(root)` set. This includes both requirements files and every new helper, not only model-selected files. Reuse reserved-segment and portable local-path/no-static-reparse guards, with namespace and ancestor preflight before each known payload's open. Config/profile remain only in existing `config/` or `protocols/development/` namespaces; reserved sealed/confirmation/ORIGINAL/incoming/reports segments remain forbidden case-insensitively. Code paths retain the existing src/scripts Python, schemas JSON and two fixed requirements grammar. Require all manifest/config/cycle/policy/code ref paths distinct and all original sizes/caps consistent.

Reuse the accepted preparation helpers `_copy(value, guard)`, `_digest(value, guard)` and `_config(value, expected, definition, guard)` from its then-accepted implementation. `_copy` bounds and owns JSON; `_config` performs exact fixed cfgv3/native recipe validation and returns the three recipe hashes. It has no file reader, package import probe or fit. Pass the same phase/context guard. Do not call the full preparer or change its recipe schema. Complete canonical config hashing covers both recipes without adding an independent mutable recipe projection.

After actually reading the complete declared closure, compare every recipe declaration to that reader-verified raw `code_map`:

- A1 implementation map: exactly `src/prospective_candidate_model.py` and `src/models/hba1_feature_candidate.py`.
- A2 implementation map: exactly those two plus `src/models/hba2_feature_candidate.py`, `src/models/research_selection.py`, `src/gpx_audit.py`.
- A2 requirements map: exactly `requirements-analysis.txt`, `requirements-osm.txt`.

Every SHA must match actual snapshot bytes, not merely agree with another rehashed JSON declaration. The unchanged native recipe validators enforce exact map keys and complete recipe digests; the loader adds physical cross-binding. A code entry cannot omit a recipe dependency, and a profile cannot add a requirement/code availability outside the cycle. Both requirements receive the same real raw-byte read, readiness validation and rescan as all code. This does not prove installed package versions, loaded Python/native bytecode, dependency execution, issuer or historic availability.

## Readiness and contradiction-first ordering

Use existing `training_boundary(heldout_night,fit_cutoff,forecast_cutoff)`: B is the minimum of the evaluated night's 07:00 JST, fit cutoff and forecast cutoff. Existing aware-time validation and operational-night semantics remain. Readiness is exactly `source_received_at`, `derived_at`, `materialized_at`, `audited_at`; no date is fabricated or inferred from file existence or an old source receipt.

For each code/policy node, usable_at equals its own four-field maximum. Cycle and config usable_at each equal the maximum of their own four stamps and every code/policy prerequisite. Profile usable_at equals the maximum of its own stamps, cycle and config usable_at. Require `frozen_at<=cycle.usable_at`. Successful profile usable_at and frozen_at must both be strictly before B, which also bounds every included readiness stamp; equality is late.

Retain the old sequence: validate known schemas/refs/readiness syntax/maxima/closure, read and validate complete config/policy/code bytes and recipe bindings, bracket membership checks and a full original-ref rescan, then classify valid late availability. Late availability must not hide any known config/hash/recipe/requirement/max/closure contradiction. No fit/backend/outcome read happens on any branch.

Malformed schema/ref/hash/map/definition/readiness maximum, duplicate paths/JSON keys, unexpected policy or changed closure/bytes is invalid (`ValueError` or the unchanged shared transport's ordinary validation error). Missing files retain the existing transport's ordinary missing-input behavior. A fully consistent declaration unavailable strictly before B raises the existing `CandidateConfigSourceBlocked`; it is not a successful empty config or NEED_MORE_DATA. Capacity uses `prospective_inputs.InputCapacityError`, deadline uses the actual shared expiry, and no partial config/receipt is returned on any failure. No new broad catch may turn runtime/caller failure into SourceBlocked/missing/data insufficiency.

## One context, actual charges and final closure

Require the caller's existing `ProspectiveReadContext` instance. It must have valid positive nonboolean integer max_bytes at most `g0.MAX_TOTAL_READ_BYTES` (2GiB), a positive remaining allowance at most300 seconds, and an unexhausted existing actual-byte ledger. Reject a broader context; do not silently tighten it or create a fresh one. Its constructor/deadline checks remain actual; do not proxy/mutate/replace its clock, check, max_bytes, deadline or charged count. Genuine nonzero prior charges are preserved, including bytes consumed by other phases of a future caller.

All source API reads and rescans use that same object and absolute deadline. Capture invocation initial_bytes once. The source phase keeps profile256KiB, config64KiB, code/cycle/policy4MiB, at most256 code refs, declared `2*sum(original ref sizes)<=16MiB` covering profile/config/cycle/policy/all code, plus actual `context.bytes_read-initial_bytes<=16MiB` guards before/after reads and throughout source operations. Never call `context.restrict(16MiB)`, refill/reset charges, pool independent contexts or increase a cap. Source JSON ownership and config digest checks remain under that phase guard and the same remaining deadline.

Before returning: reread every original consumed ref through the reader, with its original size and SHA; check current complete code membership around that rescan; create the owned receipt and whole receipt hash; run the actual final context/phase guard. Hashing cannot escape final expiry or caller abort. Cooperative checks do not promise hard preemption during one read/hash or atomic hostile-filesystem snapshot semantics.

For a receipt owned by this completed invocation, callers may reuse unchanged `recheck_research_candidate_config(root, receipt, *, context)` for later closure scans. It already uses original `consumed_refs` and `code_sha256_by_path`, bracketed guarded membership and actual same-context G0 reads. Additional scans consume global allowance outside this loader's completed first-read-plus-first-rescan16MiB phase; they never reseal/update the earlier receipt or mislabel its phase counters as a final whole-run ledger. This design adds no caller/parent integration. If a new public recheck name is desired, a new-module wrapper may delegate without changing old bodies or receipt content.

Every actual original caller exception at first/later/reader/config-validation/final-hash guard must propagate as the same object, including BaseException and falsey/equality-trap instances. Do not classify origin by message/class/cause or suppress it via broad normalization. The inspected old path/reader and selected recipe helpers have no required wrapping at these seams, but implementation must prove this through genuine guarded reads. If an unchanged helper wraps a measured original and restoring it requires old edits, report the exact separate dependency instead of silently weakening this contract or broadening AllowedPaths. Internal validation/capacity failures remain internal; a parent callback is not permission to rewrite context state.

## Exact result and no authority

The returned receipt retains the following complete field set, with its own new schema version:

```text
schema_version, status, manifest_ref, config_ref, cycle_ref,
manifest_canonical_sha256, config_sha256, cycle_canonical_sha256,
code_sha256_by_path, code_map_sha256, policy_ref, policy_canonical_sha256,
boundary, readiness, usable_at, consumed_refs, consumed_sha256,
actual_read_bytes, validation_read_bytes,
source_authentication, source_availability_authentication,
fit_authorized, selection_authorized, promotion_authorized,
scientific_execution_authorized, official_issuance_authorized,
production_activation_authorized, loaded_bytecode_authenticated,
python_native_runtime_authenticated, trusted_campaign_authorized,
trusted_pre_reveal_authorized, source_issuer_authenticated,
confirmation_authorized, receipt_sha256
```

Schema is `habu-research-candidate-config-source-v2`; status is DECLARED_CONSISTENCY_ONLY. Config is a complete bounded owned cfgv3 object. Refs include original physical sizes/SHAs; canonical hash/map fields cover their complete parsed values; consumed refs retain actual first-appearance reader order. `actual_read_bytes=context.bytes_read` is cumulative, including real prior charges; `validation_read_bytes=context.bytes_read-initial_bytes` is this completed source phase. The receipt hash covers its entire body before its own hash field. Source authentication is NOT_ATTESTED and source availability authentication CALLER_DEPENDENCY_REQUIRED. Every listed boolean authority/authentication field is exactly false; no extra field can grant authority. All returned config/receipt values are owned; caller input or sibling mutations cannot retroactively change a sealed child.

An actual implementation control charged one additional genuine byte from a caller check after the receipt hash existed. A successful receipt may not silently retain the earlier counter snapshot. If the ledger changes during final hashing/ownership/checks after that snapshot, reject the late inconsistency with ValueError and return no config/receipt; do not reset charges or rewrite a sealed child to hide it. Original caller exceptions still propagate as the same object, and all actual charges remain in the existing context. This new-entry clarification does not change historical source-v1 receipt semantics.

These hashes establish declared snapshot-content consistency, not actual-file issuer authenticity, installed-backend authentication, prereveal trust, trusted campaign allowance, scientific eligibility or production authority. There is no actual fit, model comparison, confirmation, Negative/SEARCH qualification, change to historical M0–M3 or real TRAIN. Existing source counts and UNKNOWN dispositions are not a training denominator.

## Required pre-edit baselines and decisive acceptance

Before future edits, pin the then-verified old source program/dependencies and collect executable complete old source outputs, exact callback/read/open order and counters, including success, malformed/valid-late, capacity, expiry, first/final caller abort and late source change. Preserve existing source tests and genuine original eight whole parent artifacts. Compare old/current defaults in the same actual runtime and complete code/data declarations, including full typed results, every hash field, original physical REPLAY initial/reuse bytes and complete read ledgers. Keep original golden bytes; do not regenerate from new code, omit hash/counter fields or accept changed-context whole equality. Verify actual new raw-code membership/bindings separately; a new module properly invalidates an old incomplete cycle.

New tests must cover:

- Exact source-v2/cfgv3 schemas, fixed order/full recipes, no old-version fallback, physical versus canonical hashes and owned refs/config/receipt.
- A positive complete A1+A2+two-requirements closure, and independently rehashed mismatch of every implementation/requirement value; omitted/extra/duplicate code and availability entries, wrong policy, original sizes/growth and new-helper membership.
- Every readiness field at each level, wrong maxima, frozen_at ordering, strict equality boundary, and valid-late declarations combined with bad last requirement/code/config so the known contradiction wins.
- Reserved/portable/case/alias/static-link/junction refs rejected before forbidden opens, including nested recipe closure; no source/model/backend/outcome/confirmation activity beyond the declared reads.
- Declared and actual source phase limits, each file/ref cap, true nonzero prior charges, broader/exhausted context rejection with no mutation, global exhaustion, all byte charges through rescans and no hidden context creation/restrict/reset.
- Original exception identity at actual first/later read, cfgv3 helper and final seal; internal capacity/validation still classified normally. Actual final hash/deadline interruption exposes no result.
- Late bytes or membership changes detected both at initial full rescan and the reusable later recheck; earlier receipt remains unchanged while cumulative context charges increase.
- All old source/default whole outputs, callback/read order, original archives and physical REPLAY unchanged under identical declarations. No new metric/fit/candidate dispatch or authority occurs.

Historical reviewed anchors, not promises of future-main bytes: old source loader13,222B / SHA256 `19a9a66c3f4828ab36c6348efb64a6317fcd73b207ab70afb3d702cdb7071943`, blob `c94ad002c2e4e146a0260757d9d0ef069a4d166e`; loader LF body lines120–265 (8,766B) `a085135704f1b0805947275c4f034941112c02ea1576a13d0b19f11cca0b17a6`; old source test16 methods/17,592B / `05a37c4d328366581c0a871ef98b3ebcfe9d4c1e663b7741190687078a2c657e`. At8654, new preparation24,348B / `4e69ddbc9b6cdd40f7b5e9c4c1dfb1c88244dcc982ad8c53998d3c98cd540fa1`; `_config` body lines125–135 (879B) `670e2a35ea921da9b70c80be8d70b78ffe111163c7a2d3f4c83153de246ce14b`. The current design base still matches the old loader/test pins. Refresh actual accepted helper pins and preserve their earlier history after all implementation prerequisites.

Risk is MEDIUM for the new explicit protocol, same-context accounting/origin identity and complete map cross-binding; reuse and unchanged old bodies keep the numerical/legacy surface bounded. Independent design/code review and actual exact/fresh integration CI remain required. This is ordinary consistency-reader software, not a new trust boundary or owner-critical scientific/production model selection. The Master Goal, existing trusted issuer/campaign/prereveal/confirmation gates, missing seven authentic deployment inputs, real qualified TRAIN and A2's later adapters remain unmet and unchanged.
