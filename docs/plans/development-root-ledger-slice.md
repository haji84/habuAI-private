# Task7 first slice: pure cumulative scientific reservation ledger

This implements the reviewed controller risk-check's accounting boundary before
any bridge/controller dispatch. It is a pure proposal/validation API, never a
trusted ledger, GitHub fact verifier, atomic publisher or production authority.
Actual authenticated publication, root authorization, implementation-job budget,
source reconciliation and backend continuation remain later required slices.

Own `src/development_handoff.py`, `tests/test_development_handoff.py` and this
document only. Preserve existing bridge/parent/default behavior and all Raw and
ORIGINAL bytes. Use synthetic TDD and independent review before integration.

The immutable origin binds one command/night and exactly three preregistered
recipes, including uniform. Append-only canonical hashed events retain previous
event identities. Replay derives totals rather than trusting saved summaries.
One reservation atomically proposes operation/canonical child/source/attempt,
fencing generation, round, recipe subset, lease and remaining milliseconds.
Maximum scientific compute is 300000ms and two distinct improvement rounds;
reservations consume remaining allowance and round slots before execution.
Settlements are idempotent, release only unused reserved compute and reject
stale generations. Expired leases charge all reserved compute and fence late
publication. Source/request/attempt changes under the same root cannot reset
consumed rounds, recipe identities or canonical child ownership. Clock strings
must be aware and all durations exact integer milliseconds, excluding bool.

All supplied content is bounded JSON and owned before processing. Validate every
event and hash from origin to tip, not just the current hash or a PASS field.
Every mutation requires expected tip equality; actual remote CAS must be supplied
by the future serialized direct-parent non-force Git publisher. No filesystem,
network, shell, arbitrary executable fields or authentication flags are accepted.
Returned proposals explicitly retain all execution/scientific/selection and
production authority false. A new unrelated root is not proof of authorization.

Leases are at most600seconds. Supplied clocks, elapsed durations, recipe names
and origin authorization remain caller declarations. A completion reporting
more than its reservation is rejected and does not release the reservation;
trusted runtime overrun detection/accounting and interruption enforcement must
be implemented in the future controller, never inferred from this pure result.

Tests cover competing writers from one tip, stale/CAS/altered historical event,
forged totals, fourth/replaced recipe, third round, parent200s/child100s,
expiration/late worker, repeated settlement, canonical child/source, changed code
without allowance reset, invalid timestamps/durations/fields and detached inputs.
