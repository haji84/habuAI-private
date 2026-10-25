# Official P0 readiness gate (read-only, fail-closed)

Status: implemented **preflight only**, not production issuance.

The operative contract remains [official-prediction-request-execution.md](official-prediction-request-execution.md), [prediction-freeze-versioning.md](prediction-freeze-versioning.md) and Issue #1642 in haji84/AI-. Day boundary is 07:00 Asia/Tokyo. Formal scoring is 100m ±10 minutes; initial Stage1 gate is 1km Top10 Recall ≥90%.

## What is implemented

`python scripts/check_p0_readiness.py --night YYYY-MM-DD --planned-start YYYY-MM-DDTHH:MM:SS+09:00`

- Read-only assessment. Prints a machine-readable JSON result with `status=BLOCKED`, blockers and whether a P0 directory already exists.
- Rejects naive clocks; identifies wrong operational night, after-start and historical-night attempts, and preexisting P0. **Never creates, overwrites, backdates or relabels ORIGINAL P0.**
- Binds a specific source fact: `champion_registry.SCOPE=SANDBOX_MECHANICS` and `AUTHORITY_BLOCKER` currently prevent trustworthy production issuance. Merely finding a model JSON or replay is not authority.
- Without certified ex-ante forecast-universe, environmental/terrain/road feature snapshot, formal inference and A/B/C route outputs, the checker remains BLOCKED. Does not invent them, and does not treat a narrative ChatGPT estimate as original prediction.
- The checker is not a substitute for evaluating exact input hashes, source availability/cutoff, Champion binding or final frozen SHA. Those validations must be provided by the genuine reviewed production path.

## Acceptance criteria before replacing the blocked gate

1. Production issuer and activation governance pass independent reproduction, exact-head CI, review, and durable release attestation. No sandbox context or JSON flag bypass.
2. The chosen night has verified ex-ante 1km→500m→250m→100m road-zone universe, 100m×10min targets, weather, moon, terrain/wind, routing and source availability timestamps/hashes. Unsupported families are explicit blockers or NOT_PRODUCED under a reviewed capability policy.
3. Issuance happens **before actual exploration starts**, for that operational night, from the trusted inference output; atomic P0 publication is SHA-bound and append-only. Reissues must fail if P0 exists.
4. Post-exploration PDCA imports actual capture, roadkill and sightings separately, checks GPX path/clock quality, and compares only against preexisting frozen P0. Negative requires evidenced passage. Missing evidence causes BLOCKED/PARTIAL and cannot count as formal success.
5. 1km Top10 recall and 100m±10min are calculated on valid denominators with full outside-universe misses, walk-forward gates and Champion promotion requirements. No fabricated metrics.

## 2026-10-22 retrospective observation

The actual October 22 exploration was audited post hoc. Its ORIGINAL P0 was missing; its observation report and the durable blocked execution remain separate evidence. **Do not backfill P0** for this night. All future P0 must be generated before its own search start, with genuine predictor authority.
