# Configured Stage1 source-v2 parent: design and baseline record

Status: IMPLEMENTED_PENDING_EXACT_SOURCE_REVIEW_AND_UBUNTU_CI. The initial
design-only preparation and its independent gate are preserved below. Current
implementation remains development-only; no real-data fit, scientific acceptance,
PR, controller or publication is claimed.

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
## Authorized implementation plan

Coordinator authorized inline TDD after final design PASS at 684e2cc / independent
doc commit 063b3d5. Use writing-plans, executing-plans and TDD within the same four
owned files; the independent section below remains reviewer-owned.

**Goal:** Explicit request-v4 dispatch to reviewed source-v2 without changing any
legacy result, numeric routine, input cap, authority or physical REPLAY behavior.
**Architecture:** Version-isolated request validation/dispatch metadata around
the existing config/G0/preparer/source/publication paths. No new registry/core.
**Tech stack:** Existing standard-library Python and exact source-bound JSON.
**Spec:** `docs/specs/research-configured-stage1-parent-v2.md` (final revised design).

Review focus: supplied Stage1 version is checked after admission, private resource
classes are runtime blocks, RESERVED refs never open, final mutations/expiry expose
no artifacts, and old physical/read-byte behavior remains exact.

- [x] Add eight full legacy first/reuse result and physical-byte regression cases
  in the existing parent test module using pinned native policy bytes.
- [x] Add actual v4 all-six/null/UNKNOWN/order/native/resource failure tests; run
  v4 representative tests and observe the missing version rejection as RED.
- [x] Add only explicit v4 request/dispatch/source-v2 and named private-resource
  handling in `src/research_pdca_adapter.py`; run the new and old parent targets.
- [x] Exercise source mutation, shared read/deadline, reserved refs and native
  publication/cleanup negative boundaries; retain genuine platform skips.
- [x] Run related source/config/preparer/pure/master targets, inspect the exact
  four-file diff and record native results/limits; commit exact source for review.
- [ ] Independent exact-source review, coordinator Ubuntu CI and integration are
  separate required gates; do not publish or alter STATE/freeze here.

## Implementation execution record

TDD RED: before product edits, the five new v4 methods failed because exact old
request parsing rejected request-v4. The eight whole legacy first/reused artifacts
passed in that same run (six methods, eight failed assertions/subcases,13.790s).
An earlier invocation from `tests/` had hit the existing `tests` namespace import
constraint and is not counted as feature RED; correct invocations use repo root
with `tests` on `sys.path`.

The implementation adds a version constant, explicit field/version branches,
eleven-field v4 dispatch, the public source-v2 call and v4-only private native
admission wrapper. It reuses the existing final source/config rescans and deferred
ownership-bound publisher. Named private capacity/budget classes map to runtime
errors; ordinary caller-check errors stay unwrapped. No legacy catch, model,
algorithm, upstream loader/evaluator/config/schema, registry or cap was changed.

The first green attempt identified two test-fixture mistakes: a null root left an
unreachable node and persisted into the following subcase. They were corrected in
the test setup; the source contract's valid rejection was preserved.

Owned target:

```text
python -B -X utf8 -m unittest discover -s tests -p test_research_pdca_adapter.py -v
Ran 47 tests in 93.576s; OK (skipped=2): 45 PASS, old and new actual-master POSIX skips.
```

This executes all six configured triplets with actual guarded loaders/preparer/
source-v2/pure-v2; null/UNKNOWN/incomplete/unavailable sources; real rehashed
uniform/A0/B1/A1 chronology/recipe contradictions before manifest opens; Stage1-v1
payload rejection after actual preparation/admission; exact named resource and
caller-check identity boundaries; nested full RESERVED preflight; known RAW
causal/identity contradictions even when UNKNOWN; same actual read context;
post-evaluation and post-stage source/code mutations; actual native-link
interruption; late new/reused REPLAY expiry; and all eight old first/reuse whole
hashes, actual bytes and physical bytes.

The platform probe creates an actual Windows junction for the evaluation manifest,
verifies external-open count zero and unchanged sentinel bytes, then severs only
the temporary junction. Linux executes the genuine symlink branch. Actual master
dispatch/quarantine behavior still requires Ubuntu; no fake fcntl/platform is used.

The Sept28 test uses native immutable Git CSV bytes and returns five events/six
capture occurrences with NEED_MORE_DATA and empty metrics. Its TRAIN/full-forecast
inputs are explicitly synthetic software controls: it is not a real-data fit or
an assertion of available historical features, search completeness or denominator.
No source bytes or evidence labels were changed.

