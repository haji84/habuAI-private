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
## Independent review on combined v4 snapshot

Reviewer `/root/config_review`: **PASS** for the scoped path-integrity repair
`478a5f19df2fd4784ae33baf9d0334c55ac91fa0`, independently rechecked as an actual
dependency in combined snapshot `543e75efa91b6e64d915f847e9b07a30fa085329` with
parent-v4 source `3d743d490176ade83cf89af398e4be7f9409e5fe`. This is a source/
native guard review; full coordinator Ubuntu/POSIX CI remains a separate gate.

Read the complete five-line source change and 72 added test lines. The source
adds only the re import and lexical component rejection before safe_path and
metadata. Drive/absolute/traversal, root/ancestor reparse, containment, inventory,
copy and snapshot logic are otherwise unchanged. Normal internal spaces/dots,
Japanese names, tilde~name, x~1name and an empty relative root stay supported.
No ambiguous spelling is stripped into an accepted path. The short-name pattern
is a conservative source-path rule; actual 8.3 alias creation/enabling was not
tested or claimed. Colon rejection complements existing byte-ref ADS exclusions.

The strict read chain was independently verified in source:
G0ArtifactReader.read -> prospective_inputs._local_path -> imported
master_inventory.local_path -> bounded open. Configuration profile/cycle/code,
TRAIN/forecast graph and Stage1 payload reads use it; configuration membership
and Stage1 graph preflight also call local_path directly. Standalone legacy
training_corpus uses its own safe_path-based helper, but this reviewed strict
G0 TRAIN path first binds/reads its declared closure through the shared reader.
No claim of global authentication or unrelated legacy reader repair is made.

Canonical helper blob is `e6fe8403529e1740110d7130cb37e119aaed0964`, 5,533 bytes,
SHA-256 `1f108ce34e0f450cf4b438a912bb333df923fd50b0e6752760685c00df05db27`.
Test blob is `7b7ceb93cc01be67e1104432e6a1517d380c4cce`. Fresh combined native
`python -B -X utf8 -m unittest discover -s tests -p test_master_inventory.py -v`
using the bundled Python ran **26 methods: 22 PASS/four genuine platform skips,
4.810s**. This includes pre-metadata rejection, unchanged valid-name bytes and
native Windows junction protections. No fake fcntl or platform substitution.

The reviewer's existing eight native v4 alias cases ran on the actual combined
tree: **8/8 rejected**, forbidden payload opens/candidates/REPLAYs all zero.
The original top/nested source-config bypass therefore closes at the common
boundary, including before loader-specific target reads. A separate independent
**118 assertions** passed, re-executing 16 old first/reused parent calls and
comparing full dictionaries/literal physical REPLAY to the original eight-case
archive. All old byte/read-count oracles stayed exact; no expectations were
regenerated, skipped or inferred from new v4 code.

Details and external probe identities are recorded in the companion independent
source section of research_configured_stage1_parent_v2_20261025.md. This reviewer
edited only the two approved review sections. No product source/test, Raw/ORIGINAL,
state, cycle or authority change was made. No remaining finding in the approved
portable component rule was identified.
