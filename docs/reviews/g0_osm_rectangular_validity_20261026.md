# OSM rectangular validity implementation plan and verification

> Inline execution using writing-plans/executing-plans and TDD; independent
> whole-source review is coordinated by root after clean exact release.

Goal: encode the existing pinned auxiliary OSM static validity relation compactly
without changing canonical rows, source checks, budgets or authority.
Architecture: exact new sidecar branch within existing strict `_shard`, one
small typed checker, and explicit producer-only encoding selection. Reuse the
existing reader, context, owned join, projection recomputation and publisher.
Tech: existing Python standard library/runtime only.
Spec: `docs/specs/g0-osm-rectangular-validity-v1.md` (6101094 +9b481aa).

## Constraints and focus

Only existing producer/G0 module, new test, spec and this review are owned.
Old tests/default/read order stay unchanged. No pi.join/policy/STATE/cycle/Raw/
model/parent changes. Producer uniform mode; validator individually checked
old+rectangular shards may coexist. Hybrid sidecars and non-typed predictors
reject. All caps/read accounting and late-failure cleanup remain unchanged.

Review focus: partition IDs confused with absolute ranges; forged typed headers
without verified closure; booleans accepted through Python equality; old/new
digest comparison accidentally changing availability refs; removing per-row
validation or charging only two reads. New tests cover all five.

## Task 1: strict typed sidecar

- [x] Extend synthetic33-part typed fixture to the fixed3 features and write
  exact rectangular acceptance/equality/mixed-shard and malformed controls.
- [x] Run focused tests RED; add narrow helper/dispatch, retaining source and
  per-unit physical checks; run GREEN.
- [x] Verify range/type/ID/kind/validity/readiness/dupe/scope attacks, charged
  reads, alias/final-expiry and source-rescan mutations return no partial rows.

## Task 2: producer integration

- [x] Write explicit-mode/CLI/default/equality and actual readback tests RED.
- [x] Add keyword/CLI admission and compact producer branch without building
  the expanded physical dictionary; retain native publication/cleanup.
- [x] Run new targets and existing affected suites unchanged; compile/diff/scope
  checks. Record actual RED/GREEN counts and native limitations.

## Task 3: release

- [ ] Commit only owned files; return source SHA, tests and clean tree/index.
- [ ] Root/V exact review, new freeze and Ubuntu CI (coordinator-owned).
- [ ] Actual33-source72-window run after independent code review and root's
  measurement conditions; currently NOT_EXECUTED (no P0/fit claim).

Plan ruling: root explicitly authorized inline implementation in these five
paths; this owned review ledger replaces skill-default plan/scratch locations.
No additional plan approval or subagent dispatch is needed. A later coordinator
review supplies independent evidence; author tests are not that review.

## Design review and implementation scope

Coordinator approved the MEDIUM additive representation direction, then V
reviewed exact6101094 plus the coordinator's mixed-shard interpretation PASS.
The private design receipt is
`.worktrees/full-night-osm-independent-design-review-20261026.md`,8385 bytes,
SHA256 d0cb10c9d286e06d30b9182ba7d37fbc524450ed8da85143c163e1f8e1dde08a.
Commit9b481aae8806469a87618013263b8e59982b5acf records that clarification before
runtime work. This is design evidence, not implementation independent PASS.

The implementation changes only the existing producer and strict sidecar seam.
The small pure checker takes the actual verified `osm_sources`/`typed_features`
and resolved nodes/partitions; a generic same-named static or forecast source,
generic domain, or only two typed features is insufficient. It requires exact
three-feature binding and the typed full archived candidate-cell domain.
Existing full-shard `_cover` and every-unit CSV recomputation remain unchanged.
The new per-unit physical-validity checks retain only six parsed immutable
source/feature interval pairs, then check all unit endpoints through the same
callback; they do not expand the compact relation into per-row interval maps.

The default branch's payload and read order are retained. New mode avoids
constructing `rows x features` physical interval dictionaries, uses one uniform
producer choice, and allows independently checked old/new sidecars in one
complete manifest. Code/strict-definition hashes correctly change with actual
new builder bytes. No old freeze validates this new runtime automatically;
coordinator must create/check a new exact closure before CI/integration claims.

## Actual RED/GREEN and compatibility evidence

Bundled native Windows Python3.12.14, `-B -X utf8`:

- Initial new13 test methods: RED in4.817s,13 errors across cases/subtests.
  Positive compact/mixed-manifest requests failed at the unsupported sidecar;
  producer calls failed at the absent keyword/CLI. Existing negative controls
  already rejected. Minimal source implementation made13 methods GREEN in6.323s.
- Additional typed/generic controls, duplicate JSON/cross-shard refs, capacity,
  callback identity, no-expanded-tree and real native publication tests brought
  the new suite to19 methods;19 PASS in10.080s before the final byte-saving
  assertion. Fresh final19-method run including that assertion:19 PASS in9.555s.
- Existing `test_g0_forecast_contract` + `test_prospective_inputs`:125 tests,
 124 PASS/one existing POSIX symlink skip,13.784s. The skip is
  `ProspectiveInputsTests.test_posix_symlink_cannot_read_external_features`
  (Windows junction counterparts actually execute).
- Existing native StrictOsmProducerTests17 + pure builder11:28 PASS in9.594s.
  Seven legacy POSIX `materializer_*` tests were not selected on Windows; full
  genuine Linux execution is coordinator CI work, not replaced with fake fcntl.
- Three affected/new Python files compile in memory; diff/scope checks pass.
  No existing test file was edited and no new skip or budget relaxation exists.

Fixed synthetic owned universe/feature/snapshot/availability produce exact
same full rows and joined SHA for both encodings; source/manifest refs change.
A native2-cell x2-window synthetic producer comparison charged642767 bytes for
per-row and639893 bytes for compact (2874-byte saving), with equal joined SHA.
Original synthetic source-part bytes remain unchanged. This is not the actual
16990-cell domain and proves no real source authenticity/performance claim.

Reader observers see each compact sidecar three times in the same supplied
context: durable readback, initial strict read and final rescan. The consumer
alone sees the expected two reads. A1-byte read context charges the real second
rejection byte then blocks; whole-model row/byte and per-shard join caps still
reject. Late source mutation and callback expiry return no partial collection.
The no-expanded-tree observer sees only the shard interval dictionary, without
one interval dictionary per unit/feature.

New compact native publication tests capture the actual publisher before
wrapping it, verify the destination existed after the real move, then inject
cutoff, deadline and KeyboardInterrupt. Each hook runs once and owned public
output/staging is removed, originals retained. Actual Linux renameat2/directory
barriers still require exact Ubuntu CI; native Windows results do not attest it.

## Limits and release boundary

No actual33-source72-window run was executed. Completion within300s, full
2GiB read total, real peak RSS and1,223,280-row receipt remain NOT_ESTABLISHED.
Root will set measurement conditions after independent exact code review.
No source receipt is backdated and no software rehearsal is presented as P0.
The old full-night failure evidence is retained. No model streaming, cap
increase, new G0 kind or scientific/fit/official/production authority is added.
Weather/DEM, qualified input availability, whole-island current road access,
eligible training/outcome/effort and production authority remain separate gaps.

Independent implementation review, new source freeze, exact Linux CI and actual
full72 rehearsal are pending coordinator actions. This author record claims
software target-test evidence only, with zero actual-data fitting.
