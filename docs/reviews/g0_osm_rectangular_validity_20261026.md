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


## Coordinator measured rectangular-rehearsal checkpoint

Actual UTC 2026-10-25T19:35:10.329623+00:00. The prior normal merge88d9e5e incorporated actual main 483800bfd1ba9e5603d22794c659542ca325b0a2; its separately recorded PR123 exact1540/sk32/576.459s and fresh1540/sk32/321.893s successes are now reconciled. No order between that merge and CI completion is inferred here. This inherited Ubuntu evidence covers the standalone declared planned-effort slice, not the new OSM source. Actual owner plans/fit remain0 and G0 planned/lagged kinds remain CAPABILITY_BLOCKED.

The immutable historical3e rehearsal summary (bae0c64d06bc5b7f6710fe0a2dfbe88b620f1ba12456b2ed0b030fed4ddcc64f) records16990 cells x72 windows =1223280 rows/72 shards in81.219s, 1412221558 actual product bytes under unchanged2GiB/300s, complete joined SHA b98758716096a2c2c103df049d9e55d2b30f12431b0b63229ed066601714a6c3. Its native880 files/182197645B are that artifact source snapshot, not a current-tree count. All72 sidecars had three actual reads/native opens in the same product context. The nested phase1405721469B plus late35-reference rescan6500089B equals final1412221558B. Separately, reader1339378639B + discovery6500089B + two decode/expand charges66342830B equals that final total. Discovery and late rescan are distinct physical phases; their equal byte counts do not establish phase equivalence. Ordered33 Base64 parts,34 directory members including README and35 canonical rescan refs are distinct observations. Both original raw false checks remain unchanged; the fixed final summary and independent39/39 artifact checks explain their observer-scope correction.

Observed whole Python-worker Windows lifetime peak working set183341056B is separate from sampled product peak112234496B; sampling may miss transient allocations, and no128MiB RSS guarantee is claimed. Independent hashing of475 published refs/440581245B was a separate read-only artifact audit, not another charge inside the product budget. This measured result supersedes only the earlier author record's NOT_EXECUTED rehearsal status. The earlier default per_row full72 capacity failure remains exact and is not erased or rerun.

Current reviewed source bytes remain builder37650B/f1e9dd63daea304fa07099b1af28c43a65c7779047327627443fb93456ec823f and reader55032B/4b31cca1120925f25f8687bab98366cbde93e38685cf04eb5dcd5622b6cc0e21. Code-review receipt a4eadce6622910ee4c52c75b53f25fb14eb05ffb4a2c1a3603c021791dec6f7e, actual-artifact receipt d23e9618517e219f3f36ee3d6b935e7ef624f6a69b41e82e9ba45fe5567b1664, and new immutable98-reference cycle protocols/development/cycles/20261026-osm-rectangular-validity-01.json, code 46cc6e39aebb4612b3321538bbb287de44b63a898487c9edf684fe1995870884, cycle 5f23df73ff87a929314a19bdbe1894853304a7b4c328c2df8883f979f5ff429d bind this checkpoint. Native-snapshot current-cycle CLI was independently rerun by this helper. New exact OSM Ubuntu, safe merge and fresh main remain PENDING. No model collection, global ranking, Stage1/parent or fit ran;120k/16MiB model caps and all authority restrictions remain. Auxiliary original source authenticity/current-road access remain NOT_ATTESTED. Registered source7/8 adds no Negative/TRAIN credit; science remains NOT_VALIDATED/Master NOT_COMPLETE. Root metadata execution adds no runtime, Raw, policy, source role, dependency, new cap or unattended executor.
