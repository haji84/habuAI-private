# Four-night Habu field-log reconciliation

Read-only reconciliation against preserved Library read content. No canonical changes or production parser. Found11 explicit capture statements:4 on operational night2026-08-12,2 on08-13,3 on08-15 and2 on08-17. All11 have native coordinate pairs and minute timestamps, fall within the corresponding GPX time bounds, and each matches one workbook capture row by datetime/event/coordinate strings. This is corroboration, not independent validation or exhaustive nightly outcomes.

## Capture candidates

All rows below come from `libfile_d6d1412b897081918d50057af2ca4a3e`, ハブログ8月17日なう.txt, preserved as `august-extracted.txt`. Lines refer to this extracted text, not verified original-file byte offsets. Native timestamp has no timezone suffix; canonical07:00JST interpretation is recorded separately.

| Operational night | Extracted line | Native timestamp | Latitude / longitude text | Workbook ID |
|---|---:|---|---|---:|
| 2026-08-12 | 2631 | 2026/08/12 22:28 | 28.16443546510732 / 129.3951324019098 | 215 |
| 2026-08-12 | 2770 | 2026/08/12 23:12 | 28.17642769034414 / 129.3955752641599 | 216 |
| 2026-08-12 | 2994 | 2026/08/13 1:42 | 28.17024567113178 / 129.3000524386923 | 217 |
| 2026-08-12 | 3030 | 2026/08/13 2:01 | 28.19472165899677 / 129.2832366336449 | 218 |
| 2026-08-13 | 3176 | 2026/08/13 21:04 | 28.16596370234442 / 129.3383174166765 | 220 |
| 2026-08-13 | 3470 | 2026/08/13 23:32 | 28.16531418620288 / 129.3843050275264 | 221 |
| 2026-08-15 | 3833 | 2026/08/15 21:48 | 28.18332996378373 / 129.3964131646259 | 222 |
| 2026-08-15 | 4156 | 2026/08/15 23:20 | 28.16694657884455 / 129.371365754195 | 223 |
| 2026-08-15 | 4186 | 2026/08/16 0:25 | 28.17024216566392 / 129.3029272593291 | 224 |
| 2026-08-17 | 4279 | 2026/08/17 21:47 | 28.13869737651483 / 129.346271681204 | 226 |
| 2026-08-17 | 4609 | 2026/08/18 0:48 | 28.19180829076465 / 129.3972451529137 | 227 |

Each block explicitly says捕獲 andハブ捕獲大/中/小. 大/中/小 describe size, not quantity. None gives an exact individual count: all11 exact counts remain null, with lower bound1 grounded only in the explicit capture statement. Workbook count1 for every matched row is an inherited derived claim, not a substitute for missing source quantity. These are11 distinct statements; semantic deduplication remains required before treating them as11 distinct real events or adding their lower bounds.

Ownership is not explicit within the blocks. They are recorder-capture candidates, with no other-person marker observed in these11 blocks; absence of such a marker is not proof of ownership. Every matched workbook row is marked反応 despiteイベント=捕獲. Preserve and review this role conflict; do not silently relabel from the dashboard or discard solely by inherited role.

The May–July log was also checked: its timestamp span endsAug1, so it supplies no direct event blocks for these four nights. The August log endsAug18, so it cannot resolve later GPX nights.

## Search markers and GPX coverage

| Operational night | Explicit start | Explicit end | GPX JST time bounds |
|---|---|---|---|
| 2026-08-12 | Not found in inspected full source | 2026/08/13 3:43 (L3109) | 2026-08-12T20:34:27.143000+09:00 to 2026-08-13T03:38:53.999000+09:00 |
| 2026-08-13 | Not found in inspected full source | Not found in inspected full source | 2026-08-13T20:17:55.999000+09:00 to 2026-08-14T00:46:21.999000+09:00 |
| 2026-08-15 | 2026/08/15 20:00 (L3529) | 2026/08/16 1:41 (L4252) | 2026-08-15T20:01:44.999000+09:00 to 2026-08-16T01:37:52+09:00 |
| 2026-08-17 | 2026/08/17 21:32 (L4265) | 2026/08/18 1:55 (L4648) | 2026-08-17T21:33:05.999000+09:00 to 2026-08-18T01:55:33.999000+09:00 |

Aug12 end marker03:43 is about4min6s after GPX last time03:38:53.999. Aug15 start20:00 precedes GPX first time20:01:44.999 and end01:41 follows GPX last time01:37:52. Aug17 start21:32 precedes GPX first time21:33:05.999. These observed gaps must not be filled with synthetic movement. Aug13 has no explicit search start/end marker in the recovered source; first/last species observation does not become a search boundary. Markers alone do not assert complete capture reporting, detection effort, route adherence or negative exposure. No spatial GPX match or gap QC was performed in this slice.

## Reaction and boundary controls

| Line | Timestamp | Native observation | Treatment |
|---:|---|---|---|
| 2967 | 2026/08/13 0:29 | 目撃 / ヒメハブ | Reaction only; never target capture |
| 3156 | 2026/08/13 20:58 | 轢死 / ハブ | Reaction only; never target capture |
| 4233 | 2026/08/16 0:39 | 轢死 / ハブ | Reaction only; never target capture |
| 4629 | 2026/08/18 1:28 | 目撃 / ヒメハブ | Reaction only; never target capture |

These controls include two Habu roadkill blocks (Aug13 20:58;Aug16 00:39) and twoヒメハブ sightings. Other-species records remain raw context, not captures. The Aug12 00:15 Habu capture lies on operational nightAug11 and is intentionally outside this overlap ledger; copying calendar-day rows would misassign it. The Aug13 01:42/02:01,Aug16 00:25 andAug18 00:48 candidates belong to previous dates under07:00JST.

## Structured evidence and future parser checks

`library-habu-audit/overlap-candidate-review.json` retains exact raw blocks, line ranges, native coordinate/timestamp/quantity strings, ownership status, null exact quantities, lower-bound basis, workbook corroboration and role conflict, markers, reactions and GPX hashes. Original text byte materialization was not available; input hashes identify preserved extracted read content, never original TXT/XLSX bytes.

Useful future source-parser checks from actual evidence: (1)大/中/小 are sizes and cannot default a count; (2)capture-without-quantity returns null exact count/lower bound1; (3)after-midnight operational-night mapping; (4)Habu roadkill andヒメハブ sightings are not targets; (5)reaction-tagged workbook capture conflict remains visible; (6)no adjacent-event coordinate borrowing; (7)missing search markers and GPX boundary gaps remain missing; (8)source-copy aliases do not create independent events. These would test parser behavior, not validate scientific performance.

Current receipt can support future recovered-evidence ingestion after explicit role/source review. Library archival date and native event time do not establish historical model access, ex-ante universe, ORIGINAL forecast issuance or exhaustive outcomes. No repository test suite was run.
