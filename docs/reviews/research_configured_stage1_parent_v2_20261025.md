# Configured Stage1 source-v2 parent: design and baseline record

Status: DRAFT_DESIGN_REVIEW_REQUIRED. Design-only preparation; no implementation,
real-data fit, Stage1 scientific acceptance, PR, controller or publication.

## Exact starting state and scope

Worktree `.worktrees/research-config-source-v3`, reused clean on branch
`codex/configured-stage1-parent-v4-20261025`, starts at verified main
`5d4b84fcc0d9b54683f80b4fcace0818d7fb94bd`. Owned paths are exactly the parent
module, its existing test module and the new spec/review named by the fixed
development capability. This preparation edits only the two documents.

Read actual AGENTS/handoff/model/acceptance rules, current parent request v1-v3,
config-source loader/preparer, source-v2 adapter, parent/source fixtures,
`docs/reviews/master-goal-1642-controller-risk-check.md` and
`docs/plans/development-request-proposal-slice.md`. The latter maps
`CONFIGURED_STAGE1_PARENT_DISPATCH_V2` / `REUSE_SOURCE_STAGE1_V2` to these paths;
it grants no job, source, budget or execution authority.

Current parent source native Git blob is 29,644 bytes, SHA-256
`0a98ed940e461b49dd85802e2dd4f0006f3245a1e8ff55c831120aec9b8ba104`.
Version v3 prepares configured sets, but nonlegacy Stage1 is intentionally blocked
before its manifest read. The reviewed source-v2 API is present and already
validates all configured native models, exact cutoffs, held-out night/lineage,
full source ledger and v2 projection. Existing publication uses deferred
ownership-bound cleanup for v2/v3. None needs an alternate algorithm.

## Design offered for review

The companion spec proposes explicit twelve-field request v4, the required
source-bound config and nullable Stage1 source-v2 ref; all six legal ordered
triplets; exact v4 dispatch and REPLAY envelopes; shared actual-byte/deadline
checks; and unchanged v1-v3 behavior. Before Stage1 manifest preflight, a v4-only
call to the existing `_configured_prepared` helper provides full native admission
without evaluation I/O. The public source-v2 API then performs its own ordinary
copy/bind/validation. That repeated bounded work is deliberate and charged to the
same time budget. No source adapter or pure evaluator change is proposed.

Review should explicitly accept or reject that private-helper seam, the new
eleven-field `stage1_dispatch`, six-field `parent_dispatch`, null/missing/failure
semantics and unchanged prepared receipt. The source preparer's generic missing
parent blocker is not removed/resealed; separate v4 actual dispatch records the
local connection without pretending its trusted campaign/confirmation blockers
were solved.

## Pre-edit synthetic whole-artifact baseline

An external preparation script used `git -c core.autocrlf=false archive` at the
exact starting commit, extracted only existing source/tests/schema/protocol and
requirement paths into a temporary native-byte snapshot, and imported its actual
fixture/production code. It ran eight cases twice, with new then same-content
existing REPLAY. All eight produced three candidates and exactly one immutable
REPLAY; second calls reused its exact path and bytes. No code was patched,
outcome source authenticated, real model fitted or real scope manufactured.

The external scratch oracle is
`.worktrees/research-parent-v1-v3-oracle-20261025.json`: 1,081,337 bytes, SHA-256
`6794190ade4c5fd45413f70f9bd2d47dad1dc188dc4b17b1395fab2a43c2a3d6`.
It contains full first/reused dictionaries and literal physical REPLAY JSON, not
an opaque compressed fixture. It is outside Git and is not a runtime dependency.
The pinned source and existing synthetic helpers independently reproduce it.
Future owned tests may pin the whole digests/read counts below; no new committed
fixture or unauthorized path is required.

| Variant | First whole-result canonical SHA-256 | Actual bytes first / reused |
| --- | --- | --- |
| v1 complete, no Stage1 | `c1a90f286c438ee1773efdf75165900598e9b05ec3774240818848deafd103cf` | 177664 / 204382 |
| v2 complete Stage1 | `893d9364df4efadf34e8fb03490ce415ee9d414ab428c35ee3d2a00ecc011958` | 254109 / 254109 |
| v2 UNKNOWN coverage | `cdd4d527c18ddbe730231f18aa61f7b9841e448d3cd1bb930978ff20ad0c56ae` | 251617 / 251617 |
| v3 legacy config, null Stage1 | `969b29c8f7e20daf62a1a9f9d01bf26fc1e348a7d479d0e4269caae960ff6db4` | 316516 / 316516 |
| v3 exact legacy config, complete Stage1 | `ab158b23683404cc3897479f9ecb7136bbfcb3a8d00a677fe10bbbbbcdd0778b` | 380051 / 380051 |
| v3 reversed legacy config, requested Stage1 blocked | `fffc3ddea40fd39f3ce80316bf44438f4106b8f8e1d73ddceef3c1ff36de00a0` | 324547 / 324547 |
| v3 full-seven A1 config, null Stage1 | `486c22154815499e3dcfd34bcc6dc5a3f4f06d0ecc830a68c72acd0b3c4a7e25` | 1167524 / 1167524 |
| v3 full-seven A1 config, requested Stage1 blocked | `70cefa3c1d2ef9131aaaf202c36406ddd2f729ef0fcf6c848a21a333df8e786b` | 1176038 / 1176038 |

