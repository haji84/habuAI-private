# Habu AI 原本・DB・GPX 独立監査

監査対象は haji84/habuAI-private の最新APIで確認した固定head。GitHubへの書込・main統合・原本の削除/上書きは行っていない。AGENTS.mdの原本保存、07:00 JST、Unknown≠Negative、ORIGINAL予測不改変、CI通過前merge禁止を適用した。

| PR | 監査head | 結果 |
| --- | --- | --- |
| #39 | `5d05e4889ebd37e50fd6e2eb29c7589b25b8e30a` | 4夜のGPX原本SHA/56,762点、6本人捕獲と1ハブ轢死の実測整合を再現。5テストPASS。 |
| #41 | `28c42bf91420d38ae1ca276b106982edb3f0d5bf` | 現行headの10アーカイブ全件復元・SHA/ZIP CRC・改変拒否を確認。GPXは10/16・18・20の3夜。2テストPASS。本文とbackfill manifestの「未転送」は現状と乖離。 |
| #42 | `4e003cd1036f32ce09bb1be6e909c6edbbff4931` | 25parts中000..003だけ。21parts欠損のためこのbranch単体からZIPは復元不能。Draft維持。 |
| #43 | `415837c3713a167794149770f1228190fa158fe6` | 旧統合ZIP25partsと07h訂正xlsx9partsを完全復元。後述の数量訂正版xlsx/ZIPはこのheadに未収録だが、既存ファイルから欠損を回復できた。 |

共通baseは `27f4832a23f0a3826ce96b87afb4f2f1c58aa936`。再取得した最新headも一致。#43本文にあるCI head `3c0cc134...` はこの監査headより古い。ローカル検証はCI PASSを意味せず、merge判断は親監査の最新CI結果に従う。

## 原本完全性

取得した変更ファイル132個はGit blob SHA-1と全件一致。監査用ローカルコピーの転送時改行だけをGit blob照合に基づき補正し、リポジトリ原本は変更していない。

| 保存物 | bytes | SHA-256 | 状態 |
| --- | ---: | --- | --- |
| #43旧統合ZIP | 1,868,956 | `67075a32bba202f62a51604d757660f36d4d8115e0b5b250cbb85961ec7a737a` | 25partsから復元、圧縮SHA・raw SHA・CRC一致 |
| 原本2025–08/29 workbook（ZIP内） | 709,183 | `8980fd9c857d58bd9ddde92bec36573eb4aac422dd9d51ac04355af743d3d43b` | manifestと一致 |
| 9月原本txt（ZIP内と独立取得） | 96,493 | `f27a9e06cf89b06a68520365d29630d695d59a96810c95081cfbdb88652bd733` | 両方のbytes一致 |
| 10月選択チャット転記 | 22,772 | `ec7487343eac286646c65c71cac672c95ed3197037deb2a0bc1427b2f495e4b2` | manifestと一致。チャットbyte原本ではない |
| #43 07h修正workbook | 813,283 | `7f0dd533fcf9bc27f2cb797fb63a7cf416973a1c7ce2cb9d90a219d4483824de` | 9partsから完全復元 |
| 回復した9月51匹訂正workbook | 820,713 | `ead12df59799d607a93814d91e5ed719bbc955cda3a8cf2410f22d42214d7054` | 既存ファイルから正規取得、訂正文書のSHA一致 |
| 回復した9月51匹訂正検証ZIP | 1,220,188 | `ee803478c0a1ec574591fc219fa585afad101539b5ddfaebae966e41c5b60aee` | CRC正常、内包workbookが上記xlsxとbyte一致 |

数量訂正版は `/ハブAI/ハブDB_2025-2026_10-20統合更新版_9月51匹訂正版.xlsx` および `/ハブAI/ハブAI_2025-2026_9月51匹訂正_統合DB検証パック.zip` として既存保存されていた。別の新規生成・再エンコードによる転送制限回避はしていない。

