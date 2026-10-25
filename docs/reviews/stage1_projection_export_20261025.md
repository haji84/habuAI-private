# Configured Stage1 source projection export

Base main `d2f8c759ad9817cdcafab4c97c4fbdf5f4fb08b3`; independent design
`57e8c1b8d9f2ca2a1702e6eb22d70e9a039354c6`.
Coordinator implements `src/evaluation/stage1_source_adapter.py` and
`tests/test_stage1_projection_export.py`; the independent fixture worker owns
the historical backend test/capsule. No concurrent edits to those files.

The additive public API exports the actual U/S/L already passed to pure
configured Stage1 evaluation, after existing native admission, source reads,
validation and final rescan. A separately owned fourteen-field bundle retains
the exact sealed historical result and its actual-read-byte receipt. No extra
source I/O follows that receipt. Separate whole-projection, ledger self-hash,
nested-result and bundle hash scopes are verified. All six authority flags
are false and source authentication is NOT_ATTESTED.

Export mode alone adds reserved namespace/path preflight before the first
manifest and before any scope/outcome payload. Combined owned JSON has the
existing 16MiB/2M-node/depth12 limits including its newly added receipt, one
existing cumulative read context and its existing absolute deadline. The
default APIs do not execute the export branch or its guards/copy/hashes.

This is DEVELOPMENT consistency plumbing. Mandatory strict forecast/prepared
inputs remain mandatory; zero eligible TRAIN does not cause their invention.
There is no point-universe conversion, T2 target generator/source evaluator,
protocol preregistration, parent dispatch, model registration or authorization.
No Raw/ORIGINAL, existing model definition, requirements, workflow or permission
changes. Source-declared G0 cell centres are not measured road anchors.

## Author verification

- First five tests failed at the missing explicit API, then passed after the
  implementation. Initial expanded17 methods passed in27.161s.
- Final native group: **52/52 PASS,96.916s**, Python3.12.14 `-B -X utf8`:
  `test_stage1_projection_export`, `test_stage1_configured_source_adapter`,
  `test_research_pdca_adapter.ResearchLegacyWholeOracleTests`.
- Nineteen new methods cover all six configured triplets, actual internally
  validated projection equality, independent seals, detached ownership, null
  missing projections and nonnull UNKNOWN ledgers, supplied contradictions
  alongside missing scope, absent/forged prepared rejection before source I/O,
  reserved/C0/DEL/portable aliases at all three ref positions, whole-node
  preflight, actual native Windows junction rejection, cumulative read cap
  including remaining+1 rejection byte, combined output and final-receipt caps,
  complexity/type guards, final rescan corruption and expiry before/after seal.
- Configured default whole JSON, actual source-open order and cumulative bytes
  are exact; export has zero source reads after the normal rescan. Existing
  four whole source-v1 receipts/read-byte oracles and eight whole historical
  parent/current same-runtime typed artifacts, read ledgers and physical REPLAY
  bytes remain exact. The archived original fixture remains checksum-fixed;
  the common-libm-variation equivalence control also passed without replacing
  historical Windows values or allowing platform hashes.
- Actual native Git September28 capture/individual CSVs give5events/6occurrences
  and NEED_MORE_DATA/null U/S/L/empty metrics without scope/coverage. The
  prerequisite forecast/prepared test inputs are explicitly synthetic; this
  is not an actual September28 forecast or scientific fit/evaluation.

Full Ubuntu integration, historical backend fixture integration and independent
exact-source review are pending. Genuine POSIX engine acceptance cannot be
inferred from native Windows checks. Actual external jobs, qualified TRAIN,
certified negatives, complete scopes and scientific fits remain0;75UNKNOWN.
Master NOT_COMPLETE; scientific accuracy and production NOT_VALIDATED.
