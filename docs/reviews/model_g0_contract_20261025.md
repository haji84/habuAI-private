# Independent G0 contract implementation review, 2026-10-25

Reviewer: Lane V, separate validation worktree, no implementation edits.
Implementation base: `4981592789f5a6fe01800df85105f2d0c49c0b4a`.
Final reviewed implementation: `b62b569d6214f22e10463488af5b9ad107c72469`
([PR 88](https://github.com/haji84/habuAI-private/pull/88)).
Scope: additive contract-only envelope, fixed policy, pure time/readiness APIs
and a read-only checker. No cohort eligibility, actual fitting, model comparison,
confirmation qualification, prediction issuance or Champion authority is granted.

## Review status

**CODE REVIEW PASS for the bounded contract-only implementation**, after the
coordinator repaired the independent findings and this reviewer reproduced the
repairs. No unresolved implementation defect was found in the final reviewed
source/policy/checker scope. The regenerated manifest independently validates
against an exact committed-Git-blob snapshot. Exact-head CI remains a separate
integration gate.
An envelope pass remains distinct from completion of the full G0 scientific
fold/confirmation contract.

## Independent checks

- Final independent `test_codex_cycle_contract.py`: 19 tests PASS, 0.302s.
- A real Windows directory Junction outside a temporary fixture checkout now
  fails with `REPARSE_PATH`. The earlier implementation accepted this fixture;
  the coordinator repaired it after the independent finding.
- Modifying an already-consumed helper after the initial reads fails with
  `INPUT_CHANGED`, independently checked with a temporary fixture and a hook at
  the policy digest boundary. No repository source was modified by this probe.
- Introducing a new helper after the initial closure enumeration still returned
  `CONTRACT_VALIDATED` in source SHA
  `6b024af0832ace167cba134bbca745538402295844670d0201d26b6c35a370be`.
  The coordinator added a final closure-membership check and a regression.
  Repeating the independent mutation probe now rejects it with
  `CODE_CLOSURE_CHANGED`.
- Initial independent `test_codex_parallel_handoff.py`: 4 PASS, 1 FAIL after the
  coordinator added genuine `execution_records` to STATE.
  The failing negative test copied those existing records and did not clear
  them, so its supposed missing-provenance fixture was no longer missing
  provenance. The coordinator explicitly emptied `execution_records` in the
  negative fixture while retaining the production checker's existing protection.
  Final independent rerun: 5 tests PASS, 0.042s.
- The handoff checker's status now distinguishes initial handoff from recorded
  execution. It preserves the unchanged scientific/production fields and does
  not claim that documentation itself launched workers.

## Boundary assessment

The manifest rejects unexpected fields and therefore does not accept a sealed
outcome reference. The validator-owned closure covers all `src/*.py`,
`scripts/*.py`, JSON schemas and both existing dependency profiles; callers cannot
select a smaller set. References bind exact bytes, duplicate keys and paths are
rejected, file/read bounds apply, fixed policy mutations cannot be blessed by
rehashing, and consumed sources are rechecked before return.

The policy preserves source-qualified owner-capture target semantics, UNKNOWN
as null, independent scoped search plus complete outcomes for a noncapture,
event/individual separation, full outside-universe individual denominators,
fixed spatial/time geometry and model-search budgets. Folds remain `UNALLOCATED`,
confirmation `UNSELECTED`, science `NOT_VALIDATED`, and both fit and production
authorization false.

Time helpers reuse the existing 07:00 JST semantics. Training boundary is
`min(fit cutoff, forecast cutoff, evaluated-night 07:00 JST)`; missing readiness
is rejected and readiness equal to the boundary is excluded. The final policy
separately names training and forecast availability: forecast inputs use their
own actual issuance cutoff, while training rows obey the additional
prior-night/fit boundary. Historical valid-time suitability,
authenticity and trusted freeze receipts remain separate prerequisites.

Fixed policy semantic SHA-256:
`741ce69c523a2d5cb1e010c4ca4ff49d02682fdd644d5aa4b9b54ed87c49a97a`.

Final independently reviewed committed-byte SHA-256. The existing checker/test
working copies differ only by CRLF/LF representation; normalized contents were
independently compared and are identical:

| Path | SHA-256 |
| --- | --- |
| `src/codex_cycle_contract.py` | `459b0bd41e5f96c72e226f4707876aaab9a7b5079d9b257e4ed49d395863ea0f` |
| `protocols/development/g0-policy-v1.json` | `79112d4f845b620ff928743cb1f6d14af62ce8bcf474f51fb32ec911d67941ac` |
| `schemas/codex-cycle-contract.json` | `e9cf542fb83babc46e2eb0b24329dc19b4efc3ed7fea71bc4a546103bd5bf8ac` |
| `scripts/check_codex_cycle.py` | `06db1dec14c6c159ce8e27a0f5fdebd3a49dc933e353f7d26537eaf267fa6bd7` |
| `scripts/check_codex_parallel_handoff.py` | `a28727a92a23b5d4d12cc2cd384d08f2ce6588a62437f64ff9a494c74f5de16b` |
| `tests/test_codex_cycle_contract.py` | `9b5c5669452e94597ed6990a6733d2d249584f1c44b0eb6656b91bdd6020b6f9` |
| `tests/test_codex_parallel_handoff.py` | `a9bd678fb43b46087ff1b7752e03dc27d27984cfba405682895ee7be3151f55b` |

Independent exact-commit snapshot result: 58 fixed code references,
`CONTRACT_VALIDATED`, folds `UNALLOCATED`, confirmation `UNSELECTED`, and fit and
production false. All referenced bytes came from `git show <reviewed_sha>:<path>`
into a temporary derived fixture; no Raw/ORIGINAL artifact was read or copied.

- Cycle SHA-256: `71881dcd8c296d0694da13c6a083c2cde086fd1654486691774117f88da9e03c`
- Code SHA-256: `d2030793880eb9eb3a9d61ad48780d8482f262b712e574623f1ba6c8c9d5c206`
- `git diff --check <reviewed_sha>^ <reviewed_sha>`: PASS.

## Remaining finalization

Affected tests and independent hostile probes have been repeated, and the final
manifest verified against exact committed Git bytes. Existing Windows checkout
conversion can change text bytes;
a Git-blob snapshot is the appropriate read-only fixture for this check. A
passing local fixture is software evidence only. Exact-head Linux CI and
fresh-main verification remain coordinator integration gates.

No Raw/ORIGINAL files, fitting code, shared STATE or GitHub resources were
modified by this reviewer. Existing-PR findings are recorded separately in
`docs/reviews/lane-v-pr-audit-20261025.md`.
