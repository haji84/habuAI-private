# Independent software review: August 24 N3 source batch

Decision: **PASS_FIXED_SOURCE_ONLY** at `da9e2db1c141af1f0d7f69b35b53bdd4bce72d8c`. Both independently reproduced P2 contract findings are closed. The later author release `e725ea5296648e4baa653fb1345f381591cf1769` changes only the author record and specification relative to that source checkpoint. This decision does not register the new batch, validate the inherited cycle for changed source, establish scientific TRAIN, or replace the subsequent integration and exact/fresh Ubuntu gates.

The reviewer did not author the N3 module or modify its tracked files/index. All reviewer materialization, probes, and outputs were private files outside the worktree. Root owns integration and publication. The starting normal union is `91fa5c581ae5d0c52461e475ff8cd4461e69d829`, containing registered main `c577eb21274782035afa0f5657ac99954a8379b0`. This is a pinned review of those commits, not a claim about a moving worktree or later main union.

## Exact scope and identities

The nine source-lane paths are the two new derived CSVs, new admission descriptor, family module, new N3 tests, existing family tests, readable historical family capsule, spec, and author record. `data/raw`, policy, final reviews, core, auditor, Aug31 facade, Sept28 verifier, STATE, and cycle/pointer are unchanged from the pre-extension union. The new canonical `evidence/source_reviews/august-2026/2026-08-24-batch-v1.json` remains absent. The reviewer checked native Git object bytes, rather than treating Windows checkout newline conversion as original data.

| Pinned path | LF/native bytes | SHA-256 |
| --- | ---: | --- |
| `src/august_positive_source_review.py` | 18,925 | `ad4673e0b191155343daebb3ba050e6908c6d6a8e7821095cd2fff8f7479a997` |
| `tests/test_august_source_batch_20260824.py` | 30,733 | `c2351aa709ef78807062e184fafd38cc108dbe5b1606e1d13583ff268c48b8b0` |
| `tests/test_august_positive_source_review.py` | 29,511 | `062b8f13e023615042f132a0e736833440236f1117fd202ac36f2209b5b7196b` |
| `tests/fixtures/august_positive_source_review_48d_original.py.txt` | 12,084 | `7501ce6ad1e32de9d886c61503096e7bc1f90d6631197f0625bda45a49620e9a` |
| `evidence/source_reviews/august-2026/admissions/2026-08-24-batch-v1.json` | 4,206 | `b53fe9edce2c11e409ee93c46443f68ad812070f7300cad3a043892a836798a8` |
| `data/processed/capture_events/source_reviews/august-2026/2026-08-24-batch-v1.csv` | 518 | `ac180f173926453fba5c2b80c7f50c9fa8b64483cffdf480c0ff56a39f120add` |
| `data/processed/individuals/source_reviews/august-2026/2026-08-24-batch-v1.csv` | 461 | `f19435837140616b1496444f41e0b809c67b47c8dd6dc449a9fecd9b013ded0f` |
| Unchanged `src/_owner_capture_occurrence_core.py` | 14,740 | `297b2bb4301a0234b61e63abaf92076390095957be054bce008e7d49c5b1a914` |
| Unchanged `src/evidence_audit.py` | 48,013 | `4fc0648e35d623bb29c43eff73ec832731722efcdd71bc9a896eb27302211e56` |
| Unchanged `src/aug31_positive_source_review.py` | 5,895 | `26e72df7ce45ba21fd23ec84dd14e902ee4bd5e29205daf77a07f20fd12f3397` |
| Unchanged `src/sept28_positive_source_review.py` | 18,350 | `109f39a68d7f5db10adf991d7cc6e512d4fe58edfcc050cd2219d7de737928e8` |
| Unchanged `src/gpx_audit.py` | 12,860 | `878ff42ec767e671bf9581ce2d1635c5282ffca469dc6f247654817b7c55779d` |

The family Git blob is `f141f3f95cb13adc664e62b1d26f9fb71ac74998`; the new test blob is `d0c5c7026dff038083e6d79f037ef34c9a1a52e8`. The fixed-blob receipt is `.worktrees/aug24-n3-independent-fixed-blob-checks-da9e2db-20261026.json` (4,007 B, `8dedb960cb9a61e702068af6165316d3e72d9ae7ac2b520857eb2e7bec1422af`). It also binds the unchanged policy/STATE/pointer and independently rehashed 172-file review subset.

