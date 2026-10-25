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
