# Configured pure Stage1 v2 baseline and design review

Branch `codex/stage1-configured-registry-v2-20261025`, base PR107 exact
`5b0d5e090d3addd88dbfe5d8fbec66795f03018d`.
Concrete fields and reuse seams were approved by the coordinator before TDD;
the implemented contract is `docs/specs/full-ledger-stage1-v2.md`.

Before changing any source, six complete legacy result objects and their input
objects were collected by compiling the PR107 Git blobs, not using a rewritten
or post-change evaluator. Native evaluator SHA256:
`b114c3a9a0f5197cf8ccc520a30dd95a97b879549b14e7bd4ce3977ee4018079`.
The repository-external synthetic oracle is
`.worktrees/stage1-v1-oracle-pr107-20261025.json`, 60,261 bytes, file SHA256
`d474c4a9c9e0b4add26e3ae372279d96b534fefff7c44e98dc5d68044af475c7`.
Its self digest is
`b87d4271eef3d9bf288e8bfb1e3a77bef6116df3448ae387f68c5ea4204e0449`.
The coordinator extended ownership to a readable synthetic fixture:
`tests/fixtures/stage1_v1_pr107_oracle.json` (100,777 LF bytes, pretty JSON).
Tests parse it and verify its entire canonical encoding plus LF is the original
60,261-byte baseline with the pinned SHA above, including on CRLF checkouts.
They also compare all six whole result objects, not only selected metrics or
hash strings. No Git history or GitHub fetch is needed at test runtime.

| Case | Complete output canonical SHA256 |
| --- | --- |
| one night complete | `5d3799a17eef41f12deca57778ede8c23d56b2f2ef0e10147828f6ae049db80c` |
| two nights, weighted pool | `cbfb07b92ee6ee238c1c916ebb012adae8117ac7729424f7d275b19045106fc6` |
| five nights complete | `b2b5ac7c5c5487febcbb1f5233675a17881e5b4f045d0d50df7a0c7459c3cacb` |
| complete empty denominator | `c2c8dc114bbbdeb6454d97109325afa0fcfb3fbcbdde1ceb32cca04df9dbd575` |
| incomplete second night | `6aa2fce3a8a03dd810363f3fc33ad74a979f2ea5bdf2fc422575335127192712` |
| all projections missing | `ab37a4710eeb43430bee9a63b6e8141f1bbd490b14c6471c244df9792eec5596` |

Pre-change baseline: existing pure Stage1 28/28 PASS (0.250s), existing research
preparer including configured v2 35/35 PASS (1.850s), native Windows Python.
No source, model, profile, parent, Raw, policy, state or freeze was edited during
the baseline collection. None of these synthetic receipts is scientific
evidence or permission to fit/issue/promote a model.

TDD first RED: 40 executed tests, the existing 28 tests plus six-oracle control
passed, while v2 tests failed because its public function did not exist (18
failure records including subtests). Initial implementation made 40/40 pass.
Further explicit RED-to-GREEN checks cover a known score/ledger night conflict
despite missing universe, independent ledger night capacity, and an impossible
UTM52N area despite missing universe/ledger.

The shared `_measure` contains the original numeric loop and uncertainty call.
V1 retains its signature, registry and early missing return. The v2 path alone
uses a per-call configured registry and the existing lazy pure config validator.
Partial validation uses only actual supplied score/ledger records; no temporary
universe or ledger is synthesized. UTM coordinate-domain checks are type/domain
checks, not a substituted geographical denominator.

Current targets: pure evaluator 44/44 pass (including six frozen whole outputs),
existing configured preparer 35/35 pass, HB-A1 28/28 pass, source adapter 33
(28 pass / 5 platform skips) and existing parent 14 (13 pass / 1 platform skip).
No source adapter or parent code is changed, and the configured parent dispatch
remains a later slice. Real POSIX/master execution remains CI's responsibility;
Windows skips are not reported as Linux successes.

Final combined target/regression run: 154 tests in 16.480s, 148 pass and
6 existing platform skips. All newly added pure v2/oracle tests run on Windows;
the skips belong to actual POSIX/master controls in the unchanged parent/source
adapter suites. `git diff --check` passes. This commit contains only the two
owned pure source/test paths plus the approved synthetic fixture, spec and
review. Independent exact-source review and parent exact-head CI follow;
no PR/merge/freeze/state or scientific acceptance is performed here.

