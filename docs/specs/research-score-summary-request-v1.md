# No-fit score-summary diagnostic request v1

This opt-in frontend calls the existing Stage1 summary-v2 diagnostic once. It does not connect master, PDCA or backend request dispatch, register A2, issue native predictions, authenticate a locked protocol or grant official P0/production permission. Implementation base is accepted main `f2d50506803f7f41e38bcb58cba5e934ec30d10f`; its 143 gates are historical dependency evidence, not this module's own CI.

## Public helper and physical request

`research_score_summary_request.evaluate_research_score_summary_request(root, night, *, context)` returns exactly the owned, bounded four fields `request_ref`, `request_canonical_sha256`, `request`, `child`. It is a nonpublication value. `child` is the complete original `habu-stage1-summary-source-result-v2`, including its original children, field order, hashes and phase counters. No caller-supplied prepared child, output path, adapter callback or version fallback is accepted.

Read only `config/research-score-summary-request.json`, at most 65,536 original UTF-8 bytes. Its exact eight fields are:

`schema_version`, `mode`, `operational_night`, `forecast_as_of`, `feature_definition_sha256`, `candidate_config_sha256`, `summary_manifest`, `stage1_manifest`.

The tag is `habu-research-score-summary-request-v1`; mode is `DEVELOPMENT_ONLY`; night must equal the explicit call's validated operational night. The forecast timestamp must be aware. Both hashes are lower-case SHA256. Both refs have exact `{path, sha256, size_bytes}` fields and mandatory positive original sizes. Summary refs keep existing Source2 config/development namespaces, and Stage1 refs keep existing observation namespaces. Portable aliases, reserved/reveal paths, reparse ancestors and path traversal remain rejected by existing guards. No inline outcome/TRAIN/confirmation arrays, native prediction hashes, cached children or `expected_protocol` fiction is admitted.

Capture entry bytes before the first real check. Validate the existing actual `ProspectiveReadContext` without replacing it or changing its check, absolute deadline, max bytes or ledger. Require positive remaining deadline at most 300 seconds and cumulative allowance at most 2GiB. Physically read and charge the request before calling the child. Reject excessive decoder depth before decoding; reject duplicate keys, nonfinite constants and invalid exact types/schema before an additional owned copy. Canonical hashing and original physical byte hashing are separate identities.

Call `evaluate_stage1_summary_sources_v2` exactly once with the two refs, aware timestamp and expected hashes. Its two genuine Source2 loads, full-domain summary and pure Stage1 rules remain unchanged. Reuse the fixed uniform/HB-A1/HB-A2 set and all original caps. The API invokes no selector/preparer/fitter/backend. Source2 valid-late remains its own closure barrier, G0 ordinary late remains ValueError, and whole NMD remains an empty whole-set disposition without outcome fallback. Do not change original sealed child fields to reconcile later read charges.

## CLI publication boundary

`python src/research_score_summary_request.py --root ROOT --night YYYY-MM-DD` creates one 300-second/2GiB context. It builds exactly one new `habu-research-score-summary-command-v1` receipt with these 19 fields:

`schema_version`, `purpose`, `status`, `operational_night`, `request_ref`, `request_canonical_sha256`, `child`, `child_receipt_sha256`, `entry_initial_read_bytes`, `child_entry_read_bytes`, `child_return_read_bytes`, `final_read_bytes`, `command_read_bytes`, `phase_read_ledger`, `source_authentication`, `scientific_status`, `authorities`, `limitations`, `receipt_sha256`.

Purpose is `DEVELOPMENT_DIAGNOSTIC_ONLY`; status is the unchanged child's status. Source authentication is `NOT_ATTESTED`, science is `NOT_VALIDATED`, and all nine existing summary authorities are false. Receipt SHA256 hashes the complete canonical body excluding only its own digest field. The serialized output preserves original nested child insertion order; canonical digest ordering is not a child rewrite.

`entry_initial_read_bytes` is before the first command check. Child-entry and child-return counters are the child's original sealed entry/actual counters. Final bytes are the actual command ledger after final union reads; command bytes are final minus entry. The exact three-field phase ledger is `request_and_admission_bytes = child_entry - entry`, `child_execution_bytes = child_return - child_entry`, `after_child_bytes = final - child_return`. These are disjoint and sum to command bytes. Any genuine callback/outer read after child return belongs only to the new outer phase, even if the helper has not returned yet. Child counters/hashes remain intact.

Recheck the request and the union of actual first Source2, producer and available Stage1 consumed refs under the same context, preserving every original size/hash. A ref declared in the request alone is not admission: whole producer NMD must not open an unconsumed Stage1 manifest. An actually admitted summary or Stage1 manifest remains in the consumed closure and must be rescanned. Reject conflicting bindings. Require full declared code membership before and after the scan. These are real reads, not a fake receipt overlay or second API pass. Full sealed wrapper bounds include the complete child, request identity duplicates, phase fields and own SHA: 16MiB UTF-8, two million nodes, depth12. Other inherited 4M-unit/10k-area/30k-state and Source2 phase limits stay unchanged.

Fully buffer bounded UTF-8 before publication; perform the last real check before exact final-ledger equality. Any later charged read or expiry rejects success. Emit the validated buffer through one stdout write, with no retry. A short write is an error. Sink failure/process termination can leave partial physical output; stdout and cooperative filesystem rechecks are not an atomic transaction or hostile filesystem confinement. No successful JSON is published on a prepublication validation failure.

FIRST actual caller exceptions, including falsey BaseExceptions and read/account/CSV/hash/seal origins, remain the original instance. Only explicitly named locally owned pure JSON capacity sites are normalized. No broad wrapping of Source2/reader/producer exceptions is allowed.

## Verification and scope

Seal selected genuine old complete outputs/read-open-check traces under fixed declarations before edits. Preserve old broad 3270/33/425/parent REPLAY histories without relabeling them as fresh runs. A new member changes native membership from105 to106; separately generated synthetic fixtures must bind actual new code and label their extra synthetic members. Reuse genuine frozen synthetic model bodies; no refit or child editing to manufacture readiness. Required tests cover exact request rejection, one child/two Source2 loads, original children/outside-U count2, prior and producer-entry/post-child1B charges, source-late poison, G0 late, NMD, original exception identity, final request/code/target/member drift, full sealed caps, deadline/ledger preservation and one-write stdout behavior.

Only the new module, focused test file, this versioned spec and author review are worker-owned. Old runtime/default tests/registry/parent/backend/schema/policy/Raw/requirements/workflows/STATE/cycle remain untouched. Root separately owns106 freeze, independent review and exact/fresh/main acceptance. Scientific real TRAIN/fit remains0; source/stream/P2/child/command identities are distinct and confer no issuer, prereveal, biological, calibration or production authority.
