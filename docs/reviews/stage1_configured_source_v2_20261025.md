# Configured Stage1 source v2 implementation review

Branch `codex/stage1-configured-source-v2-20261025` starts at pure review
`82e302235f21e370755536f6ffe850455bbd36ec`, normally merges reviewed preparer/parent
`cb2a1c12ef3e3a181f3f6210c24d30479e66261a` and main
`c2abdd990c60aafa5289652fb9e4bdaea0879705`. The clean pre-edit merge is
`70b3fff12ecf7241603bca35b5b7188cc144e679`. No history reset or force update.

Owned changes are the source adapter, one new configured-source test module,
the new contract spec and this review. Parent/pure/config/model implementations,
Raw/ORIGINAL, evidence policy, historical receipts, STATE and freeze are unchanged.

The implementation reuses the existing source graph/CSV/causal/scope/rescan path
and native prediction binder. It adds one combined owned config/forecast/prepared
snapshot and configured lineage checks before evaluation reads, then projects to
the reviewed pure Stage1 v2. HB-B1 native recipe and ranking meaning remain intact.
Parent request v3 still explicitly blocks nonlegacy Stage1; this source API is a
separate callable and does not grant implicit parent opt-in.

## Pre-edit compatibility baseline

An unmodified native Git archive (`git -c core.autocrlf=false archive`) executed
four existing v1 fixtures. Native source SHA-256 was
`ffc0f686481f822b1409fef5645c72e1ef68f41c279af1fdf4205773822b9037`.
The complete external oracle JSON is 17,067 bytes, SHA-256
`dc6add19bed7b92bc7d3c08c07280551ec69af910321eefd4e8813427290b79c`.
Its full-result hashes and read-byte counts are readable constants in the new
test, and include all result/projection/receipt/consumed-source fields.

| Variant | Initial read bytes | Final read bytes |
| --- | ---: | ---: |
| Complete | 90,654 | 126,056 |
| UNKNOWN | 90,654 | 126,036 |
| Missing scope | 90,654 | 96,998 |
| Missing coverage | 90,654 | 123,816 |

All four whole-result SHA comparisons and counters pass after refactoring.
Tests obtain the unchanged policy's native HEAD blob when constructing synthetic
fixtures, avoiding Windows checkout CRLF contamination without rewriting sources.

## TDD and validation

The first new suite was run before implementation: the additive API assertion
failed and v2 callers failed because that API did not exist; both v1 baseline
tests already passed. Subsequent focused RED cases exposed a malformed receipt's
AttributeError and rehashed non-integer complete-count metadata reaching the
manifest read; v2 validation now rejects both as ValueError before I/O.

The configured suite covers all six ordered triplets, native hash and recipe
binding, malformed/rehashed lineage, full scope/count/outside-FN numbers, UNKNOWN
and missing data with empty metrics, shared byte/deadline exhaustion, actual
combined rather than separate JSON caps, final rescan mutation and late seal
expiry, unchanged mean semantics, exact manifest versioning, and retained parent
v3 nonlegacy block. Actual OS link tests reject payload reads before traversal;
Windows uses a real junction and removes only that link before fixture cleanup.
Native September-28 source CSVs produce five events/six individuals and honest
NEED_MORE_DATA with no complete denominator.

Final command receipts are recorded below after running the owned and related
targets. Windows cannot validate POSIX master/fcntl paths; those existing skips
remain Linux CI requirements, not passing executions on Windows.

HB-B1's fixed native recipe was also challenged with a changed parent strength
and recomputed native model/prediction/prepared digests. The RED case reached the
manifest read; the v2-only check now compares both recipe content and digest with
the existing `hierarchy_shrinkage.RECIPE`. It does not replace the native recipe
with null or alter any ranking calculation.

Commands use the bundled Python with `-B -X utf8 -m unittest discover -s tests -p`
and each following filename. Final native Windows receipts:

| Test module | Tests | Passed | Existing POSIX skips | Elapsed seconds |
| --- | ---: | ---: | ---: | ---: |
| test_stage1_configured_source_adapter.py | 25 | 25 | 0 | 29.661 |
| test_stage1_source_adapter.py | 33 | 28 | 5 | 10.275 |
| test_full_ledger_stage1.py | 44 | 44 | 0 | 0.504 |
| test_research_model_adapter.py | 35 | 35 | 0 | 1.799 |
| test_research_pdca_adapter.py | 27 | 26 | 1 | 11.971 |
| test_research_candidate_config_source.py | 16 | 16 | 0 | 4.317 |

Total 180 tests: 174 PASS, six existing platform skips. Related targets ran after
the shared refactor; the final v2-only fixed-recipe check was then exercised by
all six configured orders and the new rehashed-recipe negative test in the final
owned-suite execution. `git diff --check` passed. No full native suite is claimed;
Linux CI and parent opt-in integration remain coordinator responsibilities.
