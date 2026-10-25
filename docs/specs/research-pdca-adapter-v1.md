# Explicit research model dispatch

An explicitly supplied `config/research-model-request.json` opts the parent into
the strict development path. The parent dispatches before the legacy learning
builder, and `model_evaluation.evaluate_models` dispatches before legacy mixed
snapshot validation. An invalid explicit request never falls back to that path.
No request using invented or uncertified real training rows is installed here.

The exact request fields are `schema_version=habu-research-model-request-v1`,
`mode=DEVELOPMENT_ONLY`, `operational_night`, `fit_cutoff`, `forecast_cutoff`,
`forecast_as_of`, `feature_definition_sha256`, `training_manifest`,
`forecast_manifest`, and `exposed_nights`. Both manifest refs have exact `path`,
raw-byte `sha256`, and `size_bytes`. The training manifest is the strict
`protocols/development/` source-closure contract. The forecast manifest is the
strict G0 full-domain contract. The same registered strict feature definition
must bind both; a digest of names alone is insufficient. The request cutoff
must equal the validated forecast cutoff and follow the fit cutoff.

One `ProspectiveReadContext` covers the request, both strict gates, selector,
all actual source reads, and final rescans. The existing 300-second parent,
three-candidate/two-round, 2 GiB read, and complete 120,000-row/16 MiB model
collection limits remain. Preparation receives only the remaining time. The
implementation uses cooperative checks, not OS preemption. Candidate output
is never released in parts and domain rows are never truncated or split into
independently ranked chunks.

The fixed recipes are uniform, HB-A0 area shrinkage and HB-B1 hierarchy. Every
candidate sees the same selector result and complete joined forecast digest.
After preparing all three, the adapter rechecks every training and forecast
source, plus the request. This catches training-source changes during later
forecast loading or fitting, which separate per-gate scans would miss.

One complete content-addressed artifact is published under
`predictions/replay/<night>/research/<content-sha>.json` with a temporary file,
fsync and exclusive hard link. It binds both gate receipts and the prepared
models/predictions. Existing content must match exactly. Complete REPLAY is
capped at 64 MiB; publication never overwrites a prior artifact. Interruption
can leave a complete untrusted artifact, never a partially written public file.
This local development REPLAY is not an official issuance or trusted seal.

Only computational `candidate_generation` can pass. Model evaluation and
feature research remain `NOT_VALIDATED`; candidate validation remains blocked,
the decision is `NEED_MORE_DATA`, and no winner or accuracy is fabricated.
Missing inputs, insufficient classes or strict capability gaps block;
malformed/hash-mismatched/leaking input fails and rejects the candidate.
Runtime/capacity exhaustion blocks without a partial returned candidate set.
Unexpected growth beyond an exact declared byte size also trips the bounded
transport's capacity block; same-size content/hash changes fail. Neither case
releases candidates. Excessively nested JSON parser errors normalize to FAIL.

No confirmation ledger is read. Canonical sealed confirmation belongs in
`sealed/confirmation/` outside the parent's source-inventory namespaces. Both
strict training refs and nested forecast source/code refs reject reserved
`sealed`/`confirmation` path segments before payload reads. Files placed in
ordinary source directories are inventoried; arbitrary names cannot turn them
into untouched sealed evidence. No independent confirmation, model selection,
formal 100m +/-10 minute issuance or production activation is authorized.

Tests use synthetic byte-bound training/forecast declarations to execute the
actual file loaders, model APIs and immutable writer. Ubuntu also executes the
actual POSIX-locked parent snapshot path, with the legacy builder forbidden.
These tests are software evidence only. Certified real training rows remain
zero until actual source qualification and observation evidence are supplied.
