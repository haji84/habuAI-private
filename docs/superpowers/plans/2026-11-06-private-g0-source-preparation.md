# Private G0 source preparation implementation plan

> **For agentic workers:** Use superpowers:executing-plans with TDD. Root owns implementation, STATE, Freeze, PR155 and integration; E owns private source packaging; C independently reviews; V checks integration and deployment effects.

**Goal:** Connect retained research evidence and independently supplied existing G0 source artifacts to a portable private input workspace and reproducible, no-fit handoff.

**Architecture:** Extend `scripts/habu_qualified_fit_cycle.py` additively. A preparation mode copies byte-bound existing inputs, checks a supplied existing v1 G0 declaration with the existing selector, and persists diagnostics. It never invents an audited corpus, labels, source timestamps, feature values or biological attestations from a research route. Without a real qualified declaration it preserves research evidence and an exact existing BLOCKED fit report.

**Tech stack:** Existing Python standard library, `ProspectiveReadContext`, private-path guards, G0 selector and immutable artifact conventions. No new dependencies or model.

**Spec:** `docs/specs/g0-training-source-contract-v1.md`; `docs/reviews/habu-auto-qualified-fit-20261104.md`; owner GPS/capture reconstruction instructions.

## Global constraints

- Base PR155 HEAD is `9d494c66c5fa866114d7a407024bbaf2f51b6940`; current main is `9ad62594bb0199a246c9a4959056579df4f9a6cc`.
- Original bytes, historic M0–M3, research models and capture tallies remain immutable.
- UNKNOWN, GPX passage, SEARCH_INFERRED, pauses and missing capture logs do not generate Negative rows.
- Positive source evidence is separate from independently proved full-window Negative search/outcome scopes.
- Preserve existing v1 corpus, validity, feature-definition and G0 declaration formats. Preparation does not grant source authentication, scientific fit, P0, production or Champion authority.
- No row-normalizer or certifier is invented for the unseen latest 154-event payload. Existing reviewed corpus artifacts must actually exist before their declaration can be prepared.
- Current inputs lack an audited corpus, complete scoped proof, feature validity/readiness and some original handles. Actual-data operation must stay BLOCKED with total eligibility null and new real fit/model/Negative counts zero.
- One caller deadline and actual-read ledger cover input references, selector, copying, integrity reads and final original/destination rescans. No nested replenishment.
- Bound unique input bytes separately (512 MiB, 256 files, 64 MiB/file); repeated reads/copies use the existing G0 2 GiB actual-read cap. The retained 29-file research input is approximately 306.5 MB before repeated reads.
- Inputs/output are private non-Git locations; output is outside and not an ancestor of the source workspace. Console output contains only fixed statuses and aggregate counts.
- Reuse existing PR155. Merge only reviewed exact final HEAD. Main integration is authorized; production publication, permissions, billing and Champion are not. Use the separately reviewed Cloudflare-only merge skip instruction while retaining main CI.

## Review focus

- Content-addressed preparation must not double-count a rerun or overwrite conflicting files.
- Raw research artifacts are not accepted as a G0 declaration even if they contain optimistic booleans.
- Complete declaration checks remain those of the existing strict selector; copying never upgrades `NOT_ATTESTED` into verified source truth.
- Late source changes, failed final checks and capacity exhaustion must not return a prepared/qualified result.
- Existing fit-report exact fields and normal qualified-fit CLI behavior remain unchanged.

## Files and interface

Root implementation AllowedPaths:

- `scripts/habu_qualified_fit_cycle.py`
- `tests/test_habu_qualified_fit_cycle.py`
- `docs/specs/g0-training-source-contract-v1.md`
- `docs/reviews/habu-auto-qualified-fit-20261104.md`
- this plan

Shared STATE/Freeze and a privacy-safe aggregate checkpoint are coordinator-only final integration changes.

Add `prepare_source(root, output, *, heldout_night, fit_cutoff, forecast_cutoff, research_refs=(), manifest_path=None, manifest_sha256=None, feature_sha256=None, exposed_nights=(), budget_seconds=30, _read_context=None)`.

