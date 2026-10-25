# Independent review: first pure root-accounting slice

**Bounded code review PASS.** No blocking defect was found in this slice at
`5a3a14eced101239d406ff3a45c80b83a110f63a`, based on source review, 17 fresh
authored tests and 92 independently written assertions. This is approval of
declared accounting proposals, not implementation or acceptance of full Task7,
an authenticated durable ledger, actual continuation or execution authority.

Branch: `codex/development-root-ledger-20261025`.
Base: `88511edd37e81b5c0c8a8714981fc7572fe1f2c3`.
Normative context reviewed: the slice plan, controller plan, controller
continuation plan and pre-implementation controller risk check. The reviewer
did not edit module, tests, plans, bridge, parent or shared state. The only
tracked reviewer addition is this document.

## Frozen source

SHA-256 values describe Git blob bytes rather than checkout line endings.

| File | Git blob ID | SHA-256 |
| --- | --- | --- |
| `src/development_handoff.py` | `bbf580e34387425482e24cc4e228fc5073357e2d` | `978d49a93cc1edf9f7939b88eed91a3abd54f60fc03ac6fabffa0e041e968694` |
| `tests/test_development_handoff.py` | `75b25d9cb3cba243606444100e1c32a0a4b0da21` | `d179c91eef5752bc689a06520012f74d0c824ee281a7c3144313d6760834821b` |
| `docs/plans/development-root-ledger-slice.md` | `f52903f814cca25860f4854907e3160671c064b1` | `77ca5210b8a0779d0f836c2fd3d32232562afb2d03c95f693595b39f2e4500aa` |

The source change adds exactly these three files: 280 module lines, 191 test
lines and 43 plan lines. No prior source, Raw, ORIGINAL, Freeze, evidence
receipt, registry, governance, shared state, parent or bridge file is changed.

## Independent accounting and replay checks

The mixed-reservation probe independently observed the following
`(used_ms, reserved_ms, remaining_ms)` sequence:

- Reserve 200000ms for A and 100000ms for B: `(0, 300000, 0)`.
- Settle A at 150000ms: `(150000, 100000, 50000)`.
- Expire B: `(250000, 0, 50000)`; expiry charges its full reservation.
- Retry A with the remaining 50000ms: `(250000, 50000, 0)`.
- Settle that retry at 17ms: `(250017, 0, 49983)`.

Every step conserves exactly 300000ms. Settlement releases only unused reserved
allowance and repeating it does not append or charge twice. A third attempt
for A and a third distinct operation/round both reject. Changing A's canonical
child, source commit or round rejects after settlement. Active reservations
consume allowance and round slots before execution; another operation cannot
spend the reserved allowance.

A separate fully reserved root rejects late completion and a reported overrun
without releasing anything. Expiry then charges all 300000ms, repeating expiry
is idempotent, and the expired attempt cannot publish or restart science.
Wrong/bool/zero generations reject. The declared lease endpoint is inclusive
for settlement; expiry requires a strictly later aware instant. Leases above
600 seconds, backwards clocks and unsupported timestamp horizons reject.
Equivalent JST/UTC instants are accepted consistently.

The reviewer recomputed every successor hash and tip after corrupting earlier
events. Replay still rejected excess/bool reservations, incorrect generation,
long leases, malformed source identities, excessive settlement, backwards time,
changed canonical child/source/round, reused attempts and altered recipe bytes.
Thus a fresh content hash cannot excuse these semantic contradictions. Saved
summary fields, extra trust fields, true authority and altered limits reject.
All three legal uniform-plus-two fixed recipe sets work; missing uniform,
missing slots, a fourth recipe and changed registered bytes reject.

Input/return/inspection ownership checks found no aliases back to caller
objects. Byte/node limits reject before owned JSON parsing, cycles and
non-JSON/non-integer scalar payloads reject, and the event cap prevents partial
publication. Patched file/network entry points were not reached.

## Fresh verification commands

Native Windows runtime:
`C:\Users\qq113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.
Working directory: the reviewed worktree. Commands used `-B -X utf8`; no fake
`fcntl`, real scientific data or confirmation outcomes were used.

- `python -B -X utf8 -m unittest discover -s tests -p test_development_handoff.py -v`:
  **17 tests PASS**, no skips.
- `python -B -X utf8 ..\root-ledger-review-probes-20261025.py .`:
  **92 independent assertions PASS**. Probe SHA-256:
  `5adb1259cebbaf90b35cea56990f4eba84bf1bc206685fa1bad4f9ce96465a0d`.
- `git diff --check 88511edd37e81b5c0c8a8714981fc7572fe1f2c3 HEAD`:
  PASS. `git diff --numstat` and `git ls-tree` confirmed the scope/blob IDs above.

The independent probe script is a local review artifact outside the tracked
source tree; its hash/path does not imply publication or CI execution.
Independent assertion counts are separate from unittest method counts.

## Limits and outstanding integration

The pure API bounds JSON to 1 MiB, 10000 nodes, depth 12, 1024-character values,
128-character keys and 64-bit integer magnitude. History is capped at 32
events; reservations are at most 300000ms cumulatively including outstanding
reservations, two distinct rounds and two attempts per operation. Durations
require exact integers, excluding bool. Each event validates the preceding
hash, canonical content, sequence and semantic transition from origin to tip.

These are self-consistency checks on caller-supplied values. A supplied origin,
clock, source hash or elapsed duration is not authenticated fact. Hash replay
does not prove that a submitted history is the authoritative durable history
or prevent replacement by a different coherent history. Expected-tip equality
checks a proposal against the supplied ledger; only a future authenticated
direct-parent non-force publisher can provide actual CAS, anti-rollback and
exclusive execution admission.

All execution/scientific/selection/production flags remain false and persistence
remains `UNPUBLISHED_PROPOSAL`. Trusted root authorization, durable publication,
runtime measurement/overrun interruption, source reconciliation, independent
GitHub fact admission, implementation-job budgets, parent/bridge integration,
controller state machine and observed backend continuation remain unimplemented.
No transport idempotency, authenticated CI fact, scientific improvement,
production readiness or Master Goal completion follows from these tests.
Exact-head Linux CI and integration on subsequently verified main remain
separate coordinator gates.
