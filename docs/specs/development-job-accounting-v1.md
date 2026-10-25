# Development accounting proposals v1

This is implementation-completeness accounting consistency, not authenticated
admission or execution. The existing owner-authorized controller still needs
actual source/request/root/fact/clock/runtime verification before launching work.
All six authority flags are false; persistence is
`UNPUBLISHED_ACCOUNTING_PROPOSAL`, runtime is `CALLER_DECLARED_NOT_ATTESTED`.
Scientific fitting/evaluation always needs its separate cumulative scientific
budget; declaring engineering work does not exempt it.

`new_development_job(request)` accepts the strict fixed-scope request proposal.
Job identity hashes master/repository/root/capability, excluding request, code,
night, strategy and scope versions. Anchor night fixes the first storage prefix;
later request nights cannot relocate the existing job. Attempt identity hashes
job+ordinal1/2; operation identity hashes job+strategy. Both are derived. An
unknown future strategy/schema is rejected by the current request inspector;
future compatibility must retain the same root+capability accounting identity.

`append_development_job(ledger, expected_tip=..., transition=...)` owns and
replays complete history before appending. Exact tagged fields:

| Kind | Caller fields besides kind | Meaning |
| --- | --- | --- |
| START | request,now,lease_until | New bounded attempt; declaration observed<=now<expiry |
| CHECKPOINT | attempt_id,generation,active_ms,phase,now,lease_until | Fence current worker and checkpoint/renew/pause/resume |
| SETTLE | attempt_id,generation,active_ms,now | Close once or retain a terminal over-budget accounting incident |
| EXPIRE | attempt_id,generation,now | Conservatively close expired ACTIVE reservation |

Exactly two attempts share7,200,000 active milliseconds; each reserves at most
3,600,000. One open attempt at most. Full request/source/strategy are fixed by
START and cannot change inside that attempt. Each event derives its sequence,
hash predecessor and semantic digest; generation derives from sequence.
`inspect_development_job` derives all totals and attempts from history, never
saved counters. Strict integer/boolean types and canonical-byte comparisons
reject rehashed changes to derived identities/allowances or unknown fields.

ACTIVE renew/pause/healthy settle require now<lease_until. Lease duration is
positive and<=600 seconds, compared by timestamp difference to avoid extreme
year overflow. At equality only EXPIRE is valid. Expiry charges its allowance
in full and fences stale completion; later ordinary claims cannot refund it.

WAITING_CI has no worker lease. Its cumulative active checkpoint stays fixed.
Resume uses the same attempt and unspent reservation with a new generation/lease;
waiting itself adds no active time. A paused settlement must match the checkpoint.
These are caller declarations, not proof the worker stopped or actual time was
measured. Request expiry/current authorization must be rechecked by the eventual
execution controller; accounting operations alone grant no right to resume.

SETTLE overrun retains the full reported actual value, bounded only by86,400,000ms
metadata capacity. It is not an authorization for extra execution. Per-attempt
or total overrun terminally blocks the whole job, sets remaining0 and fences all
other attempts. ACTIVE reservations are conservatively charged; paused CI retains
only its known checkpoint charge. Known historical attempt generations may report
late overrun even after expiry/settlement, with charged=max(prior charged,report),
adding only the positive delta. No worker/source/lease is resurrected. A decreasing
report or ordinary stale completion rejects. Reports above the metadata bound are
explicit CAPACITY_BLOCKED/unreconciled, never clipped or replaced by zero.

Exact prior SETTLE payloads are idempotent only with the reconciled current tip.
Stale expected tips reject even retries. Proposals cannot serialize two external
writers; fixed Git report publication is the separate required durable layer.
It must reject alternate bootstrap/anchor/base/reset and compare full historical
raw canonical records, not merely the latest valid hash chain.

Whole input snapshot cap1MiB,10,000 nodes/depth12 and32 event cap are enforced.
Capacity exhaustion cannot initialize a new job to regain attempts. Clock truth,
actual hard-stop/runtime overrun measurement, authenticated facts and migrated
campaign history remain external unresolved gates. No admitted job, implementation
executor, CI verifier, child issue or backend continuation is created here.
