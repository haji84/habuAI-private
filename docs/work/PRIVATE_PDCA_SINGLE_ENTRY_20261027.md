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
