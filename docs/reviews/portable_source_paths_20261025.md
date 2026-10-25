# Portable source-path validation — 2026-10-25

## Scope and implementation

Base: `be045334a5ede3d5b92088e86b2b4852ccc8b6a1`.
Branch: `codex/portable-source-paths-20261025`.
This implementation changes only `src/master_inventory.py`, its existing test
file, and this review record. Independent review is pending.

`local_path` now rejects each relative Windows-style component containing a
colon, ending in an ASCII dot or space, or matching `~[0-9]+(?:\.|$)`. This check
runs before `safe_path`, resolution, or filesystem metadata. No spelling is
trimmed or rewritten. Existing absolute/traversal, ancestor reparse, and resolved
containment checks remain intact.

The short-name rule deliberately rejects ambiguous candidate spellings even if
they name an ordinary file on a particular filesystem. No actual 8.3 alias was
established by this review. Normal internal spaces and dots, Japanese names,
`tilde~name`, and `x~1name` remain accepted and preserve exact copied bytes.

## Reproduction and shared boundary

On native Windows, benign temporary `evidence/ORIGINAL./manifest.json` passed
`samefile` against `evidence/ORIGINAL/manifest.json` and returned its exact bytes.
The previous helper accepted that spelling, and the real shared G0 reader read
it. A middle directory ending in space or dot-space did not resolve to that
directory in this environment; those names are covered by the conservative
portable rule rather than claimed as demonstrated aliases.

The shared read path is `G0ArtifactReader.read` → `prospective_inputs._local_path`
→ its imported `master_inventory.local_path` → bounded file open. Strict TRAIN,
forecast, configuration, and Stage1 source validation reuse this boundary.
Configuration/Stage1 preflight also calls `local_path` directly. No separate
loader, namespace, byte/time budget, authority flag, or model code was changed.

## Verification

- Before implementation: the final four new test methods produced **15 failing
  assertions** (13 lexical cases, native dot alias, and shared-reader alias).
  The valid-name byte-preservation control passed.
- After the five source-line addition: **4/4 PASS**. Ambiguous paths raise
  `ValueError` before `safe_path` or `Path.lstat`; the shared reader performs no
  payload open, charges zero bytes, and retains no consumed reference.
- Seven complete relevant modules: **206 tests, 196 PASS, 10 explicit platform
  skips, 77.913 seconds**. Modules: `test_master_inventory`,
  `test_g0_forecast_contract`, `test_g0_training_source_contract`,
  `test_research_candidate_config_source`, `test_stage1_source_adapter`,
  `test_stage1_configured_source_adapter`, and `test_research_pdca_adapter`.
  These include existing whole-artifact/read-byte oracles, static junction
  guards, exact-byte inventory/copy/snapshot behavior, and parent requests.
  Skips comprise three POSIX symlink cases, four POSIX atomic-cleanup cases, and
  three actual-master cases requiring `fcntl`; they are not claimed as passed.
- Intermediate native v4 probe: the existing eight-case external alias harness
  ran against unchanged v4 commit `3d743d490176ade83cf89af398e4be7f9409e5fe`
  with this repaired shared module preloaded in that process. **8/8 rejected**,
  forbidden payload opens/candidates/REPLAYs all zero. This mixed-source probe
  is not acceptance of the final coordinator snapshot; that needs independent
  verification after integration. The v4 working tree remained clean.
- Both changed Python files compile without bytecode writes; `git diff --check`
  passes. No Raw/ORIGINAL, other product source, state, cycle, or PR edits.

Canonical staged Git bytes:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `src/master_inventory.py` | 5533 | `1f108ce34e0f450cf4b438a912bb333df923fd50b0e6752760685c00df05db27` |
| `tests/test_master_inventory.py` | 19135 | `f987d80748ad4a93b2878fababa23df8ce977bbb6d8a9ee7ada894bf93a7f5a4` |

This is a path-integrity strengthening. It does not authenticate source issuers,
establish historical availability, or grant scientific or production authority.
