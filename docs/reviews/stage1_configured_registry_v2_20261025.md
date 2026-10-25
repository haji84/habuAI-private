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
