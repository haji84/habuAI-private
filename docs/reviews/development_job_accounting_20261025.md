# Development job accounting implementation evidence

Independent design review approved a focused pure module followed by a separate
fixed Git report module. It required stable root+capability accounting, paused
CI without an active worker lease, explicit late overrun and preserved original
scientific/request semantics. Root implements the slice inline.

TDD began with11 new tests failing on the missing module/API. The first pure
implementation passed11/11 in0.201s. A further declared request-window test
failed before the START observation/expiry guard was added;12/12 then passed.
Additional tests cover terminal incidents while another attempt waits for CI,
extreme-year lease arithmetic and strict false-versus-zero authority fields.
The15 new pure tests plus32 original handoff tests pass47/47 in0.258s without
skips. Original request/science/transport source files are unmodified.
Independent review of8e56791 found overrun could originate from WAIT/closed
fence-only generations. A new two-case regression failed before the fix. Replay
now tracks ACTIVE-issued generations separately, accepting late real-worker
accounting while rejecting active increases from fence-only records. Tests that
reported late expiry through a close-only generation were corrected to bind the
original ACTIVE generation. All48 combined tests now pass in0.278s.

The pure phase alone had no Git publisher or durable job completion claim. It is
replayable unauthenticated accounting only. Full runtime/worker hard-stop/root
admission/result verification/controller/continuation remain unimplemented.
Known overrun is stored at its full bounded value and blocks the job; it does
not permit extra science or implementation. Actual scientific fit rows remain0.

Independent exact-source review is required before the fixed report layer.

## Fixed report layer author evidence

After the exact pure repair passed independent review,11 new publisher tests
failed on missing API. The separate fixed transport implementation passed11/11
in63.879s, including10 actual Windows temporary bare-Git cases and one canonical
record contract. Cases exercise reconstructed restart, two siblings, a real
second-checkout push after preparation, actual push then lost response, old
prefix ACK returning latest expired accounting, changed anchor/base rejection,
noncanonical current bytes and subsequently restored current bytes with invalid
history, foreign bridge files, oversize preflight before any payload read and
preexisting base namespace. No fcntl facade, fake Git or new permissions were used.
These are synthetic job roots on real local transport; actual GitHub job admission
and trusted runtime/worker/CI/controller/continuation remain absent. Independent
transport source/adversarial review and final exact Ubuntu/fresh-main CI pending.

Independent transport review found a real base-reset defect in `b043510`:
an absent job branch could bootstrap a zero ledger under a new night while the
same job's exhausted7,200,000ms ledger existed under the old night in the report
base. The job ID itself correctly remained unchanged. The old anchor-only base
lookup failed to see that prior footprint. This failure evidence is retained;
the initial11 author tests and later combined62/62 PASS(61.470s) did not cover it.

The repair checks fixed same-job Git metadata across all nights, including a
malformed leaf at the job root, before reading report payloads. It runs during
both absent-branch bootstrap and existing-branch validation. A real temporary
bare-Git regression archives a full exhausted old-night ledger in the report
base, then attempts a same-job zero ledger under the next night. The old source
reached a payload read/publication instead of rejecting; the repair rejects
before any payload read. An independently seeded canonical new-night branch
with the same tainted base also rejects. The fixture enables long paths only
in its own synthetic checkout on Windows; no global Git setting is changed.
All12 publisher tests PASS(66.650s), including the existing actual race/lost-push
cases. Independent exact repair review and exact Ubuntu/fresh-main CI remain
required. The query is fixed job-identity metadata, not a Raw payload scan.

## Independent review

Reviewed exact repaired source
`08ea0ff647fa76ea7705b9550500096afcc6dbe0` on 2026-10-25.
Result: **PASS for Task1's pure accounting contract**. No remaining blocking
finding was found in this phase. The fixed durable report layer remains a
separate implementation and review gate.

Canonical Git blobs were copied directly into an isolated snapshot. Reviewed
artifact identities:

