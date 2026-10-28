# Private raw → PDCA → model validation → ledger: single-entry contract

Status: **PARTIAL IMPLEMENTATION** (2026-10-27). Owner requirement: post a Habu log / GPX once, with no ZIP download or manual GitHub upload. This document extends, not supersedes, `docs/specs/chat-single-entry-pdca-contract.md` and Master Goal #1642.

## Verified facts / immediate privacy restriction

- GitHub API reports `haji84/habuAI-private` has **public** visibility, notwithstanding its name and some historical README descriptions. Never publish exact GPS, source logs, unmasked addresses, or source-derived fine-grained route data to this repository, any Issue, Actions artifact visible to the public, or public PR.
- Private user Library archive of the 2026-10-26 original GPX was confirmed by a Library listing on 2026-10-27. Archive reference is held in the *private* owner PDCA ledger; do not copy its private identifier into this repository. Original file SHA-256 is separately recorded in the ledger. An accessible chat attachment is **not** automatically an input to GitHub Actions.
- Existing `scripts/run_pdca.py` and `src/master_orchestrator.py` remain the only scientific PDCA implementation. Intake validation is not scientific PDCA or model validation.

## Implemented in this bounded PR

`scripts/private_pdca_intake.py` accepts a UTF-8 field log and/or original GPX, verifies source integrity, parses a literal diagnostic event tally and the 07:00 JST night boundary, creates content-addressed immutable source copies and a private receipt **outside the repository checkout**, rejects symlinks, malformed GPX, repository-overlapping destination, altered duplicate receipts and input conflicts. stdout is deliberately limited to opaque receipt ID and technical statuses. No raw coordinate appears in the command response.

`tests/test_private_pdca_intake.py` checks night rollover, distinct capture/sighting/roadkill, exclusion of Himehabu, idempotent storage, SHA round-trip, public checkout guard, symlink rejection, invalid XML and invalid dates.

Example for a trusted LOCAL, PRIVATE working environment:

```sh
python scripts/private_pdca_intake.py \
  --repo-root /path/to/habuAI-private \
  --private-root /path/to/owner-private-storage \
  --log /path/to/2026-10-26-log.txt \
  --gpx /path/to/2026-10-26-original.gpx
```

**This is intake only, not a completed one-command PDCA.** It does not automatically fetch Chat attachments/Google Drive/Library, run `run_pdca.py`, validate models, or update a connected Google Doc. Its receipt explicitly marks those steps `NOT_RUN`.

## Required final single-chat-turn coordinator

Inputs: current owner chat message and attachments; private authenticated source store; frozen P0/P1+ references; current GitHub `main` and PR versions; private PDCA ledger. The coordinator must:

1. Capture the user-authored log in a **private, access-verified, byte-exact source** record. Attachments keep original bytes and SHA-256; if original message text cannot be durably captured verbatim, mark raw-log archiving BLOCKED. Files must be retrievable in a new conversation independently of transient chat context.
2. Perform idempotent 07:00-JST night attribution and per-event provenance before merging any totals. Duplicate same-night upload means zero incremental capture unless separate original individual IDs prove new events. Do not silently amend the prior 243/249 historical baselines.
3. Use *private* worktree/runtime/data store to present verified inputs to the existing `scripts/run_pdca.py` and `src/master_orchestrator.py`. Existing public repo Actions may run code-only smoke tests and redacted command metadata, never raw nonpublic source or sensitive spatial outputs. GitHub event Issues do not become raw-data sources.
4. Enforce provenance, source type, search-role and complete capture-outcome certification before Positive/Negative training labels. GPS passage/other fauna sightings alone do not imply actual Habu search. No backdated ORIGINAL P0.
5. Independently report `P0`, `P1+`, `REPLAY`, model / walk-forward validation and ACT status. Stage1 1km Top10 Recall >=90%; formal final 100m ±10min only with valid frozen originals, scored on held-out data. Missing inputs yield BLOCKED/NEED_MORE_DATA, not fabricated PASS.
6. Save results to *private* owner ledger with run ID, source SHA, model/protocol hashes, stage statuses, missing evidence, data store identifiers, and previous revision. Read back ledger, archive and source metadata. Public development Issue/PR contains only redacted technical progress.
7. If the private store or backend cannot be reached: fail closed and tell the owner exactly which step did/did not complete. Never say 'saved' based on a downloaded ZIP or generated local file alone.

