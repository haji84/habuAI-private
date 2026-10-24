# Lane V independent G0 and existing-PR audit, 2026-10-25

Reviewer base: `4981592789f5a6fe01800df85105f2d0c49c0b4a`.
Scope: independent design and exact-diff audit only. No model fitting,
source/label promotion, Raw/ORIGINAL modification, GitHub write or production
authorization occurred. Historical CI evidence below does not cover a future
rebase, repair or merge into current main.

## G0 design review

Reviewed coordinator design `docs/work/G0_CONTRACT_20261025.md` in the G0
worktree. The additive, contract-only envelope is appropriate: preserve existing
LearningSnapshot v1 and source contracts, bind exact implementation/schema bytes
to a versioned policy, and keep science `NOT_VALIDATED` and production false.

Design disposition: **APPROVE WITH CONDITIONS for the bounded contract slice**,
pending exact implementation review. This does not complete the scientific G0
allocation of folds, cohort eligibility or untouched confirmation.

Required implementation checks:

1. The fixed validator-owned closure must include transitive contracts/geometry
   helpers, schema and dependency pins. Manifest callers cannot omit a helper by
   removing its role. At least `master_contracts.py`, `pdca_pipeline.py`,
   `gpx_audit.py` and the applicable prospective-input implementations must be
   covered with the evidence/learning/evaluation/candidate implementations.
2. Effective training boundary is the minimum of declared fit cutoff, forecast
   cutoff and held-out operational-night 07:00 JST. All necessary readiness
   fields must be present; `max(source receipt, derivation, audit,
   materialization)` does not make unknown readiness known. Equality is
   ineligible. Historical feature valid-time and target suitability remain
   separate gates.
3. Persist machine-readable `folds unallocated` and `confirmation unselected`.
   Pure eligibility/feature/interface development can proceed, but a contract
   envelope cannot authorize actual fitting, evaluation or confirmation claims
   before Lane V's locked allocation and the E/F prerequisites.
4. This slice must not reference or deserialize confirmation outcomes. A future
   seal is a commitment, not a label artifact the fitter can inspect. Declared
   freeze time and consistent hashes do not prove a trusted pre-reveal receipt.

Later cycle bindings should refer to existing artifacts instead of duplicating
rows: target contract, corpus or explicit v1 snapshot, forecast cohorts and
cutoffs, independent complete outcome ledger, feature/universe artifacts,
availability policy, folds, metric denominator, selection plan, exposure history,
sealed confirmation commitment and full code/runtime identity. Fresh cycle IDs
must never erase research exposure or confirmation consumption.

## Exact PR identities and current remote observations

Fetched `refs/pull/{44,45,50,73}/head` and independently read GitHub PR metadata.
All supplied SHAs matched their current remote heads on 2026-10-25.
Diff scope uses merge-base-to-head, not a two-dot comparison that would falsely
attribute newer main files as PR deletions.