| Artifact | Canonical SHA-256 |
| --- | --- |
| `src/development_job_ledger.py` | `3cc61899da8a1fa4a9d87ef91df228e0153f36b3d755476fc0ebf3f45138b96f` |
| `tests/test_development_job_ledger.py` | `e8edf162744b9308aeb8f0236e8481288399830a0d9e875c96b662fa960adf9b` |
| `schemas/development-job-ledger.json` | `03cb5799acbafa2a052ac25a14d6b663dd17df0daa9336505e66eeb0ac8ec449` |

Fresh-process independent verification on that exact snapshot:

- External adversarial harness: **47/47 cases PASS**, 1.629 seconds. One case
  contains 50 additional deterministic randomized checkpoint/pause/resume traces.
- New job-ledger tests: **16/16 PASS**, 0.230 seconds.
- Existing handoff tests: **32/32 PASS**, 0.092 seconds.
- No skips in those runs. Diff whitespace checks pass. Only the six planned
  files changed from source `7169`; original science/request/pdca_bridge source
  has no diff.

The local external harness is
`.worktrees/development-job-independent-probes-20261025.py`, SHA-256
`b2c675f7d716e1f17880c4b408911606a028c6cfb01d5a1f1e89418eaf78578c`.
Its exact snapshot/file identities are recorded in
`.worktrees/development-job-review-08ea0ff6-metadata-20261025.json`.
All these tests are synthetic pure accounting verification, not actual worker,
runtime, clock, source or owner authentication.

The independent review found a concrete defect in initial source `8e567912`:
START generation1, WAITING_CI checkpoint1000ms/generation2, then a SETTLE from
that never-active generation2 reporting3600001ms was accepted as overrun.
The broad generation-membership check included WAIT and close-only fence
generations, allowing them to invent active work. The repair derives a separate
ACTIVE-issued generation history. Independent tests now reject overrun from
WAITING_CI, SETTLED and EXPIRED fence-only generations, while accepting late
incidents from the actual original or renewed ACTIVE generation. Ordinary stale
healthy settlement and renewal remain rejected. This correction does not grant
stale workers completion or execution authority.

The harness independently recomputed job/operation/attempt IDs and event hashes.
Changed source, request, run, night and protocol retain the same aggregate job
and operation; the second attempt consumes the same fixed two-attempt allowance.
No third attempt is available even if the active-time budget remains unused.
Request scope is revalidated at START, source/request are fixed within each
attempt, and rehashed derived IDs, ordinals, allowances, flags and event types
cannot bypass replay.

Long CI waits retain the same attempt/reservation without a worker lease or
added active time. Resume requires the exact checkpoint and a new generation.
Lease equality permits expiry, not ordinary completion/renewal. Expiry charges
the allowance conservatively; later ordinary reports cannot refund it. Late
known overrun adds only its positive actual delta, retains the complete bounded
reported value and blocks the whole job. Other ACTIVE reservations are charged
conservatively, while another paused CI attempt retains only its checkpoint
charge. The86,400,000ms metadata boundary, timezone/extreme-year arithmetic,
exact settlement idempotency/current-tip checks, actual32-event cap, bounded
snapshot/depth/strings/nodes, detached objects and absence of file/network/process
execution were also tested.

The pure boundary was explicitly exercised: a new zero-event proposal using the
same root/capability and a different anchor still has the same job ID, and a
self-consistent rewritten empty history can pass pure replay. Both retain false
authority. This phase therefore cannot prove persistence, prevent a remote
history reset or establish that allowance was never consumed. The next fixed
report layer must reject changed origins/anchors/bases, complete-history rewrites
and competing writers using the actual observed Git history. No durable or
restart-safe execution completion is claimed by this pure PASS.

All six authority/authentication flags remain exactly false. Actual runtime,
worker stop/fencing enforcement, deployed prerequisites, current clock, admitted
root/job and scientific-budget enforcement remain external gates. Declared
engineering purpose does not exempt scientific fitting/evaluation. No actual
job, worker, issue, controller dispatch, CI result, continuation or scientific
execution was created by this review. Exact integration/Ubuntu/fresh-main CI
and the separately tested fixed report publisher remain coordinator work.
