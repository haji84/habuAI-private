# Task 4 implementation report

Status: bounded lifecycle/inference foundation implemented locally; independent review required. Full Master Goal and production/scientific activation remain blocked. No remote writes or subagents.

Commit: `96c6cb0c4ac1f1955c26c8ea7c2993fd6f890953` — Add isolated Champion lifecycle and atomic registered inference issuance.

Only seven owned paths committed: `src/champion_registry.py`, `scripts/freeze_prediction.py`, `scripts/issue_prediction.py`, `tests/test_champion_registry.py`, `tests/test_prediction_lineage.py`, `schemas/champion-model.json`, `schemas/champion-event.json`. Parent documentation and historical data/predictions/reports were not staged or modified by this task.

## Mechanics implemented

- Model artifact validation checks canonical model hash/ID, registered family, actual installed `model_evaluation.py` file hash, exact implementation version, current empty feature schema and actual produced-output family. Content-hashed CANDIDATE artifacts remain unchanged; lifecycle state resides in append-only registry events.
- Explicit ephemeral `sandbox_registry()` allocates its own temporary root and creates a live in-process context. Callers cannot attach this context to arbitrary persisted roots; expired/forged contexts fail. No JSON field or CLI flag can enable sandbox execution. Model/event records and predictions live under `sandbox/`; issued payloads are explicitly `prediction_class: SANDBOX`, `qualification: SANDBOX_MECHANICS`, `provenance_status: NOT_VALIDATED`, official eligibility false.
- `promote` / `rollback` serialize under an exclusive OS file lock. Expected previous state is event SHA-256, avoiding model-ID ABA acceptance. Same-transition retry is idempotent. Event hash binds previous event, previous/next model, model/evidence references, reason, timestamp and mechanical qualification. A pointer is atomically updated only after the immutable event exists.
- `champion_at` walks only the current pointer's verified ancestry, never arbitrary event files. Orphans left before failed pointer publication are inactive. Chain checks model/evidence hashes, transition coherence and nondecreasing activation times. Rollback requires a model found in the previously committed, integrity-verified chain. Historical lookup uses requested time; issuance separately supplies its actual issuer clock.
- Generic freeze rejects claimed executed-Champion lineage. It remains an external-record issuer with NOT_VALIDATED provenance. It preserves an earlier information cutoff while using its own issuance/freeze clock. Strict JSON serialization rejects NaN/Infinity before publication.
- Freeze uses a per-root exclusive issuance lock, contiguous next-version calculation inside that lock, complete payload/hash serialization, fsynced staging files and same-filesystem atomic staging-directory rename. A failure before rename removes the staging directory and does not reserve P0. Existing version directories are never overwritten. `.prediction-issuance.lock` is coordination state, not a prediction version.
- `issue_prediction` executes the actual imported registered `predict_model` function. It verifies immutable snapshot/universe references, code/model/schema binding, ex-ante availability, model training cutoff, exact row cutoff/night, coordinates and prospective aligned ten-minute windows. Output probabilities change for known different fitted models, and the actual output hash is bound to the issued record.
- Registry lock remains held through selection, inference and prediction publication, serializing promotion races. Actual clock, selected event, model/code and all consumed file hashes are rechecked after inference and before publication. Already elapsed windows cannot be hidden by the earlier forecast-information cutoff.
- Current spatial adapters emit `grid_predictions` and their existing declared output families. They do not acquire invented formal time-target outputs: `targets_100m_10min: []`, `formal_100m_10min_status: NOT_PRODUCED`.

## Production boundary and decision adapter

Production `promote`/`rollback` with a filesystem Path always return BLOCKED with the exact missing trusted-authority condition. Production `champion_at` returns None without accepting any manually forged production pointer/event/model files. Production `issue_prediction` raises that authority blocker before inference/publication. There is no production bypass switch. Only a live separately allocated temporary sandbox context enables mechanical lifecycle/inference testing.

`evaluate_promotion(snapshot_root, night, evaluation_result)` is a read-only adapter returning schema version 1.0, canonical `promotion_decision` / `champion_handoff` stage records and decision/blocker lists. It preserves upstream FAIL/rejection/reasons and separate implementation/data/runtime blockers. It never writes a registry from an analysis snapshot and never returns ACCEPT_CANDIDATE.

`validate_candidate(root, validation)` validates model/artifact hashes and bindings. Tampered/unsupported evidence returns FAIL / REJECT_CANDIDATE. Consistent current model evidence returns BLOCKED / NEED_MORE_DATA, with separate missing complete outcome ledger, five distinct confirmation nights, cross-year coverage and mandatory formal/ablation/calibration/trusted-reproduction implementation blockers. It does not trust supplied summary metrics, PASS flags, decision booleans or synthetic/trusted declarations.

