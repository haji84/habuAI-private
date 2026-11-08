# Source-bound development candidate request v3

This additive request loads the existing pure candidate-config v2 from a guarded,
byte-bound development snapshot. It does not change the learner, its numeric
recipe, the three-slot limit, the v1/v2 request contracts, or the Stage1 registry.
All fixtures and fits used to verify this change are synthetic.

## Request and interfaces

`config/research-model-request.json` may use
`schema_version: habu-research-model-request-v3`. Its exact twelve fields are the
existing ten v1 fields (`schema_version`, `mode`, `operational_night`,
`fit_cutoff`, `forecast_as_of`, `forecast_cutoff`, `feature_definition_sha256`,
`training_manifest`, `forecast_manifest`, `exposed_nights`), plus
`candidate_config_manifest` and `stage1_manifest`. Mode is `DEVELOPMENT_ONLY`.
The candidate manifest is required; Stage1 is a strict byte reference or null.
The old v1 exact ten fields and v2 exact eleven fields remain unchanged.

`load_research_candidate_config(root, manifest_ref, *, heldout_night,
fit_cutoff, forecast_cutoff, expected_feature_definition_sha256, context)` in
`research_candidate_config_source` returns owned `{config, receipt}` only after
all declared code/policy/config bytes and a complete rescan pass. It uses the
existing shared `ProspectiveReadContext` and `G0ArtifactReader`. A byte reference
has exactly `{path, sha256, size_bytes}`; its SHA hashes physical file bytes.

`recheck_research_candidate_config(root, receipt, *, context)` is the parent
transport seam for a receipt owned by the same completed loader invocation. It
rechecks original consumed byte sizes/hashes and current code membership; it
does not accept a receipt as source authentication, upgrade it, or reseal it.

## Exact source profile

The profile has exactly these eight fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | `habu-research-candidate-config-source-v1` |
| `kind` | `DEVELOPMENT_CANDIDATE_CONFIG_SOURCE` |
| `feature_definition_sha256` | Strict complete feature-definition digest |
| `candidate_config` | Exact `{ref, config_sha256, readiness, usable_at}` |
| `cycle` | Exact `{ref, policy, readiness, usable_at}` |
| `code_availability` | Exact bounded list described below |
| `readiness` | Required four timestamp fields |
| `usable_at` | Effective maximum |

`candidate_config.config_sha256` hashes canonical parsed JSON. It is distinct
from `candidate_config.ref.sha256`, which hashes raw bytes including whitespace.
The config retains the pure v2 exact five-field contract: version, development
mode, ordered candidate IDs, full-seven HB-A1 recipe or null, strict feature
definition digest. Uniform is first; exactly two other unique known candidates
come from HB-A0/HB-B1/HB-A1. No fourth candidate, fallback, imputation or ablated
candidate recipe is added.

`cycle.ref` must explicitly identify `protocols/development/cycles/*.json`.
There is no ambient current-cycle pointer read. The parsed cycle uses the
existing `codex_cycle_contract.MANIFEST_FIELDS`, VERSION, fixed kind, valid cycle
ID/base-main SHA/frozen timestamp and code-manifest rules. `cycle.policy` has
exactly `{size_bytes, readiness, usable_at}`; its path and physical SHA are
derived from the cycle's exact two-field `policy_ref`. The fixed POLICY_PATH
and POLICY_DIGEST remain mandatory; canonical policy and physical policy SHAs
are recorded separately. No unchecked file read/stat discovers the policy size.

Each code availability entry has exactly
`{path, size_bytes, readiness, usable_at}`. The SHA comes only from the unique
cycle `code_manifest` entry for that path. This set must equal the full current
`code_paths(root)` registry, including requirements files, with no omitted,
extra or duplicate entry. Enumeration is bracketed by root/path and deadline
guards and repeated after reads and rescans. The old cycle CLI/validator, with
its own file-opening implementation, is not invoked. A selected HB-A1 recipe's
two implementation SHAs must match the byte-verified snapshot code map.

Profiles/configs are restricted to `config/` or `protocols/development/`.
Reserved path segments `sealed`, `confirmation`, `ORIGINAL`, `incoming` and
`reports` are rejected case-insensitively before payload opens, including code
references. Portable path rules, no reparse/symlink/junction ancestors,
containment, duplicate JSON rejection and nonfinite rejection use the shared
guarded transport. v3 also preflights nested TRAIN/forecast manifests and an
actually supported Stage1 manifest before their payloads are read.

