# Independent review: explicit research candidate configuration v2

**Disposition: bounded code review PASS after P1 repair.** No unresolved
blocking defect was found in the reviewed pure preparation interface. This
review grants no source authentication, scientific validation, candidate
selection, confirmation consumption, official issuance or production authority.

Reviewed branch: `codex/hba1-three-candidate-config-20261025`.
Base: `210a97644e381d6442bc8f94e658fe02936e8091`.
Initial source: `13e428fcda1d9eb5a8e01f0e9b5517a15f00caf6`.
Repaired source reviewed and tested:
`a6ef036c414db5a4a2a596da05fc2a7815cb9a34`.
The reviewer's only tracked edit is this record; fitting/adapter/test/spec source
was repaired by its implementation owner.

## Exact reviewed files

Hashes below describe Git blob contents, independent of checkout line endings.

| File | Git blob ID | SHA-256 of blob bytes |
| --- | --- | --- |
| `src/research_model_adapter.py` | `762e6c74120e26e144d99df2a4b2eadef5d9a789` | `e2f2443c88a1c9e3909866939dd04d6a9da05fcbf37029b218dfcc46c2f85811` |
| `tests/test_research_model_adapter.py` | `fe5f852d411aaede4ae1d062f1cb6b64e00bf670` | `6d6763525de4d99140f07b9211696eff40fc42a1e3e21ced7f993edb906df310` |
| `docs/specs/research-candidate-preparation-v2.md` | `2779e4a6133ce5bde872b02d8cf759e79d5204b5` | `1c8e23df1bf14b752b931019403d6dd5048d4ee8ec5f27fd1b7b166c0541f98e` |

The source delta is additive: 299 adapter lines, 310 test lines and 163 spec
lines, with no deletions. The complete base adapter byte prefix is preserved
after normalizing checkout CRLF to Git LF. Thus all five v1 function bodies,
constants and imports remain unchanged. Fresh tests also retain their combined
function SHA `8a0350421d84a39c781fdc78eb3c0abb23c40f1fb91022759efea44837e111e8`
and v1 fixture receipt
`a8c59d499d8fa8d132cbb05876469596c5c365755b05397f80ae06cc808184e0`.
The unchanged Stage1 v1 registry remains exactly uniform/HB-A0/HB-B1.

## Finding and independent repair check

P1 at the initial source: selecting HB-A1 with a common six-feature schema
omitting `temperature_c` bypassed every physical-range check. After removing
that field from all TRAIN/future feature maps, future source/time maps and the
declared feature names, and rebinding both hashes, `humidity_pct=101` in either
the last accepted TRAIN row or the last future row returned `NEED_MORE_DATA`.
An unsupported schema incorrectly concealed a known supplied contradiction.

At the repaired source both original direct-call reproductions raise
`ValueError`. The added v2-only check visits supplied known fields before the
missing-seven decision, without creating missing values or invoking a model.
Independent singleton-schema probes also reject both invalid bounds in the
first and last TRAIN/future rows. Valid endpoints remain data gaps; extreme
finite temperature/TPI values receive no invented additional physical bounds.
The authored regression additionally exercises 40 invalid combinations and
all 126 nonempty proper subsets, which remain insufficient without fitting.
Legacy helper, numeric core and standalone HB-A1 source are unchanged.

## Fresh native Windows verification