The final author release contains spec 24,670 B / `4ce252fbc1951b732c94a520b4ab6483837ba0475a920041bf749f88c7a228ad` and author record 19,215 B / `6c2cab1f153efee38a60ed1a3e4115db75b188e2d4485f377d253637c4af6e3e`. The original approved design `1cbcbbb183551e17eec135521553d09e288fe2ba` and its original 19,831 B / `977078fbee9119a714aebc894550982797894874eec183a3635e7c086376b07f` spec remain historical. The later clarifications do not rewrite that design record.

## Source and semantic review

The descriptor closes N=3 plus existing N=1 through the same core. The reviewer checked all records and strict proof/QC types, declared operational night, count, selectors, IDs, original byte spans, coordinates, and complete copied projections. There is no first-record-only success path. All ADMITTED source IDs and original byte intervals, including protected Aug31 intervals, are checked globally before family policy roles are published. Policy source entries remain exact four-field declarations. Closed review-reference intent and conservative path recognition reject malformed family declarations without opening a normalized spelling. Unrelated legacy roles retain their original dispatch.

The three original spans are `[76701,76818)`, `[80948,81074)`, and `[82547,82653)`, with source slice SHA-256 respectively `2c99420caa10cd6d82199747daebad27d6ffcc91a7ee2823f482ec60ef6535bc`, `be156b075377f98a1f562083def11ad6bc07a933367ebdf02dd03d7da8bf525b`, and `47c5c65b2f11b17371f8717ce79e0a6bbf4bfba7e3e8258fcacf2b47305a903b`. Their source lines are 6791–6800, 7201–7210, and 7351–7360. The latter timestamp is August 25 00:51 JST and belongs to operational night August 24 under the existing 07:00 boundary.

IDs are `AUG2026SRC-L6791`, `AUG2026SRC-L7201`, `AUG2026SRC-L7351`, with separate `-OCC01` derived occurrence selectors. Each singular source statement is counted as one recorded occurrence; it is not a literal new `1匹` assertion or proof of permanent biological identity. Missing original fields remain empty. Coordinates equal the original decimal values; no interpolation or fabricated search/effort is used.

The real GPX is 5,645,516 B / `5995bc3e8addb65f873d1416f57f18153b9a5d769bf48ff4ffb84f3c581bc671`, with 21,246 charged parsed points, zero exclusions, one segment break, maximum gap 32.58 s. Selected trackpoint indices are 2570/12595/15812; XML sequences 22965/112520/141259; rounded distances 2.074/0.104/2.117 m; time deltas 12.999/7.999/44.999 s. GPX is parsed once per API context and physically reread for final identity checks. The transcript, byte proof, owner47 record, source CSVs, descriptor and all final rereads remain source-bound; owner47/243 historical claims were not upgraded.

The shared Audit reader, cumulative physical byte/read/point limits and caller deadline remain in force. Ordinary caller exceptions, including cancellation and unusual same-object exceptions, propagate unchanged; no timeout is converted into a successful partial source qualification. The family bridge owns outbound dictionaries at the shared-core seam. Refuse-on-invalid atomicity concerns family roles, not a new transaction or hostile-filesystem confinement guarantee. Verified-reader postconditions and existing TOCTOU limits remain explicit.

## Findings, fixes, and retained history

1. **P2 borrowed-reference mutation at `23771eb1b58b8ea115f42259343fb584e1ddbdae`.** A genuine `Audit.ref` callback returned the correct bytes, then changed the borrowed dictionary's SHA. The core retained/lent that same dictionary and later raised `AUGUST_FIXED_REFERENCE`. This violated the explicit copied-outbound/saved-lineage API contract. The initial two-method independent run had one positive PASS and one ownership ERROR, 3.471 s. Receipt: `.worktrees/aug24-n3-independent-23771-20261026-r2/initial-probe-result.json` (5,164 B, `edd46fee0d6baf04c702ee4a023768b1226ac6ffe3a1e96df89af1154f288d7a`). E independently reproduced six public subcases. The fixed family-only bridge uses `read_ref=lambda value: read_ref(dict(value))`, without modifying core, adding I/O, swallowing exceptions, or changing original proof/read outputs.