After the first 46-method green run (44 PASS / 2 skips,85.756s), a final added
test confirmed insufficient TRAIN never releases a partial set or opens Stage1.
The final47-method run above includes it. Baseline policy fixtures read native
`HEAD` Git bytes with the exact original 1,751-byte/SHA-256 assertion
`79112d4f845b620ff928743cb1f6d14af62ce8bcf474f51fb32ec911d67941ac`.
Thus shallow CI does not need to fetch the old baseline commit; runtime checkout
bytes are never normalized, and the eight old artifacts remain exact.

Related native regression: `test_stage1_source_adapter`,
`test_stage1_configured_source_adapter`, `test_full_ledger_stage1`,
`test_research_candidate_config_source`, `test_research_model_adapter`,
`test_g0_training_source_contract`, `test_g0_forecast_contract` and
`test_prospective_inputs`: 297 methods in 62.307s, 291 PASS / 6 existing POSIX
skips. Run from repo root with `tests` on `sys.path`, load those names using
`unittest.defaultTestLoader.loadTestsFromNames`, and execute
`unittest.TextTestRunner`. Together with the owned target, 344 methods yielded
336 PASS / 8 genuine platform skips. No full Linux, actual POSIX master or
quarantine execution is inferred from Windows; coordinator exact-head/fresh-main
Ubuntu full-suite acceptance remains required. No fake fcntl/native library or
global runtime/dependency modification was used.

Final scope validation checks only the four owned paths changed, original
independent-design section content is byte-identical to 063b3d5, and
`git diff --check` passes. No Raw/ORIGINAL, evidence policy, source adapter,
evaluator/preparer/config, registry, schema, controller, STATE or freeze changed.

## PR111 cross-runtime oracle correction

Ubuntu CI40187765262 ran 1,282 tests in 459.949s with 22 platform skips and two
failures, both original A1 whole-hash assertions: null actual `f910a93f...` versus
original `486c2215...`, requested-blocked actual `cd054fbb...` versus original
`70cefa3c...`. No product failure or missing sklearn backend was established.
HB-A1 reuses the unchanged pure-Python logistic core with statistics.mean,
math.sqrt/math.exp and ordinary float arithmetic; numpy/scipy/sklearn are not
called. The unrounded parameters feed model/prediction/prepared/content hashes,
physical REPLAY lengths and cumulative read counters.

Before changing the test, a scratch execution verified original parent source
0a98/29,644 bytes and compared it to the current program under identical native
dependencies and the same actual synthetic input. Both FULL results and literal
REPLAY matched the original Windows artifact `486c2215...`,1,167,524 bytes read.
A controlled shared math.exp→nextafter(exp,+inf) changed coefficient[0] from
-1.1281752644830656 to -1.1281752644830654 and model SHA from `f0088dd9...` to
`03506119...`. Both programs remained completely equal, including literal REPLAY
and 1,167,522-byte read ledger, but whole SHA changed to `8ade8ac1...`.
The existing hard-coded test was then executed under that controlled diagnostic
and reproduced exactly two A1 failures in 10.279s (null `8ade8ac1...`, blocked
`2d500ba6...`). This is real RED for the test's platform assumption; it does not
claim that the controlled function is the Ubuntu implementation. The independent
reviewer separately reproduced the same old/new equality and changed artifact.
**The precise actual Linux cause remains pending same-Ubuntu old/new execution or
its actual coefficient diff; libm final-bit variation is the demonstrated leading
mechanism, not a certified Linux diagnosis.**

Coordinator authorized two exact immutable synthetic fixtures and the dual-layer
test. The original readable full archive is copied without modification from the
pre-edit external oracle:1,081,337 bytes/SHA6794190ade4c5fd45413f70f9bd2d47dad1dc188dc4b17b1395fab2a43c2a3d6.
The old parent text capsule is byte-identical to original Git source and the
coordinator's emitter fixture:29,644 bytes/SHA0a98ed940e461b49dd85802e2dd4f0006f3245a1e8ff55c831120aec9b8ba104.
Its text newline decoding preserves the original LF executable source across
CRLF checkouts; original observations are never normalized. Source/capsule hashes
are checked before trusted test-only execution. The original eight ORACLES
constants, dictionaries, first/reuse read counters, file inventories and literal
REPLAY strings are unchanged and independently checked for integrity.

