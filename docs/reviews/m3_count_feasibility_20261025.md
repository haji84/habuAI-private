# Independent M3 count feasibility review — 2026-10-25

**Verdict: PASS for the pure declaration-consistency slice.** No unresolved
blocking finding remains in the reviewed source. Coordinator integration,
source freeze and exact-head Ubuntu CI remain separate requirements.

## Exact identities

- Implementation commit: `aa76b087cb38dd35ddefb344b7b148737730e1ba`.
- Reconciled head: `0a64932474c8ff4337c8b99606aac43dc8735e82`.
- Independently compared all three owned Git blobs before/after the normal main
  merge: source, tests and specification are byte-identical.
- `src/models/count_feasibility.py` SHA-256:
  `d58d04456a49ba3538218a6f9e4bc27a8666a224f9acd44becb84fd9b066afb0`.

## Independent evidence

Fresh native Windows processes, using a new Git-archive snapshot of the exact
reconciled head, passed **52/52 external adversarial probes** and **31/31 count
unit tests** (no skips). Source/test compilation passed. The external harness is
outside worker-owned files, `m3-independent-probes-20261025.py`, and constructs
its own synthetic count/effort projections from the existing selector fixture.
It does not use the worker's new fixture. No real observation, source file,
sealed confirmation or fit was consumed by these probes.

The external positive control has three source-declared events containing six
explicit individuals and 1,800 measured active-search seconds. Same-observer
search intervals occupy disjoint halves of each 600-second window. It verifies
no file/network access or caller mutation, canonical assessment identity, no
returned fit rows/rate, and all authorization flags false.

The matrix includes complete zeros versus missing registration, explicit
count/hash contradictions alongside missing data, byte aliases, cumulative raw
lineage capacity, final-seal expiry and positive-only binary selections without
count-adequacy claims. Twenty direct-source and twenty RAW-ancestor probes alter
one readiness field at a time. For `source_received_at`, the selection's global
receipt time and all projection identities are rebound, so rejection proves the
causal lower bound rather than an incidental identity mismatch.

## Resolved findings and source reasoning

- Missing values no longer conceal a known unrelated orphan source.
- Adjacent complete-outcome intervals jointly cover measured search correctly.
- One observer cannot duplicate active time across cells, including UTC aliases;
  adjacent half-open intervals remain valid. No travel model is inferred.
- Individual-ledger evidence and every relevant ancestor obey each of the four
  causal readiness bounds. Reverse-topological maximum propagation applies the
  latest required event/scope end in O(nodes + edges), followed by per-stage
  checks; a late derived record cannot launder impossible earlier RAW evidence.
- Count remains the explicit individual ledger, never binary label/event count
  or a default one. Positive units also need complete outcomes and measured
  independent active-search scope. Missing input produces NEED_MORE_DATA with
  withheld aggregate counts/effort; known contradictions raise ValueError.

Combined JSON, graph, event/individual and cumulative raw-membership bounds are
explicit. Lineage insertion checks precede allocation, and the shared elapsed
check follows canonical final sealing. The API neither opens reference paths
nor authenticates declared source hashes, scope completeness or availability.

## Limits of this PASS

The target is only owner-captured Habu individuals during measured active search.
Results are DECLARED_CONSISTENCY_ONLY, source authenticity NOT_ATTESTED,
source authentication CALLER_DEPENDENCY_REQUIRED and statistical adequacy
NOT_ASSESSED. Event geolocation is not re-attested. Retrospective effort is not
an ex-ante predictor. Fit, scientific execution, official issuance and production
authorizations remain false. This adds no count fitter, fourth registered
candidate, parent dispatch, real-data eligibility or evidence of scientific
performance. This review does not claim an independently executed Linux suite.
