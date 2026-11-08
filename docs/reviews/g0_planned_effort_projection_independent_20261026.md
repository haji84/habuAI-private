# Independent planned-effort projection review

Disposition: **PASS for exact software source**
`454d4b2cbfefdad8606e1bc1dae12777b007a732`. Native module SHA256 is
`ff678e7205d55e9343fdd57a387ede9a5c288b76a75b8eba10a82d63a5fe1006`.
This review did not edit runtime, tests, spec, policy, STATE, cycle or data.
Only this independent record is committed after document/index release.

## Reproduced findings and repairs

Native Git source from the earlier exact
`e7193c1dab1a07a6986eb0d28c541eaf8f1e617f` was loaded separately, with unchanged
shared dependencies. Its module SHA256 was
`56c8511dfcc1017c69d409e41021adf52784ead1f3e6fc270ad192d6086aae49`.
The same external fixtures establish these old failures and new corrections:

- Four portable aliases, including `data/ORIGINAL./plan.json` and
  `data/confirmation /plan.json`, were accepted by the old source. The repaired
  source rejects them before projection. Safe Unicode/internal spaces and
  non-alias tilde names remain accepted. No real 8.3 alias is claimed.
- Two extreme-year fixtures leaked `OverflowError` in the old source and now
  raise `ValueError`. The new normalization surrounds only local datetime
  calculations; caller callback exceptions retain their exact objects.
- A coherent prior-night issue/cutoff was rejected by the old extra same-night
  restriction. The repaired source accepts it, while retaining strict readiness,
  `cutoff <= as_of < horizon start`, and horizon-only 07:00 night bounds. The
  coordinator explicitly approved this interpretation of the original contract.

The earlier native authored suite was independently run at e719:33/33 PASS in
0.270s, despite the above external counterexamples. That result is not relabeled
as final-source approval. Four unaffected complete canonical receipts—complete,
UNKNOWN, missing raw bytes and explicit complete zero—are byte-identical between
native e719 and454 source in the independent harness.

## Actual execution evidence

Commands used the bundled native Windows Python with `-B -X utf8`.

| Scope | Fresh result |
| --- | --- |
| Independent external harness |16/16 PASS,0 errors/skips; unittest0.348s, outer monotonic0.344s|
| Independent seed1907 randomized plans, included above |50 complete plans match an independent one-second tick oracle|
| New authored projection suite plus count-feasibility, Poisson and existing G0 planned-kind block |97/97 PASS,0 errors/skips; unittest1.041s, outer monotonic1.047s|
| In-memory compile of both new Python files; diff check; final identity/clean check |PASS|

The hand oracle checks nine full product rows with planned seconds
`[480,120,0,0,480,300,0,0,0]`, total1380. Random plans include shuffled/gapped
allocations and timezone-equivalent timestamps. Other controls cover every
readiness role/stage at cutoff, issue causality, 07:00/next-07:00 endpoints,
overlap across cells, duplicate IDs, unsupported crew, known contradictions
before missing/UNKNOWN returns, source physical hash versus domain canonical
hash, and preserved caller-owned inputs.

Resource controls exercise raw-token/depth rejection before decoding, huge
negative integer rejection before abs/encoding, pre-copy JSON limits, row cap
before table construction, and exact sealed-output length versus one byte less
for all four result states. Terminal callback and actual deadline expiry after
sealed encoding return no result. Early/middle/late TypeError, KeyError,
OverflowError and FileNotFoundError callback sentinels retain identity.

The actual read ledger stays at its precharged17 bytes and retains its original
deadline/limit. A native Python audit observer records no announced file open,
directory listing, socket or subprocess event during projection. This is a pure
API, not a test of an external loader or hostile concurrent filesystem access.

Private artifacts remain outside Git under the repository's `.worktrees` parent:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `planned-effort-independent-probes-20261026.py` |22718|`bd19bdccc2a2e3639fc4610c69cca2771f4f2c61a173ddf6a79de3b9641b9a6f`|
| `planned-effort-independent-receipt-20261026.json` |4225|`4cf2d17c3092cf42744195149773ab38eb2b7102e4594d3a5098d83ef026ce08`|
| `planned-effort-independent-owned-regression-20261026.json` |19085|`64eb24c128ecddcf270086f6dea7220459c6c5cf7c2e5d374d5e018ebfb0b39b`|

## Limits and integration gates

All inputs here are synthetic software fixtures, not an actual owner's plan.
Only supplied raw plan bytes/size/SHA and domain canonical content are checked.
Domain/code physical bytes, source issuer, latest revision, historical
availability and authentication remain unverified caller dependencies. A complete
zero table means declared planned zero, never measured exposure, capture absence,
Negative labels or a count-training denominator.

Every fit/science/selection/promotion/confirmation/official/production/G0/count
authority flag remains false. The existing G0 planned/lagged test still rejects
the unsupported capability; no G0 kind, model registry, fitter or parent dispatch
was changed. There was no real fit, source registration, publication or main
integration in this review. Coordinator source reconciliation, new immutable
freeze and actual exact-head Ubuntu CI remain separate integration gates.