## Declared availability and limits

The boundary B is `training_boundary(night, fit_cutoff, forecast_cutoff)`, the
minimum of evaluated-night 07:00 JST, fit cutoff and forecast cutoff.
Readiness has exactly `source_received_at`, `derived_at`, `materialized_at`,
`audited_at`, all aware and individually strictly before B. Effective maxima:

- Each code/policy usable time is its own four-field maximum.
- Cycle and config usable times each include their own four fields, all code
  usable times, and policy usable time.
- Profile usable time includes its own four fields, cycle and config.
- `frozen_at < B` and `frozen_at <= cycle.usable_at`.

Missing/malformed readiness, unknown fields, contradictory maxima, stale code
closure, hash/definition/recipe drift are invalid evidence (`ValueError` / parent
FAIL). Validly declared availability at or after B raises
`CandidateConfigSourceBlocked` / DATA_BLOCKED, with no fit. Absent files are
DATA_BLOCKED (including the shared transport's legacy missing-file exception).
No historical readiness is inferred or backdated from bytes or timestamps.

Per-file caps: profile 256KiB, config 64KiB, code/cycle/policy 4MiB, code registry
256 entries. The complete declared first-read plus first-rescan source closure
must fit 16MiB, including profile/config/cycle/policy. The same phase also checks
actual charged bytes. It does not shrink the parent's global ledger to 16MiB.
The parent retains its cumulative 2GiB read cap and absolute deadline at most
300 seconds through both source gates, pure fitting, Stage1 and publication.
All additional source rereads/rescans and reused REPLAY reads are charged.
Pure v2 retains its own combined JSON, row and result capacity limits and gets
the parent check plus remaining elapsed budget. There is no fresh outer budget.

## Parent dispatch and publication

The parent validates the config before fitting or any Stage1 outcome read,
then compares strict definitions with the actual selected TRAIN and forecast
receipts. Pure v2 prepares one complete set using the same TRAIN, full universe,
cutoff and shared deadline. Insufficient HB-A1 data returns no partial set.
All three model/prediction hashes exist before any optional Stage1 read.

Stage1 null means `NOT_REQUESTED` and performs no evaluation read. Only the exact
ordered legacy triplet `[uniform, HB-A0, HB-B1]` may use the existing source
adapter. Every other legal order/set with requested Stage1 yields explicit
`IMPLEMENTATION_BLOCKED` before even opening the Stage1 manifest. A complete
prepared set remains in REPLAY with a NEED_MORE_DATA decision and no fallback,
reorder or replacement seal. Insufficient sets publish no REPLAY. The pure v2
receipt and its blockers remain byte/content-equivalent; parent implementation
annotations are separate. Future Stage1 v2 integration is not implemented here.

The parent combines consumed SHA bindings, preserves config original byte sizes,
and rechecks all sources/code membership after fitting/evaluation and before
publication. v3 uses v2's exclusive immutable publication and ownership-bound
cleanup. Late expiry, changed source, failed publication or final guard failure
exposes no candidate set, Stage1 diagnostics or REPLAY and removes only links
created and still owned by that invocation. Sequential rescans detect ordinary
changes; they do not claim an atomic hostile filesystem snapshot.

## Authority and remaining dependencies

A successful source receipt is `DECLARED_CONSISTENCY_ONLY`, source authentication
`NOT_ATTESTED`. Raw/code/config hashes bind consumed snapshot content, not
historical source provenance or currently loaded Python/native execution.
All fit/scientific/selection/promotion/official/production, trusted campaign,
pre-reveal, source issuer, loaded-bytecode and confirmation authorities remain
false. No real-data fitting or confirmation source is enabled by this contract.

A pure proposed campaign ledger is not an actual persistent trusted ledger.
Changing config/campaign IDs cannot establish a fresh three-candidate allowance,
cumulative budget, pre-reveal freeze or consumption authority. Those trusted
campaign gates, source issuer/runner attestation, confirmation consumption and
scientific model comparison/selection remain explicit unmet dependencies.
Adding this runtime module requires a new coordinator-owned complete code freeze;
an older source closure correctly fails membership checks. No STATE or frozen
historical artifact is rewritten by this slice.
