# September corrected source recovery candidate

Status: STAGED PROSPECTIVE CANDIDATE. Canonical intake and merge remain pending passing CI and independent review.

The two original files identified in the September multiplicity correction were found in the owner's existing files and recovered through the official file download route. They are added under `incoming/2026-10-21/`; no historical raw archive is replaced. The intake receipt records original filenames, source identities, received time, byte lengths, SHA-256 and Git blob SHA-1.

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| `habu_db_september_51_corrected.xlsx` | 820,713 | `ead12df59799d607a93814d91e5ed719bbc955cda3a8cf2410f22d42214d7054` |
| `habu_db_september_51_validation.zip` | 1,220,188 | `ee803478c0a1ec574591fc219fa585afad101539b5ddfaebae966e41c5b60aee` |

The ZIP passes CRC validation and embeds bytes identical to the separately received workbook. The old `67075a...` ZIP, original workbook, and `7f0dd5...` 07:00 correction workbook remain forensic history. **The received quantity-corrected workbook reintroduces 101 older display-night errors. It is preserved as an incoming original and must not be labeled the latest authoritative view.** This receipt does not promote it to MAIN's canonical dataset.

## Combined quantity and operational-night display candidate

`scripts/build_september51_07h_view.py` reads the received XLSX XML and verifies its 314 display rows against the companion ZIP CSV. It derives the 07:00 date from workbook observation date/time, then changes only the corresponding `night` field in a CSV retaining full coordinate precision and source notes. It repairs the same 101 older display rows (91 previous capture labels and 10 noncapture rows) without rewriting either received file or recertifying historical captures.

The result is `data/processed/reconciliation_candidates/2026-10-21/historical_capture_display_september51_07h.csv`, SHA-256 `979ba7f96259c9202d084e302d08cd8f72f04017b80d4d23cc465242ca26ad07`. Its 314 rows include noncaptures and unresolved legacy labels; it is not the canonical capture-events table. Twenty-three rows fail strict ISO date/time parsing and remain unchanged. The earlier prose claimed 24 unparseable rows; that exact number is not reproduced with this parser. Quantity, classification, source IDs and all other fields are unchanged. Both source hashes and the per-row changes are recorded in `evidence/raw_intake/2026-10-21-september51-07h-derived-view.json`.

This CSV is a prospective derived candidate requiring CI and independent review. It does not authorize MAIN promotion, historical label changes, or a model update.

The builder reads only regular files under relative `incoming/` receipt paths and refuses symlinks in receipt, source and output paths, including ancestors. Nonblocking open permits FIFO rejection before any read. It parses verified byte snapshots and rechecks source/receipt bytes before publication. A matching existing CSV is reused without changing its timestamp; a different existing candidate is refused. New output uses exclusive creation. These protections preserve the received originals and any different existing candidate.

## Counting and observation evidence

| Scope | Owner capture events | Captured individuals |
| --- | ---: | ---: |
| September 2026 | 50 | 51 |
| October selected seven nights | 17 | 17 |
| Combined selected source set | 67 | 68 |

The 2026-09-29 00:00 encounter belongs to the 2026-09-28 operational night and contains two individuals in one event. The new event table remains 1,117 rows; the historical event projection remains 3,853 rows. Habu sightings (4 rows), roadkill (4 rows) and another person's capture (1 row) remain separate from the 67 owner capture events. Legacy capture/sighting ambiguity is not resolved by this repair.

An independent read of SHA-verified actual GPX originals reproduced spatial distances within 0.005m of the archived report and verified all 67 encounter locations within 100m and absolute time difference at most 600 seconds. These are **observation-to-GPX consistency checks**, not prediction hits, forecast recall, calibration, or evidence for Champion promotion. The shared two-individual encounter still contributes one GPX encounter check.

## Existing event overlap: link identities before any future intake

| Existing source | Operational nights | Existing events | Existing individuals | Intake action |
| --- | --- | ---: | ---: | --- |
| MAIN capture/individual tables | 2026-09-28 | 5 | 6 | Preserve existing IDs and link source evidence |
| PR #39 capture tables | 2026-10-14 and 2026-10-15 | 6 | 6 | Reconcile the same observations before ingesting either candidate |
| Total already represented across these sources | — | 11 | 12 | Never append these as additional captures |

The archive-only PR does not itself append canonical capture rows. The overlap becomes a duplicate-count risk at later ingestion. The complete selected source set is not 67 events newly additive to MAIN: it includes MAIN's existing five September encounters. If PR #39's six encounters are integrated too, they also require identity linking. Preserve canonical `CAP-20260929-0000-001` and both linked individuals.

The quantity correction changes a source-derived record ID and dedup key for the midnight encounter. A second owner-capture record at 2026-09-06 01:59 contains an other-species sighting note: its `1匹` is no longer attributed to the Habu quantity. That record's source-derived ID also changes; its capture event classification and count minimum of one are retained. The corrected GPX report changes only these two source IDs; its geometry, timestamps and distance metrics are unchanged. Source-derived ID equality alone is insufficient for reconciliation; match timestamp, event class and coordinates while preserving canonical identity.

## Verification and integration gate

`tests/test_habu_september_corrected_sources.py` verifies both received file hashes and sizes, embedded workbook identity, ZIP integrity, 67 encounter/68 individual grain, September 50/51 and October 17/17 splits, individual linkage, selected-event dedup keys, 07:00 attribution, non-owner categories, the exact night-only display repair, and refusal of destructive file/path cases. Eleven safety regressions first failed in two RED/GREEN cycles (path/write protection and FIFO rejection), then the complete candidate snapshot suite passed all 15 tests. Local success does not imply GitHub Actions success. Keep the PR Draft and do not merge before CI and independent review pass. P0/ORIGINAL predictions, models and Champion remain unchanged.
