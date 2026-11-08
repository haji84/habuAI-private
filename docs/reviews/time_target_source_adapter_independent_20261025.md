# Independent time-target source adapter review

Verdict: **PASS for the bounded standalone development diagnostic**, at exact
repaired commit `a7ced5670127a1993fc29b4be8b9d194fa668d1a`. This is an independent
source/API review, not approval of source authenticity, historical prereveal,
scientific adequacy, parent registration, official performance or production.
Actual Ubuntu full integration remains the coordinator's separate gate.

## Exact scope and bytes

The author release changes five files: the new T2 source module and tests,
the reviewed specification and author record, and a narrow repair limited to
the explicit Stage1 export path. Canonical Git-blob identities verified after
all test processes completed:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `src/evaluation/time_target_source_adapter.py` | 12432 | `afbc2fa527c89e88c31c782fd8f0a1292bbebf01e044de42d41d2765876929f5` |
| `src/evaluation/stage1_source_adapter.py` | 41569 | `092f851495c34b8cb3b00e68a386d520ea7cee38239049c65e683a6739b03cf0` |
| `tests/test_time_target_source_adapter.py` | 29451 | `f50c0206c945be152e9a7fc7b3a7f1a5a8c92a0300198e163dfe37ca28e3c93e` |

Against pre-implementation `9482ba836659d92f62fe9d0a0bdeb32a8752b5d9`, existing
public `evaluate_stage1_sources` and `evaluate_stage1_sources_v2` ASTs are
identical. The shared `_evaluate` changes are conditional on explicit export;
`project_stage1_sources_v2` loses its global structural exception normalizer,
and `_configured_export_prepared` is new. No model math, old scorer/matcher,
Raw/ORIGINAL, workflows, permissions, state or cycle is changed by this review.

## Findings reproduced and repaired

1. The draft whole-API catches recast caller context/check exceptions as missing
   files or malformed JSON. Actual valid fixtures showed FileNotFoundError and
   five structural exception types losing object identity at entry or during
   the delegated export. Root independently reproduced 12 failing subcases
   among 16. The two new APIs now retain only named capacity/budget translation.
   Bounded native admission alone classifies native structural failures; its
   local callback wrapper records the actual exception object and reraises it
   unchanged. There is no context mutation, proxy, new clock or traceback-origin
   inference. Independent final probes cover entry, actual admission, actual
   export and the outer final-seal boundary.
2. A one-shot FileNotFoundError, or ValueError with the exact transport-missing
   text, from a caller check inside the actual capture read was swallowed by
   legacy `read_node` missing handling. The draft returned sealed NEED_MORE_DATA
   with `FILE:captures` even though that file existed. Root reproduced RED,
   then repaired export-only static-absence classification: guarded `is_file()`
   determines normal absence and the actual reader is outside those catches.
   Final fresh probes preserve both one-shot exception objects; a genuinely
   absent capture still yields NEED_MORE_DATA. A disappearing-file race can
   propagate its actual I/O failure without publishing a partial result.
3. Root's final self-audit found that the caller's oversized byte ceiling was
   tightened only inside G0, after the wrapper's first metadata read. An
   independent real first-Path.open observer against Git `ca4865763b94813547e42370ee985e8d294d3aca`
   failed at 2147483649 versus the 2147483648-byte maximum (1.024s), then passed
   against the repair (1.832s). This uses normal small files, with no fabricated
   2GiB I/O. The same context is now restricted before metadata reads; the probe
   also checks that its absolute deadline cannot grow and its already-charged
   bytes and initial receipt counter remain intact.

## Independent execution

External probes live outside the product worktree in
`.worktrees/t2-source-independent-probes-20261025.py`, SHA256
`e9d5875c90adfa8a6cd0f55470020ca0b91c738626a89359cbd1c00640f6c0ed`.
They reuse the hermetic source fixture for real guarded files and validators,
then independently check bindings, canonical seals and side effects. They do
not substitute a POSIX engine, filesystem or backend.

- Fresh process at exact repaired release: **22/22 external methods PASS,
  45.752s**.
- Fresh process at exact repaired release: **27/27 authored T2-source methods
  PASS, 63.456s**, no skips. Both commands completed with exit code zero.
- The preceding exact `ca486` snapshot independently passed 21 external methods
  in 46.394s and 26 authored methods in 64.064s. These are retained as that prior
  snapshot's results, not substituted for the final repaired-source runs.
- Root separately reports final affected 26+19 export methods **45/45 PASS,
  84.759s**. Its broader 117-method pass imported code before the last read-node
  repair; that broader result is not final coverage of that repair. Earlier
  draft external passes likewise are not used instead of these fresh runs.
- Final source diff, canonical Git hashes, compile checks for all three listed
  Python files and `git diff --check` were clean. Between `ca486` and `a7ced`,
  the only runtime change is entry restriction of the existing context; export
  source bytes are unchanged.

The independent matrix verifies two complete actual G0 reloads and exactly one
actual Stage1 export on the same context; no replacement context is constructed.
It checks whole rows and the typed stable receipt, preservation of the original
full receipt hash, exact counter types/phase separation, all nested seals and
final byte/delta accounting. Unknown stable fields reject rather than being
silently discarded. Independent callback tests cover eight exception types at
three boundaries, five structural types inside admission, and both one-shot
missing-text cases during the real reader call.