## Independent review

Independent exact-source review: **PASS**, no blocking finding, for
`874cf5377cc99cbc206968e4529d6538761a2176`. This approves the additive pure
evaluator mechanics. It does not approve a source-bound v2 adapter, parent
connection, independent confirmation, model selection or production authority.

The reviewer extracted a fresh Git archive with `core.autocrlf=false` and
compared the snapshot directly to the committed blobs. Canonical SHA-256:

| File | SHA-256 |
| --- | --- |
| `src/evaluation/full_ledger_stage1.py` | `9eaab362a065f7e2fb0a7405c2cd8c17468308301316f432b7b45429c2269cb7` |
| `tests/test_full_ledger_stage1.py` | `314da6471ba99b5e7f4dfb0f4b5f8945df7799537c7d953393ea4cbc99ca392e` |
| `tests/fixtures/stage1_v1_pr107_oracle.json` | `7bac9e788353fcd348f3c990f06b24ee3bbbeb9238980431b4e9b0dc408bddb5` |

Fresh-process independent probes against that snapshot passed 21/21 in
0.766s. The committed pure target passed 44/44 in 0.569s. Four relevant suites
(configured model preparer, HB-A1, existing source adapter and existing parent)
were independently rerun: 110 tests in 17.436s, 104 pass and six pre-existing
POSIX/master skips. Together the target and regressions are 154 tests,
148 pass and six skips. Both changed Python blobs parse successfully and
`git diff --check` passes. No Linux execution is inferred from Windows skips;
exact-head Ubuntu CI remains an integration requirement.

The external harness constructs its own five-night, fifteen-area supplied
forecast scores and nineteen-event-per-night individual ledger. It does not
use the implementation test's fixture for those numerical checks. All six
legal ordered triplets match independently calculated lexical Top10 sets,
individual numerators, pooled count denominators and outside-universe misses.
An independently computed 2,000-draw paired night bootstrap, seed 0, matches
the reported interval endpoints. The fixture uses distinct individual IDs and
multi-individual events; it does not create model fits or real capture evidence.

The reviewer also loaded the original PR107 evaluator directly from its Git
blob, verified source SHA `b114c3a9a0f5197cf8ccc520a30dd95a97b879549b14e7bd4ce3977ee4018079`,
and executed all six oracle input sets independently. Original Git code, frozen
whole expected objects and current v1 results agree exactly. Canonical oracle
plus LF is still 60,261 bytes with SHA
`d474c4a9c9e0b4add26e3ae372279d96b534fefff7c44e98dc5d68044af475c7`;
this differs intentionally from the pretty fixture's physical blob hash above.
V1 keeps its public signature, fixed registry and early missing-input behavior.
V2 never mutates that registry or silently reorders/substitutes candidates.

Adversarial probes reject fourth/missing/duplicate/reordered candidates,
header/per-candidate config and feature-definition conflicts, wrong HB-A1
recipe identity, malformed model/prediction hashes, nonfinite/boolean scores,
duplicate event/individual IDs and contradictory UTC/night/horizon/point data.
Known contradictions remain rejected when another projection is missing or
coverage is UNKNOWN. Every missing-input combination returns empty metrics;
no placeholder universe or narrowed denominator is constructed. Combined byte
capacity is enforced before JSON copying, individual/event/night/area caps
remain effective, parent cancellation propagates, and expiry after the final
receipt digest blocks both complete and NEED_MORE_DATA results.

The no-I/O probe forbids file opening; caller-object mutation after snapshot
does not change the result. Hash agreement is treated as declared consistency,
not source/model authentication or preregistration authority. Official recall,
threshold success, confirmation source authentication, fit and production flags
remain false; no winner or promotion decision is emitted. The separate source
v3 parent's explicit Stage1 block must remain until a source-bound v2 connection
is independently reviewed.

External harness `stage1-v2-independent-probes-20261025.py` is outside the
implementation tree, SHA
`0b482a17a919036ea14fe31b00aa112fa853ea83afe2be9aeeae0a00ce109067`.
Only this Independent review section was edited by the reviewer. No source,
tests, policy, Raw, ORIGINAL, state or cycle files were changed.
