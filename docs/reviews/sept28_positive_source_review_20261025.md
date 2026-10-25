# September 28 bounded positive-source review

Base: `6c2d889da5ca5a8bf54d5b78955a8bb1541d72a8`.
Branch: `codex/sept28-positive-source-review-20261025`.

## Contract and implementation plan

The scope is the five existing September 28 capture-event records and their six
existing individual-occurrence links. Their original owner log, structured raw
log, event/individual tables and actual GPX are compared without changing any of
those sources. An occurrence ID is not evidence of permanent biological identity.
The original midnight block explicitly says two animals. The other four capture
blocks are singular statements, corroborated by the existing owner-log quantities.

The chosen implementation is a small fixed-profile pure verifier called by the
existing source-declaration gate on every audit. A standalone test or a truthy
coordinate-method string alone cannot grant this profile an outcome role.
A general evidence parser or new learner would expand this bounded task; neither
is needed. The existing numeric coordinate and GPS consistency routines remain
unchanged.

Owned paths are the new verifier/test, this review, the September 28 review and
capsule receipt under `evidence/source_reviews`, two identical encoded copies of
the already-received PR43 ZIP under `incoming/source_capsules` and
`evidence/source_reviews/capsules`, and the narrow fixed-profile hook in
`src/evidence_audit.py`. A sole-CSV entry in
`policies/observation_evidence.json` is reserved until independent implementation
and actual-source review pass. No Raw, ORIGINAL, source table, model, state or
cycle file is owned.

- [x] Write failing actual-source and hostile cross-binding tests.
- [x] Verify ZIP/CRC/member identity and the 24-part original GPX, then compare
  five timestamp/count/species/coordinate selectors and six individual links.
- [x] Verify profile metadata and all source references at runtime through the
  caller's guarded reader, shared deadline/read/point budget and final rescan.
- [x] Demonstrate missing/unknown profiles, altered bindings, duplicate JSON,
  reparse paths and expired budgets cannot qualify the fixed CSV.
- [ ] Run targeted and related regressions and publish the exact source commit
  for independent review before registering any outcome role.

The incoming capsule preserves the complete already-received validation ZIP,
not a new owner statement. Its promoted copy is in the existing master inventory
and snapshot namespace. Both copies decode to the original ZIP SHA; all members'
CRC and the native TXT member SHA are checked. The receipt embeds the unchanged
original PR43 intake receipt and separates that historical receipt from the
actual current import/check time. Runtime reads never depend on `incoming/` or a
network fetch.

The result is current-source-reviewed capture consistency only. Availability is
at the current review/audit, never the September event date. This cohort is
RESEARCH_EXPOSED. It does not certify search, no-capture observations, complete
outcomes for any night/domain, measured effort, forecast features, confirmation,
model training, accuracy, Champion, official issuance or production authority.
One positive-only night remains insufficient for the existing training gate.

## Verification record

No outcome policy has been added at this implementation checkpoint. Registration
waits for exact-source independent review.

Existing PR30 (`af9b7e100a6d3a11683d6d5a262e97ccc683f03c`) is the prior owner-command
29 report-only change (21 report files), not this source/profile implementation.
Those reports remain unchanged. PR43 is a broad 55-file Draft data aggregation;
this slice reuses its exact already-received ZIP rather than merging that whole
data proposal or appending duplicate events under its different IDs.

The complete Git-native source snapshot was audited with a temporary, sole-CSV
positive declaration: `PARTIAL`, no failed checks, five qualified capture events,
six linked individual occurrences, five positive 100m x 10min units, zero
Negatives and `denominator_coverage=NOT_ESTABLISHED`. The 29 remaining requirements
are not waived. The run consumed 517 reads / 350,684,170 actual bytes of the
unchanged 536,870,912-byte cap and 289,727 points of the 1,000,000-point cap in
15.953 seconds. No real fit, feature qualification or science PASS follows.

The first full-snapshot probe used plain `git archive HEAD`; on this Windows
host that applies `core.autocrlf` and changed the snapshot representation. The
verifier correctly rejected those bytes. Repeating with
`git -c core.autocrlf=false archive HEAD` produced the native Git bytes and the
result above. No source was normalized or rewritten. The hermetic unit fixture
reads saved Git blobs into a separate temporary snapshot, including the new
capsule/receipt/review once committed; untracked new files are an explicit
development-only fallback. A runtime filesystem with different source bytes
continues to fail the pinned hash checks.

