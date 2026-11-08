# Evidence receipt read guards — author record

Execution record: 2026-10-26 JST; the lane filename retains the approved
20261025 identifier. This is author evidence, pending independent exact-source
review and coordinator Ubuntu CI, not scientific qualification.

## Approved scope and implementation

Approved spec: `d71f179db11a0f35c249875c3f2d80f99a71e260`,
`docs/specs/evidence-receipt-read-guard-v1.md`. Implementation starts from
`fcb222801a41820ea57f2b07ce6696cb93644761`, after the coordinator normally
merged main PR117 `45c183` into the isolated branch
`codex/evidence-read-guards-20261025`.

Only three author paths change: `src/evidence_audit.py`, new
`tests/test_evidence_receipt_read_guards.py`, and this record. The runtime diff
is four inserted/two removed lines, restricted to:

- `Audit.read`: after the existing initial tick, max-size and namespace checks,
  use existing `master_inventory.local_path` instead of `safe_path` before the
  explicit source stat/open. No alternative reader, counter or clock is added.
- `_receipts`: resolve the fixed `evidence/raw_intake` anchor through that same
  helper before globbing. Keep all leaf reads through `a.js`/`a.read` and all
  receipt validation/earliest-selection/duplicate behavior unchanged.

An AST comparison confirms every other method/function is unchanged. Common
helpers, other enumerators, schemas, namespaces, policy, source roles, budgets,
Raw/ORIGINAL, state/cycles/freeze, models and permission gates are untouched.

Git-native UTF-8/LF source identities before release:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `src/evidence_audit.py` | 44489 | `cb8e9a99b310b51764bcd74600059fc0c364c405b48307357646332796338515` |
| `tests/test_evidence_receipt_read_guards.py` | 16140 | `6575b062ac032b2c30010b802379f9f57ca614196dc1ffee927e72a2b2cbf519` |

These are code bytes; CRLF checkout handling never normalizes an evidence
payload. Both files compile without creating pycache; `git diff --check` passes.

## Actual RED to GREEN

All filesystem targets are synthetic temporary files, with outside targets in
sibling temporary directories. The marker is 39 bytes/SHA256
`b48632a7b8706c9924d5f2d03091d8124abef060cff6246d4b5a834cf82c110b`.
On native Windows the tests create real mklink/J directory junctions and assert
`is_junction=True`, `is_symlink=False`. Instrumented opens/scans delegate to the
real native operations; there is no filesystem or OS facade.

Before editing runtime, three individually fail-fast tests were RED:

1. Direct `Audit.read` followed the raw ancestor junction and did not raise:
   one failure, 0.161s.
2. A normal inside receipt's outside raw reference was actually opened and
   accepted: one failure, 0.102s.
3. An intake-anchor junction was actually enumerated/read instead of rejected:
   one failure, 0.102s.

The minimal runtime change made all three GREEN together in 0.225s. Direct
rejection now has zero payload opens, zero reads/bytes and no consumed entry.
The raw-reference receipt reads only its ordinary inside JSON, records FAIL and
does not register that raw reference. The bad anchor is rejected before its
external scandir or JSON open; whole audit returns FAIL with empty units/events.

Created links are removed themselves before temporary-directory cleanup:
Windows junctions by rmdir, POSIX links by unlink. No recursive operation follows
an outside target. Tests check that the outside marker remains byte-identical.

An expanded test initially used an accidentally trailing-space Unicode directory
in its fixture setup; Windows could not create the intended file. It was changed
to a valid internal-space name before the product read. That setup error is not
a product RED/security finding.

## Final bounded verification

Native bundled Python 3.12.14/MSVC, `-B -X utf8`, no installs or fake fcntl.
Fail-fast verification from this tree:

```text
python -B -X utf8 -m unittest discover -s tests -p test_evidence_receipt_read_guards.py -v -f
python -B -X utf8 -m unittest discover -s tests -p test_gpx_attachment_intake.py -v -f
```

