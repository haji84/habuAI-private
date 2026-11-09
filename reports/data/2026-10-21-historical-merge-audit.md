# Historical Habu DB reconciliation | 2025-09 to 2026-10-20

## Evidence and storage
This is an **audited historical integration candidate**, not an authorized rewrite of the historical ORIGINAL prediction artifacts.
The **unchanged** 2025–2026-08-29 source workbook, the 2026 September source text, a carefully labeled **transcription** of the October 6/8/14/15/16/18/20 chat, the updated workbook, all merge CSVs and source scripts are together in a single 19-file ZIP.

The original 1,868,956-byte ZIP has SHA-256
`67075a32bba202f62a51604d757660f36d4d8115e0b5b250cbb85961ec7a737a`.
It is split without loss into 25 text-safe XZ/base64 parts at
`data/raw/attachment_archives/integrated_db/<zip_sha256>/`.
Use the existing `scripts/text_safe_byte_archive.py restore` function; restoration must verify compressed SHA-256, raw length and raw SHA-256. A repository test checks restoration and core record counts.

## Deduplication and evidence classification
| Source | Record count |
| --- | ---: |
| Existing normalized 2025–2026-08 historical records and preserved older rows | 2,736 |
| 2026 September source log | 893 |
| 2026 October selected chat transcript | 224 |
| **Total** | **3,853** |

In the selected new inputs, exact-normalized duplicate removal = **0**. The repeated postings of October logs are alternative presentations of the same observations and are **not** separately added. This is not a guarantee of no latent duplicates in the historical source. The integration has 43 review exceptions that must be retained for human/scientific audit.

New confirmed owner-capture log events: September **50**, October **17**, **67** total. The independently labeled GPX match report records timestamp ±10min and spatial <=100m matches; this is NOT an official prediction score.

The workbook's existing sheets are preserved as earlier snapshots. Newly added consolidated views hold the latest rows. Do not represent the earlier dashboard as automatically updated beyond August.

## Uncertainty and invariants
- 2025 `capture_or_sighting` remains ambiguous and is not upgraded to an owner capture.
- Habu roadkill, other person's Habu capture, Himehabu and other species are not owner Habu captures.
- For mixed species in a single observation event, a count of 1 is not copied onto both species.
- 07:00 Asia/Tokyo is the operational-day boundary.
- One anomalous 2026-10-18 18:48 `SESSION_END` is recorded as an inconsistency, and a corresponding START is retained.
- The October compact source is a **manual structure-preserving transcription from the chat**, not a byte-identical export of the original chat message.
- Untraveled/undetected road cells remain UNKNOWN, not true ecological negatives.
- ORIGINAL P0/P1/P2 freezes are never rewritten. These data cannot justify Champion promotion without independent temporal validation.

## Publication status
The byte-exact ZIP is a reconstructable **staged branch artifact**, not yet merged into `main`.
Do not re-ingest the corresponding October records from PR #39 or earlier conversations as independent new captures.
CI and PR review must pass before any promotion. Report any CI platform failure as blocked, not PASS.

Source ingestion artifacts: `/監査CSV・レポート/取込マニフェスト.json` and `/監査CSV・レポート/要確認_例外候補.csv` **inside** the ZIP.
