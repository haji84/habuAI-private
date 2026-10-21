# September 2026 correction: 50 capture events, **51 individual Habu**

Audit date: 2026-10-21. This document supersedes the **counting conclusions**, not the original bytes, of the earlier September/October integrated archive.

## Reproduced source issue
- Source: `ハブログ9月.txt`, raw source SHA-256 `f27a9e06cf89b06a68520365d29630d695d59a96810c95081cfbdb88652bd733`.
- At `2026/09/29 0:00`, the record says `捕獲 / ハブ捕獲~90幼体 / 待機中 / 畑 枯れ木 2匹 / ウエット`, at coordinates `28.16750618464175,129.2997244659382`.
- Operational night `2026-09-28`, because 00:00–06:59 JST belongs to the prior night.
- Old parser only recognized quantity when `2匹` occupied an entire line, so this *one encounter with two captured individuals* was counted as one individual.
- It was **not** a case of two separately entered events being accidentally deduplicated. The previous new-event dedup audit removed zero true duplicate rows.

## Verified corrected figures
| Scope | Capture events | Captured Habu individuals |
|---|---:|---:|
| September 2026 | 50 | **51** |
| September 28 operational night | 5 | **6** |
| October 6–20 registered exploration nights | 17 | **17** |
| September + October added | 67 | **68** |

Historical source before September 2026 is unchanged. The full unified event table still has 3,853 **events**, including 1,117 September/October events. The corrected individual table has 68 new rows.

## GitHub canonical validation
`main:data/processed/capture_events/2026/2026-09-28.csv` already records `CAP-20260929-0000-001, event_count=2`, and `main:data/processed/individuals/2026/2026-09-28.csv` already contains two distinct individual IDs (-01 and -02). **Do not change or delete those correct canonical records.**

## Corrected workbook
`ハブDB_2025-2026_10-20統合更新版_9月51匹訂正版.xlsx` SHA-256 `PLACEHOLDER_CORRECTED_XLSX_SHA_TO_BE_SET`.
The earlier `ハブDB_2025-2026_10-20統合更新版.xlsx` is retained for audit only; do **not** treat its 50-individual September total as canonical.

The new import splits event-layer rows and individual-layer rows. The 2026-09-06 01:59 mixed note `目撃 オットンカエル 1匹` is a different-species sighting and is not used as the Habu-capture quantity.

## Regression checks (local)
- 50 September capture events, sum(event_count) = 51
- September 29 00:00 = one event, two unique individual IDs and one shared GPS location
- September 28 operational night = six individuals
- 67 additional capture events / 68 individual Habu
- Three corrected CSV-level regression tests passed. P0 and Champion records unchanged.

## Integration gate
Do not merge the previous October integrated archive as an authoritative individual-count dataset until the new corrected workbook is byte-preserved in GitHub and the corrected one-event/two-individual test passes in CI.
