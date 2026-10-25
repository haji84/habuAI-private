# Independent GPX attachment intake review — 2026-10-25

## Exact source and verdict

Independent bounded source/Windows review **PASS**, with no remaining blocking
finding, on `9bf8c6564d08a9613f94cbc3be225c0caea06cca` in
`codex/gpx-attachment-intake-20261025`. This follows the approved
`e5c1e812009d11e7373d283eff74e10c9e18e1f1` spec. Runtime source is byte-identical
to the earlier released `3babc182a05753da516651565437080c46046ff0`; the later
commit adds the hermetic legacy CI oracle, its original-code capsule and author
record. The reviewer changed only this new document in Git.

Exact Git-native UTF-8/LF identities were independently read, hashed and compiled:

| Path | Bytes | Git blob | SHA256 |
| --- | ---: | --- | --- |
| `src/gpx_attachment_archive.py` | 11557 | `78d86695f9639e0d4993d6bde75bf9202b352bbb` | `72fb3506aa94d0c2f8706f5474bd28257b109981baad80d7d54c4b5790815a45` |
| `src/evidence_audit.py` | 44386 | `0d62e6f5cf6248a2ab4ec861c8dbae8527829018` | `2ae896d4e95094d9d0edcc1bdc18d97059e7bf4d547ad0e415c3a6ac2f1889ab` |
| `tests/test_gpx_attachment_intake.py` | 28350 | `72763b7af37b7460fb0f21b5ebb3b999b2d066c6` | `08d12425235043a68265dd0552a287905c056e539d9fec0a9076986ec9574380` |
| `tests/fixtures/evidence_audit_9c06_original.py.txt` | 42426 | `6b419055f7abe82e4aedd0984659c886afc0b110` | `4d8de850a18a79899f17baf33cbd8ab7d6caeb606550771d3a692cdfba97ccf3` |

Working code matches those Git bytes after code-only CRLF-to-LF handling. The
auditor's native Windows working-byte SHA is
`6d0debe94a59492bebd4be14e7aa685c1183c520625701de1b6684acefc44ed8`.
This is source-fixture checkout handling, never Raw/source-payload normalization.
The capsule equals actual `9c06f3d8b059439991f444dee8c7b30f35b2b6bc` auditor
Git bytes. Sixteen original function/class ASTs remain unchanged; only
`_trajectories` and `audit_evidence` gain hooks, plus one private finalizer.

## Findings and their resolution

1. **Premature Base64 padding — actual rejected-contract input accepted.** A real
   XZ stream with length modulo three equal to one or two was encoded as an early
   padded quartet followed by complete quartets. All native manifest arithmetic,
   compressed/raw sizes and hashes agreed. The joined stream failed strict
   Base64 validation, but per-part validation initially returned verified raw
   bytes. The first independent run had 22 passes and this one failure, 2.730s.
   Final code rejects `=` in every nonfinal part before decoding it. Genuine
   native PR50 transport still passes. This was an integrity-admission defect,
   not evidence of new observation/source authority.
2. **Overlong JSON integer — wrong local failure class.** A manifest below 64KiB
   containing a 5000-digit integer raised Python's conversion-limit `ValueError`
   instead of `GpxAttachmentError`; the independent regression initially errored
   in 0.043s. The outer audit already failed and cleared public units, so this
   did not demonstrate a scientific bypass. Final code normalizes the helper's
   own JSON-parse error only. Caller checks stay outside that catch, and existing
   dedicated errors preserve identity.
3. **Hermetic legacy CI acceptance missing.** The seven old/current comparisons
   initially existed only in an external Git-dependent manual harness. That did
   not satisfy the spec's immutable-reader CI requirement. The coordinator
   explicitly authorized the readable exact original capsule and one seven-case
   whole-output/read-ledger test. The final commit provides both without changing
   runtime or the spec. No manual-only test is presented as a CI fixture.

The author's separate escaped-surrogate repair is present and independently
exercised by the owned suite. No production source/test edit was made by the
reviewer to repair these findings.

## Fresh verification

Runtime: bundled Python 3.12.14/MSVC on Windows, `-B -X utf8`; no installations,
fake POSIX interfaces, fake decoder or backend were used. From the intake tree:

```text
python -B -X utf8 ..\gpx-attachment-independent-probes-20261025.py .
python -B -X utf8 -m unittest discover -s tests -p test_gpx_attachment_intake.py -v
python -B -X utf8 ..\gpx-attachment-independent-pr50-20261025.py .
```

- Final exact release: **29/29 external methods PASS**, 3.272s, no skips.
- Final exact release: **32 owned methods, 31 PASS/one genuine POSIX skip**,
  4.684s. This includes the permanent seven-case complete legacy comparison.
- Independent oracle controls also rejected seven deliberately divergent current
  outputs and an actual byte-tampered private copy of the old capsule. These are
  expected negative-control failures, not product failures. Code/capsule checks
  and those controls completed in 2.928s.
- An earlier identity sweep met an actively edited test file while the authorized
  test-only extension was being written; it was not treated as a source finding.
  Final verification used the stable exact commit and all four pinned files.

