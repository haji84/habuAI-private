# Planned effort implementation plan and verification ledger

> Inline execution using the approved design; TDD for the owned module/test,
> then an independent whole-source review coordinated by root.

Goal: project one typed original plan onto a complete bounded declared 100m/600s
domain, without opening G0, measured-effort, fitting or production authority.
Architecture: bounded raw-token/JSON ownership checks → existing pure readiness
max validation → exact identity/domain/interval checks → deterministic full
projection → checked content seal. Python standard library and existing public
G0 readiness/ProspectiveReadContext only; no new dependencies or source graph.
Spec: `docs/specs/g0-planned-effort-projection-v1.md`, approved at16d67b9.

## Global constraints and review focus

Owned: new src/g0_planned_effort_projection.py, its new test, this record and
approval-only append to the spec. Existing runtime/tests/G0/policy/STATE/Raw are
unchanged by this implementation. Latest main120 bbb5290 was normally merged
with per-command core.autocrlf=false/Codex identity before implementation.

All raw numbers are integers: booleans/floats/nonfinite reject; numeric tokens
have at most20 digits before decoding. Raw4MiB, combined16MiB,2million JSON
nodes/depth12,20000allocations,120000 complete output rows/16MiB; all limits are
checked before their respective allocations. One existing context/deadline;
no file/net reads and no fictional actual-byte accounting. Source raw byte hash
is checked; domain canonical hash is checked; domain/code physical refs are not.

Review focus: UNKNOWN/None cannot hide known scope/max conflicts; raw lexical
bounds must precede decoder calls; context exceptions retain identity; a shared
caller alias must not mutate owned output; planned zero must not become actual
measurement/Negative/Poisson denominator. These get dedicated tests below.

## Task 1: pure source and domain boundary

- [x] Add missing-module RED tests with complete explicit fixture, hand-checked
  300s/300s split, canonical row IDs, raw/canonical hash distinction and flags.
- [x] Add schema/ref/identity/time/readiness/UNKNOWN/None contradictions and raw
  decoder token tests; verify their RED state.
- [x] Implement the exact approved API, fixed input contracts and shared context
  using pure public validate_readiness (no I/O/path filesystem inspection).
- [x] Verify source/domain boundary tests GREEN.

## Task 2: complete planned projection and bounded execution

- [x] Add RED controls for overlap/timezone aliases, out-of-domain, seconds,
  multi-crew, full-zero versus missing, before-copy/parse/output/final-seal
  resource failure, native no-I/O observation and callback exception identity.
- [x] Implement exact half-open bin intersections and full cell-major projection
  under one shared context; release no rows on incomplete/failed input.
- [x] Verify new tests plus existing planned/lagged rejection and count tests.

## Task 3: exact release

- [x] Compile/diff checks and bounded dependency regression before owned commit.
- [x] Record actual command counts/timing and limitations, no actual fit/source
  authenticity or independent review claimed before they occur.
- [ ] Independent review and coordinator CI/integration (pending exact release).

Ruling: the coordinator explicitly approved inline TDD implementation and this
owned-path ledger; no additional plan approval or duplicate model package is
introduced. The spec's64-character draft numeric bound is superseded by the
approved20-digit integer-only raw token rule. A valid source/header with crew>1
is an explicit unsupported capability, not a new biological/source policy ban.

## Implementation evidence — 2026-10-26

Base/design commit16d67b9fdbe857037fed29ec2098c17489982c5e was followed by the
authorized normal merge825431b865365bcbc860177497240ea3d778769e of main120
bbb5290f37f9c9bb6ddf631b3db4eb1137e8fbdd. The implementation commit contains
only the four owned files; imported coordinator STATE/cycle contents were not
manually edited. No PR/push/new freeze or actual-data fit was performed.

Initial25 tests failed because the module did not exist, then passed with the
bounded implementation. Additional owned probes increased the module suite to
33 tests. The seed1642 randomized test checks40 shuffled, gapped source plans
against an independent one-second tick oracle, including exact per-bin totals
and conservation. This is synthetic software verification, not source evidence.

The release checks used the bundled native Windows Python3.12.14 with
`-B -X utf8`. Fresh results:

