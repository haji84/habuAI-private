# 小型AIの指摘を実行証拠で検証する共通契約 v1

対象：ハブAI 既存PR #136。主目的は小型AIのコード審査の「指摘を多く出す」行動を、証拠で検証可能なものに変えること。新機能・外部レビューサービスの導入ではない。

## 1. 判定を三層に分離

1. SOURCE_ANCHORED_ONLY：引用したコードが固定HEAD上の実行行に存在する。これだけではバグではない。
2. REPRODUCED_STRUCTURED_BEHAVIOR：AIが特定の入力に対して予告した実行結果を、独立した信頼できる実行装置が確認し、それが独立に定義された必要動作に反している。これは具体的な入出力主張の証拠になる。
3. NARRATIVE_NOT_AUTOMATICALLY_VERIFIED：問題文の原因分析、影響範囲、修正提案の適切さは別の検証。実行値が一致しただけで文章全体が正しいとは認定しない。

## 2. 再現主張の入力契約

共通エンジン：tools/dashboard_ai_review/behavioral_evidence.py

AIの構造化主張には、以下の項目を要求する。

- schema: habu-structured-behavior-claim-v1
- case_id: モデルが審査した対象の識別子
- source_sha256: 実際に確認したコードのSHA-256
- input: 具体的に誤動作すると主張する入力。文字列や数値の型も維持。
- claimed_actual: その入力で実際に返ると主張する値
- claimed_required: 仕様上必要だと主張する値
- line と code_quote: コードの追加行番号と、その行から引用した原文
- problem と impact: 問題の説明。実行証拠とは別評価。

これらをAIが書いたというだけでは、何も再現済みにはならない。

## 3. 信頼できる実行結果との突合

- 実行装置は、モデル出力のコードをそのまま実行しない。
- 現段階では固定した合成コードの保管庫 holdout_v1.py（Git blob daac52dfed89cb946e736aed49ed109a56307ffa）のみを実行できる。
- 現段階での実行入力は、事前に正解を確定した合成ケースの入力のみ。AIが違う入力を提案した場合は UNTESTED_MODEL_INPUT として止める。
- 信頼できる実行装置が観測した actual、要求仕様の expected、対象ソースのハッシュが一致しているかを検査する。
- Python の True と 1 を同じとみなす暗黙の型変換は行わない。
- 単独の compare_behavior 関数は、呼び出し元が用意した観測情報の出所を暗号学的には保証できない。実アプリへ使う際は別途、権限分離した隔離実行器と実行証拠の真正性保証が必要。

## 4. 不合格・保留の契約

| 状況 | 実行証拠の判定 |
|---|---|
| 自然言語の指摘だけで、具体的な入力・実結果・期待値がない | UNSTRUCTURED_CLAIM |
| 元のケースとソースのハッシュが合わない | SOURCE_OR_CASE_MISMATCH |
| AIが指定した入力を固定試験で検証していない | UNTESTED_MODEL_INPUT |
| 実行結果と必要動作が一致する | NO_DEFECT_ON_TRUSTED_WITNESS |
| AIの主張した必要動作が固定仕様と異なる | CLAIMED_REQUIREMENT_CONTRADICTED |
| AIの予告した実行結果が現物と異なる | CLAIMED_RESULT_CONTRADICTED |
| 実際の動作の違反がAIの構造化主張どおり再現される | REPRODUCED_STRUCTURED_BEHAVIOR |
| 実行値は再現したが、コード引用が誤っている | REPRODUCED_BEHAVIOR_BAD_CITATION |
| 信頼できる実行装置が失敗・未実行 | TRUSTED_WITNESS_EXECUTION_FAILED |

すべての判定で、PRの正式承認・製品本番統合の許可フラグは false とする。一般的なコード、ネットワーク、端末の実機データについて、現段階での証明はできない。

## 5. 既存40件のQwen結果に適用

既存の実Qwen原文は docs/qa/synthetic/qwen_claims_run_41369985317.json に固定されている。これは自由記述の推測であり、モデル自身が明示した input / claimed_actual / claimed_required を持っていない。

そのため、新しい実行証拠検証器で自動的に確認済みバグへ昇格させない。既存の独立意味照合（説明方向が一致16、矛盾20、根拠不足4）は人手相当の一次解釈として別に保管する。

汎用化したのは「証拠の形式と突合条件」であり、モデルの判断能力自体ではない。実Qwenの品質ゲートはHOLDのままとする。

## 6. 受入試験

tools/dashboard_ai_review/test_behavioral_evidence.py では、偽のモデル入力、異なるソースハッシュ、嘘の戻り値、誤った仕様、コードの引用不正、型の誤判定、NaN、任意コード実行の拒否、固定40件の正例・負例、元Qwen40件の非自動承認を確認する。

固定ケースそのもの、評価ラベル、モデルの過去回答は書き換えない。実製品を試験する場合は、別途権限と隔離実行方式を正式設計し、安全審査と承認を受ける。

外部CodeRabbit/Copilotの利用、新PR、main統合、本番公開、課金、権限変更はしない。個人のGPS・捕獲位置・原文ログを公開環境に送信しない。
