# OSM道路母集団 監査・完成報告

作成日: 2026-09-25  
対象: 奄美大島・加計呂麻島  
位置づけ: OpenStreetMap補助データ（公的道路GISではない）

## 結論

奄美大島と加計呂麻島の道路を複数タイルで取得し、OSM要素IDによる重複除去、対象島ポリゴンによる島外除外、車両通行候補の分類、100mセル化まで完了した。林道・農道等に相当する `track`、`service`、`unclassified` を通常ルート候補へ含めた。明示的な車両禁止・私有制限は原本および道路中心線には残し、通常ルート母集団からだけ除外した。

既存の正式予測仕様は `candidate_source=official_road_gis` を必須とするため変更していない。このOSM母集団を公的データと偽って既存仕様へ投入することはできない。次の実GPX夜へ使用する場合は、地形・過去捕獲・時刻・気象等の特徴を同じセルへ付与した後、OSM補助データを許容する別の将来夜用仕様を、正解開示前にfreezeする必要がある。

## 監査結果

|項目|結果|
|---|---:|
|設定ルートタイル|36|
|対象島と交差したタイル|20|
|対象島外として未照会のタイル|16|
|保存したOSM JSON原本|92|
|取得したOSM要素|115,183|
|重複除去後の要素|102,721|
|node|96,136|
|way|6,585|
|対象島内way|6,583|
|島外way|2|
|通常ルートway|6,151|
|制限・非車両way|432|
|欠損nodeを含むway|0|
|100m候補セル|16,990|
|奄美大島セル|15,329|
|加計呂麻島セル|1,661|
|通常ルート道路延長|1,803,154.185m|

## 道路分類

|highway|通常ルートway数|
|---|---:|
|unclassified|2,338|
|residential|2,036|
|service|596|
|tertiary|415|
|track|324|
|primary|223|
|secondary|118|
|trunk|99|
|living_street|2|

通常ルート判定はOSMタグに基づく。タグが不完全な道路の実際の通行可否や現況を保証するものではなく、出発時には現地規制・災害・工事情報を別途確認する必要がある。

## 処理と追跡性

1. Nominatimから対象2島の境界ポリゴンを取得。
2. 全体範囲を6×6タイルに分割し、対象島ポリゴンと交差する20タイルだけをOverpassへ照会。
3. 応答失敗時はタイルを再分割。中断・再照会で生じた原本も削除せず保存。
4. OSM要素を種別・IDで重複除去。同一versionの内容矛盾はエラー扱い。
5. wayをnode列から復元。欠損nodeを直線で架空補間しない。
6. 対象島ポリゴンで島外道路を除外し、車両通行候補を分類。
7. 道路線分を平面直角座標系へ投影し、100mセル境界で正確に分割して延長等を集約。

取得・加工の各ファイルは `12_evidence/osm_road_evidence_manifest.csv` にSHA-256付きで記録した。派生特徴の定義は `07_features/osm_road_feature_definitions.json`、集計監査値は `04_processed_road/osm_processing_audit.json` に保存した。

## 成果物

- `02_raw_road/osm_acquisition_manifest.csv`
- `02_raw_road/osm_island_boundaries.geojson`
- `02_raw_road/osm_overpass_tiles/*.json`
- `04_processed_road/osm_road_centerlines.geojsonl`
- `04_processed_road/osm_road_candidate_cells.csv`
- `04_processed_road/osm_road_candidate_cells.parquet`
- `04_processed_road/osm_processing_audit.json`
- `07_features/osm_road_feature_definitions.json`
- `12_evidence/osm_road_evidence_manifest.csv`

## 未完了・制約

- 公的道路GISとの突合は未完了。
- DEM由来の斜面・山側/海側等はこのOSM道路母集団へ未結合。
- OSMには道路幅員、通行規制、道路種別が欠損または現況と異なる場合がある。
- 時刻binとモデル特徴量を付与した出発前予測ファイルは未生成。
- 次の実GPX夜を採点するには、正解開示前の予測freezeが必要。

## 出典・ライセンス

OSMデータ: © OpenStreetMap contributors、Open Data Commons Open Database License (ODbL) 1.0。
