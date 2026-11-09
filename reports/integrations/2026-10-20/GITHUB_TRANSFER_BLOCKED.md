# 2026 September/October merge: GitHub backfill status

Status: **PARTIAL / DO NOT MERGE** (2026-10-21).

The owner requested a deduplicated 2026 September and October integration into their existing 2025-2026 Habu DB. The complete locally generated, SHA-verified integration pack is in the source ChatGPT conversation, not yet fully replicated in this Git branch.

## Local verified result
- Base workbook: `ハブDB_2025-2026_08-29完全統合版.xlsx`, SHA-256 `8980fd9c857d58bd9ddde92bec36573eb4aac422dd9d51ac04355af743d3d43b`.
- New September 2026 evidence: 893 timestamped blocks; 50 owner Habu captures.
- October 2026 evidence: 224 transcribed event rows from seven operational nights; 17 owner Habu captures.
- New unique events: 1,117; new confirmed owner captures: 67.
- Matched 67/67 new captures to the corresponding uploaded real GPX at <=100m spatial distance and +/-10 minutes.
- Historic old normalized events: 2,677. Historic pre-May-2026 legacy events: 59. Merged event-view rows: 3,853.
- Retain unresolved 2025 `capture_or_sighting` as non-definitive. Mixed-species observations preserve ambiguity.
- 2026-10-18 18:48 repeated contradictory SESSION_END vs START has been quarantined in exception table.

## Exact archive transport
Full local pack file: `ハブAI_2025-2026_10-20統合DB・重複監査パック.zip`.
SHA-256: `67075a32bba202f62a51604d757660f36d4d8115e0b5b250cbb85961ec7a737a`.
The XZ/base64 archival manifest is committed under `artifacts/habu_merged/2026-10-20/<sha>/manifest.json`.
The manifest requires **25 parts**; only parts `000..003` are committed on this branch. Part 004 transfer was rejected by the connector security validation; parts 005..024 were not sent. The archive is **NOT RESTORABLE FROM THIS BRANCH**. Do not call this a saved full artifact or promote it as canonical data.

The source conversation contains the completed verified ZIP and Excel artifacts. Evidence CSVs and audit manifest are staged in `reports/integrations/2026-10-20/` for durable partial tracking.

## Gate to proceed
1. Fully store the source bytes via an authorized transfer path. Verify each part, XZ SHA, original ZIP byte length and original ZIP SHA.
2. Restore both underlying Excel workbooks, September log and October transcription and re-execute the supplied reproducibility scripts.
3. Verify all merged event/capture counts and GPX evidence. Ensure no old Raw or ORIGINAL prediction was modified.
4. Green CI + independent data integrity checks + eligible PR review before main integration.
5. No historical P0 recreation, retroactive ORIGINAL score or premature Champion promotion.

Status reason: `CONNECTOR_TRANSFER_SECURITY_BLOCKED`. This is not a source data quality failure.