- `research_refs` uses existing `{path, sha256, size_bytes}` identities, private relative paths only. It identifies research artifacts/original copies; it never supplies labels or creates a corpus.
- A non-null manifest is the existing strict G0 declaration, with real source files/corpus/validity/code/policy available under `root`. Validate it with the existing selector; copy the actually consumed existing artifact bytes into an immutable private workspace; validate the destination and originals again with the same read context.
- Missing declaration: preserve the research refs/artifacts and persist the unchanged report returned by existing `run_cycle(..., manifest_path=None, ...)`. No fitter/selector/candidate is invoked in that branch.
- Valid declaration: report only declared selector status/counts/selection identity, never source truth or scientific qualification. Preparation never fits, even if the declaration is development-training eligible. The original qualified-fit mode remains the separate existing way to request a gated development fit.
- Persist a stable semantic preparation receipt and, separately, per-execution byte/deadline evidence. Same input/context preserves byte-identical prepared artifacts and semantic identity. Do not add references to the exact fit-report envelope.
- Stable semantic identity contains the manifest/corpus/feature/selection identities, sorted copied path/hash/size references and cutoff/exposure context. Source and destination selector receipts are preserved unchanged in per-execution evidence; their actual-read ledgers and receipt hashes are not forced to match or mixed into semantic identity.
- Preflight the finite union of research references and actually consumed declaration/source/code/policy references before writing. Reject same-path SHA/size conflicts and file/directory prefix collisions. Bind missing sizes by verified actual reads, not a guessed mapping.
- Publish a completed semantic receipt only after destination validation and final rescans of both sides. Incomplete private staging files have no completed receipt and cannot be reused as success.
- This slice prepares existing independently supplied v1 artifacts; it does not implement a speculative research-to-qualified-row converter for unseen original formats or missing source attestations.

CLI adds explicit `--prepare-only`, `--research-sources-path` and `--research-sources-sha256`. The research-sources file is only a bounded JSON array of the existing reference objects, not a new public data schema. Existing CLI invocation/default behavior remains unchanged. The CLI reuses one read context for reading this list and preparing inputs.

## Task 1 — preparation and genuine existing-format delegation

- [ ] Write RED controls: missing declaration preserves research bytes plus exact BLOCKED report; genuine existing-format fixture calls actual strict selector, produces a portable checked workspace, never calls fitter; rerun preserves artifacts/identity.
- [ ] Run RED and confirm the missing preparation API is the failure.
- [ ] Implement the smallest preparation path and shared-context immutable writer support, preserving existing fit behavior.
- [ ] Run GREEN and original source/fit regressions.

## Task 2 — hostile controls and private CLI

- [ ] Pin original/output tamper, duplicate refs/JSON, unsafe/reparse path, output overlap/Git, depleted/prior-charged budget, late/equal readiness, invalid feature closure/validity, duplicate units/events and final-rescan failure.
- [ ] Verify research capture/effort artifacts (including mixed species/owner and uncertain clocks) cannot act as a G0 declaration or mint formal rows.
- [ ] Add and test CLI preparation without exposing paths, identities or coordinates; preserve old CLI behavior.
- [ ] Document private invocation and declaration-versus-authenticity limitations.

## Task 3 — actual evidence and existing PR/main

- [ ] E packages existing seven-night originals/research references only, with incoming SHA/size/source metadata. Reuse existing reconstruction; do not parse/recompute GPX, fabricate labels or overwrite models.
- [ ] Run real-data preparation twice. Verify original SHA preservation, stable artifacts/identity, exact BLOCKED fit report, no candidate/model, and explicit unresolved proof/feature/handle conditions. Separate this from synthetic passing cases.
- [ ] Independent review; repair; commit; append aggregate evidence/STATE and a new frozen runtime checkpoint when needed; push the existing PR155 branch without force.
- [ ] Confirm final exact-head full/dashboard/handoff CI and SHA bindings. Make PR reviewable/ready and merge only the verified head with expected-head protection and the reviewed Cloudflare-only skip title. No production deployment.
- [ ] Confirm actual merged main SHA, fresh main CI and unchanged canonical Pages deployment. Record commits/runs/evidence/remaining G0 requirements in Issue86 and shared state. Do not claim Master Goal/science complete.
