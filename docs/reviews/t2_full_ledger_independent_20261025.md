# Independent full-ledger time-target API review

Reviewer: `/root/validation`. **PASS for this bounded pure diagnostic API**
at released source `b01501ea6b664545ec5ba3eb8614291eba1b5e6e`, containing
author commit `75885ad01c3c10e3c43d384a5c431f8d6c20cf1b` and a normal
merge of main `4aca7cd`. Matcher review-only commit
`939629d1b3c258de7208ad9bd60cbab89dc1465b` changes no runtime/test bytes.
This review adds no source qualification, forecast issuance, target generation,
fit, parent integration, confirmation, selection or production authority.
Actual Ubuntu integration remains a coordinator gate.

## Exact source and scope

Git-native bytes were checked, avoiding checkout CRLF as an evidence identity.
The following runtime and test files are unchanged between the author commit,
the released main merge and the subsequent matcher-review document commit.

| Path | Canonical bytes | SHA-256 |
| --- | ---: | --- |
| `src/time_target_evaluation.py` | 19446 | `984e5438f3d170d14d27ff92dbc5ac599cea4ec74d0ee929b54d41002d9ef69d` |
| `src/event_matching.py` | 1490 | `2a5203141afd34b4f6b7ac835c9aa808d05fb998fb26f3dfce4e1d09a6dc21b4` |
| `src/pdca_pipeline.py` | 32613 | `7d8e989192d95aaa1c64fd8737184ed86d24e62da2ead20312d59c48cb4e0c7f` |
| `tests/test_time_target_evaluation.py` | 33493 | `57bcd7869953b4cfe93930094eb718daba56aba1a34d6b854f93ab2cd6235bc8` |

The existing Stage1 validator is reused, not replaced. Its current blob is
31246 bytes, SHA-256
`9eaab362a065f7e2fb0a7405c2cd8c17468308301316f432b7b45429c2269cb7`.
This review concentrates on `evaluate_time_targets`, its full universe,
ledger/source bindings, chronology, missing-data behavior, resource bounds and
receipt. The separate independent matcher/whole frozen-scorer review is recorded
in `docs/reviews/full_ledger_time_target_20261025.md`; that broader oracle audit
was not duplicated here.

## Contract findings

No blocking defect remained in the released API under the agreed contract.

- Protocol and projection schemas are exact. Crossbindings use each
  projection's self-hash, excluding its own hash field. Returned `input_digests`
  instead hash the full supplied projections, including those self-hashes;
  the independently computed receipt hash excludes only `receipt_sha256`.
- The entire supplied universe is validated and indexed by actual 100m cell
  and normalized 600-second window. It is never reduced to selected/observed
  units. An actual event outside that full unit set stays in the event and
  individual denominators and has no edge, even when a target is within the
  physical tolerance. An event in an eligible unselected neighboring unit can
  match. Explicit finite UTM52N points are used; no inverse projection, inferred
  point or native-rank probability conversion is introduced.
- Matching is event-primary. Two individuals in one event do not create two
  primary events or alter a tie to favor individual coverage. Secondary
  individual coverage uses the same event assignment. Exact 100m/600-second
  tolerance boundaries are inclusive; scope/window membership is half-open.
  Unmatched targets remain UNKNOWN, with precision and false positives null.
- Known schema, hash, source-ref, ID, point, night, cutoff and horizon
  contradictions are checked before missing/incomplete input can return
  NEED_MORE_DATA. Prior-night cutoffs and equivalent aware timezone strings
  remain legal. 07:00 belongs to the next operational night. Declared freeze
  equality at cutoff is allowed; a later freeze is rejected. Missing freeze,
  prediction lineage, projection or complete ledger yields empty metrics and
  all matching/ID lists empty. An issued empty target set is valid abstention:
  known positive event denominator gives recall zero; a zero denominator gives
  null recall.
