# Task7 declared implementation scope proposal

This slice implements only pure scope proposals and strict inspection. It does
not implement authenticated DevelopmentRequest admission, a job/claim/result
ledger, controller dispatch, continuation or background wake-up.

The sole current fixed capability is `CONFIGURED_STAGE1_PARENT_DISPATCH_V2`,
strategy `REUSE_SOURCE_STAGE1_V2`, requirements R005/R026. It reuses the separately
reviewed source adapter rather than duplicating E's active implementation. The
mapping permits exactly four parent/test/spec/review paths and a fixed Python
verification profile/acceptance list. No Raw/ORIGINAL, policies, schema, workflow,
registry, model, source-adapter or cycle writes are part of that proposed job.

`propose_development_request(provenance, need)` validates the complete bounded
declarations before no-request decisions. Missing data, unmapped requirements,
an installed parent or absent compatible deployed prerequisite return no request.
The successful status is `DECLARED_SCOPE_PROPOSAL`; every admission, execution,
science, selection, production and authenticated-GitHub flag is false.

`inspect_development_request(request)` rederives the entire request from the
fixed mapping and compares canonical bytes, including types, fields and hashes.
A rehashed path/profile/acceptance/limit/authority alteration cannot pass. The
stable strategy key contains master/repository/root/capability/strategy only;
source, parent run/night, evidence, registry version and expiry cannot reset it.
Future job accounting must aggregate root+capability across strategy/scope
revisions rather than treating a new request hash as fresh allowance.

Evidence refs have exact path/SHA-256/size fields and the same explicit night/run
namespace. Canonical relative nonlabel JSON paths, unique paths, exact positive
integers, at most16 refs/256KiB each/1MiB declared aggregate are enforced. Actual
files/modes/bytes and source/owner/PR/CI facts are not opened or authenticated.
Artifact raw-byte SHA and canonical request SHA are different identities.
Observed/expiry ordering is limited to24h; neither timestamp attests the actual
clock or proves the proposal is currently valid.

Engineering limits are declared schema caps: two attempts,3600 active seconds
per attempt,7200 cumulative,600-second lease. No budget is consumed/reserved or
enforced by a live job. Scientific fitting/research/evaluation must still use
the root300-second/two-round/three-recipe ledger and cannot be exempted by this
engineering purpose. Existing used campaigns cannot initialize fresh allowance.

Design review accepted this bounded pure interface and the concrete constraints
before implementation. TDD first ran the ten new methods without the APIs:
expected missing-API assertions failed (47 reported failures including subtests).
After implementation and additional boundary tests, all30 development handoff
tests passed in0.086s:17 existing accounting and13 proposal/inspector tests. Tests
cover changed-source identity, no-job decisions, exact booleans, malformed early
data returns, source/run/path/size/hash/expiry mismatch, rehashed authority and
scope injection, no file/network access, detached objects, schema scope agreement
and deliberately expired declarations retaining false admission. This is
synthetic contract verification, not a live admitted implementation job.

The combined original/new handoff, real Git persistence and connector suites
passed49/49 in61.123s without skips. All25 prior function/class AST bodies are
identical to the native PR108 source. During independent review a valid one-hour
interval in year9999 exposed overflow in observation+24h. A dedicated regression
failed first; changing only the new helper to compare the timestamp difference
fixed it. The complete handoff suite now passes31/31 in0.089s (14 new tests).
Schema review also found its RFC3339 date-time annotation narrower than the
existing aware-ISO parser. A regression first failed on that annotation; only
the two new schema clock annotations changed to explicit inspector validation.
The existing clock parser and accepted timestamps are preserved. All32 handoff
tests now pass in0.089s (15 new tests); no third-party dependency was added.

Before a future claim, the active authorized controller must directly inspect
the pinned deployed source: reviewed source-v2 prerequisite is actually present
and parent capability is actually absent. It must authenticate parent evidence,
root/command provenance, current clock, cumulative job attempts, real source/mode
and applicable verification facts, then atomically claim durable budget. This
proposal must not be sent to the scientific publisher or unsupported continuation
handler as execution permission. No actual job or child issue was created here.

