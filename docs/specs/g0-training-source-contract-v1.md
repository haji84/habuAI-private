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
The same byte SHA cannot bypass that boundary by being copied to another path
and redeclared as a feature while also appearing as label or effort evidence.

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
The cumulative cached raw-source lineage memberships are capped at 1,000,000,
checked before each set expansion. Shared-parent fan-out cannot grow quadratic
lineage caches beyond this bound; excess is `CAPACITY_BLOCKED`, never a sampled
or partially successful corpus.

The `habu-g0-training-validity-v1` sidecar contains `corpus_sha256`,
`feature_definition_sha256` and `rows`. Every corpus row and registered feature
must have an explicit `valid_time={start,end}` covering its complete physical
600-second window, and `source_ids` matching the row's feature-source bindings.
Sidecar readiness includes corpus readiness. A night-valid boolean alone is
insufficient at this gate; physical-source declarations remain distinct from
proof that the underlying measurement was authentic.

## Private preparation and existing-artifact handoff

`scripts/habu_qualified_fit_cycle.py --prepare-only` is an additive, no-fit
preparation entrance. `prepare_source` retains research references and can copy
an **already supplied** existing v1 corpus/validity/source declaration and its
actually consumed source/code/policy bytes into an immutable private workspace.
It does not infer audited rows, biological ownership, event identities, features,
negative scopes or timestamps from a route/capture candidate.

Research references use the existing `{path,sha256,size_bytes}` shape. A CLI
reference-list file is a bare JSON array with a separate raw-byte SHA binding;
the list itself is also preserved and checked as a research-only input. This
does not expand any source namespace or role accepted by the strict G0 selector.

With a supplied G0 manifest, the unchanged selector runs on the original and
copied workspace using one `ProspectiveReadContext`. Their selection identities
must match. The two original selector receipts, including their different
actual-read byte counters, are kept unchanged in per-execution evidence.
`DECLARATION_PREPARED` means consistent declarations/bytes, **not** independent
source attestation or formal biological qualification. Preparation never fits,
even if the existing selector reports development training eligibility.

Without a real declaration, available research bytes are retained and the exact
existing `BLOCKED / MISSING_SOURCE_QUALIFIED_G0_MANIFEST` fit-report envelope is
saved separately. References are not appended to that downstream envelope.
Source/copy references, unavailable qualification and null total eligibility
remain in a distinct private preparation receipt. Research sidecars with
optimistic booleans cannot substitute for the existing strict declaration.

Limits are 256 unique paths, 64 MiB per file and 512 MiB unique input bytes;
repeated actual reads use the existing G0 2 GiB parent ledger. Default preparation
time is 30 seconds, explicitly configurable up to the existing 300-second cap.
Private roots, output separation, reparse/path aliases, duplicate JSON, byte SHA,
source/destination rescans and caller prior charges are checked. No allowance is
restarted in child validation or integrity reads. The CLI reports the final
actual-read total; stored execution evidence labels its earlier audit snapshot.

Semantic identity binds sorted path/hash/size references, declaration/feature/
selection identities, cutoff and exposed-night context. Same-input reruns do
not add observation weight, overwrite conflicting bytes or trust a prior marker
instead of rechecking inputs. Completion validation has its final cooperative
deadline guard while creation ownership is live; descriptor release performs no
more input work. A failed newly owned completion is rolled back where generation
ownership is provable. Existing/foreign generations are preserved. If an actual
OS close failure destroys ownership proof, the original error and an explicit
cleanup-residual note are retained rather than deleting unproven files. Such an
error returns no successful preparation; a record alone never grants authority.
This is cooperative validation, not OS-preemptible execution or an atomic
filesystem snapshot.

Copying byte-identical existing artifacts preserves their declared original
availability; it does not backdate newly derived corpus/feature artifacts. New
materialization must retain real four-readiness and parent maximum usability.
Missing historical as-issued inputs are not a permanent ban on future TRAIN:
genuine sources may be used only after their actual readiness and before the
future fit/evaluation boundary, with physical validity and all source gates met.

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