The preserved ZIP is 1,220,188 bytes, SHA256
`ee803478c0a1ec574591fc219fa585afad101539b5ddfaebae966e41c5b60aee`;
all 19 member CRCs pass. Its native TXT member is 96,493 bytes, SHA256
`f27a9e06cf89b06a68520365d29630d695d59a96810c95081cfbdb88652bd733`.
The existing GPX restores from 24/24 parts to 6,068,111 bytes, SHA256
`2e9fde7aa459fc100abf8014d95635e697a638679cc9df731f4e0f6a80fb62f3`.
Its 22,990 real points have no excluded point or segment break under the existing
QC routine; maximum consecutive interval is 24.401 seconds. All five selected
source points have acceptable HDOP and one-second neighboring intervals.
Coordinates come from the original TXT, with GPX corroboration; no interpolation
or GPX-derived animal count is used.

TDD observed the absent verifier, missing/unknown profile role grants, stat/read
growth escaping shared byte accounting, nested exponent overflow, typed proof
number substitution, final-rescan budget exhaustion and final-success-hash
deadline expiry. The last two now return `BLOCKED` with no public observation
units. All reads and rescans use the same audit reader, including actual bytes;
the previous uncharged final file-hash pass has been removed. Success sealing is
inside that same deadline, while the existing small blocked-result seal remains.
A legacy qualified synthetic audit is exactly equal to the base implementation,
including audit SHA `dccf02e5dc9349d42f967137ff65a3e28ddb36b216bcc87984e6392fcfd65ae0`.

The new target command is
`python -B -X utf8 -m unittest discover -s tests -p test_sept28_positive_source_review.py -v`:
21 tests, 20 pass and one POSIX-only symlink skip. The actual Windows junction
test runs at the CSV, review, capsule and root-ancestor boundaries and observes
zero external payload opens. Junction cleanup uses `os.rmdir` on the verified
fixture link itself before temporary-directory cleanup.

Related native regressions: `test_training_corpus.py` 52 tests (51 pass, one
platform skip); `test_master_inventory.py` 22 (18 pass, four platform skips).
`test_evidence_audit.py` runs 34 (31 pass, three environment errors), and
`test_learning_snapshot.py` runs 14 (11 pass, three environment errors).
All six errors are the existing Windows `ModuleNotFoundError: fcntl` in:

- `test_master_executes_audit_and_preserves_snapshot_inventory`
- `test_only_exact_osm_archive_is_inventoried_not_bridge_runtime`
- `test_zero_master_budget_never_invokes_auditor`
- `test_master_failed_audit_never_calls_model_adapter`
- `test_master_generated_workspace_is_recoverable_without_input_exemption`
- `test_master_passes_shared_budget_into_builder`

They are not reported as passes or hidden with a fake lock module. Full Linux
suite, source freeze, state and PR receipts belong to the coordinator.

## Independent review

Verdict: PASS for the narrow, current-review-time source-consistency registration
of the existing September 28 capture CSV. No blocking implementation finding
remains. This verdict covers implementation commit
`d2236deaa8447142b759411be1c4b9a4b2e8b172`, before any policy registration.
Its canonical Git-blob SHA-256 identities are:

| File | SHA-256 |
| --- | --- |
| `src/sept28_positive_source_review.py` | `109f39a68d7f5db10adf991d7cc6e512d4fe58edfcc050cd2219d7de737928e8` |
| `src/evidence_audit.py` | `4d8de850a18a79899f17baf33cbd8ab7d6caeb606550771d3a692cdfba97ccf3` |
| `tests/test_sept28_positive_source_review.py` | `20d31708aaa227f711a1c06d8782f45fa5a57a0a5d1940b6f0f2a2f57e401366` |

