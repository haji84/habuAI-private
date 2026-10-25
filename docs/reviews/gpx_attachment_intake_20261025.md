# GPX attachment intake implementation record — 2026-10-25

Author record, not independent review or scientific qualification. Approved design
is `docs/specs/gpx-attachment-intake-v1.md` at `e5c1e812009d11e7373d283eff74e10c9e18e1f1`.
Implementation checkout base is `a82c5d9c52e0d1629b030efd64c1eb8bf2d0650f`,
which normally incorporates actual main PR115 `c860795` and the approved spec.

## Exact runtime and scope

Only the new helper/test, narrow `evidence_audit.py` hook/private accounting/final
membership checks and this record are runtime implementation deliverables. The
coordinator subsequently approved the immutable old-reader test capsule below to
close a concrete hermetic-CI acceptance gap. The approved
spec is unchanged. No Raw, source policy, namespace allowlist, requirements,
workflow, state, cycle, parent, restore CLI or original-promotion change.

Canonical source bytes use UTF-8/LF, as Git blobs do:

| File | Bytes | Git blob | SHA256 |
| --- | ---: | --- | --- |
| `src/gpx_attachment_archive.py` |11557|`78d86695f9639e0d4993d6bde75bf9202b352bbb`|`72fb3506aa94d0c2f8706f5474bd28257b109981baad80d7d54c4b5790815a45`|
| `src/evidence_audit.py` |44386|`0d62e6f5cf6248a2ab4ec861c8dbae8527829018`|`2ae896d4e95094d9d0edcc1bdc18d97059e7bf4d547ad0e415c3a6ac2f1889ab`|
| `tests/test_gpx_attachment_intake.py` |28350|`72763b7af37b7460fb0f21b5ebb3b999b2d066c6`|`08d12425235043a68265dd0552a287905c056e539d9fec0a9076986ec9574380`|
| `tests/fixtures/evidence_audit_9c06_original.py.txt` |42426|`6b419055f7abe82e4aedd0984659c886afc0b110`|`4d8de850a18a79899f17baf33cbd8ab7d6caeb606550771d3a692cdfba97ccf3`|

The helper guards only canonical `data/raw/attachment_archives/gpx/<rawSHA>/`
members before metadata/open, bounds discovery, validates all 15 native fields,
decodes exact numeric parts, verifies compressed identity before bounded XZ,
and returns phase bytes/crosswalk without writing. Every physical read is through
the original Audit reader. A caller-owned decoded counter charges returned chunks
before later validation and survives rejected archives. Existing 512MiB/4000-read/
1000000-point limits and actual caller deadline remain shared. New intake has a
100MiB aggregate decoded allowance and 128MiB decoder working-memory limit.

The hook preserves physical manifest versus reconstructed GPX identities,
registers diagnostic crosswalks even for raw-content aliases, and uses the old
raw-SHA duplicate exclusion and parser. Membership is checked after GPX and after
the original complete consumed-file reread pass. New source roles remain UNKNOWN/
diagnostic unless independently qualified elsewhere. Default audit budget remains
300 seconds without inventing an existing upper-bound validation.

## TDD and repairs

- Initial five tests: **five intended failures**, 0.037s, before product code;
  missing helper, absent trajectory intake and missing late-membership rejection.
  Minimal implementation: five passes, 0.369s.
- Escaped unpaired-surrogate metadata counterexample: one failure, 0.048s;
  UTF-8-encodability admission before part reads: one pass, 0.035s. This prevents
  returning metadata that the canonical JSON receipt cannot serialize.
- Independent E found premature Base64 padding: all compressed/raw identities
  agreed, but padding in a nonfinal quartet made the joined Base64 stream invalid.
  Authored real-XZ counterexample: one intended failure, 0.388s. The repair rejects
  `=` in every nonfinal part before decoding it; no native transport is rewritten.