Runtime for every command:
`C:\Users\qq113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
with `-B -X utf8`. Working directory is the reviewed worktree. No fake `fcntl`,
source modifications, real field fitting or confirmation payloads were used.

- `python -B -X utf8 -m unittest discover -s tests -p test_research_model_adapter.py -v`:
  **35 tests PASS**, no skips (13 existing v1 methods and 22 v2 methods).
- `python -B -X utf8 -m unittest discover -s tests -p test_hba1_feature_candidate.py -v`:
  **28 tests PASS**, no skips.
- The exact runner below loads selector, A0, B1 and legacy candidate suites:
  **100 tests PASS**, no skips.
- `python -B -X utf8 ..\config-review-independent-probes-20261025.py .`:
  **125 independent assertions PASS**. Local probe SHA-256:
  `3fb78b1f5b84791361edb76d232cb57dfc6143e35763ff50ec28db1f2bb65e09`.
- `python -B -X utf8 ..\config-independent-probes-20261025.py .`:
  **18 coordinator assertions PASS**. Local probe SHA-256:
  `9ed6a0616ab25db575bc44498884cc19ffb2bb5214edd888ccb3c0475ef106c6`.
- `git diff --check 210a97644e381d6442bc8f94e658fe02936e8091 HEAD`: PASS.
  `git diff --name-status` lists only the three reviewed files before this
  documentation addition. No Raw, ORIGINAL, Freeze, parent, Stage1, model,
  source receipt, shared state, policy or registry file changes occur.

Related-suite runner, supplied on standard input to the named runtime:

```python
import sys, unittest
sys.path[:0] = ['src', 'tests', '.']
loader = unittest.TestLoader()
suite = unittest.TestSuite(loader.loadTestsFromName(name) for name in (
    'test_research_selection', 'test_occupancy_shrinkage',
    'test_hierarchy_shrinkage', 'test_prospective_candidate_model'))
result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(not result.wasSuccessful())
```

There are **163 passing unittest methods** across these commands. Independent
assertions are counted separately, not presented as additional unittest cases.
Both external probe scripts are local review artifacts outside the tracked
source tree; their paths and hashes do not imply publication or CI execution.

## Contracts checked and limits of the result

All six ordered legal configurations retain uniform first and exactly two
unique fixed optional IDs. Reversed future input order remains hash-bound and
fully covered. Uniform retains Beta(1,1), A0 retains area probabilities and B1
retains native diagnostic hierarchy/conditional ranks. A1 uses the fixed full
seven-feature recipe and the existing numeric core. Independent 19-row/five-night
and 20-row/four-night cohorts both block the whole set before any candidate fit.
Late valid A1 insufficiency clears local earlier candidates. No fourth slot,
fallback, ablation slot, metric or winner is introduced.

Candidate wrappers bind the same accepted TRAIN rows, ordered row IDs, complete
raw feature maps, selection, config, strict feature definition, cutoff and full
joined future snapshot. Native artifact digests and full night/window/physical
row identities are checked. Caller mutation cannot change returned artifacts.
Malformed future rows remain rejected even when training is insufficient.

Independent checks cover all four pre-copy caps, a combined byte limit where
each separate input fits, and a final output limit. Limits remain combined
16 MiB canonical UTF-8 input, 2,000,000 nodes, depth 12, 4096-character values,
512-character keys, 1024-bit integers, 20,000 accepted/rejected TRAIN rows and
120,000 complete future rows. Final output is also bounded to 16 MiB; these are
joint ceilings, not a promise that the maximum row count fits. No truncation or
independently concatenated rank chunks are accepted.

Parent expiry propagates from the actual numeric core after 300 callback checks
and from actual prediction execution through a real `ProspectiveReadContext`.
That context charges zero source bytes. Both success and insufficiency reject
an expiry after the final receipt digest. This remains a cooperative shared
deadline, default 30 seconds and maximum 300; existing callback-free A0/B1 calls,
validators, parse/sort/aggregation and legacy digests retain bounded before/after
checks. Process preemption and a hard CPU deadline are not established.

All authority remains false; supplied config/recipe/code hashes establish
declared consistency only. Actual source-byte authentication, a persistent
campaign slot/exposure/cumulative-budget ledger, trusted independent pre-reveal
freeze/consumption, versioned source-bound parent dispatch and a reviewed new
Stage1 registry are explicitly unimplemented. Changing config hashes cannot
reset campaign or confirmation authority. No genuine scientific cohort,
calibration, model advantage, formal KPI, production readiness or Master Goal
completion was established. Exact-head Linux CI, any subsequent merge/source
changes and fresh-main integration remain separate coordinator gates.
