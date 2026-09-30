# Task 5 bridge integration: minimal design and concrete blockers

Read-only recommendation from current workflows, master_orchestrator.py, master_contracts.py, scripts/run_pdca.py, Task 5 brief and repository rules. No code changed. Existing owner authorization covers implementing and testing this extension without another routine approval; independent review and PR remain required. No permissions, secrets or bridge changes are proposed.

## Recommended single executor

Reuse `.github/workflows/pdca-command.yml` as both its existing owner-issue event workflow and a reusable `workflow_call` workflow accepting only an integer issue number. Keep the poller's schedule/dispatch triggers. Poller does discovery only, then a dependent `uses: ./.github/workflows/pdca-command.yml` job calls the same executor with that issue number. This is one implementation behind the existing two triggers, not a replacement bridge. No workflow dispatch API permission is needed.

Use one literal repository-wide concurrency group on the executor job, `habu-pdca-executor`, cancel-in-progress false. Do not put that group on the waiting caller or discovery job, which could deadlock with its child. Global serialization is intentionally conservative and sufficient at present volume. Scheduled discovery should eventually revisit every unfinished eligible issue; concurrency alone is not a durable queue or deduplication mechanism.

Inside the shared executor, refetch the issue through GitHub API and independently verify repository owner author, exact command prefix, open/handled state and one valid calendar date via datetime.date.fromisoformat. Do not trust caller-provided title/night or event payload as current authorization. Pass values by environment or subprocess argv; no interpolation of issue body/title into shell code. Pin processing to a resolved trusted default-branch commit SHA. Never check out a ref from issue text, report branch or restored artifacts as executable code.

## Identities and durable control record

Distinguish command, scientific run and attempt:

- command identity: repository + issue number + normalized operational night + hash of authorized command text;
- run identity: orchestrator's full hash over night, source inventory, actual code, policy and runtime;
- attempt: Actions run ID and run attempt, started_at, pinned source commit.

Do not replace these with a single issue number, date or GITHUB_RUN_ID. Current orchestrator command_key hashes night + inputs, not GitHub command identity; bind the two in a bridge receipt instead of modifying historical manifests or confusing them.

Use a deterministic report branch namespace and structured receipt under `reports/pdca/<night>/bridge/` as the durable control record. Initialize the command receipt before expensive execution, with normalized command, source commit, expected inventory/identity, attempt, lease expiry, state RUNNING and maximum budget. Push only receipt paths to the existing report branch mechanism, never to main. Serialize updates through the executor; also verify expected previous remote branch SHA so outside changes fail safely. Poller labels are convenience, not authority. A stale pdca-processing label must not suppress recovery after the receipt lease expires. A valid terminal receipt lets the duplicate event/poller return the same report and PR without rerunning.

Different issues with identical command night/source/code/policy/runtime should converge on the same run publication. Each issue gets its own small receipt/reference to that shared run. New source/code/policy/runtime generates a new scientific run; it does not overwrite an existing one. Repeated transport delivery of an already-bound command stays pinned to its receipt, even if main subsequently changes. A new owner command intentionally observes current main.

Use deterministic branch/PR identity per run, query an existing PR before creating, and upsert one marked result comment per command. If publication succeeds but PR creation/comment fails, recovery completes only that missing step. No force push and no second branch named by workflow run ID. Issue-comment creation has no atomic idempotency key: with serialization and marker lookup this is practically recoverable; do not claim transactionally exactly-once remote messaging.

## Durable artifacts without permissions changes

Current permissions declare contents/issues/pull-requests write but no actions read. Do not add `actions: read` or assume cross-run artifact download is permitted. Keep upload-artifact for diagnostic convenience, but cross-run recovery must work from existing contents permission and repository storage.

Do not commit `reports/pdca/<night>/runs/<id>/snapshot/` wholesale. The current source data alone is about 68 MiB, and each run snapshots code, docs, raw data and predictions. Blanket `git add reports/pdca/$NIGHT` would duplicate that on every run.

Use a compact recovery bundle on the report branch:

1. Source commit SHA, exact input inventory, runtime/policy identity and recovery manifest.
2. The run's checkpoint.json, checkpoint.sha256.json, evidence_manifest.json, committed stage artifacts, finalization checkpoint and run manifest when present.
3. Only generated snapshot files referenced by checkpoint output hashes; original snapshot files are reconstructed from the pinned source commit.
4. A bridge receipt identifying exact paths, SHA-256, byte sizes and total size.

Before publishing, prove every source inventory item exists byte-for-byte in the pinned source commit (including legacy report input). If any consumed source is untracked or differs, either include that exact source in the bounded recovery bundle or return `RECOVERY_SOURCE_UNAVAILABLE`; never claim resumability. No raw evidence is overwritten or deleted. Use a separate temporary git index/worktree rooted at the trusted commit for publication so ordinary dirty working-tree changes cannot be staged accidentally.

On a fresh runner, fetch only the exact recorded source commit and bundle commit, parse receipts as data, validate safe relative paths, prohibit symlinks/traversal, enforce size/file-count limits and verify all hashes before writing a restore directory. Reconstruct snapshot source paths from the pinned commit and verify against evidence inventory. Restore generated outputs and checkpoint at their expected run-relative paths. Then call the existing entrypoint; the orchestrator must independently revalidate restored artifacts. Never execute Python/YAML from the recovery branch.