## 数量と分類

| 範囲 | 全イベント | 本人ハブ捕獲イベント | 本人捕獲匹数 | ハブ目撃 | ハブ轢死 | 他者ハブ捕獲 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 9月選択原本 | 893 | 50 | 51 | 3 | 3 | 1 |
| 10月選択転記 | 224 | 17 | 17 | 1 | 1 | 0 |
| 追加選択集合 | 1,117 | 67 | 68 | 4 | 4 | 1 |

`50/17/67` は捕獲イベント数として成立する。9月は9/29 00:00の「畑 枯れ木 2匹」を含むため51匹、合計68匹。MAINはすでに同じ遭遇を `CAP-20260929-0000-001, event_count=2` と個体2件で正しく保持する。旧統合ZIPと07h版の「50匹」は数量正本にできない。

全期間3,853行は既存2,736行（正規化2,677＋古い保存行59）と新規1,117行のイベント投影。全期間本人捕獲匹数ではない。元capture view314行の分類は旧未解決9、非捕獲41、原本再検証待ち既存captureラベル197、新規本人捕獲67。旧capture_or_sighting等を本人捕獲に昇格させていない。

選択した新規1,117行のdedup_keyは一意で、正規化完全一致の重複除去は0。ただし既存MAINやPR #39との重複がないという意味ではない。43例外は混合種数量未割当42＋同分の終了/開始矛盾1。歴史全体の潜在重複・真の捕獲総数は未確定。

数量訂正版では本人捕獲2行のsource-derived record_id/dedup_keyが変わる。9/29 00:00の2匹訂正と、9/6 01:59の本人捕獲記録に含まれる他種目撃メモの数量をハブ捕獲数量へ流用しない訂正である。後者のcapture分類とcount_min=1は保持される。訂正版GPX照合CSVの変更もこの2件のsource IDだけで、位置・日時・距離は全67行同じ。イベントID文字列だけに依存せず、時刻・分類・位置・原本行で既存イベントにリンクする必要がある。

## 07:00日界の独立検証

旧workbookと07h版をXMLセル値で比較し、`捕獲原DBと追加_314件` の探索夜D列101セルだけの変更を確認した。内訳は既存captureラベル91行、非捕獲10行。101は捕獲匹数でもcaptureイベント数でもない。

3,853行masterの解釈可能な3,834日時は日界誤り0、日時解釈不能19行は保持。新規1,117行は全て解釈可能で日界誤り0。9/29 00:00/00:08/00:19は9/28夜、10/15 00:20は10/14夜、07:00から当日夜。

**追加blocker:** 回復した最新数量訂正workbook `ead12...` は07h版から派生しておらず、同じcapture view101行の暦日誤りを再導入していた。数量は訂正されているがlatest authoritative viewとして採用できない。原本bytesはincomingに保存し、別の派生CSVで両訂正を合わせる。XMLを読み同じ314行をZIP内CSVと照合し、night101列値だけ変更した。非捕獲・未解決カテゴリ・数量・他列は変更なし。strict ISO parserで日時解釈不能23行は保持した（元文書の24件はこのparserでは再現しない）。

## GPX 67件の独立再計算

旧ZIPの照合CSVを追認せず、そこに記されたGPX SHAを原本と突合した。9月15夜原本を既存保存ファイルから、10月7夜をPR #39/#41の復元原本から取得。計22ソース（うち捕獲あり20夜）を解析した。

全67捕獲遭遇について、実trackpointの絶対時間差600秒以内で最近接Haversine距離を計算し、全67件が100m以内だった。既存照合CSVの距離との最大差は0.00497m（丸め誤差内）。2匹同時遭遇は1つの時空間照合なので、67イベントの照合結果を68個別の独立位置観測に言い換えない。

**これは観測ログと実GPXの整合性。予測100m±10分の的中率、公式Recall、校正、P0/P1成績やChampion昇格の根拠ではない。** 原ORIGINAL freezeが不足する夜を後付け予測で埋めていない。

