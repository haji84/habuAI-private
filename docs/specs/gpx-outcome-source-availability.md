# 2026 August/September actual GPX versus owner event source matrix

This is a strictly read-only input-source audit for Issue #64, **not** a scientific model-learning dataset.

`python scripts/build_gpx_outcome_source_matrix.py --output artifacts/source-matrix/availability.json`

The 13 historical GPX records on main include **12 August operational nights (Aug 12, 13, 15, 17, 19, 21, 23, 24, 27, 28, 29, 31) and Sep 2**, not 13 August nights. They sum to 243,747 measurement points. A separate Sep 28 reconstructed archive has 22,990 points and a complete captured-individual event audit.

The tool independently cross-checks GPX time-derived operational nights, byte SHA-256 and point counts against `evidence/legacy/habuAI-public/v2_actual_gpx_13night_qc.csv`. For each nightly source, it inventories whether three authoritative paths really exist: original owner Habu log, capture-event ledger, and one-to-many capture-individual ledger. Raw GPX never implies that the owner recorded all captures or that every traversed spot was actually surveyed. Without matched original owner log/individual source and exhaustive observation quality the event label remains **UNKNOWN**, even if GPX or a monthly dashboard exists. The matrix never fabricates zero-capture observations or retroactively creates predictions.

Source-availability findings are separate from cross-chat memory and prior spreadsheet summaries. These may guide recovery but must not be treated as original source files when they are not committed and independently available on main.

The next work slice must recover or properly ingest genuine August owner logs and separate reaction data for the same date, run event-to-individual reconciliation and classify each sampled spatial/time unit as Positive, qualified noncapture, or Unknown. Source-availability times and an ex-ante forecast universe are required before feature training. A nominal GPX candidate cell is not automatically an eligible model Negative.

This matrix reports **0 verified Positive and 0 verified Negative training rows**, not because the snakes were absent, but because supervised label completeness has not been established. The authentic Sep 28 five events/six individuals remain source-corroborated yet not sufficient to train and validate a real production model.