Independent exact-source review, exact Ubuntu and fresh-main CI remain required.

## Independent review

Reviewed exact source commit `fe69a02c68df41e48ab230b49b7ad6b2447331ac`
on 2026-10-25. Result: **PASS for the bounded pure proposal/inspector slice**;
no remaining blocking finding. This does not approve a live implementation job
or complete the controller/continuation work.

Canonical Git blobs were copied directly to an isolated review snapshot; the
review did not normalize working originals or use their potentially converted
line endings. Reviewed identities:

| Artifact | Canonical SHA-256 |
| --- | --- |
| `src/development_handoff.py` | `0d502e56401b5a3bfad5aa600d8507a4e77ab56051c54bf83f2981d034a7afa0` |
| `tests/test_development_handoff.py` | `42996a5cabaf9a2493934aff4d24c646bab3653f83266f1ba9c9e7aff621ff31` |
| `schemas/development-job.json` | `637b352c6106415c3a2c1ba5b6990749fd599264d23f2e48747d556210473ab8` |

Independent verification against that snapshot:

- External adversarial harness: **69/69 PASS**, 0.025 seconds, no skips.
- Complete handoff tests: **32/32 PASS**, 0.085 seconds, no skips.
- All 25 pre-existing function/class AST bodies are identical to source `a919`.
- Commit diff whitespace check passes; only the five planned files changed.

The external harness is
`.worktrees/development-request-independent-probes-20261025.py`, SHA-256
`c18a93abe67a9e427fd8c18bb12ceb2db8273062aa4bea0d67b546284ab40552`.
Snapshot and per-file receipts are recorded locally in
`.worktrees/development-request-review-fe69a02c-metadata-20261025.json`.
These are synthetic pure-contract probes, not source authentication or admitted
execution. The implementer's real-Git publisher/connector run reported above
is separate evidence; this review did not claim to rerun that whole Git suite.

The independent probes recomputed strategy/request digests, varied source,
protocol, evidence, parent command, run, night and expiry, and checked that only
request identity changes. A different root changes the strategy key but still
provides no root authorization. All supplied malformed fields are rejected
before DATA_REQUIREMENT or other no-request outcomes. Exact booleans, duplicate
or foreign-run refs, traversal/reserved namespaces, declared byte/count limits,
bounded nodes/strings/encoded bytes/cycles, detached snapshots and absent
file/network/process access were checked. Rehashing wider paths, profiles,
acceptance criteria, limits, scope versions, trust flags or executable statuses
does not defeat the inspector's canonical rederivation; False/0 substitutions
are also rejected.

Two review findings were repaired before this PASS. A valid one-hour declared
interval on 9999-12-31 originally raised OverflowError when adding 24 hours;
the new helper now compares the duration safely, and the independent probe
passes. The schema's RFC3339 annotation was narrower than the existing aware-ISO
parser; its two clock fields now explicitly defer awareness/order/TTL validation
to the inspector. The old clock helper is unchanged. Equivalent timezone
instants and deliberately expired declarations retain the intended distinction
between declared consistency and a live authorized lease.

The fixed four-path scope, capability/strategy, verification profile and finite
engineering caps are derived by code. They cannot grant model, data, policy,
workflow, cycle or registry write scope. Source/prerequisite deployment, actual
missing capability, parent evidence, clock, real file modes/bytes and owner/root
provenance remain NOT_ATTESTED. All six admission/authentication/authority flags
are exactly false. No job, claim, result, publication, child issue or continuation
submission is implemented here. Future admission must inspect the pinned
deployed source and authenticate a durable cumulative budget across request and
scope revisions; neither a new source nor a new request hash is fresh allowance.
Scientific work remains subject to its existing cumulative science limits.

Exact Ubuntu and fresh-main CI, integration freeze and any live-controller
acceptance remain coordinator work and are not asserted by this review.