## 二重計上防止

| 重複元 | 夜 | 既存イベント | 既存匹数 | 候補内の扱い |
| --- | --- | ---: | ---: | --- |
| MAIN capture/individual | 9/28 | 5 | 6 | 全5件が同時刻・同位置で候補に含まれる。既存CAP IDを保持 |
| PR #39 | 10/14 | 3 | 3 | 全3件が候補に含まれる |
| PR #39 | 10/15 | 3 | 3 | 全3件が候補に含まれる |
| 合計 | — | 11 | 12 | source evidenceとしてリンクし、追加捕獲としてappendしない |

PR #43は原本archiveのみを追加しているため、そのmergeだけでcanonical capture表に11重複行が自動追加されるわけではない。後の取込で二重計上を防ぐ必要がある。新規67イベント/68匹のうちMAIN既存分は5イベント/6匹、さらにPR #39の統合と合わせるなら6イベント/6匹も同じ観測である。個々の対応11行は `event-identity-reconciliation.json` に既存ID、旧archive ID、数量訂正版IDを記録した。

## 限定修復案

`/workspace/scratch/ded5451af149/data-audit-repair/` にASCII名の原本copy2件、incoming receipt、根拠文書、07h派生CSVと再現スクリプト、回帰テスト案を用意した。GitHub書込は親へ集約する。receiptはSHA-256、bytes、Git blob SHA1、元ファイル名、元保存identity、受領UTC、duplicate statusを保持し、原本workbookの101行日界問題を明記する。派生CSV `historical_capture_display_september51_07h.csv` は314行、SHA `979ba7f96259c9202d084e302d08cd8f72f04017b80d4d23cc465242ca26ad07`。候補はCI/独立review待ちであり、MAIN正本認定はしていない。

補修builderの出力保護も限定修正した。receipt/sourceはrelative incoming配下のregular fileに限定し、rootからの祖先を含むsymlinkを拒否。検証済bytes snapshotを解析し公開前に再hashする。同bytes既存候補はinode/mtimeを変えず再利用、異bytes既存候補は拒否、新規出力は排他作成する。実temp fixtureで9保護テストのRED（11 failures、path逸脱subcases含む）→GREEN、続いてFIFO source/targetがblockする2 RED→O_NONBLOCKによるfail-fast GREENを確認し、実候補のCSV SHA/inode/mtime不変も確認した。

6 suites計27ローカルテストPASS（#39:5、#41:2、#43旧ZIP:1、07h:2、既存同時捕獲:2、新候補:15）。最小候補snapshot全suiteも15PASS。監査fixtureだけのimport欠損を解消後にPASSを確認。既存raw/ORIGINAL予測/モデル/Championを変更せず、最新GitHub CIと独立reviewが通るまでDraft/merge禁止を維持する。

証拠ディレクトリ: `/workspace/scratch/ded5451af149/data-audit-evidence/`。主要JSON: `restored-integrity.json`, `pr41-restored-integrity.json`, `library-source-integrity.json`, `counts.json`, `workbook-audit.json`, `corrected-row-changes.json`, `gpx-independent-results.json`, `event-identity-reconciliation.json`, `local-test-results.json`, `final-api-heads.json`。再計算スクリプトは `reproduce_audit.py`。


## Parent publication addendum

The eight-file source repair was appended to existing Draft PR43 at1a95d5c2. A later append at76680cba preserved15 raw September GPX originals in a verified source-evidence ZIP; receipt and independent evidence explicitly add zero observations and do not certify search completeness or Negative/Gold eligibility. The independently verified April and cross-PR audit documents already on that branch were preserved unchanged. Final fixed-profile full-suite receipts are indexed in the Work checkpoint manifest; the historical local test counts above retain their original scope. Hosted CI remains blocked and main was not changed.