2. **P2 family-set atomicity for forbidden aliases at the same original source.** Directory components ending in ASCII dot/space were not recognized as family intent, so an invalid family declaration could fail the check while canonical N1/N3 outcome roles remained. Four role-leak cases were measured in `.worktrees/aug24-n3-independent-23771-20261026-r2/alias-atomicity-red.json` (5,563 B, `7db19052c012f7de0db4985861f0167ca8a5b1b98a18c31b8d626eb6c8c4cc8a`); those initial four did **not** instrument payload opens. Five additional DOS-style `~digits`, colon/ADS, drive-like, C0 and DEL intent controls independently observed strict reader rejection with zero payload opens, but leaked a canonical role (`malformed-family-intent-controls.json`, 3,316 B / `cadf40d9c5539b047061e60ac6f67ed74e58dd85c9ced3424453c37d04bc5e5b`). No actual DOS short-name mapping or containment bypass is claimed. The fixed classifier is recognition-only and unions closed admitted review-reference intent; exact raw path/schema validation then rejects. It never opens an alias after normalization.

The initial native harness also failed before product calls because the temporary Git alternates file had text-mode CRLF. That failed directory is retained; R2 uses native LF bytes/object IDs. The final small Sept28 fixture attempt similarly stopped before verifier calls at Windows Git-show path-length stat; its unchanged script is retained and an R2 object-ID `cat-file` wrapper supplies exact native bytes. Neither reviewer materialization failure is counted as a product PASS or hidden by an OS facade.

The old nine-method contract run at `23771` remains a positive-control result only, not an overall source approval in the presence of the two findings. The original full source audits and all original baseline artifacts remain immutable historical observations.

## Independent executed controls

The fixed native review subset has **172 files / 17,951,352 B**, not the complete 913-file audit input. Its raw Git manifest is 33,816 B / `96d73e9f7914c1ed37618930cc91275a14b229ed64c9c91490d0964024292972`; all bytes were rehashed after the contract, matrix, and N3-whole runs.

Commands used the actual bundled Windows Python with `-B -X utf8`, no fake `fcntl`, backend, estimator, clock, or platform facade:

```text
python -B -X utf8 .worktrees/aug24-n3-independent-contracts-20261026.py da9e2db1c141af1f0d7f69b35b53bdd4bce72d8c
python -B -X utf8 .worktrees/aug24-n3-independent-final-matrix-20261026.py
python -B -X utf8 .worktrees/aug24-n3-independent-n3-whole-oracle-20261026.py
python -B -X utf8 .worktrees/aug24-n3-independent-sept28-verifier-whole-r2-20261026.py
```

The contract suite passed **9/9, zero skips**, recorded elapsed 25.375 s. It includes 45 independent record variants, 27 strict QC variants, actual original spans/coordinates/night, global collision/alias rejection, caller exception identity at all public seams, whole original N1, and both existing Aug31 capsule controls. Result: `.worktrees/aug24-n3-independent-contracts-da9e2db1c141-20261026/contract-result.json` (605 B, `648b1604b74da1e39038292cca431806518e3c9363e3c9ee57365d8b04468e91`).

The final matrix passed **6/6, zero skips**, recorded elapsed 24.343 s: 80 directory aliases, 384 atomic bad sets, 7 malformed nested-type cases, 6 borrowed-reference ownership cases across N1/N3 × reproduce/verify/preflight, and both normal canonical orders. **85 controlled strict-reader cases** actually instrumented `Path.open` and observed zero opens. Atomic cases rejected before source proof/point consumption; no general zero-I/O/confinement claim extends beyond those controls. Result: `.worktrees/aug24-n3-independent-final-matrix-da9e2db1c141-20261026.json` (500 B, `f45d8e84dc09be4ee8b0a165ebdb5eeaf051a49c8b8141d7bacaf1ca3633c869`).

E's author run is separately attributed: final 48/48 PASS, zero skips, 120.768 s. Its earlier 16/16, 43/43, and 72 methods with one genuine POSIX skip remain author history, not extra fresh reviewer executions. Author log: 9,342 B / `c1373745b48999140dcee346cfc6557e6c3c72146b73848b24936f1f9ae29019`.

## Whole old/current comparisons

