# Evidence and receipt read guard v1

Design base: actual main `4e08f93961a627058df5e44c4b554c5549114c4c`.
This is a narrow ordinary path-validation repair, subject to root approval before
implementation. It does not establish source authenticity or qualify observations.

## Reproduced boundary

E executed real Windows temporary-directory/junction probes at that exact base,
without a filesystem/OS facade or protected data. A workspace `data/raw/junction`
pointed to a sibling temporary directory. Its benign `sentinel.bin` contained
39 bytes, SHA256 `b48632a7b8706c9924d5f2d03091d8124abef060cff6246d4b5a834cf82c110b`.
The link was an actual junction (`is_junction=True`, `is_symlink=False`).

- Direct `Audit.read` returned all 39 outside bytes.
- An inside intake receipt naming that raw path passed `_receipts`: two actual
  reads/247 bytes, including the outside payload.
- A separate `evidence/raw_intake` junction to an outside receipt directory was
  scanned, its JSON opened and a normal inside raw reference accepted: PASS,
  two reads/213 bytes.

Cleanup removed only junctions with `os.rmdir`; outside sentinels stayed intact.
These were actual inline probes, not a persisted reproducibility script. Tests
must reproduce them before fixing the product; documentation is not their substitute.

## Minimal change and unchanged contract

Implementation is limited to `src/evidence_audit.py`, new focused tests such as
`tests/test_evidence_receipt_read_guards.py`, and an author review. This spec and
later independent review belong to V. Root owns dependency merges/freeze/CI.
Do not edit `master_inventory`, `master_contracts`, other scanners, policy or Raw.

1. In `Audit.read`, retain existing tick, max-size validation and namespace checks
   in their current order. Resolve the admitted relative path with the existing
   `master_inventory.local_path(self.root, path)` before the method's explicit
   source `stat` or `open`, replacing its current `safe_path` use. Reuse the common
   lexical/ancestor/reparse/containment rules; do not clone them or add a namespace.
2. In `_receipts`, guard `evidence/raw_intake` with that same helper before its
   `glob('*.json')` or any anchor enumeration. A normal missing anchor retains
   the old empty behavior: no receipt reads/checks/requirements are added.
3. Keep per-leaf reads through `a.js`/`a.read`; both receipt JSON and its declared
   `raw_path` or `raw_duplicate_path` therefore receive the central read guard.
   Preserve all existing receipt shape/hash/size/time checks, earliest-receipt
   selection, duplicate behavior and source availability semantics.

No public signature, result field, schema, read order or ordinary read ledger
changes. Keep existing INPUT_PREFIXES/OSM allowance, 100MiB single-source,
512MiB cumulative/4000-read/1M-point limits, remaining+one accounting, consumed
hashes/read sizes, actual counters, deadline and finalization unchanged. Added
guard metadata operations are not payload reads or fictitious charged bytes.
No fresh clock, budget reset, parser/error-normalizer or new dependency.

Direct invalid-path reads reject before payload open. A rejected receipt leaf
uses its existing FAIL handling and is not registered in `a.receipts`; unrelated
receipt processing retains its current behavior. Invalid anchor resolution
propagates to the existing whole-audit failure boundary, which returns FAIL with
empty observation units. Preserve existing runtime-budget classification. Do not
invent new receipt success or source-role semantics.

## Exact scope limitation

The guarantee is **zero external payload opens on these guarded read paths and
zero external receipt-anchor scans**, including static junction/ancestor links.
It is not zero external metadata access. Existing `local_path` first calls
`safe_path`; E traced one outside-leaf `lstat` through a Windows junction before
the later ancestor reparse check rejected it. This known metadata-only seam is
not repaired or concealed here. Any common-helper ordering repair is a separate
reviewed change, not an implied consequence of this patch.

Nor does this fix guard enumeration in every other legacy capture, individual,
raw-log, direct-GPX, line-archive, OSM or recovered-source scanner. Central reads
reject their invalid payload paths; their preceding glob/rglob/scandir behavior
is outside this slice. No atomic snapshot, hostile concurrent-replacement defense
or hard-preemption guarantee is added.

## Required RED/GREEN and release evidence

- Reproduce the three actual Windows cases above. Then verify direct read rejects
  with zero external opens/zero payload bytes, a receipt cannot PASS/register an
  outside raw path, and an anchor junction is rejected before external scandir or
  receipt open. Instrumentation must delegate real native operations when allowed.
- Cover receipt-leaf links, linked raw ancestors/root ancestors and the intake
  anchor, using sibling synthetic temporary files; preserve all outside bytes.
  Remove only created links before temporary-directory teardown.
- Use actual POSIX symlinks on Ubuntu CI. Windows junction success does not count
  as POSIX execution. Assert class/rejection ordering and the real platform's
  message rather than requiring Windows Reparse text on POSIX.
- Cover common portable aliases (trailing ASCII dot/space, colon and ambiguous
  `~digits` components) before payload opens. Preserve valid Unicode/internal
  spaces/dots and nonambiguous tilde names under the existing common rules.
- Check absent normal anchor, normal inside receipts/raw duplicates, hash/time
  failures, read budget/remaining+one, expiry and ordinary final source rereads.
- After the normal reviewed PR117 merge, run its checksum-pinned seven-case
  original/current hermetic CI oracle: complete canonical typed objects, hashes,
  actual read counts/bytes/points, read order and Path.open order must remain
  identical for ordinary inputs. No exclusions, regenerated goldens, Raw text
  normalization or CI dependency on an external Git object/worktree/network.

E's prior post-read observer admitted 104 normal reads/15 paths with all seven
whole pairs equal; it establishes compatibility feasibility only. It did not
guard before opening and is not proof of this implementation. Final acceptance
requires exact-source independent review, native evidence and actual Ubuntu CI.
Source/receipt issuer authenticity, SEARCH/outcome/Negative/individual/TRAIN
qualification, fit, production permissions and master completion remain unchanged.
