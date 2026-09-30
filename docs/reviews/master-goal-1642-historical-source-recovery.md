# Habu Library evidence recovery audit — 2026-09-30

Read-only audit. No canonical repository data was imported or changed. This recovered substantive historical capture source content, not merely research/forecast narratives. All potential eligibility remains subject to role, deduplication, source and time validation.

## Resolved inventory

| File / Library identity | Observed provenance | Assessment |
|---|---|---|
| ハブDB_2025-2026_08-29_捕獲カウント完全修正版.xlsx — `libfile_ea59b2e755cc8191bfc5b0abee96acf7`; file `file_00000000a110820b988a300b5ea63c2b` | 781972 advertised bytes; created/modified 2026-08-30T02:24:45.700118Z; version null; model_generated true | Actual dated event tables and quoted original blocks, plus derivative classifications/calculations. Candidate recovery ledger, not independently verified raw capture truth. |
| ハブログ5~7月.txt — `libfile_7580f6fa1a1c8191b0a39980e349798b`; file `file_0000000064288206a38d443deec8fa0a` | 159242 advertised bytes; created/modified 2026-08-19T10:25:12.800291Z; version null; model_generated false | Full extracted content read: 14470 lines. Timestamped field-log style records from May5 through Aug1, including explicit Habu captures, reactions, roadkill, other species and ambiguous blocks. Strong source candidate. |
| ハブログ5~7月(1).txt — `libfile_ff1c273b04dc81918d068e2c3315ea52` | 159242 advertised bytes; created/modified 2026-08-24T17:58:03.449351Z; version null; model_generated false | First1000 lines match the other copy. Duplicate candidate only: full bytes/hash equality not established. Do not count as independent events. |
| ハブログ8月17日なう.txt — `libfile_d6d1412b897081918d50057af2ca4a3e`; file `file_000000000f948206805afa1fba2123be` | 52921 advertised bytes; created/modified 2026-08-19T10:25:11.893130Z; version null; model_generated false | Full4653 extracted lines read, Aug2 through Aug18. Explicit capture blocks and exploration markers. Strong source candidate. |
| Habu_AI_v2_89夜_GPS_GPX復元監査.xlsx — `libfile_30e80c5a3e3c8191a5a8a9fca5a57c08` | 20337 advertised bytes; search version1; created2026-09-01T14:05:00.187377Z, modified14:20:28.363055Z; model_generated true | All137 extracted lines read. Derivative89-night classification claims; not measured exposure or complete outcome evidence. |
| ハブAI_10m区間_GPX通過履歴_ハブログ統合.zip — `libfile_6343a4caf5808191a56d16ec61ea1561` | 602612 advertised bytes; model_generated true | Resolved, but read returned no readable content and materialization failed. Payload/claims unverified; cannot treat10m derivative as100m exposure. |
| ハブ研究マスターDB_v1_過去研究比較基盤.xlsx — `libfile_8f8ca03569bc81919d01194498f97644` | 19709 advertised bytes; model_generated true | Read: literature master/research comparison schema, not user's own capture ledger. No training positives from this workbook. |
| 今日の捕獲予想9.30まで.pdf — `libfile_4935527416908191aa59b5de1f11b81f` | Archived long conversation/forecasts; only initial excerpt inspected | May contain pasted logs, but AI statements and archived predictions are not new ORIGINAL issuance. Not extracted into canonical events. |

Discovery stayed within Habu capture/history/GPX provenance queries with top_k10. Exact source `8:2~8:29ハブ.txt` named by workbook was not resolved by the bounded searches. No assertion that it does not exist. Other resolved forecast/comparison DOCX files were not pursued as primary field evidence.

## Exact content preservation and limitations

Scratch folder `library-habu-audit` contains complete serialized search/read structured results, extracted text, candidate-block audit, and `inventory.json` SHA256/size hashes. These hashes identify **response/extracted-content bytes**, not original XLSX/TXT/ZIP bytes. Original workbook materialization failed HTTP502 twice; ZIP also failed. No manual transfer or credential fallback. The original files' advertised byte counts are metadata, not local-byte verification. Version null remains null. No code from source archives was executed.

Workbook read pages were requested at starts1,1001,...,9001. Advertised9073 lines;9001 returned empty/no content. The capture tab occurs early and was fully parsed, but the ending daily-summary tab is incomplete. CSV across multiline cells/pagination produced one malformed normalized row; normalized overall row counts below are diagnostic only. Preserve exact read responses for future re-extraction rather than claiming a complete byte-faithful workbook export.

## Capture ledger findings

`捕獲DB` contains247 nonblank records, all species ハブ:206 `捕獲`,21 `轢死`,12 `roadkill_sighting`,4 `目撃`,2 `sighting`,2 `no_capture`. The206 capture-labeled rows sum208 individuals, matching the cached dashboard, but this is a **candidate ledger total, not an independently verified eligible training total**.150 of206 have both coordinates and strict HH:MM time;193 have strict time,56 lack coordinate pairs. Two multi-individual rows: source index46/ID47,2025-11-24 time`夜`,count2; source index231/ID232,2026-08-20 01:44,count2. No identical nonempty `重複キー` among206 rows; this does not prove semantic uniqueness or absence of overlapping source copies.

