# Encrypted public dashboard Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans task-by-task.

**Goal:** Connect authenticated encrypted owner inputs to an aggregate-only dashboard without releasing keys or individual records.
**Architecture:** Existing vault verifier + existing owner overlay -> allowlisted public summary -> isolated static release. No cryptographic redesign, no browser decryption.
**Tech Stack:** Python standard library, existing cryptography AESGCM, static HTML/JS, unittest.
**Spec:** docs/superpowers/specs/2026-11-10-encrypted-public-dashboard-design.md

## Global Constraints
Public GitHub code only; real vault/key/input/receipts outside Git and Public Actions. Preserve original bytes, counts, earlier forecasts and all official model gates. Keep PR #160; no main merge, new host or new recurring task.

## Review Focus
- Nested private strings and keys must never flow into HTML or JSON.
- Count discrepancies must be preserved, not corrected by deleting animals.
- Bad AEAD/tag/source hash must emit no new public release.
- No stale private fallback snapshot or browser-side key is allowed.
- Repeated input must be idempotent and conflicting output must fail.

### Task 1: Aggregate projection
Files: tools/dashboard_release/public_summary.py; tests/test_public_dashboard_release.py.
Interface: project_public_summary(private: dict) -> dict, validate_public_summary(public: dict) -> dict.
- [x] Tests first: monthly/effort consistency, excluded surveys, owner mismatch, private canaries absent, impossible public fields rejected.
- [x] Implement strict structured projection using no input free-text.
- [x] Run tests, record results.

### Task 2: Encrypted bridge and static page
Files: tools/dashboard_release/vault_dashboard.py; tools/dashboard_release/habu_library_vault_tool.py (existing verified code); dashboard/public-summary.html.
Interface: build_from_vault(archive, key_file, base_entry, overlay_entry, destination, template, expected_archive_sha256, expected_base_sha256, expected_overlay_sha256) -> private receipt.
- [x] Test wrong-key/tag, encrypted manifest, hash validation, safe destinations and atomic/no-overwrite behavior before implementation.
- [x] Verify vault, decrypt just required JSONs in memory, reuse apply_overlay, project safe data, render a sanitized release with no requests to the private source.
- [x] Run browser/synthetic tests.

### Task 3: Real snapshot and integration
- [x] Verify old archive with the existing key without printing it.
- [x] Append new originals and source snapshots with existing vault extension. Preserve old archive.
- [x] Run the real private-to-public pipeline and independent readback/scan; save artifacts to Library.
- [ ] Update PR #160 with code/synthetic tests and an exact-source freeze for the already added overlay helper. Verify fresh CI; leave hosted activation and official model promotion unasserted.

## Verification boundary
Local targeted suite: 36 tests passed using installed cryptography 46.0.4. CI pins current verified PyPI release 50.0.2; its result must be checked separately before release. No fresh independent reviewer was available in this execution environment. Do not describe local tests as full-repository CI or independent security approval.
