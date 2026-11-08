# PR #136: PR #138で実行確認したQwen 1.5Bを補助レビューへ接続

更新：2026-11-03
対象：haji84/habuAI-private、既存PR #136のみ
元実装：PR #138 HEAD `53247ab41d6797c98f7e1c12bd2075ca5af7600a`
元実行証拠：[PR #138 実Qwenレビュー SUCCESS](https://github.com/haji84/habuAI-private/actions/runs/41440807341)
元レビュー：`tools/free_ai_review/review.py`（Git blob `da2974e6922dfd54b5f96479d38f20c6c669e115`）

## 接続方式（審査AIの新規開発ではない）

動いた既存1.5Bレビューコードを、同じPR #136の
`tools/advisory_qwen/review.py` に移植。主要な変更は
`mobile/`用ソース選択を `dashboard/`、`scripts/`、`tests/`へ差し替えること。
元の完全差分の分割、各segment ID検査、失敗時の再試行、未処理末尾を許さない
fail-closed、単一合成バグの実モデル検出の試験を維持する。
参照元の固定ロジック・テスト内容を再設計して別の審査AIを作ることはしない。

## 本人データの保護

`SOURCE_SUFFIXES` は Python/JS/HTML/CSS/シェル等の**コード**だけ。
`.json`、`.jsonl`、`.gpx`、`.ndjson`、`.kml`はレビュー対象外。
`dashboard/private/`、`dashboard/raw/`、`dashboard/data/`、
`dashboard/dist/`、`scripts/private/`、`scripts/raw/`、
`tests/private/` などのパスを拒否する。
GitHubの公開コード以外の原本や秘密情報を取得せず、
外部有料AI・個人捕獲GPS・実探索ログをモデルに送信しない。
推論はGitHub標準公開ランナーのlocalhost Ollamaのみ。

## 既存Actionsの再利用

`.github/workflows/habu-free-dashboard-review.yml`内の
**既存1.5B起動ジョブをそのまま共有**し、二重のモデルpullや別runnerの新設を避ける。
レビュー試験はモデルダウンロード前に実行し、
reviewの実行結果は GitHub Step Summary と Actions log に出す。
`PR136_QWEN_ADVISORY=COMPLETED_UNVERIFIED` または
`PR136_QWEN_ADVISORY=HOLD_NONBLOCKING` を必ず出し、失敗した場合も
通常の製品機能開発を止めない。

元の6件較正、40件評価、構造化診断の失敗証拠は削除・偽装・改ざんしない。
1.5Bの厳格な研究ゲートが不合格でも、**研究結果はそのままHOLD**で、
補助モデルの結果だけを本番品質・正式独立承認と誤読させない。

## 合格と未合格を分ける

- モデルなし契約：移植元25件と追加のPR136コード選択テストをPASS。
- 実Qwen補助レビュー：同じPR #136 HEAD、ローカルQwen 1.5B、
  事前の合成不具合1件を検出し、予定したeligibleコード差分
  の全segmentを実モデルで処理した実ログがあって初めて
  `COMPLETED_UNVERIFIED`。
- 不完全、未実行、生成上限、トークン不足、モデルの誤り、
  データ対象外は明示的にHOLD。未処理をPASS扱いにしない。
- ソース行に見えるAIの指摘は**すべて未検証の提案**。
  実際の不具合かはテストで再現し、危険な指摘は採用しない。
- 独立審査AIを新規に作らず、既存のテスト、Actions、実機試験が本体開発の判断基準。
- PR136以外に自動接続したと主張しない。PR138は無変更。
- main統合、本番切替、公開設定・権限・課金変更なし。

公式品質判定の`QUALITY_HOLD`は元の研究用7B/1.5Bの
品質認定として維持し、PR136の通常開発工程を一律に停止させない。