Crucial role conflict: capture-labeled rows have `本命カウント` 本命95,対象58,反応53.44 of those53反応 rows are August explicit capture candidates, many with original blocks. Do not blindly use either the dashboard206 or filter only本命/対象: preserve the contradiction and resolve against actual source text and ownership. `確度=high/source_confirmed` is an inherited assertion, not independently validated Gold/Silver evidence.

Workbook source values actually present include recovered, May recovered, handoff_yaml_2026-05-30, user_log_* dated families, ハブログ5~7月.txt, ハブログ8月17日なう.txt, and8:2~8:29ハブ.txt. Most are names/labels without immutable upstream byte hashes or contemporaneous receipt. No exact GitHub archival path or PR50 locator was established from the inspected content.

`正規化イベントDB` exposes native datetime/calendar date/operational night, raw and normalized event/species, 本命, 他者捕獲, raw quantity/lower/upper bounds, lower-bound flag, coordinates, quality/review reason, source and 元ブロック. An explicit other-person capture is source index209,2026-05-15 22:50:00, `目撃`, `ハブ`, `別の人が捕獲`,1匹. It must remain reaction evidence, not user's own target capture. Other species, blank/unknown event kinds, sightings and roadkill must remain separate.

Two recovered no_capture records (2025-11-11 `night`;2026-04-12 `19:30-20:30`) do not establish exhaustive verified search coverage. The former says 決定的捕獲なし, the latter peak-before-end uncertainty. Neither licenses arbitrary negative100m×10min cells.

### Tabs observed

README7 records; ダッシュボード10; 捕獲DB247; 生物反応DB841 parsed records; 正規化イベントDB708 parser records including one malformed row; 要確認一覧59; 新規ハブ監査_8月20; 取込サマリー_8月8; 月別自動集計12; 日別自動集計275 parsed records (tail incomplete). Counts are parsed extracted CSV, not native XLSX dimensions.

### Time conflict

README states07:00 boundary and fields say運用日_7時. `取込サマリー_8月` source index6 instead states05:00未満は前日扱い. Canonical07:00JST remains fixed. Recompute night from verified native date/time with an explicit timezone rule, preserve workbook's assigned night as diagnostic, flag disagreements. Approximate times such as 夜/頃/前/前後 and 文脈推定 cannot be turned into precise timestamps.

## Raw-log evidence and bounded candidate scan

Both full primary text logs were read. `may-july-extracted.txt` has14470 lines; `august-extracted.txt`4653. A deliberately simple timestamp-block scanner identified1575/484 dated blocks and117/26 blocks mentioning bothハブ and捕獲. These are **candidate mention counts only**, not eligible capture counts;2/1 include ambiguity keywords and the scanner can miss shorthand, include headers, or combine species. `candidate-blocks.json` preserves raw blocks and source line locations for review. No missing quantity was silently made1.

Concrete source examples:
- May–July line368:2026/05/07 22:58,ハブ捕獲,捕獲,道路中央,移動中,捕食後; coordinates absent in that block, so do not borrow next23:02 roadkill coordinates.
- May9 23:03 block explicitlyハブ捕獲/捕獲,節子1335,28.16568814952801/129.3828351422025. This is a genuine capture statement requiring quantity/ownership validation, not a forecast.
- August line18:2026/08/02 0:50,捕獲,ハブ捕獲中,道路脇,阿木名,28.16784377023349/129.3368015044549. Native date/time and coordinate text can be preserved and mapped to canonical previous operational night under07:00JST.

The89-night workbook itself warns eventGPS anchors are only recovery possibilities and map matching was not performed. Its claims87positive+2zero,10actualGPX+21high-recovery+13partial+45spatial are archived derivative results, not a reason to overwrite the current byte-audited13GPX corpus or declare21 reconstructed nights measured.

## Recommended next bounded intake

1. Review extracted-response identity and classify source as current-time recovered evidence, preserving provider file IDs, null version, read line coverage, retrieval receipt and response SHA256. Prefer later original-byte recovery when available; do not mislabel response hashes as source-file hashes.
2. Reconcile source-local capture candidates against workbook rows by native date/time, species/event, coordinates and quoted block. Explicitly resolve ownership and the53 role conflicts. Assign event IDs once; keep quantity separate from event count. Copy aliases and cumulative logs form duplicate groups, not new observations.
3. Build a review queue for ambiguous event/species/quantity/time, coordinate absence and conflicts. Do not fill fields from adjacent events or memory. Keep lower/upper quantity bounds where native source does.
4. Link validated positive events to the13 actual GPX nights using canonical07:00JST, temporal support and distance tolerances. This may recover positive outcomes for formerly unlabeled nights. It does not establish a complete nightly count or legitimate negative cells without explicit outcome completeness and exposure evidence.
5. Any approved ingestion can support future training after verified receipt and role validation. Archived event date, source filename and Library creation time do not establish historical model feature access, ex-ante universe, past ORIGINAL issuance or leakage-free past predictions. Forecasts and route decisions must be issued prospectively with frozen inputs.

No repository tests were run for this data audit. Numerical claims above are audit-script counts on preserved content, not scientific validation or model performance results.