The reviewer independently recovered the PR43 ZIP from exact commit
`76680cba924b72a9069a4d12b0819cae95fd5349`: 1,220,188 decoded bytes, SHA-256
`ee803478c0a1ec574591fc219fa585afad101539b5ddfaebae966e41c5b60aee`.
All member CRCs pass. The original TXT member is 96,493 bytes with SHA-256
`f27a9e06cf89b06a68520365d29630d695d59a96810c95081cfbdb88652bd733`.
Selectors 7712, 7935, 8105, 8115 and 8125 bind the original event times and decimal
coordinates to the five existing CSV events and raw-log quantities 1/1/2/1/1.
The midnight TXT block explicitly records two animals; the four singleton
statements are corroborated by the structured original quantities. The six
existing individual-occurrence links agree, including both midnight links.

The 24 original GPX Git blobs reconstruct 6,068,111 bytes with SHA-256
`2e9fde7aa459fc100abf8014d95635e697a638679cc9df731f4e0f6a80fb62f3`:
22,990 real points, zero QC exclusions, zero segment breaks and a maximum gap of
24.401 seconds. The spatially selected points are approximately 21--55.999
seconds from the minute-resolution event times and 0.002--2.600 metres from the
original coordinates. These are actual points, without interpolation. Their
timestamps are not asserted to equal the event timestamps. Incoming and promoted
encoded capsule bytes were independently confirmed identical. Runtime reads use
the promoted evidence namespace and do not fetch the network or read incoming.

The external independent harness
`../sept28-independent-probes-20261025.py` (outside repository implementation
paths; SHA-256 `2a2067e4361b29952bce353d65d21924e536c56dceb9b193f6cd961bcaa6524b`)
passed 31/31 tests in a fresh process, 36.368 seconds. Tested source bytes match
the exact implementation commit above. The checks include:

- Missing, unknown, null and malformed profiles cannot fall back to legacy
  outcome-role metadata; duplicate and nonfinite JSON is rejected.
- Altered source bytes, re-signed reference metadata, selectors, quantities,
  coordinates, species and individual links cannot replace the fixed crosswalk.
  Canonical proof digests reject Python's otherwise equal bool/int or int/float
  substitutions. Device-authentication and authority claims remain constrained.
- All referenced filesystem reads and rescans share caller byte/read/point and
  deadline accounting. A stat-then-grow source reads at most remaining bytes plus
  one; expected sizes also bound reads. Expiry during point processing, final
  proof sealing and parent audit sealing returns no successful public units.
- Real Windows junctions at the initial CSV, review and capsule directories are
  rejected before any external payload opens. A junction installed after source
  verification is also rejected during the parent final rescan before external
  reads. Late source growth or exhausted final-rescan budget publishes no units.

An isolated native-byte parent audit independently returns PARTIAL with five
canonical events, six individual occurrences and five positive units; Negative
count is zero. Complete outcome and session scopes remain empty and denominator
coverage remains `NOT_ESTABLISHED`. The shared reader charges 29,279,289 actual
bytes and the two actual GPX parses charge 45,980 points for that fixture. A
later audit time moves qualification availability forward; historical
availability is not inferred from the event or original intake date.

The reviewer also independently executed the initial owned 20-test suite
(19 pass, one POSIX-only skip) and the subsequently added successful-seal expiry
regression (pass). The existing 34-test evidence-audit suite produced 31 passes
and the three already documented native Windows `fcntl` import errors, with no
assertion failures. The final test-fixture change only reads committed capsule,
receipt and review bytes from Git after commit; the verifier and audit source
hashes stayed identical. Linux orchestration still requires coordinator CI.

These results use independent temporary snapshots of the preserved Git blob
bytes. The Windows working checkout has existing automatic line-ending changes
(for example the capture CSV is 893 working bytes versus the preserved 887-byte
blob). No Raw file was rewritten to make a check pass, and those differing
working bytes are not certified by this review. Their runtime SHA rejection is
expected. The reviewed commit changes no Raw or existing processed source table.

The accepted scope is five preserved, retrospectively source-consistent positive
events and six individual occurrences, available only at the actual current
review/audit. The data remain `RESEARCH_EXPOSED`. This review does not authenticate
the recording device or owner identity, prove permanent animal identity, certify
active search or complete outcomes, authorize any Negative, establish forecast
feature availability, authorize model fitting, create confirmation evidence, or
validate science, Champion, official issuance or production. A single sole-CSV
outcome-role registration may follow this review; those other authorities remain
unavailable.