**Explicit limitation:** complete-outcome-ledger recomputation, formal target gate reproduction, untouched confirmation consumption/uncertainty, true retraining ablation/calibration and authenticated CI/controller authority are not implemented here. Current Task3 artifacts cannot satisfy them. This code deliberately has no scientific acceptance path; registry mechanical success does not count as completion of those gates. Those verifiers and production authority must be supplied by later reviewed slices before any production activation can exist.

## Interfaces for parent integration

Registry public functions:

- `validate_candidate(root: Path, validation: dict) -> dict`
- `promote(root: Path | SandboxContext, model_id, evidence_path, expected_previous_event_sha256) -> dict`
- `rollback(root: Path | SandboxContext, target_id, reason, expected_previous_event_sha256) -> dict`
- `champion_at(root: Path | SandboxContext, cutoff: aware ISO string) -> dict | None`
- `evaluate_promotion(snapshot_root, night, evaluation_result) -> canonical adapter envelope`
- `sandbox_registry()` context manager, test mechanics only; not exposed on CLI.

Validation envelope: `schema_version: 1.0`, `model: {path, sha256}` (raw-file SHA-256), `model_id`, optional `artifact_refs: [{path, sha256}]`, optional `folds: [{night,...}]`. Artifacts are locally scoped, strict JSON; no summary fields grant authority. Registry returns sandbox event data plus `event_path`; returned `event_sha256` is the next CAS token. Stored events exclude the derived return-only `event_path`.

Issuance API:

`issue_prediction(root, snapshot_path, snapshot_sha256, night, version=None, *, clock=None) -> Path`

`clock` is test injection; CLI takes `--root`, `--snapshot`, `--snapshot-sha256`, `--night`, `--version` and has no clock/sandbox override. Production CLI exits nonzero with the missing authority blocker.

Inference snapshot contract:

```
{
  schema_version: "1.0",
  operational_night: "YYYY-MM-DD",
  cutoff_time: "aware ISO information cutoff",
  universe: {path, sha256, available_at},
  feature_schema_sha256: digest([]),
  source_manifest: [{path, sha256, available_at, role: "feature" | "universe"}],
  features: {}
}
```

The referenced universe uses Task3's `schema_version: 1.0`, `source_type: EX_ANTE_FORECAST`, nonempty `geographic_domain`, nonempty `rows`. Each row requires unique string row_id, operational_night, cutoff_time, aligned window_start_jst and validated exact UTM52N coordinates or latitude/longitude. Source/universe availability must precede information cutoff. Current supported models have an empty feature schema; feature-aware contracts are rejected rather than silently ignored. Referenced provenance artifacts in this bounded issuer are JSON objects; a future feature-aware adapter may need explicit raw-source support.

Schemas document model and sandbox event structures but are not authority. Runtime validation remains responsible for hashes, installed code identity, timestamps, chain and boundary checks.

## TDD and verification

- Read Task4 brief in full, normative specification and Task3 report/interface; followed existing TDD skill and verification-before-completion skill.
- Registry initial RED: 10 test methods failed because the registry module was absent. Then lifecycle, CAS, rollback, hash, production-denial and adapter tests passed.
- Issuance initial RED: concurrent freeze raised a race/version error; generic claimed lineage was accepted; atomic-rename failure injection and issuer APIs were absent. Implemented locked atomic staging and registered inference.
- Further RED: artifact changed between hash check and decode returned BLOCKED rather than FAIL; changed read to hash the exact decoded bytes. Explicit sandbox class test initially saw ORIGINAL, corrected to SANDBOX. Adapter test initially lost the upstream tamper reason, corrected propagation.
- Additional regressions cover strict nonfinite JSON rejection, naive clocks, idempotent transition retry and exact installed code binding; existing correct protections remained tested.
- Focused final registry suite: 12 tests passed.
- Focused lineage/atomic issuance suite: 10 tests passed.
- Final full command `python -m unittest discover -s tests`: **158 tests passed** (136 prior +22 new methods), 9.123 seconds in final run.
- Scoped diff-check and staged diff-check passed. No existing tests were weakened or removed.

Coverage includes tampered model/evidence/event and wrong adapter identity, missing/insufficient full evidence, production self-declared trust denial, concurrent CAS, stale ABA token, rollback rejection, historical lookup, pointer-crash orphan, changed real inference outputs, immutable earlier output, promotion race, input hash mutation, future availability/training cutoff, expiry during calculation, contiguous concurrent freezes and prepublication failure cleanup. Unit failures use disposable temp roots. Local tests are not remote Actions or live scientific/production validation.

## Remaining concerns