Acceptance E2E tests: owner pastes a whole night log once; original text and GPX survive fresh-chat retrieval; deliberately repeated/modified logs do not double count; zero-capture night preserved; source details not observable in public GitHub outputs; canonical PDCA is invoked from private input; missing P0 yields explicit BLOCKED; candidate evaluation only uses available pre-cutoff features; owner ledger update survives readback. Verify exact final-head CI and independent security review before merge.

## Unfinished integration blockers

- Native owner Chat message → persistent private raw text sink and attached GPX → private scientific runner bridge not yet implemented. The Library/Drive connector is available to an **active** ChatGPT invocation; a GitHub Actions runner cannot independently call it with the user's permissions.
- A verified private execution service (and least-privilege credentials for unattended access, if pursued) is not provisioned. Do not add tokens to a public repository or enable a cloud service / fees without owner authorization.
- Public GitHub report content already under development may contain sensitive legacy evidence. This PR neither audits nor removes historical blobs; privacy audit/remediation needs an explicit, scoped Human Gate.
- Independent head review and CI are pending. Do not merge this PR or promote Champion based on the unit tests alone.

## Next bounded implementation slices

A. Private raw log writer from connected Chat, provenance receipt, fresh-chat roundtrip. No user download.

B. Private PDCA workspace adapter that runs existing `run_pdca.py` against **verified** private sources, status-only safe output and checkpoint continuation. Zero need for public GitHub to ingest raw.

C. Private ledger adapter with revision guards, readback, duplicate handling and blocked-state persistence. E2E using actual night log, plus deliberate failures.

D. Independent privacy/threat review and final-head CI; then integrate with existing single-entry chat contract. No new generic PDCA engine and no repeated PR proliferation.


## 2026-10-28 bounded runner implementation

- Added `scripts/private_pdca_runner.py` and `tests/test_private_pdca_runner.py` in the **same** Draft PR #146. This is a private-workspace adapter that verifies previously archived source SHA-256, refuses overlap with the public code repository and any store-to-workspace symlink escape, copies source bytes to a private incoming folder, and launches **the existing** `scripts/run_pdca.py --root <private-workspace> --night <night>`.
- The private incoming directory is **NOT canonical data admission**. The adapter therefore marks source science eligibility false, P0/P1 NOT_CERTIFIED, model validation NOT_CERTIFIED and Champion activation forbidden, even when an engine process returns success. No model weights or ORIGINAL predictions are modified.
- In the local test harness, six focused runner tests passed: repeat idempotence, original-byte tamper, public workspace rejection, invalid date command, raw symlink rejection, and misleading backend PASS rejection. Final GitHub exact-head Actions result and independent reviewer are separate gates, not inferred from local success.
- The owner's 2026-10-26 raw GPX was re-fetched from their private personal Library and independently byte-compared to the current conversation attachment. SHA-256 matches `dcba4c855d7acd103ce2beaa038674a18185cba99b8e4fbeb0478a483d4264ef`; file size 5,572,720 bytes. These values are identifiers, not released coordinates.
- The private Library now also holds three **derived**, explicitly non-raw 2026-10-06..26 artifacts (habu event CSV, night summary CSV, PDCA diagnostic Markdown). Fresh listing confirmed the exact basenames and byte sizes. This is a durable save/readback, **not** automatic raw chat transcript intake or machine learning.
- Read-only Cloudflare account R2 bucket listing returned HTTP 403 with provider message **Please enable R2 through the Cloudflare Dashboard**. Do not enable R2, change billing, create buckets or turn on a new paid service without an owner Human Gate. Existing personal Library is the confirmed private source-store option in this interactive session.

