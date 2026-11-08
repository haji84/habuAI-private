# Bounded development accounting and standalone HB-A2 checkpoint

Verified base main `5d4b84fcc0d9b54683f80b4fcace0818d7fb94bd` passed
[PR109 exact CI](https://github.com/haji84/habuAI-private/actions/runs/40181162085)
and [fresh main CI](https://github.com/haji84/habuAI-private/actions/runs/40181924042):
1208 tests,21 existing skips, current-cycle CLI CONTRACT_VALIDATED and secret
guard PASS. Both handoff workflows passed. State now reconciles those receipts.

Normally merged independently reviewed branches:

- Pure job accounting: source `8e56791212512490ca326d13633a81011c03822a`,
  ACTIVE-generation repair `08ea0ff647fa76ea7705b9550500096afcc6dbe0`,
  pure review `8be0a46755cac7b0bef34813294fd30a76c8d553`.
  Two attempts share a root+capability budget across changed source/run/night;
  CI waiting retains the same checkpoint without a live lease or wait charge.
  Known late overrun retains the full bounded actual delta and blocks the job.
- Fixed report transport: source `b043510a0f12f790c6ed94796bee99d33769bb12`,
  cross-night base repair `bbcbb568c33747c49e4637b5530394ed01059d74`,
  independent review `051a15a482bd60fbc3692439cfd239be18bea92c`.
  Canonical origin/state/event prefixes and every linear historical commit are
  verified using unchanged bounded byte/mode primitives. Same-job evidence in
  any base night rejects before payload reads. Lost replies and old prefix ACKs
  return only the latest observed ledger; actual sibling pushes cannot both win.
- Standalone HB-A2: source `84985580b62e49423039a6272b59b646e42dbde3`,
  import-boundary repair `8ad5a7004bc9371f299f44e82b1e49409c85651e`,
  independent review `5a4963f3592eca06f90ad3eeeafef119e0ccae9e`.
  The fixed existing-pinned 32-tree classifier exports JSON-only inference with
  float32 input/float64 thresholds, unscaled finalized leaves and ordered single
  learning-rate accumulation. TRAIN/future parity and actual native monitor
  expiry require genuine pinned Ubuntu execution; a CI skip is forbidden.
  It is standalone and adds no fourth registered/selectable candidate.

Retained independent failures led to minimal repairs: WAIT/closed fence-only
generations could invent late active work; an exhausted7,200,000ms old-night
ledger in a report base could reset to zero under a new night; ABI ValueError/
OSError escaped backend admission; expiry after NumPy import could start SciPy.
Independent final checks passed47 pure cases,12 transport cases,165 A2 assertions
and8 import-boundary cases. Actual temporary bare-Git tests include a second
checkout racing after preparation, successful push followed by a lost response,
latest expired/late-overrun/CI-wait reconciliation, historical-state tamper,
executable modes and real16MiB materialization limits. No fake Git/backend/fcntl
or native package installation was used.

One final combined native run collected11 related modules: **274 methods,
272 PASS and2 explicit skips in125.384s**. Skips are the unavailable genuine
pinned numerical backend and an existing POSIX master-path case. An earlier
coordinator collection script omitted the repository root from sys.path and
failed226 collected cases with65 import errors; correcting only that external
script produced the final run above. This is targeted verification, not a full
native-suite or numerical-fit PASS.

Native Git-index source closure contains90 references. New immutable cycle:
`protocols/development/cycles/20261025-development-job-hba2-01.json`.
Code SHA-256 `1e088468a1e331df37fd97c75bedd6fce27edd2795ce241723719c2afc7ab1c7`;
cycle SHA-256 `20d16b27f7106c21ab2b03d0d30ddfbf5bb5b48f6f3cb57a0573ab92b2741d0c`.
Native-index snapshot CLI is CONTRACT_VALIDATED; prior cycles are preserved.
Exact Ubuntu/full-suite/genuine numerical and fresh-main gates remain pending
at this pre-CI snapshot.

Job proposals and transport observations authenticate no root, request, clock,
runtime, worker, lease or CI result. Actual GitHub jobs/campaigns published0;
controller admission/execution/return and hard-stop enforcement remain absent.
Git metadata/network/native stages are not hard-preemptible, and nonforce
sibling protection does not prove server exact CAS against administrator reset.
Explicit configured Stage1 parent-v4 is the next separately reviewed design;
existing request-v3 nonlegacy block remains unchanged.

Real qualified TRAIN/fitted rows/nights, Negative/search sessions/complete
outcome scopes and untouched confirmation remain0. Sept28 source consistency
stays5 positive units/6 occurrences, separate from75 UNKNOWN fauna packets.
Stage1>=90%,100m±10min and production remain NOT_VALIDATED. Raw/ORIGINAL,
historical M0–M3, existing registry/policy/requirements/workflows/permissions
are unchanged. Master is NOT_COMPLETE; implementation work remains.
