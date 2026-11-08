# Full-ledger time-target diagnostic implementation

Approved design: `docs/specs/full-ledger-time-target-diagnostic-v1.md`,
`de4e6c313238035633ac9ac697c6cdb1d2da7f5d`; base main
`be045334a5ede3d5b92088e86b2b4852ccc8b6a1`.

Implementation plan:

1. Observe missing-API RED using synthetic greedy, exact UTM tolerance,
   outside-universe and full-ledger cases.
2. Extract only the old ordered augmentation into a pure iterative edge helper;
   compare exact owners against the original recursion, and whole old scorer
   outputs against the pinned original source on the same runtime.
3. Implement bounded owned JSON input validation, explicit UTM universe/target
   joins and the existing strict Stage1 ledger validator. Validate known
   contradictions before missing-data results. Apply one cooperative deadline
   and caller callback through matching and final sealing.
4. Exercise malformed/missing inputs, identities, chronology, source bindings,
   capacity, caller expiry and final sealing; run the old scorer regressions.

Generated universes, targets and complete ledgers are synthetic. A separate
read-only actual Git September28 CSV regression checks five capture events/six
individuals, with no universe, issued target, freeze or complete denominator;
its result is NEED_MORE_DATA with empty metrics. No source qualification,
target generation, real model fit, source loader, parent dispatch, original
data modification or authority is added.
The new primary denominator is events; individuals are secondary under the same
matching. Outside-universe events remain FN. Precision/FP are always null.

Projection bindings use the projection's self-hash (excluding its own hash key).
`input_digests` separately hashes each complete supplied projection, including
its self-hash. Both bindings are checked; no source authenticity is inferred.

## Verification

Native Python3.12.14, Windows:

- Initial RED: five missing-API failures for greedy matching, exact100m/600s,
  outside-universe FN/eligible neighbor, issued empty output and prior-night
  cutoff. These cases subsequently passed.
- Two further adversarial REDs: a contradictory nonnull universe hash in an
  unproduced set was not rejected, and an enormous integer budget raised
  OverflowError. Both now raise ValueError before a missing-data return.
- Whole-scorer corpus guard RED exposed an incorrect synthetic time key that
  exercised zero parsed targets. Corrected to the legacy `predicted_time_jst`
  and require nonzero parsed targets and actual matches across the corpus.
- New owned suite:40/40 PASS,0.614s. It includes4096 exhaustive ordered3x3
  graphs and200 seeded graphs compared against the checksum-frozen original
  recursive AST,1801-target augmentation,80 whole original/current scorer
  outputs on the same runtime,8003 full universe rows indexed once, typed
  hashes/identities, missing/contradictory data, strict limits, callback identity,
  matching expiry and post-success/post-NEED final-hash expiry.
- Broader native attempt before the final four added tests:105 methods,
  94 PASS/11 environment errors,5.194s. Seven errors require genuine POSIX
  fcntl in Freeze, two are Windows symlink privilege errors (WinError1314),
  and two module imports require fcntl (run_pdca/pdca_e2e). These are not PASS
  or simulated skips. Actual Ubuntu integration remains required.
- Final executable native target/regression group:87/87 PASS,1.025s
  (new40 + existing pure Stage1 registry44 + legacy PDCA diagnostic3).

Pinned original fixture is the full Git-native be045 scorer,32918 bytes,
SHA256 `4f3204fd704b6cfd7df1f199d29dbea55057eb546cd2b9c5aef1f4d5221a22cc`.
Its source is executed on the current runtime; no cross-platform numeric golden
is regenerated. Text-fixture checkout line endings are restored to canonical
LF for identity verification, not applied to any runtime source data.

Legacy scorer edits are limited to replacing the recursive owner block with
the ordered iterative helper. It receives no new deadline/cap, target sorting,
geometry, output rounding or schema. New T2 matching remains cooperative; Python
sorting/encoding and bounded parsing are not hard-preemptible. Hashes and
declared completeness do not establish source truth, issuer chronology, formal
precision, independent confirmation, fit, promotion or production authority.

Independent exact-source review is pending.

The independent-review section is reserved for the reviewer.

## Independent matcher and legacy scorer review