### Hard remaining E2E dependencies
1. The model currently has no authorized unattended connector from new chat message body directly into a persistent byte-exact raw text file. ChatGPT's attached file API can store uploaded GPX into the personal Library when an interactive turn runs, but this is **not** a GitHub Actions source or continuous background trigger.
2. Need private source admission to `data/raw/gpx`, `data/raw/habu_logs`, capture CSV and independent search/outcome attestations in a **private** scientific workspace before canonical PDCA can use this run. An inbox copy is not enough. Reuse the existing PR #136 intake parser; do not create a competing authoritative importer.
3. Original P0/P1 Freeze evidence is missing for the submitted October nights; formal location-time hit rate, Stage1 model validation, and promotion remain BLOCKED/NOT_VALIDATED.
4. Need an authenticated private ledger writer + revision guard + readback to update the owner's existing Google Doc automatically from the scientific result. This conversation's direct connected update is not yet the unattended pipeline.
5. Need actual night E2E, fresh CI at exact final HEAD, independent reviewer, safe integration into main and subsequent main verification. Keep PR in Draft while any gate fails.

## 2026-10-28 local repair of F1–F3 only

The repair is based on fixed PR146 head `b97f29ef98f0ba735055c2c2749152d026bba578` in a separate local worktree. It does not establish a new private service, ACL, visibility, authenticated source role or execution authority. The author does not independently approve their own repair. Root must obtain independent review before deciding how to reuse the existing PR and integrate it.

- **F1:** the intake test's location/address-like literals have been replaced with explicitly synthetic, non-identifying inputs. Synthetic test XML uses a marked placeholder point; it is not an owner route. No claim is made that the prior literals were authentic private data or an actual disclosure. No public history, real log, GPX or Library object was changed or fetched.
- **F2:** intake archive and receipt writes, runner incoming copies and runner result receipts now check every existing component beneath the configured private root, including the leaf, with `lstat` and Windows reparse attributes. Symlink, junction and other reparse components are rejected. Containment is checked before/after parent creation and before publication or existing-file reuse. Existing raw/receipt/result files are never replaced. A known-unsafe result path is rejected before inbox copying or starting the child.
- **F3:** the runner requires the existing v1 receipt schema and one or two distinct typed source rows. It rejects extra fields, unsupported kinds, invalid digests/paths, bool/non-int/zero/oversize sizes, and malformed rows. It recomputes `receipt_id` using the **unchanged original records-only definition**, `sha256(json.dumps(records, ensure_ascii=False, sort_keys=True).encode())`, before reading source content. Regular one- and two-source intake receipts round-trip without rewriting old receipt or source bytes. A hash is declared byte consistency, not owner or issuer authentication.

These are cooperative path checks in a trusted local environment, **not atomic filesystem confinement or a cross-file transaction**. They do not prevent every adversarial concurrent rename/reparse race. Windows private ACL/owner access and the approved executable/code root still require separate deployment verification; filename existence is not executable provenance. No permissions are elevated by these tests or by this repair.

TDD evidence is retained privately in `.worktrees/pr146-f1-f3-repair-20261028/`:

- `pre-edit-native-pins.json` and five byte-exact code/test/document snapshots precede edits.
- `red.raw.log`: 25 tests, 9 failures, 2 errors, 7 skips, 1.034s. One error was the synthetic UTF-8 fixture being read with the Windows default cp932; the test now specifies UTF-8. This initial failure record is retained.
- `red2.raw.log`: 27 tests, 9 failures, 2 errors, 7 skips, 1.197s. The remaining errors expose missing typed row/path rejection. The three actual Windows junction controls for raw, receipts and run-result ancestors fail against the old code; receipt-ID/schema/bool/zero/extra-field attacks also fail. SHA-256: `5a6ac95b05ecfda7923e44d888a784a4a42cc3a7ef906653bd8b7c3ebe592a2c`.
- `green.raw.log`: 27 tests, **20 actual passes, 7 skips, no failures/errors**, 0.945s. SHA-256: `92f4d5c11d9ee1f1c4c037505c15387ab1ec9c89b442720c04e9223fcb8a1f68`. All three actual Windows junction controls execute and pass. Seven actual symlink controls cannot create links without the unavailable Windows privilege (WinError1314); they are honestly skipped, not mocked successes. POSIX symlink execution remains an independent/CI requirement. The private final handoff separately pins the final targeted rerun, compile and diff checks.

All executed intake/runner tests use dedicated temporary directories and synthetic bytes. Runner compatibility tests invoke a temporary fake `run_pdca.py` emitter in that temporary tree, **not the real canonical engine**. Original five intake and six runner test purposes are retained; runner receipt fixtures now come from real intake over synthetic data instead of an arbitrary ID. No real source, GPX, Library, product engine, provider, network, fit or scientific E2E is exercised. The wider suite is not executed under this explicitly limited test authorization.

**Still unmet (F4–F7):** complete I/O/output/deadline bounds; binding diagnostic parsing to the same immutable archived bytes; a pre-child immutable attempt/reuse claim; and complete strict child-result/primary-failure preservation. The new parent guard does not supply those controls. Neither test status nor wrapper NOT_CERTIFIED fields prove that a separately configured canonical child performs no fitting. No source admission, training/Negative/SEARCH qualification, P0/Champion/production or Master completion follows.

No STATE, cycle/cursor, policy, requirements, workflow, master connection or current C six-path code is changed. The supplied old PR146 manifest is deliberately not rewritten by this repair. If Root later composes these two scripts with actual PR145 main and accepted C changes, it must measure the complete native union, refresh the development cycle/cursor, obtain independent review and run that union's own exact/fresh CI. The conditional 108 native / 109 code+policy / 111 selected capsule counts are distinct from the accepted PR145 native106/CLI107; old CI cannot certify the new union. Registered SOURCE17/18/17 remains provenance, formal TRAIN/Negative/SEARCH/real fit remain0, science NOT_VALIDATED and Master NOT_COMPLETE.

### F2 follow-up: temporary cleanup ownership

Root's independent synthetic probe against local commit `a0a0d8b4ac0c93e67eb14ad5c8308bfcc8d07645` found that a linked archive stayed exact but a different regular file substituted at the temp pathname was deleted by `finally`. No private source or real engine was involved. That baseline and Root's original RED JSON/probe remain immutable; the earlier path guard alone was insufficient to establish cleanup ownership.

All four temp cleanup points (intake archive, intake receipt, runner inbox copy, runner result receipt) now capture `(st_dev, st_ino)` from the **opened temp handle** with `fstat`. Cleanup applies the no-reparse guard and uses `lstat`; only the same regular-file identity is unlinked. A known replacement is retained. With no primary failure, ownership uncertainty raises an explicit `TEMP_CLEANUP_RESIDUAL`; with a primary failure, that exact exception object remains primary and receives the residual note. Already published archive/receipt links are not rolled back, and this does not authorize an automatic retry.

New private evidence: `.worktrees/pr146-f2-cleanup-ownership-repair-20261028/`. Before implementation, eight replacement/primary controls failed against a0a0: **37 tests, 8 failures, 0 errors, 7 skips, 1.599s**. After the narrow cleanup fix: **37 tests, 30 actual passes, 0 failures/errors, 7 skips, 1.346s**. The eight controls perform real temporary hardlink/replacement operations with fault injection at `os.link`, verify the published source bytes, preserve the unowned marker, and check primary exception identity/residual notes. Two normal cleanup controls cover the unchanged owned-temp success paths. The prior three actual Windows junction controls still pass; the same seven actual symlink controls remain skipped on WinError1314 without elevation.

