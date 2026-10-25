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
and each following filename. Initial native Windows receipts at `42c49fa`:

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

## Native admission counterexample repair

Independent review of `42c49fa` found a blocking gap despite the initial 25-test
suite passing: recomputed hashes could hide a changed native uniform/HB-A0/HB-B1
fit cutoff behind an unchanged common prepared cutoff. The original source
returned DIAGNOSTIC_ONLY and pooled 2/3 for those inputs. Admission of HB-A0/B1's
native structure and common fit/night identity was missing. This was a software
consistency failure; it does not establish any scientific performance result.

Before the repair, new tests reproduced all three future-cutoff cases reaching
the first evaluation open. Separate RED cases covered native-valid but different
earlier cutoffs/held-out nights, malformed native structure, and uniform `.99`
contradicting its own fixed Beta counts. The v2-only candidate gate now reuses
`occupancy_shrinkage._validate_model` and `hierarchy_shrinkage._checked_tables`,
with checks before/after the native calls. It binds every actual native fit cutoff
to the common prepared cutoff and each existing native held-out field to the
common forecast night. Uniform's existing exact envelope, recipe, typed support
and fixed probability identity are checked locally because it has no separate
native admission helper. No fitted numeric routine or score projection changes.

The independent external harness `stage1-source-admission-review-probes-20261025.py`
was run in both modes: original `42c49fa` accepted all 14 adverse inputs; repaired
working source rejected all 14. Tests also exercise native capacity translation
to the existing parent capacity error and shared expiry immediately after both
native admission helpers. The v1 route never enters this new gate.

Post-repair commands use the same `-B -X utf8` unittest invocation above:

| Test module | Tests | Passed | Existing POSIX skips | Elapsed seconds |
| --- | ---: | ---: | ---: | ---: |
| test_stage1_configured_source_adapter.py | 30 | 30 | 0 | 31.289 |
| test_stage1_source_adapter.py | 33 | 28 | 5 | 10.504 |
| test_research_pdca_adapter.py | 27 | 26 | 1 | 11.841 |
| test_research_model_adapter.py | 35 | 35 | 0 | 1.916 |
| test_full_ledger_stage1.py | 44 | 44 | 0 | 0.502 |
| test_research_candidate_config_source.py | 16 | 16 | 0 | 4.449 |

Total 185 tests: 179 PASS and six existing POSIX skips. All four v1 whole-receipt
hashes/read-byte counters pass inside the new suite. `git diff --check` passes.
The correction changes only v2 native admission; Linux/full integration remains
the coordinator's subsequent CI responsibility.