**N1:** The genuine pre-extension baseline was made at `91fa5c58` at actual `2026-10-25T21:40:06.240193+00:00`, before N3 product edits. It used the real saved N1 review and independent contexts. Both `reproduce_sources` and `verify_review` produced identical 13,101 B whole artifacts / `6445cfe75e334649aa95a485b3c74d35d9d74aa8f1efcf59ed5266db1890a874`, with 14 reads / 7,400,394 B / 13,565 points each. The fixed code and independently compiled genuine 12,084 B historical 48d capsule both match the entire artifact: typed proof/result hash, input hashes, actual read/open order and interleaving. No hash/body fields are removed or goldens regenerated. Baseline receipt: 1,575 B / `e8e351e8769dff700b6884ed739919de1957c44d69e7c3959e70c9df9a59f994`. This byte equivalence does not assert equal wall-clock time or tick count; additional validation ticks remain subject to the same caller deadline.

**N3 valid inputs across the repairs:** Genuine frozen `23771` and fixed `da9e` are distinct loaded modules, using the same owned fixture, runtime and clock. Both APIs' complete typed proof and physical ledgers match exactly: 14,428 B / `844bbc7b3f066d77628d93d67e422eb552768621ef70c3d5aa19551927c842c9` per API, 14 reads / 11,542,312 B / 21,246 points; full proof SHA `2748ccd1c6f2bc4b628ab4cb26b72f13e58fcf18314b5a06fa6bba4d9a56ef6f`. Receipt `.worktrees/aug24-n3-whole-old-current-da9e2db-20261026.json` is 892 B / `81327b584cb220f977ca1c824564fc0e5460d8ece76ae4cc69fb42586dbd76e4`.

**Aug31:** The executed capsule controls are `LegacyCapsuleTests.test_immutable_old_profile_whole_proof_and_read_open_order` and `test_hermetic_old_auditor_whole_results_read_and_open_ledgers`. They use the genuine old Aug31 profile (16,887 B / `bf5d204ab2f2d2ea39df2e2824f2e10f04eedc7bdd3a0cfc91237d2929841e41`) and old auditor (45,897 B / `4329ed74e1f58b63b3010beda76859beabe9b5f3be2f517efc8bc904a209cd4b`), respectively. They compare complete fixed-input proof/public results and read/open ledgers. These are Aug31 controls, not a fresh September full-audit reproduction.

**Sept28 bounded API control:** `sept28_positive_source_review.verify_review` was executed twice, old native `91fa` module versus fixed `da9e` module (the same pinned 18,350 B verifier bytes), with the same 31 native input files / 7,734,009 B and `now=2026-10-25T12:00:00+00:00`. All inputs were verified unchanged before/between/after. Complete typed proof/result SHA, consumed hashes, read/open order and interleaving match exactly: 5 events / 6 SOURCE occurrences, 60 reads / 15,450,788 B / 22,990 points each. Whole artifact `.worktrees/aug24-n3-sept28-verify-review-whole-da9e2db-20261026.json` is **49,246 B / `02773380631d4c0be1494a9715500687936e24b8faba5694fba9110db53dd266`**. Receipt is 6,286 B / `6758f121fc8c8f26d06ef83953c79dc55ea9dc0ea6038b3d5cab396358abf6c3`; elapsed 6.323 s for both bounded runs/materialization.

The preserved **566,151 B / `e1e16caac9986c8d0441dbf1ab4f167aa1907f1d3534dfe61f12efe1fa304904` September full public artifact was not rerun here**. Its historical 362-file catalog omitted 25 Japanese GPX manifest/part entries; the separately established complete 387-input catalog/history remains preserved. The bounded 31-file verifier comparison must not be relabeled as that 387-input public audit.

## Fixed-source complete-input audit pair: independently checked receipts

E ran each fixed-source public audit exactly once; the reviewer checked their physical artifacts, native manifests, complete result bodies/digests and ledgers without repeating either audit. Both use frozen `da9e` tree `e7bc2b7226bb98f1265802d404ed20f74a57c9ca`, **913 native files / 182,783,412 B**, manifest `ed01dd22ef289134bb2fa2fc6b3be9dfaca2eb9e9f10360bd3d2deab64cae9a8`. All native originals remain exact. The separate provisional snapshot has 914 files because of its temporary final review; only that review and private policy differ. Neither is registered in the repository.

