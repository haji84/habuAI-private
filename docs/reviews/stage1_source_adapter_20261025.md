# Source-bound Stage1 implementation plan and review

Base `71f04564e8c200b7dc2cd8bd595310ed6de7242c`, branch
`codex/stage1-source-parent-20261025`.

The coordinator approved the contract in
`docs/specs/stage1-source-adapter.md` before code. Reusing the pure evaluator and
the existing research request/REPLAY path avoids a duplicate numerical evaluator
or competing parent pipeline. The implementation owns only the new adapter,
test/spec/review, the narrow request opt-in and the approved optional pure
check callback. G0 schemas, policy, master orchestration, Raw, ORIGINAL, model
recipes, state and freeze remain outside this slice.

- [x] Prove missing adapter and shared-deadline behavior with failing tests.
- [x] Validate explicit source/DAG/readiness/namespace and canonical CSV links.
- [x] Construct complete common-universe projections and reuse pure evaluation.
- [x] Add explicit v2 request opt-in and one immutable diagnostic REPLAY.
- [x] Test numeric full-ledger/outside-FN/two-ID fixtures, missing completeness,
  contradictory sources, sealed/read-order, resource and rescan boundaries.
- [x] Demonstrate actual September28 missing complete denominator honestly.
- [x] Run target/regression tests and hand over for exact independent review.

Initial RED after fixing the test's own aware-datetime fixture: 12 tests,
4 errors (missing new module/callback), 3 failures (v2 unsupported),
4 existing reject controls passing and 1 POSIX skip. Those passing reject
controls were not evidence that the absent adapter performed validation.
Further explicit RED-to-GREEN controls cover known actual timestamps in UNKNOWN
coverage, invalid coverage despite missing scope, empty CSV coordinate schema,
and interruption immediately after the native immutable link succeeds.

Current target receipt: 33 tests, 28 pass and 5 platform skips on
Windows. Existing pure evaluator: 28/28 pass. Existing parent: 14 tests,
13 pass and 1 POSIX skip. The optional callback with a no-op produces the same
entire result/digest; its parent timeout interrupts work. Full Linux master
dispatch remains a real CI requirement, not a simulated `fcntl` success.

The synthetic two-event ledger contains three existing fixture IDs: two IDs in
the predicted area and one in the same prior scope but outside its universe.
All fixed3 candidates report numerator 2 / denominator 3. This verifies the
individual denominator and outside-universe miss rule, not actual accuracy.
Task6's `statistics.mean` is used for every candidate's native unit scores;
HB-B1 rank scores are not probability conversions.

Actual September28 capture/individual CSV bytes are loaded from immutable Git
blobs in the hermetic test (5 event IDs, 6 linked IDs). It supplies no invented
prior scope or complete coverage. The fixture receipt is explicitly current
October25, not a backdated operational forecast. Result is NEED_MORE_DATA with
empty per-night/pooled/uncertainty metrics. No source qualification, label,
policy or actual training result is altered by this test.

The native Windows junction tests create real directory junctions in a
synthetic temporary root, confirms `is_junction`, counts zero external opens,
and removes only the junction itself before temporary cleanup. Linux uses a
real symlink for the corresponding guard. New/reused/replaced REPLAY fixtures
verify ownership cleanup without deleting a pre-existing or replacement file.
A real late directory-junction swap initially deleted an external temporary
sentinel (explicit RED). The initial path/identity fix was then independently
refuted by an ancestor swap after the own lstat returned. Final Windows cleanup
opens a native DELETE/attributes handle, verifies the fd device/inode and
deletes via that handle. Real post-fstat final-leaf replacement preserves the
replacement and deletes the owned handle only. On this Windows runtime,
an attempted ancestor rename while the handle is open is denied by the OS
(WinError5); the test records that denial rather than claiming the swap happened.
Both external replay and temporary sentinels survive late directory swaps.
Newly linked replay bytes are read back with
the shared guarded reader and actual byte accounting before success.

Additional regressions: strict G0 forecast 60/60, G0 training source 14/14,
prospective inputs 65 (64 pass, 1 platform skip), pure fixed3 model adapter
13/13, model evaluation 32/32, development walk-forward 7/7. Together with the
three suites above, the aggregate is 266 tests, 259 pass and 7 platform skips.
The preceding combined run of 260 tests passed (257 pass, 3 skip, 29.066s);
the additional v1 syscall compatibility control was explicitly RED-to-GREEN.
A preceding 70-test new/pure/parent run passed (68 pass, 2 skip, 14.059s),
before final safe-cleanup changes. Final source is verified separately below;
earlier receipts are not substituted for it.

POSIX cleanup pins every ancestor and atomically claims the public leaf into
an owned private 0700 quarantine before inode comparison. A foreign claim is
restored with a no-replace hardlink if possible and retained in quarantine;
contested restoration keeps both contents and reports original/recovery paths.
Four real POSIX-only controls cover public-leaf replacement, interruption after
native claim, UUID collision with an unowned directory and contested restore.
They are Windows skips, not executed Linux results. No general same-user
adversarial-process confinement is claimed for the private quarantine.
Unsupported cleanup fails closed without plain-path fallback.

Windows handle implementation follows the native
[SetFileInformationByHandle contract](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfileinformationbyhandle)
and [CRT handle ownership contract](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/open-osfhandle?view=msvc-170).

Final verification on the bounded safe-cleanup implementation: combined nine
suites, 266 tests in 30.186s, 259 pass / 7 platform skips. After the final
diagnostic-only recovery-path message was made explicit, new adapter + old
parent were repeated: 47 tests in 13.437s, 41 pass / 6 platform skips.
`git diff --check` passes. There is no native Windows full-suite or actual
Linux execution claim. Parent CI must run the real POSIX master dispatch and
quarantine cases before integration. No freeze/state/policy/Raw changes or
scientific acceptance are included in this implementation commit.