This remains cooperative identity checking, **not hostile-filesystem atomic confinement**: a later adversarial race between `lstat` and `unlink` is not ruled out. F4–F7 remain unmet outside this F2 cleanup boundary; no new run/controller, whole deadline, source trust or scientific permission was added. Only synthetic dedicated-TempDirectory tests and temporary fake emitters were executed; independent review and composed own CI remain required.


## 2026-10-28 Slice A: bounded intake and stable parse/archive bytes

This is an author report for the separate `codex/private-pdca-bounded-snapshot-20261028` lane based on reviewed `7402e429cd911ed9d6a003fb962bfecf46ba7a70`. Root dispatched A after independent scoped design review (`.worktrees/pr146-slice-a-independent-design-20261028/`). It changes only the two private scripts, their two tests and this append. It is not independent acceptance or completion of PR146.

A declared oversized original is rejected from regular-file metadata before opening or hashing it. An opened regular descriptor is checked against that metadata and copied once to an exclusive, owned private staging file. The actual staged bytes determine the SHA/size; only that stage is parsed. Log diagnostics and GPX parse reads are bound back to its digest, and bounded archive copy/readback verifies the same original size and SHA, including existing destinations. The original path is not reopened for a separate text parse. This fixes the demonstrated A→B→A reopen mismatch; it does not promise an atomic snapshot of a concurrently changing original filesystem.

One cooperative read ledger and absolute deadline begin at each public entry, before preflight: intake at most300s; runner finite-positive-nonbool timeout at most330s. All original/stage/copy/hash/existing-target/receipt reads consume the same parent allowance of2GiB. Each read request is limited by original size, per-file cap and remaining global bytes, plus one rejection byte; actual failure bytes are charged before rejection. Writes are not counted as reads. The existing child wait receives only the remaining whole-entry time. Blocking OS calls/parser work remain cooperative; there is no hard process-tree, RSS or hostile-child lifetime guarantee.

The raw cap remains200MiB per source and at most2 source rows. The log diagnostic has4MiB/20,000-record/128-night limits, checked before collection growth. Incremental Expat parsing retains no ElementTree and limits XML to1M trackpoints/2M elements/depth64. DTD/entity declarations are rejected by parser handlers before expansion, including tested BOM/UTF16 and split-chunk declarations. Namespace processing retains rejection of undeclared prefixes and counts namespaced points. Existing literal event/species/night interpretation remains diagnostic only. The complete v1 receipt has one shared producer/consumer256KiB cap; decoding, encoding and existing-receipt verification remain within the same budget. No counters or new timestamp/version fields are inserted into old v1 receipts.

The reviewed7402 path guard, records-only `source_receipt_id`, operational-night function and device/inode-owned cleanup are unchanged. Cleanup applies the same FIRST/residual policy to the new capture stage: a replacement is preserved, an existing primary exception remains the identical object with a residual note, and uncertain cleanup without a primary is explicit failure. Published links are not automatically rolled back or retried. A receipt-cap/deadline failure can leave a prior verified raw archive; it never means a complete intake or scientific run succeeded.

Actual synthetic TDD/evidence, preserved in `.worktrees/private-pdca-bounded-snapshot-author-20261028/`:

- Initial2 methods failed on7402 in0.028s:33B with32B cap was opened/hashed before rejection; a same-size A→B→A source produced archive sighting A but capture diagnostic B. Eight additional resource/parser methods produced16 failure subcases in0.314s, with engine0.
- Namespace compatibility followup caught1 new-parser failure in2 methods/0.031s; namespace-aware handling then passed both in0.019s. A bounded5000-digit JSON integer exposed an owned decoder ValueError (1method/1ERROR/0.039s); conversion is restricted to the pure receipt-decoder call and the target passed in0.032s. Physical read/copy failures are outside that catch.
- Final62 methods:55 actual passes,7 genuine Windows symlink privilege skips,0 failures/errors,1.801s. All37 old methods retain identical AST; the three existing actual Windows junction controls pass. New cases include failed+1 byte charges, accumulated stage/receipt readback charges, real elapsed deadlines at parse/copy/receipt/preflight, remaining child wait, staged replacement FIRST identity, log/XML limits, growth, encoded declarations and existing destination conflicts. New A controls invoke no engine; existing old runner tests use bounded synthetic child emitters, not the canonical scientific engine.
- A genuine pre-edit BOM-log/ordinary-GPX v1 receipt and complete return were captured before product edits. On exactly the same fixed paths, post-edit receipt1414B is byte-identical (SHA256 `a20948ea81f78d287300cb0527cffd4059486fb5cf32ac9dbfc1e6a62f7bfc98`), with the same complete return/records-only ID and original bytes. V separately owns an untouched7402 same-path fixture for independent verification.
- One private collector failed after a completed61-method successful test log because its skipped-test objects were not JSON serializable. That full log and error explanation remain unchanged; the summary was recovered from the saved log without rerunning those tests. A separate corrected collector recorded the final62-method run above. This was a reporting failure, not a product/test pass inferred from a failed command.
- The doc append's first precondition stopped before writing because the checkout had CRLF whereas the sealed raw-Git7402 prefix was LF. Exact normalization equality was verified. Only the five allowed authored files were normalized to nativeLF; this append preserves the full original18101B Git prefix. Code/test AST and compilation are checked separately from that byte-format normalization.

F4 is still PARTIAL: child `capture_output` stdout/stderr bounds and process cleanup need separately authorized B. F6 pre-engine idempotency/full code/protocol/workspace binding and F7 faithful child-result/failure mapping remain OPEN; this patch does not close them. The existing canonical `run_pdca.py`, night lock, scientific budgets, private admission, ledger service, backend and trust roots are untouched. No provider fetch, real source, canonical engine, model fit, authenticated issuer, SEARCH/Negative/TRAIN eligibility or new authority was created. Historical owner47/dated243 anchors remain preserved; formal TRAIN/Negative/SEARCH/real fit remain0, science NOT_VALIDATED and Master NOT_COMPLETE. Root's independent code review, composition/freeze and genuine exact/fresh CI remain separate future gates.


## 2026-10-28 B1: private bounded binding/reservation helpers, not a new runner

Root explicitly dispatched B1 after accepting A d9ffe and V's concrete R2 plus immutable three-rule clarification (`.worktrees/pr146-slice-b1-concrete-r2-20261028/`). This author lane changes only the existing private runner, its test file and this append. All ten pre-existing runner functions, including `run_private` and `main`, are **literal-source and AST identical** to accepted A. B1 is not wired to the existing command; the old unbounded child path remains unfinished. No v2 terminal writer, completed reuse, B2 supervisor, new engine or second pipeline is installed.

The new private helpers lazily import only the already selected installed tool's own src modules, reject conflicting cached origins and externally selected code roots, and never patch scientific hashing/locking functions. Actual Windows absence of POSIX master capability is explicit NOT_STARTED_CAPABILITY before claims. There is no fcntl facade. Interpreter/import/version-discovery housekeeping is outside the artifact-byte ledger, bracketed by the same actual deadline checks. Exact `_runtime` and `_scientific_identity` are reused on supported POSIX; complete cycle-code digest remains distinct from master's src/scripts runtime digest and native policy/run identities. No hash match authenticates executable bytecode or an issuer.

