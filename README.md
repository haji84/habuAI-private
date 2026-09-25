# Habu AI Private Canonical Repository

ハブAIの非公開正本リポジトリ。実GPX、ハブログ、捕獲DB、GIS原本、加工データ、モデル仕様、凍結予測、評価結果、Evidenceを保存する。

## 重要ルール

- `data/raw/` の原本は上書き・削除しない。
- GPX欠損区間から架空軌跡を生成しない。
- 未探索セルをNegativeにしない。
- 日界は07:00 JST。00:00〜06:59は前日の探索夜として扱う。
- 評価夜より後の情報を学習・特徴量生成に使わない。
- OSMは補助データであり、公的道路GISとして扱わない。
- 追加データは `incoming/` へ置き、SHA-256・重複・形式・時刻を監査してから正本へ移す。
- mainへ直接投入せず、ブランチとPull Requestで反映する。

## ディレクトリ

```text
incoming/                 新規ファイルの受付箱
data/raw/gpx/             実GPX原本
data/raw/habu_logs/       ハブログ原本
data/raw/capture_db/      捕獲DB原本
data/raw/gis/             DEM・道路・境界等の原本
data/processed/           監査済み加工データ
features/                 学習用特徴量
model_specs/              freeze済みモデル仕様
predictions_frozen/       正解開示前の凍結予測
results/                  walk-forward・ablation結果
evidence/                 SHA-256・取得証跡・監査ログ
reports/                  人向け報告書
scripts/                  再現スクリプト
tests/                    自動検証
artifacts/                復元用分割アーカイブ
```

## 新しいGPX・ハブログの受入手順

1. 原本を `incoming/gpx/` または `incoming/habu_logs/` へ追加する。
2. `python scripts/register_raw_file.py --kind gpx --file incoming/gpx/FILE.gpx` のように監査する。
3. 出力されたSHA-256と重複判定を確認する。
4. 既存正本との対応、探索夜、07:00日界、時刻帯を監査する。
5. 問題がなければ `data/raw/` 配下へ原本のまま移し、Evidenceを更新する。
6. Pull Requestで差分と監査結果を確認してからmainへ統合する。

## 現在のOSM道路母集団

- 対象: 奄美大島・加計呂麻島
- 通常ルートway: 6,151
- 100m候補セル: 16,990
- 通常ルート道路延長: 1,803,154.185m
- 位置づけ: OpenStreetMap補助データ

詳細は `reports/osm_road_candidate_grid_report.md` と `evidence/osm/` を参照。

