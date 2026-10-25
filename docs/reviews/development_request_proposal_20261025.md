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