| Context (operational night August 24) | Actual verified UTC | Product result | Reads / actual bytes / points | Source events / occurrences / positive / UNKNOWN | Requirements |
| --- | --- | --- | --- | --- | ---: |
| Existing repository policy | 2026-10-25T22:52:47.669756+00:00 | PARTIAL, 0 failed checks, 17.718 s | 589 / 369,050,961 / 338,929 | 8 / 9 / 8 / 762 | 34 |
| Private provisional N3 only | 2026-10-25T22:54:18.120313+00:00 | PARTIAL, 0 failed checks, 21.297 s | 606 / 380,609,817 / 360,175 | 11 / 12 / 11 / 759 | 31 |

Both retain zero Negative and zero TRAIN credit, NOT_ESTABLISHED denominator, no complete SEARCH/outcome scopes, fit=false and parent=false. Their 52 checks pass but the product status remains PARTIAL. UNKNOWN counts are for requested night August 24; 619 August29 and 688 August31 are different requested-night diagnostics, not a common-cohort reduction. The private new three labels are source-only occurrence qualification under the provisional policy, not scientific training or permanent animal identities.

The private review was created at actual `2026-10-25T22:54:16.126498+00:00`, 5,108 B / `455fc29a12b7b561ce0bea15e75dc56ad6ac7b1c938f51cd50a44ec78ba4f822`; private policy is 1,476 B / `19dfd679af44a8f18847cb6319743ea2014a8c1d11a02e8f61d77c12b3d8091c`. Preparation used a **separate** 14-read / 11,542,312 B / 21,246-point context (1.422 s); those charges are not silently merged with, reset inside, or substituted for the public audit ledger.

All following files are under private `.worktrees/aug24-n3-native-verification-da9e2db-20261026/`:

| Receipt/artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `default-summary.json` | 2,097 | `a231b2bda17eb7a3d3a342bac2356791e62f394e0a2355794292ceae58d29933` |
| `default-full-receipt.json` | 541,207 | `88db9a95ea7000d545fbdbae21d953e4c5cf0f7b90dc837b4df5ca968d87e209` |
| `default-whole-audit.json` | 795,177 | `a6d6eeb502b5665c45b368ce5608daed2586340678c73b5c40785698ae911760` |
| `provisional-summary.json` | 5,731 | `e7c7e6545194e69d23c0db47dd099372f359d5f4b5302396e270c6e1a1e25413` |
| `provisional-full-receipt.json` | 545,468 | `eb5456ceb442c5b296cedc9eac13fc4816354791e8f7088063d5e20486824f3c` |
| `provisional-whole-audit.json` | 809,841 | `8d49a2414961e3cc48a048fa5a0f730e834218f77792747cb23df330593ae641` |
| `fixed-vs-23771-data-and-read-ledger-comparison.json` | 6,161 | `eb214a8747691397b4d2679c4f9e97f882c1c7a13696b7989bb421352195e58a` |

The last comparison performs no new source calls. It explicitly enumerates actual-clock `available_at` differences and the two changed private temporary-file hashes/read rows. It preserves order, other qualified fields, and actual read/byte/point/open structure. It does not claim whole-output equality across different clocks/private review bytes. The direct same-context whole N1/N3/legacy controls above are the exact-byte compatibility evidence. E's final handoff is 9,192 B / `3fc4c6f655f8d7451289330b52317b20b603683be182613f640bea05edb16977`.

## Limits and release

This approves the bounded fixed software contracts and closes the two findings. Native Windows tests exercise actual source and alias rejection; genuine POSIX and complete integration remain the subsequent Ubuntu gates. This is not a performance benchmark, historical prereveal/device/issuer authentication, hostile-filesystem confinement proof, full biological identity determination, complete outcome/effort certification, model fit, source-to-TRAIN promotion, P0 issuance, permission upgrade, unattended runtime, or Master completion.

Repository registration remains **8 source events / 9 SOURCE occurrences / 8 positive units** at this review scope; the N3 canonical review is absent. The private 11/12/11 result is not registration. All eight authority flags remain false; permanent identity remains unverified; scientific validation is NOT_VALIDATED. Root must perform its latest-main normal union, new candidate code closure/freeze, and exact/fresh CI before any later registration review. No old `a6`/`f4222` full audit or 425-score replay was introduced by this review. No reviewer tracked/index write, commit, push, policy update, source registration, or raw-file mutation occurred.
