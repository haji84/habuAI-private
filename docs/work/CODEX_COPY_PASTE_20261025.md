# Paste into Codex: HABU-AI complete parallel-development execution order

This is an operational handoff prompt. It must be supplied to an actually connected Codex session with repository read/write access. A GitHub Issue, PR or Markdown file alone does **not** start a Codex worker.

```text
【ハブAI 複数モデル高精度化＋探索証拠認証 並列自律開発 実行指示】

あなたは haji84/habuAI-private のCodex統合責任者です。
最上位正本: https://github.com/haji84/AI-/issues/1642
対象main: https://github.com/haji84/habuAI-private

この指示は既存 Master Goalを置き換えません。これまでの実装、データ正本、原本P0、
科学KPI、承認ゲートを厳守したまま、ハブ探索・捕獲予測AIの完成まで
実際にコードを書き、検証し、修復し、成果を統合するための実行指示です。

【最初に絶対読む】
1. AGENTS.md
2. docs/specs/master-goal-1642-source.md
3. docs/specs/master-goal-1642.md
4. docs/work/CODEX_PARALLEL_MASTER_20261025.md
5. docs/work/CODEX_LANES_20261025.md
6. docs/work/CODEX_MODELS_20261025.md
7. docs/work/CODEX_ACCEPTANCE_20261025.md
8. docs/work/CODEX_STATE_20261025.json
9. docs/plans/master-goal-1642-training-corpus.md
10. docs/plans/master-goal-1642-feature-models.md
11. docs/plans/master-goal-1642-composite-inference.md

【START: 現mainを直接監査】
現在の正確なmain HEAD SHA、最新PR、Actions、テスト、モデル、
データセットのsource/usable_at、feature/universe、P0/Pn Freeze、
ORIGINAL/REPLAY、PDCA Bridge/Orchestrator、Champion Registryを監査。
OPEN PR #32/#33/#46（予測基盤）、#44/#45/#50/#73をまず確認し、
衝突する実装は既存PRを再利用・安全に修復する。新規PR乱立禁止。
mainにないGOAL.md/PROJECT_STATE.mdがあれば勝手に実在と報告しない。

【並列タスクを編成】
統合責任者1つの下で必要な数だけ独立Codexワーカーを編成する。
各ワーカーは異なるgit worktree/branch・AllowedPaths・担当仕様を持つ。
同一ファイルを複数ワーカーが同時に編集しない。

G0: 学習データ / 評価 / feature cutoff / prediction universe の共有契約を
まず固定し独立設計レビューと契約テストを通す。

並列レーン:
 E: 実探索/単なる通行の認証。まず動きが混在した4審査パケットを詳しく調査し、
    残り71、合計75件へ展開。動物目撃・原文・実GPX・OSM補助線・
    捕獲/目撃/轢死を照合。探索時間・結果網羅性・重複/個体IDを別認証。
 F: 出発前に利用できる道路・DEM・天候・風・雨・月・潮汐・
    生態・探索圧等を研究し、ex-ante特徴量/母集団とsource availabilityを構築。
 M1: 確率校正付き占有/遭遇モデル、GAM/正則化・Boosting・平滑化基準モデルを比較。
 M2: 1km Top10→500m→250m→100m道路Zone→100m×10分の
    時空間階層ランキング候補モデルを開発。
 M3: 努力量条件付き捕獲数・発見率・大型分類・生物反応・
    アンサンブル等を、証拠が許すターゲットだけ実装・比較。
 V: 独立レビュアー/密封確認/未来日blockのスプリット・リーク・
    母数・不確実性/モデル比較。モデル構築担当と分離。
 I: レビュー合格済みの各部を既存親Orchestrator/REPLAY/
    Champion/次の正式P0/Pn/ルートA,B,Cに統合。
 
E/F/VはG0後すぐ並列化。M1/M2はデータ・評価インターフェースに依存せず
純粋な実装・契約テストを並列開始可。ただし未認証データを使って正式に
学習・的中率測定することは禁止。M3のFit/EnsembleはM1/M2の
実測OOF成果など依存条件が揃ってから。Iは依存PRを独立に審査して統合。

【全体の目的】
奄美・加計呂麻のハブ出現・活動・本人捕獲を科学的に予測する。
Stage1正式KPIは1km Area Top10 Recall ≥90%。
最終評価は100m±10分。ルート3案 A=捕獲期待値最大、
B=時間距離当たり期待値最大、C=大型又は未探索/分散高期待。
高精度は成果目標であり達成を捏造しない。
常に観測範囲、母集団、失敗、不確実性、モデル版を明記する。

【安全】
07:00 JST探索夜。個体とイベントを分け、本人47匹（2026年8月月計）、
2026/10/20まで累計243匹の確定史実を根拠なく変更しない。
GPX通過・低速運転・他種動物目撃はハブ不在でも
「ハブを探した道路」の確定でもない。
現状3,491非捕獲レビュー候補・774グループ・75優先パケットに
正式Negativeを一括付与しない。元データ/ORIGINAL/P0を改変しない。
OSM9/25補助道路は8月の事前予測入力と偽らない。
観測にないGPX・気象・個体ID・負例・経路・的中率を作らない。
既存M0〜M3モデル定義を変更しない。

【研究・モデル比較】
各モデルは同一の認証済データ、同一future-blocked折り、
同一全域Universeと外側FNを含む正式母数で比較。
一部の陽性データだけから確率校正や負例をでっち上げない。
未入手の天気や事後情報を昔のcutoffへ流さない。
特徴量の時間差、相互作用、重要度、除外再学習アブレーション、
キャリブレーション、季節/雨後/地形/地理/努力量の層別評価を行う。
未到達ならFAIL/NEED_MORE_DATAを報告し改善を続ける。
密封した未公開確認データは学習AIへ渡さずVのみが最終判定する。

【開発ループ】
現状確認→Gap→有用機能提案→独立設計レビュー→
bounded slice選択→テスト先行→実装→対象テスト→
実データE2E→CI→別AI批判レビュー→修正(同一PR)→
最新HEADで最終CI→安全なmain統合→fresh main E2E→
永続証拠＋CODEX_STATE更新→次の未完了タスク。
毎回PRを作り直さない。
失敗の原因と最小修正場所を決め、修復で保護機能を緩めない。
CIの実行開始だけで成功報告しない。
GitHub Actions中心で必要な数だけ並列し、実行枠・費用を監視。
レビュー不能ならレビュー済と報告しない。

【Human Gate】
最上位GOALの変更、重要なアーキテクチャ変更、
破壊的原本変更、権限/セキュリティ、公開、課金、
本番Championの信頼境界変更は事前承認が必要。
通常のテスト、修正、PR、レビュー、合格済み通常統合は自律。
必要な本人確認が出たら、問いを具体的に限定して
科学的認定だけBLOCKEDにし、その他の並列レーンを止めない。

【直近の最初の3到達物】
A. current-main監査＋既存OPEN PR差分＋G0契約と失敗テスト
B. E:75パケットを検索/非検索に仕分けるための追加証拠審査
   (独立証拠がないものはUNKNOWN維持)、
   F:予測前Universe/feature availability実装、
   V:シール確認・外部FN含む分母定義
C. M1/M2モデル候補複数を同じ適格データ上で比較できる実Fit/E2E
   (適格データが足りなければ正しいNEED_MORE_DATA判定とモック境界)

【状態報告】
毎回実行したコミット/PR/Actions URL、
モデル別実Fit件数・対象探索夜・データ素性、
テスト合格数・失敗数、標本数・リーク監査、
Stage1/100m±10分の正式到達/未検証を分ける。
GitHub Docsと状態ファイルに保存する。
明示的権限外の作業は拒否しながら、
可能な通常の開発を止めない。
計画を書いて止まらず、現在の実行環境でできる範囲の
実装・テスト・修復を開始する。
ただし未接続のCodexセッションのバックグラウンド実行を
偽って報告してはならない。

最初の返答は「取得した正確なmain SHA / 既存PR監査結果 /
G0欠落/並列laneの最初のbounded slice / 実行した第一変更」で返す。
私に確認し直すのではなく、承認が必須のHuman Gateだけ質問する。
```

## Immediate proof checklist for Codex owner

- Read repository source/goal and all docs by actual GitHub file contents, not inferred chat memory.
- Publish audited exact `main` SHA, open PR head SHAs and source-level differences.
- Independently review G0 contract before rushing to 7 parallel branches.
- Actually launch Codex work in isolated worktrees only if the current Codex runtime provides real independent workers; if not, execute sequential bounded tasks honestly.
- Use an existing Actions CI run only if it tested the **exact** branch HEAD and relevant changed paths.
- At session end, report what **was actually executed**, what is blocked, and the deterministic next invocation. Creating Issues/docs is not equivalent to starting a job.