Only declared byte/readiness/source consistency is asserted. Complete scope
issuer truth, geographic completeness, scientific adequacy, confirmation,
promotion and production authority remain unvalidated/false.

## Independent review

Reviewed exact implementation commit
`b37cb9efe468ec8247459ebcbadd2512958634a2`. Independent source and native Windows
review: **PASS**, with actual POSIX quarantine/master execution still required
in exact-head Ubuntu CI before integration. This is implementation review,
not scientific acceptance or source authentication.

The reviewer extracted `src/`, `tests/` and the existing G0 policy with
`git -c core.autocrlf=false archive`, then compared the reviewed files to their
Git blobs. The initial Windows archive with automatic CRLF conversion was
discarded as a byte-exact snapshot; no working Raw files were normalized.
Canonical SHA-256 values are:

| File | SHA-256 |
| --- | --- |
| `src/evaluation/stage1_source_adapter.py` | `ffc0f686481f822b1409fef5645c72e1ef68f41c279af1fdf4205773822b9037` |
| `src/research_pdca_adapter.py` | `cd230406dba3d10e738881fb8864b1a29ac2ca7e5948876da47950e507db9ac2` |
| `src/evaluation/full_ledger_stage1.py` | `b114c3a9a0f5197cf8ccc520a30dd95a97b879549b14e7bd4ce3977ee4018079` |
| `tests/test_stage1_source_adapter.py` | `7068ec13e5e2d0a758a833eee11fe791723338e760780c150aafc93a5c058ca7` |

Fresh-process external probes against that snapshot passed 28/28 in 11.290s.
A separate four-case native Windows handle-cleanup harness passed 4/4 in
0.069s. Independently rerun committed targets were new adapter 33 tests
(28 pass, 5 POSIX skips), existing pure evaluator 28/28 pass, and existing
parent 14 tests (13 pass, 1 POSIX skip): 75 tests, 69 pass and 6 skips.
All four reviewed Python blobs parse successfully and `git diff --check`
passes. The independent POSIX harness has six actual-native cases; all six
were explicitly skipped on Windows and are not claimed as executed Linux
evidence. The committed suite contains the corresponding POSIX claim,
contested-restore, collision, interruption and ancestor-swap controls.

The six frozen pre-change pure cases match the entire new default and no-op
callback result dictionaries, including receipt hashes, seed 0 and 2,000
bootstrap replicates. The baseline SHA-256 is
`9a72c2460fbedb3625e6942dbd29fd47cc0d1c22d81ee333a5e87b38175f1641`.
The v1 ten-field request, fixed three candidates, absence of Stage1 fields,
and legacy publication syscall path remain covered by regression tests.

Independent probes verify all three model/prediction hashes before the first
outcome payload read, the same complete forecast row set, exact Task6
`statistics.mean` area aggregation, and native HB-B1 rank-score semantics.
The synthetic complete ledger produces numerator 2 / denominator 3 because
the outside-universe individual remains a miss and the two-ID event counts
twice. Missing IDs are rejected, and UNKNOWN/INCOMPLETE or missing inputs
return no Stage1 metrics while preserving prepared candidates. Supplied
contradictions are checked even when another input is missing. Actual Git
September28 CSVs remain five events/six individuals with NEED_MORE_DATA,
without invented scope or a complete denominator.

Known-event causality is checked at each of four readiness stages and across
observational RAW ancestors, including listed actual records in UNKNOWN
coverage. COMPLETE coverage additionally requires the full horizon end.
Prior scope is checked before outcome reads. Strict JSON, source/ref hashes,
all-row CSV links/counts, sealed paths, shared byte/deadline accounting,
post-fit/final rescans, final receipt expiry and parent post-adapter mutation
rejection were exercised. Source receipt bindings include the prepared receipt
and the exact universe/scores/ledger projection digests.

Publication review reproduced a native link succeeding before TimeoutError,
and a real Windows junction swap after the former path-identity check that
deleted an external sentinel. The final implementation fixes those cases:
v2 records possible ownership before linking, reads back new bytes through
the shared reader, and cleans only newly owned replay/temp artifacts. Existing
same-content replay and foreign replacement fixtures survive. Windows cleanup
uses the verified open handle; a post-fstat leaf replacement survives, and an
attempted ancestor rename is truthfully recorded as native WinError 5 denial.
An ancestor junction present before handle opening produces a residual without
deleting its external sentinel.

POSIX source review confirms pinned directory descriptors and atomic claim
into a private 0700 directory precede inode comparison. A foreign claim is
preserved, no-replace restoration never overwrites another public file, and
both recovery/original paths are reported. Interrupted native claims and UUID
collisions retain ownership boundaries. No plain-public-leaf unlink fallback
or general hostile same-user process confinement is claimed. Actual Linux
execution of these native operations and master dispatch remains a CI gate.

The external harness SHA-256 values are
`667a6eb60bf750029d37933e46775d6c9cd6516ca23ba5cb9236041f74216d7a`
(28 source/pure/parent probes),
`0434c0adfe54cd18adfcd6c4e7588054c75f028d59164022145bcefa163cd883`
(four native Windows handle probes), and
`139961420079557b3e5ed28b72384324c4876e2cba685532ce1cb999fdc8aa4d`
(six POSIX-only probes). They live outside the implementation tree.
The review changed only this section: no source, model, policy, Raw, ORIGINAL,
shared state or cycle files. Issuer authenticity, real completeness, adequacy,
independent confirmation, selection and production remain unvalidated/false.