- Full production authority and scientific gate reproduction remain intentionally BLOCKED as described above. No claim of a production Champion or successful live handoff.
- Sandbox consistency hashes are not cryptographic authenticity; the context is a local test capability. Users with arbitrary Python/process control could alter in-process state, but that still cannot enable the Path-only production APIs in this implementation.
- Locks use stdlib `fcntl` and atomic rename on one local filesystem; distributed locks, network filesystem guarantees and reviewed durable remote persistence belong to later production integration.
- A crash during an immutable model/event file write can leave a partial orphan that fails integrity checks; it cannot activate without a committed current pointer. Recovery rejects conflicting immutable artifacts rather than silently repairing or treating them as success.
- Snapshot/source availability is a hash-bound declaration checked for consistency, not authenticated ex-ante provenance. Full-scope observation/outcome coverage is not inferred from restricted universe rows.
- Full generic prediction-schema hardening and existing broader output/run recovery remain separate from this task. Existing historical ORIGINAL/Raw records are untouched.

## Independent review fix round 1

Read the complete independent review `/workspace/scratch/fb45a4f31791/task-4-review.md`; addressed all three Important findings, with no production-boundary expansion. Parent explicitly authorized the small shared `src/model_evaluation.py` correction and newly-created directory-link durability work.

Fix commit: `f3c77632e4ee07f547e952e60fe9a03547405a2d` — Validate complete fitted state and harden durable JST issuance.

1. **Complete fitted-state validation:** `predict_model` validates the default and every area value for probability families before iterating universe rows. All values were already checked finite/nonnegative; uniform/prevalence values now also cannot exceed one, including empty-universe verification and unused areas. `verify_model`, candidate validation and sandbox activation therefore reject invalid self-consistent artifacts before committing a model. Score-only families keep nonnegative values above one and null probability; no family formula/hyperparameter was changed. The actual source file hash changes, so prior model artifacts bound to the old adapter hash are intentionally not silently relabeled as supported by the new code.
2. **Publication durability:** freeze now fsyncs the staging directory after both file entries are written/fsynced and before rename. Destination-parent fsync remains after rename. Output-directory ancestry through the root's parent is synced before staging, establishing newly-created links and re-establishing them on retries after a prior sync failure. An injected staging-directory sync failure cleans the pending directory and leaves P0 available for the next attempt. This is a supported local-filesystem durability ordering check, not a claim of a destructive power-loss experiment.
3. **JST window contract:** the issuer converts the aware window timestamp to Asia/Tokyo before checking ten-minute alignment. Equivalent UTC and +05:45 encodings of 21:00 JST are accepted; +05:45 local 18:00 (21:15 JST) is rejected. Absolute-time prospectiveness and existing 07:00 operational-night behavior remain intact.

TDD evidence: before fixes, focused registry tests showed eight failing probability-bound subcases (empty universe and unused/invalid defaults/areas), candidate validation returned BLOCKED instead of FAIL, directory-sync tests showed absent staging sync / absent expected failure, and timezone tests reproduced both misaligned acceptance and aligned-equivalent rejection. Changes were then made only in the three production files named above, with regressions in the two owned Task4 test files.

Final verification:

- `python -m unittest discover -s tests -p test_champion_registry.py`: **14 pass**.
- `python -m unittest discover -s tests -p test_prediction_lineage.py`: **13 pass**.
- `python -m unittest discover -s tests`: **163 pass**, 9.067 seconds.
- Scoped and staged `git diff --check`: pass.

Five files committed; parent plan/docs/evidence were not staged. No remote writes, historical data or ORIGINAL changes. Test OS instrumentation forwards the actual fsync/rename calls and records their order; the durability tests use Linux `/proc/self/fd`, consistent with the implementation's existing Linux/fcntl environment. All scientific, source-authenticity and production-authority blockers above remain unchanged. Independent re-review is still required.

## Independent re-review fix round 2

Read `/workspace/scratch/fb45a4f31791/task-4-rereview.md`. The sole remaining Important finding was recursively created ancestors above the synced root-parent boundary. Selected the review's explicitly permitted minimal API restriction: **the prediction root's parent must already exist**. Freeze validates that prerequisite before creating the root or output directories, and root creation no longer uses recursive `parents=True`. This makes the already-existing parent the supported durability boundary; freeze still syncs the complete output ancestry through that parent and repeats those syncs on retries.

Commit: `7a95ff9b3fbcf3b01c9dab7f3fa0dccf6f2afc09` — Require existing freeze-root parent as durability boundary.

TDD: a nested absent root `T/new-parent/new-root` initially published successfully and failed the new rejection assertion. After the fix it raises a clear ValueError before creating `new-parent`; a new root immediately under existing T still publishes normally. A second regression injects a failure syncing the existing ancestor, verifies no P0 is published, and verifies the next attempt actually syncs that same ancestor again before publishing P0. This prevents assuming visible directories from a failed attempt are already durable.

Verification: lineage suite **15 pass**; full `python -m unittest discover -s tests` **165 pass** in 8.635 seconds; scoped/staged diff checks pass. Only `scripts/freeze_prediction.py` and `tests/test_prediction_lineage.py` committed. Parent docs/evidence untouched, no remote writes or historical rewrites. The model/probability/JST repairs from round 1 and all production/scientific blockers remain unchanged. No destructive power-loss experiment was performed.
