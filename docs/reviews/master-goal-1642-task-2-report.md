# Task 2 implementation report

Status: bounded Task 2 implemented locally; independent review pending. Whole Master Goal #1642 remains incomplete.

Commit: `55795f8472eb730f577817ee14b880080558a52a` — Add durable master contracts and snapshot orchestration.

Scope: only `src/master_contracts.py`, `src/master_orchestrator.py`, `scripts/run_pdca.py`, `tests/test_master_orchestrator.py`, and three `schemas/master-*.json` files committed. Existing untracked data and parent-owned documentation changes were not staged. No remote writes.

Implemented:
- Existing CLI calls `run_master(root, night, budget_seconds=300)` and preserves operational result fields plus authoritative master stages/status. Added optional `--budget-seconds`.
- Nine required stages always reported; malformed operational evidence is FAIL while independent model adapter discovery still proceeds. Implementation blockers and data blockers remain separate. Missing development/model/Champion adapters never become success.
- Deterministic content identity covers source inventory, actual source code, fixed policy, Champion/model inventory, Python/platform and installed dependencies. Generated report trees are excluded, except the explicit legacy report input.
- Isolated input copies in run snapshot; all source inventory and consumed snapshot files, code and runtime are checked at finalization and on duplicate reuse. Raw/ORIGINAL are never written. Snapshot REPLAY is an allowed output namespace; generated artifacts are hashed for retry verification.
- Local per-night exclusive flock, atomic/fsynced JSON, stage output hashes, evidence manifest, run manifest, durable checkpoint and separate verified finalization checkpoint. Corruption becomes current-run FAIL, not old-report success.
- Interruption recovery, cumulative elapsed budget, conservative charging of killed-worker downtime, persisted improvement-round count, candidate/round bounds, and explicit budget retry conditions. Increasing the total budget can resume budget-blocked stages without resetting spent time.
- Future interfaces: `model_evaluation.evaluate_models(snapshot_root, night, remaining_budget)` and `champion_registry.evaluate_promotion(snapshot_root, night, evaluation_result)`. No future modules implemented.

TDD evidence:
1. Read test-driven-development skill and writing-good-tests reference.
2. Initial 10 tests failed because the master module did not exist; after implementation all 10 passed.
3. Four new recovery/output tests failed for budget retry, interrupted-stage resume, suppressed independent research, and unhashed generated operational output; fixes yielded 14 passing tests.
4. Additional killed-worker accounting and generated REPLAY tests failed; fixes yielded 17 passing tests including actual concurrent CLI processes.
5. Malformed adapter blocker handling and finalization checkpoint reference failed before fixes; final suite has 20 new orchestration tests.

Validation:
- `python -m unittest discover -s tests -p test_master_orchestrator.py`: 20 passed.
- `python -m unittest discover -s tests`: 97 passed (77 prior + 20 new).
- `git diff --cached --check`: passed before commit.
- Raw/ORIGINAL exact-byte preservation, malformed prediction FAIL, mid-run processed learning replacement FAIL, changed code/policy/Champion identity, checkpoint/artifact corruption, interruption and hard worker exit, budget exhaustion/resume, and duplicate command behavior covered locally.
- JSON schemas were parsed/materialized with stdlib; no external schema-validator dependency was installed. Runtime contracts validate adapter/stage structure.

Limitations / review focus:
- This is local evidence, not remote Actions or live bridge evidence. Parent owns independent review and any later remote publication.
- No scientific validation, approved development executor, trusted production runner, model implementation, Champion implementation, or production activation is claimed. Evidence audit explicitly leaves quality/availability/search eligibility unresolved.
- Snapshot readers must use the supplied root and declared input namespaces. Later adapters must keep all consumed source artifacts in the inventory-covered namespaces; do not introduce hidden external reads. Hashes establish consistency, not issuer authenticity.
- Budget checks are cooperative at parent stage boundaries. Model adapters must enforce their supplied remaining budget within folds. An adapter is never allowed arbitrary generated shell/code.
- Deliberately conservative corruption handling rejects rather than trusting or silently recomputing damaged results; raw failures are never treated as an old successful report.

## Independent review round 1 remediation

Review: `/workspace/scratch/fb45a4f31791/task-2-review.md` identified three Important defects. All three were reproduced with targeted tests before remediation.

Commit: `4e5a2ca78ad1583cb513d34bcf8f343962d7847b` — Fail closed on interrupted artifacts and operational contracts.

Changes:
- Completed-stage checkpoints now include generated artifact digests immediately, before the stage is considered durable. Resume compares the exact generated artifact set against checkpoint hashes. Changed completed reports and injected/uncommitted REPLAY artifacts are rejected; finalization no longer silently adopts them.
- Operational payloads require nonempty, well-formed child stages, valid string blocker lists, serializable contents, and summary status consistent with the derived child-stage aggregate. Nested FAIL cannot be published as operational PASS/VALIDATED.
- Artifact collection and finalization have a durable FAIL fallback that replaces the compatibility pointer for the current invocation. Error reporting does not attempt to certify invalid generated artifacts.
- Added controlled `evidence/` and `model_specs/` input namespaces. Existing generated report/run trees remain excluded from source inventory, avoiding recursive snapshot copying.

TDD / validation:
- Seven regression tests added. Initial run: 5 failures and 2 escaped-exception errors reproduced the review issues and missing namespace snapshot behavior.
- `python -m unittest discover -s tests -p test_master_orchestrator.py`: 27 passed.
- `python -m unittest discover -s tests`: 104 passed.
- `git diff --cached --check`: passed.
- No documentation, raw, ORIGINAL, or unrelated files staged; no remote writes.

Remaining concerns are unchanged: independent re-review is needed; whole Master remains incomplete. Cross-run Actions restore/publication/idempotency, report publication views, missing approved development executor, scientific adapters and trusted production persistence belong to later slices. As a conservative recovery policy, new uncommitted files left by a killed stage cause rejection rather than being adopted or silently recomputed.
