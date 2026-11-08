# Evidence receipt read guards — independent review

Review date: 2026-10-26 JST. The filename retains the assigned 20261025 lane.
Scope: ordinary byte-read/path repair under approved spec
`d71f179db11a0f35c249875c3f2d80f99a71e260`; no source qualification.

## Exact reviewed source

Independent source review and fresh native execution PASS on author commit
`30096b4d94f85ad43da72c02019c07c4316b8e1c`, parent
`fcb222801a41820ea57f2b07ce6696cb93644761` (normal main PR117 integration).
The author commit changes exactly three paths: the auditor, its new focused
suite, and the author record. This review adds only this separate document.

| Git-native file | Bytes | SHA256 |
| --- | ---: | --- |
| `src/evidence_audit.py` | 44489 | `cb8e9a99b310b51764bcd74600059fc0c364c405b48307357646332796338515` |
| `tests/test_evidence_receipt_read_guards.py` | 16140 | `6575b062ac032b2c30010b802379f9f57ca614196dc1ffee927e72a2b2cbf519` |

Native Git blobs, index and the code checkout after source-only CRLF decoding
agree. No evidence payload was normalized. Both sources compile without pycache;
`git diff --check` passes. Reversing exactly the two approved replacement blocks
reconstructs the complete parent auditor byte-for-byte; an independent AST check
also finds only `Audit.read` and `_receipts` changed. No schema, Raw, policy,
common helper, old cycle, namespace or budget change accompanies this patch.

`Audit.read` retains its initial tick, expected-size and namespace checks, then
uses existing `master_inventory.local_path` before its explicit stat/open.
`_receipts` guards its fixed anchor before globbing. Leaf JSON and raw/duplicate
references retain the existing central reader, error handling and earliest-time
selection. The lazy imports introduce no scientific-engine dependency.

## Fresh independent native evidence

Bundled Python 3.12.14/MSVC on actual Windows, `-B -X utf8`; no fake OS, fcntl,
filesystem or backend. External harness, outside the worktree:
`.worktrees/evidence-receipt-independent-probes-20261025.py`, physical SHA256
`78e136574b4ba50ce3d0c62e236f4eb91cecf4995919e0f32a08d4431e865fe7`.

```text
python -B -X utf8 ../evidence-receipt-independent-probes-20261025.py .
python -B -X utf8 -m unittest discover -s tests -p test_evidence_receipt_read_guards.py -v
python -B -X utf8 -m unittest discover -s tests -p test_gpx_attachment_intake.py -v
```

- Independent external: **17/17 PASS, 5.032s**, including eight actual junctions.
- New authored suite: **16 methods, 15 PASS/one genuine POSIX-file-symlink skip**,
  0.946s.
- Existing GPX suite: **32 methods, 31 PASS/one genuine POSIX-symlink skip**,
  5.351s; its native junction case actually executes.
- Existing auditor pure selection: **31/31 PASS, 11.419s**. The existing three
  POSIX master-import tests were explicitly excluded from this native command,
  not edited, newly skipped or reported as executed:
  `test_master_executes_audit_and_preserves_snapshot_inventory`,
  `test_only_exact_osm_archive_is_inventoried_not_bridge_runtime`, and
  `test_zero_master_budget_never_invokes_auditor`.

The external harness loads the actual old `4e08f939` Git source and executes the
same synthetic temporary filesystem counterexamples before the new source:

1. Old direct read returns the 39-byte sibling sentinel. The new reader rejects
   with zero opens, reads, bytes and consumed entries.
2. Old inside receipt follows the raw ancestor junction and records PASS. The new
   reader opens only the inside receipt JSON, records FAIL and registers no raw
   receipt or outside payload bytes.
3. Old receipt-anchor junction is actually scanned/read and accepted. The new
   anchor rejects before scandir or receipt open; no payload bytes are charged.
   The whole-audit failure boundary returns FAIL with empty units/events/hashes.

These reproduce the product boundary independently, not merely an observer
placed after an already successful read. Instruments delegate actual native
open/scandir/lstat when permitted. Junctions assert `is_junction=True` and
`is_symlink=False`; cleanup removes only those links. Every outside sentinel
remains byte-identical. Root and root-ancestor links, receipt-directory leaf
links and both raw reference fields are covered by the combined suites.

Portable trailing dot/space, colon and ambiguous `~digits` names reject before
payload open. A real Windows trailing-dot alias is independently shown to access
the ordinary inside fixture before rejection by the new helper path. No actual
8.3 alias existence is claimed. Japanese/internal spaces/dots, `tilde~name` and
`x~1name` remain valid. Missing normal anchor leaves the entire Audit state
unchanged. Normal receipt ordering, duplicate/earliest selection, hash/future-time
FAILs, missing-source handling and unrelated receipt processing remain intact.
Shared actual remaining-plus-one reads, max-size, max-reads, expired deadline,
read-growth limits and same-size hash mutation checks preserve their prior
counters/classification. Budget exhaustion remains runtime failure, not a
misleading ordinary receipt FAIL.

## Whole ordinary compatibility

The independent harness executes all seven ordinary fixtures against three real
implementations: the checksum-pinned hermetic 9c06 original capsule, actual PR117
parent `fcb22280`, and the reviewed source. Capsule identity is 42426 bytes/SHA256
`4d8de850a18a79899f17baf33cbd8ab7d6caeb606550771d3a692cdfba97ccf3`.
Complete canonical typed outputs, every input hash/list order, actual counters,
read order and Path.open order match, with no field exclusions or tolerances.

| Fixture | Reads | Actual bytes | Points |
| --- | ---: | ---: | ---: |
| empty | 0 | 0 | 0 |
| unqualified | 12 | 2212 | 2 |
| qualified_search | 34 | 10227 | 2 |
| qualified_passage | 34 | 10229 | 2 |
| raw_conflict | 15 | 2752 | 2 |
| line_archive | 5 | 768 | 1 |
| bad_line_archive | 4 | 586 | 0 |

The old/new comparison uses actual frozen code, not newly calculated expected
results. Synthetic qualified fixture names confer no real source authority.

## Limits and release disposition

No blocking finding remains within the approved static-link byte-read scope.
This is a source/native review PASS, subject to coordinator exact combined
Ubuntu CI. Native Windows results do not execute the real POSIX cases above.

The independent real trace confirms **one outside leaf lstat still occurs**:
common `local_path` calls `safe_path` before its later ancestor reparse rejection.
This metadata-only seam is explicit and unchanged. The guarantee here is zero
external payload opens on guarded central reads and zero external receipt-anchor
scans, not zero metadata access. Other capture/individual/log/direct-GPX/line/
OSM/recovered-source enumeration remains outside this repair. No concurrent
replacement confinement, atomic snapshot or hard-preemption guarantee is added.

This patch grants no issuer/source/receipt authentication, complete SEARCH or
outcome coverage, Negative/individual/TRAIN qualification, fit, confirmation,
scientific execution, model selection, official issuance or production authority.
No full parent audit or whole-master completion is claimed by these tests.