- E also found Python's overlong-JSON-integer ValueError escaping the dedicated
  format class. Authored counterexample: one intended failure, 0.036s. Normalize
  ValueError only around the helper's own JSON parse, rethrowing existing dedicated
  errors unchanged with all caller checks outside. Runtime-repair owned suite:
  **31 methods, 30 passes, one genuine POSIX skip**, 3.794s.

The owned suite covers strict schema/JSON/part admission, early unsafe-path
rejection, actual XZ memory failure, decoded output excess and shared rejected-work
charges, read/byte/point/discovery limits, shared expiry, callback exception identity,
late payload/membership/new-anchor mutation, exact actual read accounting, raw
alias exclusion and UNKNOWN-safe outcomes. An actual native Windows junction test
passed with zero external directory scans or payload reads. The POSIX symlink test
is genuinely skipped here; no fcntl substitute or fake backend is installed.

Commands use
`C:\Users\qq113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
with `-B -X utf8`, from this worktree:

```text
python -B -X utf8 -m unittest discover -s tests -p test_gpx_attachment_intake.py -v
python -B -X utf8 ..\gpx-attachment-independent-probes-20261025.py . -v
python -B -X utf8 ..\gpx-attachment-manual-regression-20261025.py .
git diff --check
```

E's independent external harness initially reported 22 passes/one concrete padding
failure in 2.730s. The author reran that 23-probe version after padding repair:
23/23 pass, 2.843s. E subsequently expanded the independent controls and reproduced
the JSON integer issue. After both repairs, the author ran the unchanged final
external harness: **28/28 pass**, 3.909s. Its SHA256 is
`570a13b3f55ef7dda5b1bded24fdbf053b29e83e4fbf5f9382ed907ffc9f926a`.
This author rerun does not replace independent exact-commit review. E separately
reported a working-tree 27/27 pass and matching genuine PR50 audit before the final
integer normalization; final exact-commit review remains pending.

## Whole legacy compatibility and genuine PR50 regression

The separate external native harness loaded original `9c06f3d` auditor bytes into
a distinct temporary module: 42426 bytes, SHA256
`4d8de850a18a79899f17baf33cbd8ab7d6caeb606550771d3a692cdfba97ccf3`.
Sixteen old functions/classes retain exact ASTs; only `_trajectories` and
`audit_evidence` receive new hooks, with one new private finalizer.

Seven same-runtime old/current pairs compare **complete canonical typed objects**,
input hashes, real read counts/bytes, read order and actual `Path.open` order:
empty, unqualified direct GPX, qualified SEARCH plus full coverage, qualified
PASSAGE plus full coverage, conflicting raw counts, valid line archive and bad
line archive. All equal with no exclusions or platform hash allowlists. This is a
same-runtime original-source oracle, not regenerated expectations from new code.

The same harness separately materialized seven exact PR50 Git transport files at
`86127f79163fd004cf65b5b6fc8ab2ad5f154ac8` into a temporary input outside Git.
It did not check out/merge PR50, commit its Raw, restore an output or load the report
ZIP/manual-capture transcriptions. Actual new audit results:

- Original decoded GPX: **4675850 bytes**, SHA256
  `7ee4f005cc27fb3d680bd05b7de19d5e9d33241b906c545bbb356c885a2849aa`.
- **17731 actual parsed points**, **14 actual reads**, **1048530 actual bytes**:
  two complete physical passes of 524265 bytes. Exact physical part references
  equal the independently materialized seven-file identities.
- `PARTIAL`; **1123 sampled units, all labels null**; outcome denominator
  `NOT_ESTABLISHED`. No fit, SEARCH, complete outcome or source-role upgrade.
- Audit SHA256 `2a79a70f221d1eba80ae880ecdd7df575a5e9e453b790536267be5ef4a0f344a`;
  full result SHA256 `346504cf8cfe0fc86f722e8b485f7b5e5c0748a1f3ef0194bf5ac12335cbffdf`.
  These identify this fixed actual-runtime manual result, not a cross-libm golden.

The final combined manual run took 4.047s. External harness SHA256:
`23c7793fb828624baae7f60fc3ba0c722ef849f5ae714ae67d8b59cc6ef85576`.
Readable external receipt `../gpx-attachment-manual-regression-20261025.json`,
23576 bytes, SHA256
`348de27df6da514c5503c102c4cb0b70bb844f2f4eaf07a5e424e01088d8b48e`.
CI does not depend on this file, PR50 objects, another worktree or network access;
its new fixtures are self-contained synthetic transport/XML.

## Hermetic CI compatibility follow-up

Independent E correctly identified that the first source release `3babc182` kept
the seven whole-object controls only in an external Git-dependent manual harness,
while the approved spec also required this protection in hermetic CI. The
coordinator authorized only a readable old-code capsule, one test in the owned
test module and this record; runtime blobs remain exactly `3babc182`.

The capsule is the exact original `9c06f3d` auditor, with the 42426-byte/SHA identity
above checked **before** compilation into a distinct temporary module object.
Only this code fixture uses `read_text(encoding='utf-8').encode('utf-8')` to recover
canonical LF across checkout conventions. This does not normalize any Raw or
consumed scientific source. CI invokes no Git command and needs no PR50 object,
network or external worktree. Existing bounded synthetic fixtures construct all
seven cases, and the test compares full canonical typed results, all input hashes,
real read byte/count/point ledgers, read order and actual file-open order.

The new test first failed for the missing capsule (one intended failure, 0.003s).
After installing the checksum-verified original, all seven pairs passed (one
method, 1.871s). Fresh complete owned module: **32 methods, 31 passes, one genuine
POSIX skip**, 4.543s. No runtime, spec, Raw or policy change accompanies this fix.

## Native limits and remaining gates

Related native runs: evidence audit 34 methods/31 passes/three unavailable-fcntl
errors (9.561s); learning snapshot 14/11 passes/three unavailable-fcntl errors
(4.049s); inventory 26/22 passes/four explicit platform skips (3.695s); restore
CLI four passes (0.096s); observation eligibility 13 passes (0.011s).

The six errors are the existing parent-import cases:
`test_master_executes_audit_and_preserves_snapshot_inventory`,
`test_only_exact_osm_archive_is_inventoried_not_bridge_runtime`,
`test_zero_master_budget_never_invokes_auditor`,
`test_master_failed_audit_never_calls_model_adapter`,
`test_master_generated_workspace_is_recoverable_without_input_exemption`, and
`test_master_passes_shared_budget_into_builder`. No skips or test edits hide them.

A full native `unittest discover -s tests -v` was started once before the final
small admission repairs and was still running at the first author release. During
this test-only follow-up it completed: **1316 methods, 1175 passes, two failures,
120 errors, 19 skips**, 689.618s. Its transcript is external
`../gpx-attachment-full-native-20261025.log`. It imported pre-final helper code and
is **not** a passing or exact-final-source gate; no full native rerun was made.

The two failures are
`test_owner_monthly_count_does_not_override_missing_raw_event_bytes` (the expected
owner-count rejection message was preceded by a native source-byte mismatch) and
`test_checkpoint_callback_persists_before_hard_exit_and_fresh_restore` (expected
exit77, actual exit1 with missing `fcntl`). The 120 errors comprise 87 missing
`fcntl`, eight native symlink-privilege errors, five missing-file errors, 19
reported source-byte/hash mismatches and one missing `sklearn`. These are retained
diagnostics, not silently converted to skips or fixed by source normalization.
No fake POSIX, dependency install or protected-input change was performed.
Known native limitations and coordinator-owned freeze remain outside this scope.
Independent exact-source review, coordinator freeze and genuine full Ubuntu CI
remain required. No full integrated parent audit, scientific fit, qualification,
formal KPI, authority or original promotion is claimed.

## Independent review

Pending independent exact-source review; this author record does not grant PASS.