The repaired execution test builds fresh identical fixtures for each old/current
invocation, then compares all eight complete first/reuse objects, their canonical
JSON bytes (including exact numeric types), actual read ledgers, filenames and
literal physical REPLAY. It does not compare a newly regenerated expected result,
round parameters, relax tolerances, permit platform hashes or skip any platform.
A separate controlled ULP diagnostic repeats exact old/current equivalence;
genuine core/library numerical tests are unchanged. When the actual old runtime
differs from the immutable historical artifact, CI prints its actual A1 parameter
vector/read count/whole hash for diagnosis only; those values never become an
alternate expected result.

Base alignment was an authorized ordinary merge of current PR111 source00d01ba
into this branch (merge41f4ed7), with no reset, source edit or manual STATE/freeze
change. Only test harness/immutable fixtures and this spec/review are repaired;
the parent implementation, learners, policy and numerical recipes are unchanged.

Repair verification:

- New oracle class: 3/3 PASS in32.742s (immutable original artifacts/source,
  all-eight actual-runtime whole comparisons, controlled ULP whole comparison).
- Final owned parent + genuine standalone HB-A1/shared logistic numeric modules:
  120 methods in114.406s,118 PASS /2 genuine actual-master POSIX skips. This final
  run includes canonical typed equality, not only Python bool/int equality.
- Additional native reproduction invoked the exact original program for all
  eight cases and compared FULL first/reuse results, read ledgers and literal
  physical REPLAY to the preserved historical dictionaries: all8 exact. No static
  expected digest or byte was updated.
- Original ORACLES literals compare unchanged to3d743d4 via AST. Original archive
  bytes compare identical to the pre-edit external file. The archive has zero
  physical LF/CRLF characters (literal REPLAY newlines are JSON escapes), so its
  read_bytes/hash remains exact on autocrlf checkouts. No fixture attribute change
  is needed. Source capsule matches the coordinator's Git blob byte-for-byte.
- Prior independent review sections remain byte-identical; no product source
  edits exist relative to the integration merge. Coordinator actual Ubuntu
  old/new pair, full suite and refreshed CI acceptance remain unperformed here.

## Independent design review

Reviewer `/root/config_review` gives **DESIGN PASS** at exact revised design
`684e2cc0d96d57e0cb50239607b7f059f2f8d87a`, following initial draft
`a833bf31b9dfc9809fbd77905af0fb091c5d03e4`. This accepts the bounded design for
coordinator-authorized TDD; it is not implementation, runtime, scientific or
integration acceptance. No product code/test was edited or product test executed
by this design review. The tree was clean before this independent section.

The reviewed spec Git blob is
`db61bd713b43f2cff8679940ae7fbfbe84d3d3ca`; the implementer's review before this
section is blob `301d7cd748f465369798655e997cc88d85eb1b79`. Both design commits add
only the two owned documents relative to base
`5d4b84fcc0d9b54683f80b4fcace0818d7fb94bd`; source/test trees remain identical to
that base. Current parent/source-v2/config loader/preparer and context/publication
code were read against the proposed interfaces and order.

The explicit twelve-field v4 request, eleven-field Stage1 dispatch and six-field
parent dispatch are coherent with existing parent envelopes. The six configured
orders are exactly uniform first plus two distinct A0/B1/A1 candidates. Reusing
the existing source-v2 evaluator retains native B1 recipe/rank-score semantics,
null configured recipe projection for non-A1, complete individual denominators,
outside-universe misses and fixed paired-night bootstrap. HB-A2, fourth candidates,
fallback, reordered output and implicit v3 widening are excluded. Null Stage1
opens no evaluation manifest or outcome; valid insufficient Stage1 retains the
whole prepared set with empty metrics. Invalid supplied evidence releases no
partial set or new owned REPLAY. Prepared/native objects stay immutable and the
standalone preparer's generic blocker is not removed or resealed.

The private `_configured_prepared(config, forecast, prepared, expected,
definitions, context.check)` seam is accepted for this owned-parent slice.
It performs bounded admission without evaluation I/O, before manifest preflight;
discarding its projection and then calling the unchanged public source-v2 API
duplicates validation deliberately under the same budget. It must not become a
second validator or evaluator. Exact native schema, recipe, common fit/held-out
night and prediction/TRAIN/config bindings precede evaluation-manifest opens.

Two initial design issues were resolved in the reviewed revision:

- Request/reference/config contradictions reject before fit. A correctly byte-bound
  Stage1-v1 payload is rejected later, after native preparation/admission at the
  source-manifest gate and before outcome payloads; v4 never downgrades. The old
  wording could have moved manifest reading ahead of required native admission.
- The private helper bypasses public source-v2 exception normalization. A direct
  independent call using a 4,097-character JSON string reproduced raw
  `pure.Stage1CapacityBlocked`, a ValueError subclass that the current parent
  would otherwise classify as invalid evidence. The revised v4-only boundary
  names the same four capacity classes and Stage1 budget class as the public API,
  requires equivalent RUNTIME_BLOCKED handling, and preserves ordinary shared
  timeout/input-capacity and other caller-check failures. Broad ValueError/Exception
  swallowing and changes to v1-v3 exception behavior remain forbidden.

The full RESERVED set is checked in top/nested manifest refs before their targets
open, without introducing recursive arbitrary-file traversal or widening source
namespaces. The existing source-v2 graph still owns RAW/DERIVED closure, four-stage
readiness causality, actual CSV/individual/coverage identity and known-contradiction
checks before missing-data metrics. All source/config/code rescans, repeated reads,
readback and reused-artifact reads use one actual-byte ledger and deadline through
the final result. Publication remains deferred and cleanup uses only the existing
ownership-bound mechanisms, preserving reused/foreign bytes and reporting unsafe
residuals truthfully. These checks do not promise atomic hostile snapshots or
hard preemption between cooperative checks.

Independent baseline validation used the bundled Python executable with
`-B -X utf8` and standard-library JSON/SHA-256 plus `git show` at the pinned base.
It verified **107 assertions** across all eight stored first/reused complete
objects, recorded canonical hashes, three-candidate/single-file counts, literal
physical REPLAY size/hash/reference identities, positive actual-read counters and
the base native source size/hash. All matched the implementer's tables, including
v1's distinct reused result/read count. The external oracle remains 1,081,337 bytes,
SHA-256 `6794190ade4c5fd45413f70f9bd2d47dad1dc188dc4b17b1395fab2a43c2a3d6`.
This checks the stored baseline's internal/document consistency; it does not claim
new v4 behavior or rerun the eight original product executions.

Implementation acceptance must still prove those whole old artifacts unchanged,
all six actual source-backed v4 orders, native-before-manifest sentinels, null and
missing/UNKNOWN behavior, named runtime translations, late mutation/expiry, genuine
platform link containment and owned new/reused cleanup, followed by independent
exact-source review and coordinator exact-head/fresh-main Ubuntu CI. All source,
campaign, prereveal, confirmation, selection and production authority remains false
or NOT_ATTESTED. Task7 admission/controller/backend return and real qualified model
training are outside this slice. No real-data or scientific success is inferred.
## Independent exact-source review with portable-path correction

Reviewer `/root/config_review`: **source/guard review PASS** on actual combined
snapshot `543e75efa91b6e64d915f847e9b07a30fa085329`, branch
`codex/configured-stage1-portable-20261025`, base
`be045334a5ede3d5b92088e86b2b4852ccc8b6a1`. This snapshot normally merges parent
implementation `3d743d490176ade83cf89af398e4be7f9409e5fe` and shared path repair
`478a5f19df2fd4784ae33baf9d0334c55ac91fa0`. Final acceptance used the repair
actually present in that Git tree, not a process-preloaded mixed-source probe.
The combined tree was clean before these independent review sections. Full
coordinator exact-head/fresh-main Ubuntu and POSIX gates remain required.

| Reviewed source | Git blob | Canonical bytes | Canonical SHA-256 |
| --- | --- | ---: | --- |
| src/research_pdca_adapter.py | cb73ffd399ebc84b563a93eec240dba90a1d693d | 31947 | 1892440621057125b40adfef09a583395a744e505a3cc5fff657fa0f2db2fcc9 |
| src/master_inventory.py | e6fe8403529e1740110d7130cb37e119aaed0964 | 5533 | 1f108ce34e0f450cf4b438a912bb333df923fd50b0e6752760685c00df05db27 |

Parent test blob is `fe9d212b4be16c2d745e28dac92e6bc97243f39d`; helper test blob
is `7b7ceb93cc01be67e1104432e6a1517d380c4cce`. The native CRLF checkout hashes
were respectively `d2f6c3c6a0a20726c60049251d404895bf263217e9957e41924c781ab872f15a`
and `8ab3064e4060cd4995ed801f578c8fb75ab6cb1adc88352c912a19de35f7f3e0` for the
two source files. These byte identities do not authenticate loaded code or issuers.