The external probes independently cover exact crosswalk hashes/sizes/read order,
pre-part schema/membership rejection, malformed JSON/Base64/XZ, trailing and
concatenated XZ, decoder memory, raw-size excess, and rejected raw-hash work
remaining charged to one decoded allowance. They also check ordinary
`ValueError`, `GpxAttachmentError` and `TimeoutError` callback object identity;
shared discovery/read/byte/point/deadline limits; direct/line/attachment raw-SHA
deduplication; and complete physical final reread accounting.

Actual Windows junctions were tested at root/ancestor, anchor and archive
positions. Pre-open rejection produced zero external scans/payload opens. A
genuine late archive-directory swap to an external junction after GPX parsing
also produced FAIL, no public units/events and zero external final-read opens;
the external sentinel survived. Cleanup removed the junction itself with rmdir,
never recursively deleting its target. Membership insertion after decode, during
unrelated later work and during final rereads, late byte changes, a newly created
previously missing anchor and final-seal expiry all prevented retained public
units or outcome events.

The hermetic CI oracle runs distinct original code against current code on the
same actual dependencies and synthetic inputs: empty, unqualified, qualified
SEARCH, qualified PASSAGE, raw-count conflict, valid line archive and invalid
line archive. It compares complete canonical typed results, all input hashes,
actual read counts/bytes/points, read order and actual Path.open order. No field
exclusions, platform digest allowlists, regenerated golden or tolerances apply.
It needs no network, historical Git object or PR50 transport in CI.

External probe identity: 21720 bytes, SHA256
`90db97e1d14f17efe84da9c4a1d662c55696699e1c4ad3fa4205dbefef3ab6a4`.
Independent manual script: 3706 bytes, SHA256
`8ea92888931e5fffcf93bf7839aee5dcb2fa7125495c3dac02ab622c36887fa0`.
Both live outside Git in `.worktrees/`; they are review tools, not CI inputs.

## Genuine PR50 temporary-input regression

Seven immutable Git blobs at exact PR50
`86127f79163fd004cf65b5b6fc8ab2ad5f154ac8` were independently materialized into a
TemporaryDirectory outside Git. No checkout/merge, persistent Raw copy, report ZIP
or capture-transcription admission occurred. The final manual run took 0.735s on
the runtime subsequently proved byte-identical in the final source commit.

Prefix: `data/raw/attachment_archives/gpx/7ee4f005cc27fb3d680bd05b7de19d5e9d33241b906c545bbb356c885a2849aa/`.

| Physical file | Bytes per pass | SHA256 |
| --- | ---: | --- |
| `manifest.json` | 601 | `5c5032c570f35880d5ab04ec10be27c90d8a19167264f222d57ecd5312ebb344` |
| `part_000.b64` | 100000 | `0f30222b10948efbf6d98e2c4c8e97ef42f40cd023ebad15df2114c569a1417c` |
| `part_001.b64` | 100000 | `b2624c7600e2aa2b8c7a73726e968c195ffada7ab33d53f2852a4e529e5ef77f` |
| `part_002.b64` | 100000 | `a8380e940b425d02ecf460ad14b6502bd7b6f83688e94bc496612ec2f6ea5622` |
| `part_003.b64` | 100000 | `d91d844095c95d7f5bda0f10f3985451b0599d3c359f93d96acfeae565c65b09` |
| `part_004.b64` | 100000 | `e57d7d3e1e97f1b08fd2cfdbf9687e3cd7d37dce7ef1625c8a7243c6af33eb2b` |
| `part_005.b64` | 23664 | `611b6553cedb6ba5c5c7677bcf944fb9e02871ed22188efb7082509546b5ea42` |

The exact compressed identity is 392748 bytes/SHA256
`23db6564258f4c09d99e974df03cfd0c849c65fe46e6f574cbccd98a8013c592`;
decoded identity is 4675850 bytes/SHA256
`7ee4f005cc27fb3d680bd05b7de19d5e9d33241b906c545bbb356c885a2849aa`.
The audit parsed 17731 valid points and charged exactly 4675850 decoded bytes.
Its actual read ledger is the listed seven files in numeric order, followed by
the same seven guarded final rereads: **14 reads/1048530 physical bytes**, two
524265-byte passes. Every physical SHA/size matches the crosswalk.

Result: PARTIAL, 1123 sampled units with all labels null, zero positive/negative
units, no eligible outcome events, denominator NOT_ESTABLISHED and scientific
validation NOT_VALIDATED. Physical manifest SHA remains distinct from raw GPX
SHA; roles remain diagnostic_only, quality/recovery/search UNKNOWN and historical
availability null. This proves bounded reader compatibility, not search intent,
complete owner outcomes, capture qualification or predictive skill.

## Limits and remaining integration gates

No full integrated main/parent input run is claimed. Genuine POSIX execution and
the final combined Ubuntu CI/freeze remain coordinator gates. The author's
pre-final broad native diagnostic is not final-fix coverage or a passing full
suite. No runtime limit was raised, no Raw/source/role/policy/STATE/freeze was
edited, and no source authentication, source promotion, Negative label, TRAIN,
fit, confirmation, formal KPI or production authority is granted.

Checks are cooperative around bounded native codec/XML calls and final rereads.
Decoder memlimit is not process-RSS measurement; retained derived-byte accounting
is not a claim to count invisible native work. The final source closure is
ordinary guarded I/O, not an atomic snapshot against arbitrary concurrent changes
after the last check. These limitations remain explicit rather than being hidden
by a successful transport receipt.
