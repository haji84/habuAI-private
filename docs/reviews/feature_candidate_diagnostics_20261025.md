# Independent review: development calibration diagnostics

Implementation source: `b80bc751d728e6b0a3e9f7f81536368dac46278d` on
main base `6c2d889da5ca5a8bf54d5b78955a8bb1541d72a8`.
Runtime Git-blob SHA-256:
`adfadb2140990113413ae5bca27d2b54543a75557557de06e08c1ced9c0aaa05`.

The coordinator reviewed the implementation independently of the feature worker.
The bounded contract was approved before implementation. The worker first
observed the missing-module RED test, and repaired a separately reproduced UTC
timestamp overflow into a rejected contract value.

## Verified behavior

- Exactly one probability is required for every accepted source-selected observed
  unit, with matching physical cell, normalized window, declared fold/model and
  training identity. Missing/extra/duplicate units cannot improve a subset score.
- Fixed bins cover [0,1] once, internal endpoints belong to the right bin, and
  empty bins remain null. Brier uses the original probability; log-loss uses only
  the protocol's fixed clipping rule. Equal-night and pooled-unit summaries have
  separate fields. Single-class observations remain descriptive, never adequate.
- Declared training nights and cutoff precede the evaluated operational night.
  This verifies supplied declarations; actual model/source/readiness and genuine
  pre-reveal freezing are explicit caller dependencies, not SHA-based authority.
- Combined JSON is bounded before the owned copy. Callbacks/deadline checks cover
  new loops and encoding through the final seal and return. Existing selector
  validation and JSON parsing are bounded cooperative boundaries, not preemption.
- The result is structurally a diagnostic, has no learner/candidate payload,
  performs no I/O, fit, recalibration or ranking, and grants no selection,
  scientific, official or production authority. Existing three candidates and
  numerical learners are unchanged. Historical M0-M3 are unchanged.

The coordinator reran all 22 new tests successfully. A separate in-memory probe
used seed 1642 for 40 sets of random probabilities and fixed bin edges, comparing
bin counts/means, observed fractions, pooled Brier and the final content digest
against an independent direct calculation. Two additional all-zero/all-one
probability cases verified finite clipped log-loss and complete coverage:
**42 independent probes PASS**. No real observations or confirmation bytes were
read. The worker's related 22+26+31 tests passed (79 total).

## Decision and limits

PASS for the additive pure development diagnostic source. Exact-head Linux full
CI, immutable current-cycle verification and fresh-main CI remain integration
conditions and are recorded with the actual head/run in Issue #86.

Legacy evaluation already has descriptive fixed five-bin calibration; its fields
and numerical behavior are unchanged. This slice adds the stricter content/fold/
coverage/budget contract, configurable fixed bins and log-loss. It does not close
the missing HB-A1 common adapter, actual TRAIN-only retrained ablation, parent
dispatch or independent calibration/confirmation acceptance. Real fits remain
0 rows/0 nights. Stage1 and formal 100m +/-10min remain NOT_VALIDATED.