Physical collectors use A's same read/deadline budget, original-size/+1 checks and real empty-file EOF reads. Entry/file/frontier/path/JSON limits apply before retained growth. SOURCE_DIRS/root-special membership, complete code namespace (including matching Python under cache-named directories), root requirements and existing4MiB/16MiB/256 code limits are kept distinct. Existing unbounded inventory/runtime-code/checkpoint facades are not called. Strict bounded JSON rejects duplicate/nonfinite/deep/node-overflow forms. Physical cycle binding follows the **actual** path+SHA-only code_manifest/policy_ref schema; binding refs independently record measured size. Physical policy SHA differs from the canonical policy digest. No new cycle validation/CLI or current changed-code freeze is claimed.

An owned preparation can be physically rechecked before private reservation. Source/binding metadata is exclusively published/read back and retained as shared scope state forever: a losing claimant cannot roll it back. Active acquisition and attempt claim are exclusive; late unknown/orphan state blocks. Unknown/partial/legacy attempts do not relaunch, steal leases or reset native master budgets. FIRST/residual cleanup retains replacements. Low-level reservation tests use explicitly hand-declared synthetic metadata; RESERVED_ONLY_B2_NOT_INSTALLED is not source validation or execution permission.

B1's native checkpoint-chain reader validates bounded actual artifact references, evidence/snapshot/stage/finalization/result consistency and rejects uncommitted members, but returns only NATIVE_CHAIN_ONLY_B2_NOT_INSTALLED. Historical terminal strings/flags never become real supervisor evidence. Until B2 defines and verifies that evidence, all old terminal histories/new revisions remain B2_REQUIRED or incomplete/conflict; no accepted v2 reuse is minted. Future B2 alone may map an evidenced owned timeout/output-capacity failure to BLOCKED; spawn/crash/invalid/unproven origins remain FAIL. Native-result fields cannot be invented for supervisor failure.

Actual synthetic evidence is preserved in `.worktrees/pr146-B1-author-20261028/`:

- Initial missing-helper TDD:6 methods/8 subcase AttributeErrors/0passes in0.032s. After the first implementation6 methods passed in0.149s.
- Meaningful intermediate RED: legacy v1 result and an orphan inserted after binding publication each wrongly allowed reservation,2FAIL/0.102s. Fixed prewrite legacy rejection and final membership/byte recheck block both; shared binding/source survive the losing/cancelled process.
- Native-chain engineering fixture found bool evidence size accepted as1 (3methods/1FAIL/0.270s), huge elapsed leaking OverflowError (1ERROR/0.033s), and malformed cycle timestamp accepted (1FAIL/0.045s). Strict typed guards close these. The synthetic cycle fixture initially used an incorrect size-bearing reference schema, then failed policy comparison when raw SHA was confused with canonical policy digest; those failures are retained and fixture/helper now follow the actual installed contract. No fabricated full-root successful preflight is claimed.
- Final combined targets:89 methods,81 actual passes,8 genuine skips,0 failures/errors in3.209s. Of these27 are new B1 methods:26 pass locally and one real POSIX master-identity parity test is skipped on Windows and must execute on actual supported POSIX CI. The other7 skips are A's existing WinError1314 symlink limitations. New B1 controls execute no subprocess/canonical engine/model fit/provider/source audit. Existing old runner regression tests still use synthetic child emitters; those are not scientific E2E.
- Both authored Python files compile without pyc; diff check passes. Every old runner function remains literal/AST exact. The intake script and its tests are untouched from accepted A, and this document retains its complete24680B native A prefix. No old A artifacts/unsupported-reader result or earlier proposals are overwritten.

This is AUTHOR RELEASE FOR INDEPENDENT B1 REVIEW only. F4 child stdout/stderr supervision/process cleanup, F6 integrated pre-engine idempotency/reuse and F7 faithful child failure are still open until separate B2 implementation/review/integration. The current changed runner is not covered by the old frozen-code cursor; Root owns future composition/freeze/genuine exact/fresh CI. Source17/18/17 provenance is not TRAIN; formal Negative/SEARCH/TRAIN/real fit remain0, science NOT_VALIDATED and Master NOT_COMPLETE. Historical owner47/dated243 and all existing permission/production/Champion boundaries remain unchanged.
