# Strict training source declarations

`select_g0_training_rows` is an additive conservative entrance to the existing
PR46 source-bound selector. It neither replaces the selector nor changes how
legacy rejected/UNKNOWN rows are classified. A corpus containing unused later
sources can still be useful to the legacy retrospective tools while this stricter
mode returns `G0TrainingInputBlocked`. A scoped corpus projection would be a new
artifact and hash, never an edit to an original source.

The `habu-g0-training-source-contract-v1` manifest has exact fields:
`schema_version`, `kind=TRAIN_ONLY_SOURCE_CLOSURE`, `corpus`, `policy`,
`row_validity`, `features`, `feature_definition_sha256`, `source_nodes`,
`readiness` and `usable_at`. The three artifact bindings each contain `ref`
(`path`, raw-byte `sha256`, `size_bytes`), all four readiness times and `usable_at`.
The policy remains the existing frozen G0 policy.

Each source node has exact `id`, `ref`, `source_role`, `source_kind`, `parents`,
`readiness` and `usable_at`. Source roles match the existing corpus manifest,
including independent search and complete-outcome scope receipts. RAW nodes have
no parents; DERIVED nodes preserve their actual declared parents. Scope receipt
parents must equal their byte-bound basis references. Node paths/SHA/roles and
received times must match the complete corpus source manifest; actual bytes and
sizes are read and checked. A feature derived from labels or effort requires a
separate typed lagged projection and is currently `CAPABILITY_BLOCKED`.

The public forecast `validate_readiness_graph`, `G0ArtifactReader` and
`ProspectiveReadContext` are reused. Every source and derived artifact must be
usable strictly before `min(fit cutoff, forecast cutoff, evaluated-night 07:00)`.
Usability equals the maximum of all four own readiness times and all parent
usability times; later parent audits are not discarded. The same absolute
deadline and actual byte ledger cover initial reads, selector reads, scope
receipts and all final rescans. No child replenishes either allowance.

Feature definitions reuse the forecast units/version/definition/code/deployment
binding, checked against the registered strict definition hash and available
before the training boundary. Required raw feature-source IDs must exist in
the actual closure. For each row and feature, raw feature leaves reachable from
its bound sources must exactly equal that registered set. The older digest of
feature *names* remains separately identified.

The `habu-g0-training-validity-v1` sidecar contains `corpus_sha256`,
`feature_definition_sha256` and `rows`. Every corpus row and registered feature
must have an explicit `valid_time={start,end}` covering its complete physical
600-second window, and `source_ids` matching the row's feature-source bindings.
Sidecar readiness includes corpus readiness. A night-valid boolean alone is
insufficient at this gate; physical-source declarations remain distinct from
proof that the underlying measurement was authentic.

All references, including feature code, are preflighted before bound payload
reads. Training sources use `data`, `evidence` or `features`; contract metadata
uses `protocols/development`; code uses `src/*.py` or `scripts/*.py` recursively.
Reserved `sealed`/`confirmation` path segments are rejected. The parent keeps
canonical sealed outcomes outside its source-inventory namespaces and must not
pretend that arbitrary user-labelled files inside source directories are sealed.

Success returns `{receipt,selection}` only after final rescans and a final
deadline check. The selector's output is preserved exactly. Source authentication
is `NOT_ATTESTED`, scientific fit authority and production authority remain false.
Byte consistency and caller declarations do not certify witnesses, genuine
search, biological absence or untouched confirmation. Real-data qualification,
independent evaluation and parent dispatch are separate obligations.