| PR | Exact head | Actual changes | Observed CI | Audit disposition |
| --- | --- | --- | --- | --- |
| [44](https://github.com/haji84/habuAI-private/pull/44) | `cdbdd49a7e5a65b653f3723dd982a93b35d7ca95` | 106 documentation/evidence paths; no canonical runtime paths | [39603087866](https://github.com/haji84/habuAI-private/actions/runs/39603087866), success | Historical audit material; reconcile dated/current claims and whitespace before integration |
| [45](https://github.com/haji84/habuAI-private/pull/45) | `706470fd69c5e7da1371eb768782d1a9cc7da8cb` | `pdca_pipeline.py` and one integration test | [39603049079](https://github.com/haji84/habuAI-private/actions/runs/39603049079), success | **CHANGES REQUIRED**, Windows sidecar bypass |
| [50](https://github.com/haji84/habuAI-private/pull/50) | `017d3804c5f0d0e786413909dc823dffdff607d2` | 14 archive/report/test paths | [39885431310](https://github.com/haji84/habuAI-private/actions/runs/39885431310), failure | **CHANGES REQUIRED**, ZIP test references nonexistent directory |
| [73](https://github.com/haji84/habuAI-private/pull/73) | `71c60aeb107321a9652d14fee9ac326251c2bae1` | 10 source/script/test/workflow paths | [39994961546](https://github.com/haji84/habuAI-private/actions/runs/39994961546), [39994961541](https://github.com/haji84/habuAI-private/actions/runs/39994961541), [39994961644](https://github.com/haji84/habuAI-private/actions/runs/39994961644), success | Preserve source as distinct historical evidence; reconcile superseded source coverage and confirmation-floor text |

For #44/#45, the test jobs show executed checkout, Python setup, dependency
installation and `unittest discover` success. #50's test job executed and failed;
it was not merely waiting for a runner. #73's source-crossmatch job executed all
three audit scripts and the diagnostic artifact upload. These are observations
of existing runs, not new tests dispatched by this reviewer.

## Findings requiring repair

### P1: #45 skips Freeze sidecar validation on native Windows loader paths

`load_predictions` stores `_path` with `str(Path.relative_to(root))`. On Windows
it is `predictions\\original\\2026-10-22\\P0\\prediction.json`. The added
`verify_predictions` builds `canonical_path` with forward slashes and requires
literal string equality before checking the sidecar. The condition is false,
and even a corrupt `sha256.txt` returns integrity `PASS` with sidecar status
`NOT_CHECKED` when payload content remains internally consistent.

Independent reproduction compiled the exact PR module from `git show` into
memory, used the real native loader against a temporary fixture and supplied a
corrupt sidecar. Observed result: `('PASS', sidecar_status='NOT_CHECKED')`.
No real prediction record was changed. Repair should compare normalized relative
paths or have the loader emit one canonical path convention, and add a native
loader regression that cannot silently skip this integrity check.

The full PR integration test cannot import unchanged `freeze_prediction.py` on
this Windows runtime because its baseline `fcntl` import is Linux-only. That
platform limitation is not evidence against the independent loader probe, and
the existing Linux CI success does not cover this Windows bypass.

### P1: #50 ZIP archive test points to a nonexistent full-digest directory

The test constructs
`data/raw/attachment_archives/pdca_artifact/3cb92409ee699bdfc6923f680398cc7297688b3ac9f298a1c613e42693d2bfa1`.
The exact tree stores the report ZIP under
`data/raw/attachment_archives/pdca_artifact/3cb92409ee699bdfc6923f680398cc7297688b3ac9`.
Consequently line 23's directory assertion fails before ZIP restoration.

The actual CI log independently reports this same assertion. The run executed
259 tests in 47.964 seconds, with one failure and one separate baseline bridge
temporary-directory cleanup error. Repair the archive lookup without changing
immutable archive bytes; then rerun the exact repaired head and independent
verification. The existing archive manifest's complete SHA remains authoritative
for byte identity even though its storage directory uses a shorter identifier.

Both actual archives were decoded/decompressed **in memory from Git blobs**:
compressed hash, raw hash and raw byte size all match. GPX raw size is 4,675,850
bytes; ZIP raw size is 20,796 bytes. All three standalone report files also match
their evidence-manifest hashes and corresponding ZIP members. The provisional
exposure CSV's label state is `PROVISIONAL_NOT_PRODUCTION_ROAD_GRID`, with no
certified supervised Negative admission. No corrupt original archive was found.

### P2: #73's confirmation-floor and current-source prose need reconciliation

`docs/specs/august-source-gpx-reconciliation.md` asks for two untouched future
confirmation nights, while the normative Master contract requires at least five
untouched confirmation nights as an engineering floor plus sufficient coverage
and uncertainty. Correct the stale two-night statement before treating this
document as a current protocol.

Its 111,323-byte, 10,016-line `8:2~8:29` source with SHA
`3c541bcbd994e1da397e083a9b094520926ebc9647879e4b001edbf9471c7eed`
must remain a distinct source/version. Current main has a separately verified
116,496-byte, 10,506-line August source with SHA
`130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c`
and later audits covering additional source evidence. Preserve aliases and
source identities; do not overwrite current source coverage, owner-count facts,
or the higher-fidelity audit with older `highest-fidelity/current` prose.

The PR's scripts emit diagnostic matches and explicitly zero admitted training
positives/negatives. They neither fit models nor establish prospective accuracy.
GPX proximity and a native capture statement do not resolve owner identities,
quantity for unnumbered events, independent active-search proof or full outcomes.

## Other verification

#44's CSV retains exactly R001-R112. Comparing common columns against its actual
merge base found only R110 `missing_data_or_executor` changed; every
`master_validation` remains `NOT_VALIDATED`. Added audit metadata is explicitly
dated 2026-10-21 and binds an old main SHA, so it cannot substitute for current
CODEX_STATE or live CI facts.

`git diff --check <mergebase> <head>`: #45 and #73 pass; #44 and #50 return 2 for
whitespace/CRLF diagnostics. Keep evidence byte identity when choosing any
format-only repair; do not silently normalize hashed evidence artifacts.

This review changed only this document. It does not authorize merges of stale
heads or label any scientific gate successful.
