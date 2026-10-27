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