- JSON copying and hashing are bounded and use one cooperative deadline plus
  the caller callback. Caps include 16MiB combined canonical JSON, depth12,
  2M nodes, 120000 full units, 100 targets, 20000 events, 100000 individuals,
  20000 source refs and 2M target/event candidates/stored edges. Capacity,
  malformed input and expiry raise without returning partial metrics. Final
  hashing is followed by another deadline/callback check for both successful
  and NEED_MORE_DATA results. Callback exceptions retain their identity.
- No source file or network is opened by the pure API. Supplied hashes,
  coordinates, freeze time and completeness declarations are caller claims;
  source and prereveal authentication remain NOT_ATTESTED, adequacy remains
  NOT_ASSESSED, and all six authority/official flags remain false.

## Independent executed evidence

Native Windows, bundled Python3.12, fresh process with `-B -X utf8`:

```text
python -B -X utf8 ..\t2-independent-probes-20261025.py .
```

**15/15 independent methods PASS, 0.238s**, re-executed at released `b015`.
The harness is external to product worktrees and independently constructs JSON
fixtures and canonical hashes. Its SHA-256 is
`1368666386df2a97e45f3385a043778dde8a92f340e441f2ef3213d09cff3ca3`.
Its banner continues to say intermediate until
the separate source review is complete; this document records the exact-source
verification, rather than treating a working-tree test as release approval.
Coverage includes outside-cell and outside-window near-boundary misses;
eligible unselected neighbor matches; event-vs-individual tie semantics;
augmenting assignments and input permutations; exact and just-outside physical
and time tolerances; prior-night cutoff/UTC aliases/06:59:59 and 07:00; issued
abstention; missing/incomplete inputs; nine known-contradiction/missing
combinations; strict ledger refs; full-universe capacity; callback interruption;
expiry at the last callback and after output hashing; and caller-input mutation
which must either fail closed or return the unchanged owned snapshot.

The actual September28 Git CSVs were independently read without modifying
originals. Existing strict parsers confirm **5 events / 6 individual IDs**:

| Git source | Canonical bytes | SHA-256 |
| --- | ---: | --- |
| `data/processed/capture_events/2026/2026-09-28.csv` | 887 | `e58d3c26001b62c86c5afe0b94911f3440b58a9f9d5702d93f12a711e9b4e033` |
| `data/processed/individuals/2026/2026-09-28.csv` | 901 | `7aaec196b60bf3d7c7f3883928dfd2d32c149397f495c3eff3b740b90a6762f3` |

Only a pure incomplete projection was constructed from these records, with no
complete scopes, universe, issued target set or freeze. Synthetic incomplete
planning metadata is explicitly not an issued forecast. The result is
NEED_MORE_DATA with empty metrics and match/ID lists. Five/six actual input
identities are not proof of a complete denominator, target timing, source
authentication or prospective performance.

The corrected discover-equivalent command explicitly adds the existing test
module search paths and runs the authored40, existing pure Stage1 44 and legacy
PDCA diagnostic3 tests:

```text
python -B -X utf8 -c 'import sys,unittest; sys.path[:0]=["src","tests"]; suite=unittest.defaultTestLoader.loadTestsFromNames(["test_time_target_evaluation","test_full_ledger_stage1","test_pdca_legacy_diagnostic"]); result=unittest.TextTestRunner(verbosity=1).run(suite); sys.exit(not result.wasSuccessful())'
```

**87/87 PASS, 1.087s; no skips.** The earlier reviewer command used package
imports without the existing `tests` search-path convention and named a
nonexistent integrity-test class: it collected85 tests with17 loader errors
(16 missing top-level fixture imports and one wrong class name). That command
was not a source-test PASS and is replaced by the explicit successful command
above. A temporary model-capacity interruption likewise supplied no approval;
the exact-source commands were subsequently rerun normally. `git diff --check`
passed. No fcntl facade, filesystem/backend substitute, test-source edit or
waived assertion was used.

These tests establish bounded diagnostic mechanics on synthetic cases and
honest missing-data behavior on the real five/six inputs. They do not establish
100m/10min forecast skill, a qualified complete ledger, pre-reveal freezing,
independent confirmation or model/production eligibility. Source-bound loading,
target generation and parent registration remain separate work.