Other independent cases cover target/protocol absence before outcome opens;
each readiness stage versus fit; freeze equality versus missing/early freeze;
nonnull wrong native lineage even with unproduced targets and missing scope;
null target/lineage and UNKNOWN coverage; explicit issued-empty abstention;
ownership after caller mutation; reserved/C0/portable alias and nested G0-ref
preflight; late forecast and target changes; exact remaining+one charging at
entry and final reads; and combined input/output capacity including the newly
added outer receipt. Malformed supplied declarations never become partial
successful metrics.

## Contract and qualification boundaries

The API reuses the actual complete G0 loader at entry and final boundaries.
The metadata-only path preflight does not widen its runtime admission. Actual
`g0_forecast_contract._input_ref` still allows ordinary sources only below
`features/` or `data/processed/`; `osm_archive_part` accepts exactly the existing
33 pinned `artifacts/Habu_AI_OSM_Road_Grid_2026-09-25.zip.parts/part_NNN.b64`
paths. The existing typed ZIP/CSV closure remains responsible for those sources.
No generic artifacts namespace, source-parser clone or inferred ref sizes are
introduced.

Every forecast row is copied to the point universe at its actual declared G0
cell centre. This is neither measured road-anchor geometry nor HB-B1 cell-origin
promotion. External target selection is separately bound to physical refs,
readiness, projection self-hash and the supplied protocol. Native model and
prediction hashes identify spatial inputs, not a generated time-target model.
Full-input digests remain distinct from self-hashes and physical byte hashes.
Outside-universe event misses and event-first matching remain the reviewed pure
T2 rules; no matching algorithm or formal historical metric is changed here.

An independent actual Git-native September 28 CSV case checks five events and
six individual occurrences. Without scope/coverage and a declared freeze/target
it returns NEED_MORE_DATA, null universe/ledger/targets and empty T2 metrics.
Its mandatory native forecast/prepared/protocol setup is explicitly synthetic;
it is not a historic September 28 forecast or an authenticated complete ledger.

All reads, hashing and final checks share the caller's existing bounds. Final
combined rereads cover the bound source/protocol/target refs; phase receipts
retain their earlier counters while the outer receipt reports the final total.
Sequential rereads and owned JSON are not an atomic filesystem snapshot,
hostile-thread isolation, loaded-code authentication or hard preemption. A
later publisher must recheck its consumed bindings. This adapter writes
nothing, fits nothing, generates no targets and registers no parent request.
Source and prereveal authentication remain NOT_ATTESTED; all six authority
flags remain exact false booleans. No scientific completion claim is made.

## Independent platform-expectation repair review

Narrow repair verdict: **PASS**, reviewed against PR115 head
`13a57060c21bae1a1e4967cb6fa85119c2c5016d` plus the test-only working change.
Actual Ubuntu run40199476739/job121187377400 is **NOT_PASS**:1387 tests,
one failure,23 skips,417.246s. Independently fetched job logs show the sole
failure at the directory-link assertion: the real guard raised
`ValueError: Symlink path is forbidden: evidence/t2-linked/protocol.json`,
while the test expected `Reparse`. This failed CI is retained, not converted
into a passing full-suite result.

The patch selects `Reparse` for an actual Windows junction and `Symlink` for
an actual POSIX symlink. Both filesystem-creation branches already use that
same platform distinction. Static inspection confirms `master_inventory.local_path`
calls `master_contracts.safe_path` before its reparse-attribute loop; the latter
helper rejects a real symlink with the observed Symlink message. No OS/platform
facade was used to exercise POSIX behavior on Windows.

The independent targeted command loaded
`test_time_target_source_adapter.TimeTargetSourceAdapterTests.test_actual_native_directory_link_rejects_before_protocol_read`:
**1/1 PASS,1.038s**, no skips, using native `mklink /J` against temporary files.
The test still forbids any `Path.open` during rejection, verifies the outside
protocol's exact original bytes, and removes only the junction before temporary
directory cleanup. There is no broadened catch, disabled assertion, new skip,
runtime guard modification or permission change. Root separately reports all
27 authored methods PASS58.996s after the patch; that full native rerun was not
repeated by this independent narrow review.

All runtime/dependency paths are unchanged against both `13a57060` and exact
reviewed runtime `a7ced567`. Independently compared all94 index refs again with
native snapshot `habu-native-source-freeze-bg1f9ikn`, then executed its actual
current-cycle CLI: CONTRACT_VALIDATED, code SHA
`e1f36ea2c0f6f73e0229ce7d3e443b80789c75a48427940bac4ecb45261f7031`,
cycle SHA `cc98ea2a2588f4ebb31ed0471c768b7b4e32dc7317117d3c13003359e549f607`,
fit/production flags false. No new runtime cycle is needed for this test-only
change. The root's three dirty paths (test, author review and STATE) correctly
retain the failed attempt and mark the repaired exact Ubuntu gate pending;
this doc-only commit does not stage them. Actual repaired POSIX/full-suite CI
is still required. Source/prereveal/scientific/admission authority and completion
claims remain unchanged.
