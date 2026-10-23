# Actual 2026-09-28 GPX / capture / individual reconciliation

This audit is the **first real-data preparation slice** for Issue #64. It connects four independent data sources and exposes contradictory quantities without altering any source:

1. Byte-exact, 24-part GPX archive `data/raw/gpx_archives/2026-09-28-探索.gpx.lines`, manifest SHA-256, raw point count and 07:00 JST day boundary.
2. User-capture event CSV `data/processed/capture_events/2026/2026-09-28.csv`, whose five events include one event containing two distinct individuals.
3. Individual CSV `data/processed/individuals/2026/2026-09-28.csv`, requiring exactly one linked individual ID per physically captured Habu.
4. Original night log `data/raw/habu_logs/2026/2026-09-28.json` and frozen dashboard `dashboard/baseline_2026.json`.

## Current discrepancy

- Reconstructed GPX manifest records **22,990 points** with SHA-256 `2e9fde7aa459fc100abf8014d95635e697a638679cc9df731f4e0f6a80fb62f3`.
- Event and individual source records: **five capture events, six captured Habu individuals**. At 2026-09-29 00:00 there are TWO individual Habu records related to ONE capture event.
- Frozen dashboard currently lists **five captures** for the same night. This is a frozen aggregate-versus-event count discrepancy, **not** permission to rewrite a user-confirmed monthly total or discard one verified individual.
- The old `reports/pdca/2026-09-28/exposure_100m_10min.csv` has historical `observed_negative` labels. Re-sampling GPS-only passages does NOT verify actual searching, all possible captures, legal road-space coverage or observation quality. Those labels must **not** automatically become training Negatives.
- Model-eligible labeled rows are **0** until 5-vs-6 is reconciled with actual source evidence, search effort/complete outcomes are audited, and an ex-ante ForecastUniverse/feature-availability snapshot exists.

## What this code implements

`python scripts/reconcile_actual_gpx_exposure.py --night 2026-09-28 --output artifacts/reconciliation/2026-09-28.json`

- Reads the actual multipart GPX as immutable bytes, checks SHA-256, count, ISO timestamps and 07:00 JST operational-night consistency.
- Uses existing GPS anomaly marking and HDOP quality checks; aggregates only valid **sampled passage points** into UTM52N 100m×10min candidate units. It does not fabricate searched roads between samples.
- Reconciles original log timestamps/multiplicities with the event CSV, checks one-to-many event→individual ID links, and reports GPS spatial/temporal proximity for each distinct capture event. Proximity is **not** proof that the full exploration route was searched.
- Compares individual count to the preexisting frozen dashboard, emits `TRAINING_BLOCKED` and explicit blockers. Never writes a `model_learning.json`, an ORIGINAL P0, or verified Negative labels.
- An Actions workflow executes against **real archived input** and uploads a machine-readable diagnostic artifact (not a scientific PASS). Unit tests include real-source checksum and conflict assertions.

## What remains

- Resolve 5-vs-6 source discrepancy without silent capture deletion/duplication; consider whether dashboard is inaccurate versus original IDs.
- Obtain more authentic night event+GPX data in the same format (including 10/22), with actual byte preservation, GPS quality and documented session effort.
- Freeze future forecast universe and historically available weather/DEM/road snapshots; certify source receipts that precede each historical prediction cutoff.
- Only then construct audited labels and historical walk-forward folds. Unvisited=UNKNOWN, sightings and roadkill remain separate, and data from the evaluation night never sets that night's ex-ante road universe.
- Never claim 1km Top10 Recall ≥90% or 100m±10min official score without sufficient valid, unseen held-out nights.

Historical evidence is retained; the code neither fabricates negatives nor modifies any confirmed counts.
