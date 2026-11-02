# Qwen指摘本文の独立意味検証（合成コードのみ）

記録日：2026-11-02
対象：既存PR #136、`qwen2.5-coder:1.5b`。
元の発言：[GitHub Actions run 41354115659](https://github.com/haji84/habuAI-private/actions/runs/41354115659) ／ job `124990438170` の `QUALITY_DIAG`。
再現試験：`tools/dashboard_ai_review/test_semantic_claim_audit.py`。仕様・合成コードは `quality.py` の6固定ケースから読み、ラベルを書き換えない。

## Qwenが実際に書いた指摘の検証

| 合成ケース | Qwenの主張（要約） | 静的引用判定 | 独立した実行・検証 | 指摘内容の結論 |
|---|---|---|---|---|
| `stale_prestart_defect` | 「探索開始前の測位を許す」 | 不正な引用。複数行を1行として繋ぎ合わせた | `should_record(95,100)` は `True` を返し、開始前の95を拒否できていない | **問題の内容は再現できる**。ただしQwenの引用は不合格 |
| `unknown_owner_defaults_to_self` | 「`item.owner` がnull/undefinedだとTypeError」 | 指定行と引用が不一致 | `normalizeOwner({owner:null})` は `self` を返す。モデルが主張した例外は起きない | **主張は矛盾**。別の問題である本人誤計上の可能性と混同しない |
| `correct_prestart_guard` | 「開始時刻以上かを検査していない」 | 指定行と引用が不一致 | `should_record(95,100)` は `False`、`should_record(100,100)` は `True` | **主張は矛盾** |
| `correct_owner_validation` | 「`self` と `other` の検査がない」 | 指定行と引用が不一致 | `unknown` は例外で拒否し、`self/other` は通す | **主張は矛盾** |
| `defined_callback_not_missing` | 「GPSのpositionを検証せず返す」 | 実コード行の引用は一致 | この合成ケースの要件はコールバック結線で、位置の妥当性検証ではない。定義済み関数は正常に実行 | **追加要件がないため不具合認定不能** |
| `complete_labeled_html` | 「headerの閉じタグがない」 | 実コード行の引用は一致 | HTMLパーサで `<header>` と `</header>` が1組、buttonにaria-labelが存在 | **主張は矛盾** |

合計：再現できた主張1、実行・構造と矛盾4、要求仕様上の根拠不足1。ただし本表は**6件の既存Qwen発言を検証した事例集**であり、残り34例・実製品全体の正誤を断定する統計ではない。

## 今後の正式分類と採点

1. **SOURCE_CITATION_REJECTED**：コードの引用と対象行が一致しない。AIの不具合主張が正しい可能性は残るが、引用は審査根拠に採用しない。
2. **SOURCE_ANCHORED_ONLY**：引用が実コードに一致。しかしそれだけではバグではない。
3. **REPRODUCED_CLAIM**：AIが主張した誤動作と、それを引き起こす具体的な入力・実行結果が一致する。再現したテストを示す。
4. **CONTRADICTED_BY_EXECUTION**：AIの主張と同じ条件で実際に動かし、その主張に反する結果を観測。
5. **INSUFFICIENT_REQUIREMENT_FOR_DEFECT**：その動作を禁止する要件がなく、確定バグとみなせない。追加仕様をAIが勝手に創作しない。
6. **INCONCLUSIVE**：再現のためのデータ、入力、端末条件、仕様が足りない。再現不能なものを自動的に「誤検出」「0件」にしない。

**判定原則：** 合成ホールドアウトでは `20 positive + 20 negative` の確定ラベルは固定したまま、AIの**主張内容**の再現と、コードの**原文引用**の正確さを別々に採点する。ひとつでも違えば「確認済みバグ」に自動昇格させない。Qwenの校正スモーク6例の合格・ソース全区間レビューの成功と、この意味検証の合格は別ゲート。

## 40件の本文取得経路

追加ファイル `tools/dashboard_ai_review/synthetic_claims.py` と `measure_holdout.py` で、モデルが生成した**合成コードに関する文字列だけ**を1件ずつ `HOLDOUT_CLAIM_TEXT:` に出す。記録内容はID、行番号、`problem`、`impact`、`code_quote`、引用検証理由、`UNVERIFIED_REQUIRES_CLAIM_SPECIFIC_COUNTEREXAMPLE`。入力済みholdout v1の正解、件数、合格閾値、推論プロンプトは変更しない。

**40件の個別の意味検証はまだ完了していない。** この出力を使って独立検証する。ログを公開に含めるのは固定合成コードだけ。公開のGitHubリポジトリへGPS原本・捕獲場所・認証情報を追加しない。main統合/本番公開は保留。