Initial exact-source review was **NOT_PASS**: the real Win32 spelling
`evidence/ORIGINAL./manifest.json` read the same temporary file as
`evidence/ORIGINAL/manifest.json`. Raw RESERVED component comparisons missed it.
The original parent opened that manifest six times and returned three candidates
and one diagnostic REPLAY. The existing external eight-case harness also showed
top TRAIN/forecast/config-profile and nested config-binding bypasses. Native
payloads and Path.open were observed directly; no filesystem/platform was faked.

The separate approved helper repair rejects trailing ASCII dot/space, colon and
`~[0-9]+(?:\.|$)` components before safe_path or metadata, retaining original
containment/reparse checks. Strict config/TRAIN/forecast/Stage1 G0 reads all pass
through this boundary before payload open. Final actual-combined execution of
the same eight cases gave **8/8 PASS**, forbidden actual opens/candidates/REPLAYs
all zero, with REJECT_CANDIDATE. No new filename demonstrations were added after
the coordinator narrowed that investigation. No actual 8.3 alias is claimed.

Static source review confirmed explicit exact v4 request/dispatch branches,
all six configured orders, nullable Stage1, unchanged public signature and old
v1-v3 paths. The private admission seam validates native schemas, recipes,
chronology and TRAIN/prediction bindings before Stage1-manifest preflight. It
translates only the approved named capacity/budget classes and preserves ordinary
shared-check errors. The public source-v2 evaluator, pure evaluator, algorithms,
native B1 score/recipe and prepared receipt are reused unchanged. No new learner,
fourth registration, fallback, reordering, authority or prepared-object reseal
was introduced. The six-field parent and eleven-field Stage1 dispatch metadata
retain their fixed false/NOT_ATTESTED boundaries.

Independent commands used the bundled executable
`C:\Users\qq113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
with `-B -X utf8`, from the actual combined tree:

```text
python -B -X utf8 ..\configured-parent-v4-review-probes-20261025.py .
python -B -X utf8 ..\configured-parent-v4-alias-review-probes-20261025.py .
python -B -X utf8 -m unittest discover -s tests -p test_master_inventory.py -v
```

The first external harness passed **118 assertions**, including **16 actual
first/reused legacy parent invocations**. Each complete dictionary and literal
physical REPLAY was compared to the original eight-case archive, plus exact file
counts. Original oracle SHA-256 remains
`6794190ade4c5fd45413f70f9bd2d47dad1dc188dc4b17b1395fab2a43c2a3d6`.
All whole objects/read counts/physical bytes matched under the corrected helper:
no golden drift occurred, and no expectations were regenerated from v4, skipped
or replaced. Original v1 first/reused differences remain intact.

Further assertions exercise actual private-helper JSON byte/node exhaustion
before any manifest read, exact metadata/order/false flags, the 2/3 individual
denominator and outside-universe miss, final cumulative actual bytes, same-size
forecast/profile/code mutation after the real evaluator, UNKNOWN with an actual
duplicate individual, final postpublication expiry, and a real foreign inode
replacement preserved with a truthful residual report. These are synthetic
software controls, not real-source model fitting or scientific scoring.

The eight-case alias harness and 118-assertion harness are reviewer-owned external
files, unchanged by product code. Their SHA-256 values are respectively
`9d1327007d99d1577ca1830472af6e24b8af8c851b50412c67d8829fbc92951c` and
`9803fd291c24f04a435fedd7d374cbd3002981dda797116ddfba40b68367b684`.
Independent combined helper tests ran **26 methods: 22 PASS, four genuine
platform skips, 4.810s**. The parent target was independently run on exact
`3d743d4` before the helper merge: **47 methods, 45 PASS, two actual-master
POSIX skips, 89.401s**. The final combined external reruns above verify the
corrected dependency; no skipped POSIX execution or full Ubuntu result is claimed.

No remaining source-review findings were identified. Source/time/ID graph rules,
known contradictions before missing-data metrics, final source/config rescans,
one context/read ledger, deferred publication and ownership-bound cleanup remain
the controlling boundaries. Rescans are not atomic hostile snapshots; cooperative
checks are not hard preemption. Five source-qualified Sept28 events/six capture
occurrences still do not establish historical TRAIN/forecast eligibility or a
complete denominator. Source authentication, campaign/prereveal trust, selection,
confirmation and production authority remain absent/false. No source, tests,
state, cycle or historical artifact was edited by this reviewer.