Reviewer `/root/config_review`: **PASS for the shared matcher extraction and
legacy scorer compatibility only**, at released clean snapshot
`b01501ea6b664545ec5ba3eb8614291eba1b5e6e` (author source
`75885ad01c3c10e3c43d384a5c431f8d6c20cf1b`, normally merged with main `4aca`).
The separate full T2 API/ledger/resource review is outside this section. Full
Ubuntu integration and genuine POSIX paths remain coordinator gates.

| Artifact | Git blob | Canonical bytes | Canonical SHA-256 |
| --- | --- | ---: | --- |
| src/event_matching.py | dbf887a8416134de97e61887bd43e5cfad0813a8 | 1490 | 2a5203141afd34b4f6b7ac835c9aa808d05fb998fb26f3dfce4e1d09a6dc21b4 |
| src/pdca_pipeline.py | ec4c5ae4b15d972b5d1949d4cf5fcf43bf4ab4e8 | 32613 | 7d8e989192d95aaa1c64fd8737184ed86d24e62da2ead20312d59c48cb4e0c7f |
| Frozen original scorer fixture | 3b02d3f2cc2826b101059b4ebee9bbd07c040ed3 | 32918 | 4f3204fd704b6cfd7df1f199d29dbea55057eb546cd2b9c5aef1f4d5221a22cc |

The fixture matches the original `be045334a5ede3d5b92088e86b2b4852ccc8b6a1`
Git source and pre-existing external capsule exactly. Its checksum is checked
before executing that distinct original module on the actual current runtime.
No expected scorer output was regenerated from the new implementation.

Static review found only the approved local import and recursive-augmentation
replacement in the old scorer. Independently reinserting the original block
in an in-memory AST makes the **entire module AST identical** to the original.
Thus its signature, filtering, target/event sorting, geometry, edge ordering,
time/distance inclusivity, negatives, rounding, output fields and other functions
retain their previous code. The helper creates no clock or capacity limit for
the legacy caller. Successful unwind assignments and event insertion order are
preserved; no different distance/count objective or tie optimization is added.

Independent external command, using the bundled Python with `-B -X utf8`:

```text
python -B -X utf8 ..\t2-matching-review-probes-20261025.py .
```

Fresh execution on the released snapshot passed **10,551 exact owner-map and
insertion-order comparisons**: 4,544 exhaustive ordered-subset graphs through
3x3, 6,000 deterministic random graphs through 10x10, and seven explicit empty,
duplicate-edge, sparse-index and reassignment cases. Caller graph immutability
is checked. A separate **1,801-target forced alternating chain** returned the
explicit expected owners without recursion. There were **10,137 actual callback
invocations**, including interruption at every callback position of a smaller
reassignment graph with TimeoutError, ValueError and RuntimeError; the exact
caller exception objects propagated and inputs remained unchanged.

The same harness called the checksum-frozen original and current scorer for
**723 complete synthetic cases**, comparing entire returned dictionaries and
canonical typed JSON, plus caller-input immutability. Cases include ordering
ties/permutations, duplicate IDs, aliases, malformed target times, cutoff/night
filtering, fixed tolerance overrides, exposure labels and count diagnostics.
The result-set checksum is
`f2aaa3991a893e8e95466a2a03673047f8ae34de6157bde565d89da7a854bb1f`.
Controlled helper corruption caused current results to differ while the original
still matched, and an injected current-helper error left original execution
independent. These are oracle-sensitivity controls, not replacement algorithms.
External harness SHA-256:
`3dedfd7beca714adb31b9b6de35f3a12b3159193fa645cf2e53aceedc4aa69f1`.

The focused authored `OrderedMatcherCompatibilityTests` also ran independently:
**5/5 PASS, no skips, 0.067s**. Attempts to import existing master-scoring and
run-PDCA test modules stopped at genuine missing native `fcntl`; no test-body
PASS or simulated platform coverage is claimed. No fcntl facade, dependency
installation, runtime/test/state/cycle edit or performance-authority claim was
introduced. The reviewer changed only this section. These synthetic compatibility
results establish no real forecast, complete observation denominator, scientific
qualification, official KPI, selection or production authority.