All reused whole-result hashes equal the first hash except the intentionally
different legacy v1 result:
`cd9a07a18a5e257583f6ab9e5d0e502d0a2867bbda5f7c44de1f441e1dad2faf`.
v1's extra reused read is existing behavior and must not be normalized away.

| Variant | Physical REPLAY SHA-256 | Bytes |
| --- | --- | --- |
| v1 complete | `b0bc9c552d400cd13a94d3c3df851a298b360bc100a16284ea7da9231a78fb7b` | 26718 |
| v2 complete | `89378f8ebe84036ebf16ea4d0379352a86c788072b7ffb39012470c951252b9a` | 32810 |
| v2 UNKNOWN | `243b598a3fa7ab672740f1f84c4ea75e53b345db3c38bc19a74a0d51aa714f2d` | 30358 |
| v3 legacy null | `65a641843a561ec0c9a34f73f4e70fc9920f4ec7d64f288d03adb8b6e48d73ed` | 35621 |
| v3 legacy complete | `50189e30f3f2e460a969cccef5b66b014ab4207fbb8f21ed463397cabaea1385` | 41716 |
| v3 reversed requested | `2c4b8f8171d940fd0002036f9dc46ff94ee13c4853ce71583f9cb76247570a82` | 35754 |
| v3 A1 null | `b66f77cc182e6577de85fc9b4fa92ad5ef25cfc56886e4360ad92b02d1c8110e` | 55580 |
| v3 A1 requested | `f4f28e09c657cecb5bcba187d175f97f302d132411f1f9b32b628fa7d66771d5` | 55713 |

## Proposed verification and remaining limits

The spec's TDD section requires actual source-loader/parent E2E for all six
ordered triplets, null/UNKNOWN/complete Stage1, native rehashed chronology before
manifest read, nested reserved refs before payload read, same-context bytes and
expiry, source/code mutations, new/reused artifact cleanup and true platform
link tests. Existing genuine POSIX tests remain Ubuntu-only, not fake fcntl.
Whole outputs, not just selected metrics, must preserve all eight old oracles.

No product test was written and no product source was edited in this preparation.
The eight synthetic baseline executions are not an implementation test pass or
Linux acceptance claim. Existing September-28 five source-qualified events/six
capture occurrences still lack a complete eligible denominator and usable
historical TRAIN/forecast feature contract. The parent may block at its earlier
strict gates; standalone source Stage1 remains NEED_MORE_DATA/empty metrics.

Current issuer/completeness claims remain DECLARED_CONSISTENCY_ONLY /
NOT_ATTESTED. Hashes do not authenticate loaded bytecode or historical availability.
No trusted cumulative campaign/three-candidate budget, root CAS reservation,
pre-reveal consumption ledger, independent confirmation, winner selection,
production activation or durable background controller is added. Cooperative
checks do not hard-preempt native operations; filesystem rescans do not create
an atomic hostile snapshot. Existing cleanup truthfully reports residuals where
ownership cannot be safely established and must preserve foreign bytes.

Independent design review and explicit coordinator implementation authorization
are required before product code/TDD. The coordinator retains freeze/STATE,
publication, exact-head/fresh-main Linux CI and main integration ownership.

Preparation validation passed: both documents decode as UTF-8/LF without trailing
whitespace; request table has exactly the intended twelve unique fields; all eight
first/reused canonical hashes, actual-read counters, single-file counts and physical
REPLAY bytes/hashes agree with the external native-snapshot oracle; native source
size/hash agrees with `git show` at the pinned starting commit. The tracked source
diff was empty. No product-suite or Linux execution was claimed for this doc-only
preparation.

## Design revision after independent comments

The first draft's acceptance item 2 incorrectly grouped Stage1 payload version
validation with request/config fit-before-input rejection. The revised design
keeps native admission before the first Stage1 manifest open. Request/ref/config
contradictions reject before fit; a correctly byte-bound supplied Stage1-v1
manifest is read and rejected only after preparation/admission, at the source
manifest gate and before evaluation payloads. There is no v4 downgrade. Separate
order sentinels and no-new-REPLAY assertions are required for both paths.

Source reading also confirms private `_configured_prepared` lacks the public-v2
runtime normalization. The revision names the same four capacity classes and
Stage1 budget exception as the public API and requires a narrow v4-only
translation/equivalent RUNTIME_BLOCKED handling. Shared-check TimeoutError and
InputCapacityError remain unwrapped, and unrelated caller-check exceptions must
not be suppressed or relabelled by that seam. No broad invalid-input exception
can become a resource block. Tests must exercise each named class and prove no
Stage1 manifest open, partial result or new physical REPLAY on exhaustion. Old
v1-v3 catches, outputs and baseline bytes remain unchanged.

This revision still changes documents only; implementation authorization remains
pending independent final design PASS.