- New projection suite:33 tests PASS in0.268s.
- Combined projection, count-feasibility, constant-Poisson diagnostic and
  `G0ForecastTests.test_planned_and_lagged_are_capability_blocked_not_prohibited_policy`:
  94 tests PASS in1.047s.
- Both new Python files compile in memory; `git diff --check` passes.
- Native Python audit observer records no open/listdir/scandir/socket/subprocess
  operation during projection. The supplied read context's actual-read bytes,
  byte limit and absolute deadline remain unchanged; its check callback is used.

The two last coordinator resource findings were reproduced before correction:
an enormous negative in-memory integer reached `abs`, and output size checking
omitted the added receipt-hash field. The integer preflight now rejects
bit_length>67 before abs/encoding, then compares the exact20-digit magnitude.
Tests observe no huge-value abs/encoding call through domain, bindings and
identity paths and retain the positive/negative20-digit boundaries. The result
self-hash still covers only its body; a final streaming encoding checks the
entire sealed object. Sealed-length-minus-one rejects, exact length passes, and
a terminal context exception retains identity. A separate malformed-night RED
probe became ValueError with a local string guard; shared validators are intact.

No blanket Windows full-suite success is claimed. Parent-managed Ubuntu exact
CI and independent hostile review remain pending. Tests here add no fcntl
substitute, skips, longer deadline or capacity relaxation.

## Source and capability limitations

The design's main699 GitHub/tracked-source audit did not establish any qualified
typed planned allocation. Its search scope is recorded in the spec; absence is
not proof that all owner originals or branches were searched. Real original
captures/GPX are neither deleted nor repurposed as plans. No actual plan was
created or inferred in this implementation.

Only the caller-supplied raw plan's physical bytes/size/SHA and the supplied
domain's canonical SHA are checked. Domain/code physical-file refs, issuer,
latest revision and claimed historical availability are unverified caller
dependencies. A newly manufactured coherent JSON plan is not authenticated.
All output fit/science/selection/promotion/confirmation/official/production/G0/
count-denominator authority flags remain false, including complete zero plans.

The API rejects outside-domain allocations rather than dropping them, keeps
full-scope outside-universe captures as an independent FN-ledger obligation,
and never invents routes, interpolation or observed effort. Single-observer
overlap is rejected globally. Multi-crew is unsupported. Whole-table output is
bounded at120000 rows/16MiB; archived16990x72 exceeds this collector, so no
full-night capability is claimed. G0's existing planned/lagged capability block,
model registry, measured-count gates and parent dispatch remain unchanged.

## Independent review

V independently reviewed initial exacte7193c1dab1a07a6986eb0d28c541eaf8f1e617f,
ran its33 owned tests successfully, and reported portable path aliases and
JST-boundary OverflowError findings. Root verified and authorized the repair,
plus removal of the undocumented same-night cutoff requirement. Final hostile
review of the repaired exact commit remains pending; no PASS is claimed here.

### Review repair and fresh verification

The three new regression tests were RED before the source repair: trailing
dot/space and short-name path aliases were accepted; year9999 local conversion
leaked OverflowError; coherent prior-night cutoff/issue/readiness was rejected.
The portable fix copies only the existing lexical component rule, without any
filesystem guard/I/O. Safe Unicode, internal spaces and non-short-name tildes
remain accepted. Local horizon datetime conversion/arithmetic alone normalizes
OverflowError to ValueError; the caller's OverflowError callback retains identity.
Prior-night cutoff now accepts a coherent plan; late readiness still returns
NEED_MORE_DATA/rows=[], and causal/as_of contradictions still raise ValueError.

Fresh native verification:36 projection tests PASS in0.436s; combined36+31
count+29 Poisson+1 existing G0 rejection=97 tests PASS in1.216s. Compile checks
for both new Python files pass. The exact canonical digests of the complete,
UNKNOWN, missing and complete-empty control receipts match the original e719
outputs (respectively cc2ceecc...,23a3f5e4...,bb91f118...,46c17b97...). These
changes do not modify the existing G0/runtime, policy, registry, STATE/cycle,
Raw, authority flags or any actual data. No capacity/deadline is relaxed.