- New guard suite: **16 methods, 15 PASS/one actual POSIX-file-symlink skip**,
  0.764s. Ordinary directory-link tests run real junctions on Windows and actual
  symlinks on POSIX. No Windows success is counted as POSIX execution.
- Unchanged GPX intake suite: **32 methods, 31 PASS/one actual POSIX skip**,
  4.741s. Its checksum-pinned original-reader capsule remains unchanged.
- Existing `EvidenceAuditTests` native pure selection: **31/31 PASS**, 10.491s.
  The native command explicitly excluded only the existing POSIX master-import
  methods `test_master_executes_audit_and_preserves_snapshot_inventory`,
  `test_only_exact_osm_archive_is_inventoried_not_bridge_runtime`, and
  `test_zero_master_budget_never_invokes_auditor`. No existing test was changed,
  given a new skip or represented as executed; full Ubuntu CI must run them.

The existing hermetic seven-case no-attachment oracle compares complete
canonical typed old/current results, input hashes, actual read counts/bytes/
points, read order and Path.open order. All seven remain exact on the new guard.
There is no new golden, field exclusion, tolerance, platform digest allowlist,
Git-history/network dependency or Raw normalization.

Additional controls cover receipt leaf links, linked roots/ancestors, portable
trailing-dot/space/colon/ambiguous-tilde aliases, valid Unicode/internal spaces/
dots/nonambiguous tilde names, missing anchor, raw_duplicate_path, earliest
receipt selection, ordinary hash/future-time FAILs and unrelated valid receipts.
They also preserve namespace/max-size/expiry-before-guard ordering, exact
remaining-plus-one bytes, read budget failures, consumed-hash rereads, and
existing source availability/diagnostic-only semantics.

## Explicit limits and remaining gates

The guarantee is zero external payload opens on the guarded central read paths
and zero external receipt-anchor scans for static invalid links. It is not zero
external metadata access: current common `local_path` calls `safe_path` first,
and the independent native trace found an outside leaf lstat before later
ancestor reparse rejection. This metadata-only ordering seam is unchanged.

Other legacy capture/individual/raw-log/direct-GPX/line-archive/OSM/recovered
enumeration remains outside this slice. Their central payload reads now use the
guard, but preceding glob/rglob metadata/enumeration is not declared confined.
No atomic snapshot, concurrent replacement defense, hard preemption or process
RSS claim is added. Existing caps/deadline/actual-read accounting are unchanged.

No full unsupported native-suite rerun is used as evidence. Independent review
and genuine combined Ubuntu CI remain pending at author release; coordinator
owns integration and the new freeze/state. No source/receipt issuer
authentication, SEARCH/complete outcome/Negative/individual/TRAIN qualification,
model fit, promotion or production authority is granted.

## Coordinator integration checkpoint

Actual checkpoint UTC 2026-10-25T15:28:52.808342+00:00. Source remains exactly `30096b4` after independent doc-only review `54eddbd5`. Coordinator related65 methods:63PASS/two genuine POSIX skips,6.299s. Existing complete seven-case output/read-ledger oracle remains exact; no old golden or Raw bytes changed. Actual Ubuntu execution of the new source is pending.

Native-Git96-reference cycle `20261025-evidence-read-guard-01`: code SHA256 `929f40480ab9727caf382fe4219b0ea353459769d0eae96ffcf77d45db0705f0`, cycle contract SHA256 `6c45bbaf3cb9580dc56def20a36c93090434e86498e3349e68bb1fe6fd94d203`; native snapshot CLI CONTRACT_VALIDATED. Frozen-cycle pointer hashes the physical JSON separately. Prior cycles remain immutable.

State reconciles actual PR116 exact/fresh1416 tests/23skips, PR117 exact/fresh1448 tests/24skips and the separate fresh-main23-step August audit. The parallel PR50 preservation branch is not main intake or accepted science. One outside leaf lstat, other legacy enumerators and non-atomic hostile-concurrency limits remain explicit. Master NOT_COMPLETE, science NOT_VALIDATED, real TRAIN and Negative counts remain zero.
