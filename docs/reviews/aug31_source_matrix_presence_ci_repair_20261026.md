# August31 source-matrix presence CI assertion repair

The old test assumed every night lacked derived capture/occurrence CSVs. The
August31 software branch legitimately adds its two source-derived tables. The
unchanged availability matrix reports their presence without qualifying complete
outcomes, search exposure, training rows or official KPIs. This repair changes
only that test and this record; no runtime, source policy or data is changed.

Baseline: `f9cf42a261db052601b31bd92d0513b656232920`. Coordinator-reported PR121
Ubuntu run40216628850/job121239055050 ran1504 tests, one failure,32 skips,570.869s.
The sole failure was the blanket capture-ledger absence assertion; later CI cycle
and secret checks were skipped. This record does not relabel that run as passing.

## Actual RED and observed matrix

The unchanged two-test module was run on actual Windows/Python3.12.14 against a
complete native-Git snapshot: **one failure, zero errors,2.955s**, at the same
line29 `capture_event_ledger.present` assertion. The other tamper test passed.
Every one of the876 native files/182135221 bytes was checked against its Git blob
ID, byte size and SHA before execution. Git archive used command-local
`core.autocrlf=false`; no repository Raw was normalized or rewritten.

All13 actual rows were observed. Only2026-08-31 has the two derived CSVs present:

| Role/path | Native bytes | Fixed SHA256 |
| --- | ---: | --- |
| `data/processed/capture_events/2026/2026-08-31.csv` |413|`137c04b5abe6713c1668633fe10afa61f601a5c0a8d5331471d71f8cbf0a972f`|
| `data/processed/individuals/2026/2026-08-31.csv` |378|`6d0c01d185722044bf976f2858461990518dffe6ee402815269ad94f5f242947`|

The revised test requires exactly that presence/hash map, one August31 row among
all13 rows, and strict absent/None maps for all other12 nights. The canonical raw
owner JSON remains absent/None for every night. It reads both actual CSV byte
payloads, checks fixed size/SHA, exactly two records datedAugust31, event IDs
`AUG31SRC-L10110`/`AUG31SRC-L10492`, count1 per event, and the matching two
`-OCC01` source-occurrence selectors. Those identifiers do not assert permanent
animal identity or completeness of outcomes.

Every row must retain exact `OUTCOME_LEDGER_MISSING` classification, both exact
UNKNOWN reason strings, training false and official-KPI false. The overall
blocked status,13-category count, verified-positive/negative training counts0 and
original-P0 false remain asserted. Presence is required where evidence exists;
it is not an optional pass or a qualification decision. The original standalone
registry-tampering test has an unchanged AST.

## GREEN and unchanged runtime closure

Only the repaired test was copied into that native snapshot. Its other875 files
were verified unchanged after the runs. Actual results, no skips or fake POSIX:

- Matrix module: **2/2 PASS,3.395s**.
- Actual GPX inventory plus September28 reconciliation: **9/9 PASS,10.348s**.
- Native-Git `scripts/check_codex_cycle.py`: **CONTRACT_VALIDATED**; fit and
  production authorization false, scientific NOT_VALIDATED.

All97 frozen runtime references still match native Git and their declared SHAs.
The current pointer and immutable cycle are unchanged: pointer-bound physical
cycle SHA`1cbbe661caa1030b24b5cdbf02c33f10c80ebc4503fc90197f5a355f5053b1a0`,
semantic cycle SHA`a5675602fa647e53918e5904636f7158bd836a325c3766628e3e2cf255f8370e`,
code SHA`0d694c4c29f8d7f6d12f4413a53fa10e44bc102beb3d70cfa599ee7aeb843fff`.
This test-only change does not regenerate that freeze. No new scientific,
source-authentication, confirmation, issuer, permission or production capability
is introduced. Full exact-head Ubuntu CI remains the coordinator's next gate.

Commands used bundled Python with `-B -X utf8`, from the native snapshot:

```text
python -B -X utf8 -m unittest discover -s tests -p test_gpx_outcome_source_matrix.py -v
# From its tests directory:
python -B -X utf8 -m unittest test_inventory_real_gpx_sources test_reconcile_actual_gpx_exposure -v
# From its root:
python -B -X utf8 scripts/check_codex_cycle.py
```

The direct old-test run in the existing Windows checkout stopped earlier with a
known physical-GPX/QC SHA mismatch from checkout line endings: two tests, one
error,3.925s. That is retained as an environment diagnostic, not a successful
reproduction of the presence failure. An initial temporary archive without the
command-local autocrlf override also failed native-blob preflight before tests;
that temporary snapshot was left separate. Neither prompted a runtime change,
Raw rewrite, test normalization or relaxed hash check.

Private receipts remain outside Git in
`C:\Users\qq113\OneDrive\ドキュメント\ChatGPT\ハブAI\.worktrees\aug31-source-matrix-ci-repair-f9cf42a-20261026`:

| Receipt | Bytes | Physical SHA256 |
| --- | ---: | --- |
| `old-native-git-red.log` |1040|`a6f4e5db47e10955b0ba20ae68d7c75e8877b0ebbe50a6655c0a1d25b5873223`|
| `matrix-green.log` |367|`e9718b722649c54f62778de934867e031ec5908eb432a9cbec45699b823da745`|
| `inventory-reconcile-green.log` |1660|`f329d34440cbcd456c388a1f95590f00ba1ae088ca194e5ff6d5006e275fb0d2`|
| `actual-thirteen-source-matrix.json` |14298|`4553382d65dad295d75ce594251b298e686a44bfe0bcc3d7763e00f3635437c0`|
| `native-git-cycle-cli.log` |11185|`de99b9b455d9933df6d716aa81fbce43cf4bfb524a0ac646c0497851079f7457`|
| `verification-summary.json` |12232|`a3fafb1442b5ee377298a6237b0a6659e8d1e96cf0518a183377e1ccc19b896a`|
