# Native Task6a to private G0 materialization

This additive adapter reuses `evidence_audit.audit_evidence`, the existing
physical-unit key, the existing training corpus and strict G0 selector. It does
not introduce another source certificate, model, fitter or observation parser.
`prepare_source` remains the separate portable packaging operation.

## Interface

`scripts/materialize_private_g0_sources.py` exports:

```python
materialize_sources(source_root, private_output, *, night,
    feature_corpus_ref=None, strict_manifest_ref=None,
    heldout_night=None, fit_cutoff=None, forecast_cutoff=None,
    budget_seconds=300, _read_context=None)
```

The two optional references use the existing exact `{path, sha256, size_bytes}`
format. They refer to the existing v1 training corpus and strict TRAIN_ONLY
manifest components. They do not supply authenticated labels. Feature values,
source bindings and physical validity join by one exact100m/600s unit; duplicate
or missing physical joins fail. Caller labels, event IDs and quality are ignored.

The CLI has `--root`, `--output`, `--night`, `--budget-seconds`,
`--feature-corpus-ref`, `--strict-manifest-ref`, `--heldout-night`, `--fit-cutoff`
and `--forecast-cutoff`. Reference arguments are bounded JSON objects. stdout
contains fixed statuses/reasons and aggregate counts only. Output is private
and outside the input checkout; raw files and old artifacts are not overwritten.

## What is materialized

The adapter executes native Task6a at the current time and rechecks its actual
input bytes. Canonical source events are joined to native units with their
original IDs, recorded quantities and inherited identity links. No biological
identity, exact emergence time or measurement precision is invented.

An owner-Habu capture projection requires byte-bound actual record columns for
owner/species, OBSERVED_AT semantics and known time/position uncertainty that
fits one physical unit. Missing declarations, conflicting aliases, other species
and uncertainty spanning units remain UNKNOWN. These consistency checks do not
authenticate the source declarations or certify biological truth.

A sample-based Task6a label0 is insufficient. Existing typed active-search and
complete-owner-outcome receipts must pass the existing scope verifier for the
whole600s, and their raw source ancestry must be disjoint. Positive preservation
does not require those Negative-only receipts.

When components are absent, native audit and diagnostic observations are saved
with BLOCKED reasons and no strict manifest reference. With complete existing
components, a new corpus/validity/manifest is bound to real new materialization
times and checked by the unchanged G0 selector. Original readiness must be valid
before rebinding; it is never repaired or backdated to pass an old forecast fold.
Retrospective observations may train a later future model under that model's
target contract, but do not reconstruct historical forecast availability.

The returned `private_workspace`, `manifest_ref`, feature-definition hash and
`research_refs` can be passed to `prepare_source`. Research refs retain the native
audit and diagnostic observations; they confer no new source role or authority.
One optional native ProspectiveReadContext spans both operations. The final
ledger includes completion-time checks; neither operation replenishes its parent.

Every source, copied dependency and generated output is checked through the final
completion fence. A failed final check revokes only this invocation's newly
created completion receipt. Foreign replacements and previous artifacts remain.
These are bounded consistency checks, not an authenticated atomic filesystem.

## Verification checkpoint

The implementation ran28 synthetic tests, including a real native Task6a -> G0
-> prepare_source integration with one parent budget. Independent review added24
cases. Initial HOLD findings for late output mutation, comma fractional-time
truncation and foreign budget callbacks were reproduced and repaired. The failed
receipts remain preserved privately. Repair review SHA256:
`7d609dcd2d2ab54db58749dd3f8d627c08679dcc503604048c49fdb8015ac433`.

Related native suites ran209 selected tests:206PASS/3symlink SKIP/0fail/error.
Three existing master tests requiring POSIX fcntl were explicitly outside this
Windows selection, unchanged from the baseline; the final Linux suite must run
them. Related-run receipt SHA256:
`992aedbb6ccf1220f1f97f099eba252d494766690956977b3b5a4202beb638b6`.

An actual snapshot-wide native audit requested for2026-10-22 ran24.407s with
825,193,848 actual read bytes, including105,168,893 bytes of independently
recomputed post-completion checks. It preserved17source events, recorded quantity18
and18 inherited declared identity links; these are not certified biological IDs.
All1,140 diagnostic units remained UNKNOWN:1,123 nonnegative unknowns and17 with
unestablished role/precision. All236 native input hashes and the466-file input
inventory remained unchanged. This is a bounded snapshot result, not a global
historical training denominator or another cohort to add to October counts.

Actual-data status is BLOCKED for FEATURE_CORPUS_NOT_SUPPLIED and
STRICT_G0_COMPONENTS_NOT_SUPPLIED. Selector/fitter were not run on those real
inputs. New real fits/models/Negative rows0; eligible total null; scientific
metrics NOT_EVALUATED; formal P0 and real-field E2E not established. Actual-data
independent receipt SHA256:
`9184126d2a4aa28bb33a33dfb877a9a0dc6ee716be3e19877f0a59bb2cf69dcd`.

This is a dated prepublication software/data checkpoint. Final exact-head CI,
approved main integration and remaining gates are recorded in the existing
[Master verification record](https://github.com/haji84/AI-/issues/1642#issuecomment-6618423329)
and [Issue86](https://github.com/haji84/habuAI-private/issues/86). A new source HEAD
does not inherit9d494c6's earlier CI. No private GPS, locations, logs, model or
operational payload is added to public Git; production/Champion remains gated.
