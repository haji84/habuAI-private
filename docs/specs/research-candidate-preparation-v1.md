# Bounded diagnostic candidate preparation

`src/research_model_adapter.py:prepare_research_candidates` is a pure preparation
boundary for three fixed recipes: `uniform`, `HB-A0` and `HB-B1`. It does not
change historical M0--M3. Uniform uses the historical `(positives + 1) /
(observed units + 2)` formula on the same selected training rows.

The caller supplies the existing PR46 TRAIN_ONLY selection envelope, label-free
joined future rows, their canonical JSON digest, forecast cutoff and shared
remaining budget. Every supplied future row is validated before fitting any
candidate, including when training is insufficient. The adapter owns a JSON
copy, checks model/selection and prediction/universe hashes, and checks output
row identities against their original night, physical 100m cell and timezone
aware 10-minute window. The HB-A0 fit wrapper and the HB-B1 direct serialized
model are handled explicitly. Native diagnostic rank scores retain their meaning.

The shared model input boundary retains its existing limits: 20,000 training
rows, 120,000 forecast rows, 32 features and 16 MiB JSON per model input. JSON
encoding now stops at the byte cap instead of serializing the remaining input.
Forecast capacity overflow is an explicit `ResearchCapacityBlocked`, with no
sampling or truncation. A large strict G0 forecast-validation receipt does not
mean these models can compute on that complete domain. HB-B1 global and
conditional ranks cannot be obtained by simply concatenating independent chunks.

A complete successful return has status `DIAGNOSTIC_CANDIDATES_PREPARED` and a
canonical `receipt_sha256`. Valid insufficient training returns `NEED_MORE_DATA`
and no candidates. Malformed or inconsistent evidence raises `ValueError`.
`ResearchBudgetExhausted` releases no partial candidates, including when the
deadline expires during final receipt sealing. Each bounded pure model call is
checked before and after execution; this is a cooperative deadline, not an OS
preemption guarantee. The total request cannot exceed the existing 300 seconds.

These are **prepared diagnostics**, not a published immutable REPLAY or trusted
freeze. The API reads no files or held-out labels. It produces no metrics,
winner, promotion or formal 100m +/-10min target. Source authentication remains
`CALLER_DEPENDENCY_REQUIRED`; numerical consistency of a selector envelope is
not proof that its observations were genuine. Production and official issuance
authority remain false; scientific status is `NOT_VALIDATED`.

Integration prerequisites remain explicit: the strict G0 loader must validate
source roles, source/derivation closure, all four readiness times, feature
definition/deployment semantics, physical valid time and full declared domain;
the repaired source-bound selector must authenticate the accepted TRAIN-only
scope; and a separate frozen protocol must control independent evaluation.
Its strict feature-definition hash differs from the older feature-name digest.
Neither hash may silently replace the other in a caller receipt. Parent PDCA
dispatch before the legacy builder and immutable REPLAY publication are separate
integration work, not accomplished by this pure API alone.