Suggested engineering caps: at most one selected run per publication, 2,000 generated files, 20 MiB total compact bundle, 5 MiB per generated file. Choose/document final numbers before implementation. Above-cap results must produce a small failure/blocked receipt and required condition, not truncate artifacts and report successful recovery. Full upload-artifact retention is not indefinite durable storage. These are publication limits, never scientific KPI adjustments.

For hard process termination, post-job upload is insufficient. Persist a validated compact checkpoint generation after each completed stage, or use a bounded supervisor that copies only a self-consistent checkpoint/output set and verifies hashes before publishing. Checkpoint.json and checkpoint.sha256.json are separate atomic writes, so a watcher must read/verify/re-read and retry inconsistent generations; it must not publish a partially observed pair. If integrating such a publisher requires extending Task 2's interface, make the narrow integration fix explicitly rather than claiming hard-kill recovery from an `always()` step.

## No stale success and exact binding

Create a unique output receipt path for this attempt using the CLI's existing `--output` option, and remove only the compatibility `pdca_result.json` before invoking the command. Do not delete authoritative prior runs. Execute with a bounded subprocess timeout shorter than job timeout, capture exit code, and allow finalization time.

A result is authoritative only when all of these hold:

- attempt-local output exists and parses under the result contract;
- night, command binding, run ID, code/input/policy/runtime identity match the prebound receipt;
- the referenced run_manifest exists, matches the checkpoint's result_sha256, and the finalization checkpoint chain validates;
- every expected stage is present once and aggregate severity/completed agree with child stages;
- the subprocess termination agrees with the result.

Important current contract: scripts/run_pdca.py returns 2 for both BLOCKED and FAIL. Thus `exit != 0` does not always mean execution crashed. Accept exit 2 only with a valid current BLOCKED/FAIL manifest and report that status; never turn it into PASS. Exit 0 allows the documented successful execution statuses but still does not imply master completion. Missing receipt, signal, unexpected exit or mismatched identity yields a new bridge FAIL record, never a read of an old compatibility report. Preserve existing checkpoint evidence for recovery.

Persist all statuses, including BLOCKED and FAIL, before publishing a terminal issue result. Leave failed publication/infrastructure attempts retryable with a recoverable lease; do not label them pdca-complete. A scientifically blocked but successfully persisted command can be marked handled to avoid polling every five minutes, while clearly reporting master incomplete. Do not close the master issue. If command issues are closed, avoid representing BLOCKED/FAIL as successful completed science; document handled-versus-master-complete semantics explicitly.

## Current implementation integration risks needing parent action

1. `_runtime()` includes platform.platform(), full sys.version and every installed distribution. Fresh runners can have different kernels/platform strings or incidental packages, generating a different run identity despite identical scientific runtime. Do not fake the recorded identity to resume. Either document resume unavailable when runtime differs, or make a reviewed Task 2 change to distinguish stable scientific runtime identity from machine diagnostics, using the actual relevant interpreter/dependencies. Add a two-clean-runner identity test.
2. Checkpoint recovery adds all wall-clock downtime since active_since to the 300-second elapsed budget. A five-minute scheduled retry after crash will often immediately exhaust its budget. The plan's recovery promise requires a deliberate bounded retry policy; do not silently reset the ledger. Persist attempt time limits and explicit remaining allowance, or declare BUDGET_EXHAUSTED and stop. Charging at most the prior attempt's proven hard timeout is safer than charging an indefinite outage, but requires reviewed Task 2 contract work.
3. Source/runtime identity computation is private and duplicated if embedded in workflow scripts. Prefer one narrow exported identity/verification helper; if the Task 5 allowed paths prohibit it, parent should explicitly integrate the minimal reviewed Task 2 change. Do not maintain a subtly different workflow hashing algorithm.
4. Job killed before remote checkpoint persistence cannot recover those unpersisted stages. Never advertise stronger recovery than tested. Persistent publication failure must remain a separate infrastructure blocker from scientific status.
5. Existing workflow installs only requirements-osm.txt; baseline environment includes additional preinstalled distributions. Preserve dependencies, but test clean Actions runtime so local PASS does not mask undeclared imports.

## Required verification

Test shared executor structure/owner gate and unchanged permission map; invalid calendar dates; event plus poller for one command; two separate issues for identical snapshot; changed source creates new run; crash after remote run publication but before PR/comment; stale processing lease; stale PASS present before failed command; exit-2 BLOCKED; corrupted checkpoint, bundle path traversal and hash mismatch; bundle cap; restore in a clean temporary root from pinned source plus compact generated artifacts; hard-kill recovery to last persisted checkpoint with cumulative budget; exact raw/ORIGINAL before/after hashes. Remote Actions and real bridge evidence are distinct from local synthetic tests. Keep master open.

## Workflow risk/authorization

Workflow edits are security-sensitive because existing contents-write credentials can publish branches and privileged repository code executes on owner issue events. The real risks here are untrusted checkout refs, command interpolation, overly broad staging, unverified restore bundles and permission escalation. Mitigate those directly through trusted pinned source, structured argument passing, explicit path allowlists, hash/size validation and unchanged permissions. Repository AGENTS.md contains no additional workflow-specific approval requirement in the inspected tree. The user's explicit autonomous authorization already covers this bounded workflow extension; no routine confirmation is needed. Still require independent review and PR, and do not assert eligibility to merge or production activation without their actual gates.
