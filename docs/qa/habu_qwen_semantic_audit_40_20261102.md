# Qwen2.5-Coder 1.5B｜指摘本文40件の意味照合（合成コード限定）

作成日：2026-11-02
対象：既存PR #136。
実Qwen原文：GitHub Actions [run 41369985317](https://github.com/haji84/habuAI-private/actions/runs/41369985317)、job `125038398498`、固定HEAD `30c5315174d6da2931a0be7fe9fa05e3222f90c4`。
モデル：`qwen2.5-coder:1.5b`。
固定コーパス：`tools/dashboard_ai_review/holdout_v1.py`、Git blob `daac52dfed89cb946e736aed49ed109a56307ffa`。
正解コード・正解ラベル：**一切変更なし**。

## 判定概要

- 実際の入力で確認した不具合と説明の方向性が一致：**16件**。**モデルの引用が正しい・精密な因果説明が成立した、という意味ではない**。
- Qwenの主張が合成コードの正しい動作またはソースと矛盾：**20件**。
- 不具合版に真の欠陥は存在するがQwenの説明が的外れ、自己矛盾、または要件外：**4件**。
- 原文40件において、当時の文字列引用ゲートを通過したのは9件。ただし**出典行が一致しても実際の不具合確定ではない**。この指標と本文の意味判定を混ぜない。

### 判定の限界

この文書は、実際にQwenが書いた日本語・英語の主張について、固定合成コードと実行証拠を参照して**作成者が解釈した一次監査**である。第三者または別AIの独立正式審査ではない。

`test_original_qwen_claim_audit.py` はコードの実行結果、母集団・対応関係、原文/判定ファイルのGit blob固定を検証する。しかし自然言語の因果説明すべてを機械的に証明したわけではない。境界例は保留に分けた。

**最重要：この40件の監査を使ってQwenのプロンプトを調整し、同じ40件の点数を上げても未見コードに一般化した性能とは言えない。** 今回は診断と出典照合を改善し、固定コーパスをいじらない。

## 全40件の指摘本文と判定

| No. | 種別 | 合成ケースID | コード | 指摘本文の一次判定 | 原文引用 | 固定入力での根拠 |
|---:|---|---|---|---|---|---|
| 1 | `capture_kind` | `861163c0458e3dbd` | 不具合版 | 実行結果と方向性一致 | 引用位置不合格 | With sighting input, 'not roadkill' returns 1 and incorrectly counts it as capture. |
| 2 | `capture_kind` | `3ac311996fe9795e` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | Exact capture-only filter returns 0 on a sighting, contrary to 'always true'. |
| 3 | `species_filter` | `62d12de11961f5d9` | 不具合版 | 実行結果と方向性一致 | 引用位置不合格 | With ヒメハブ input, the code returns 1 despite exact ハブ requirement. |
| 4 | `species_filter` | `06354b2b6d70773a` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | Exact ハブ test rejects ヒメハブ; the claim of accepting it is false. |
| 5 | `seven_hour` | `4b8e359d632c9cba` | 不具合版 | 説明不一致・根拠不足 | 引用位置不合格 | The bad 06:00 boundary returns false, but the model's impact inaccurately says it returns true for hours before 07:00. |
| 6 | `seven_hour` | `ac388422ed977b73` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | 06:00 is accepted by the correct before-07:00 rule, contrary to the model. |
| 7 | `latitude_range` | `eaa975e0945e29a4` | 不具合版 | 実行結果と方向性一致 | 引用位置一致 | Latitude 100 is accepted by the -180..180 check, contrary to the -90..90 requirement. |
| 8 | `latitude_range` | `5f81a8acef9eb04c` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | Latitude 100 is rejected by the -90..90 check, refuting the model. |
| 9 | `longitude_range` | `f1e0c8fe2b4b9b6d` | 不具合版 | 実行結果と方向性一致 | 引用位置不合格 | Longitude 200 passes the -360..360 check, violating -180..180. |
| 10 | `longitude_range` | `85c4b951b77b3465` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | Longitude 200 fails the correct -180..180 check; rejection is explicit. |
| 11 | `event_id_dedup` | `2bf126048752fa72` | 不具合版 | 実行結果と方向性一致 | 引用位置不合格 | An already recorded ID equal to seen[-1] is accepted again. |
| 12 | `event_id_dedup` | `a95d44e465c6c44d` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | The duplicate ID is rejected by membership, contrary to the model. |
| 13 | `boolean_not_count` | `1ffd454b0aa523b0` | 不具合版 | 実行結果と方向性一致 | 引用位置不合格 | Python bool True passes isinstance(value,int), contradicting requirement. |
| 14 | `boolean_not_count` | `c7be0a54b75e44da` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | type(True) is int is false, so the boolean is correctly rejected. |
| 15 | `confirmed_zero` | `b9e5f3f79d66524f` | 不具合版 | 実行結果と方向性一致 | 引用位置不合格 | Zero with confirmed=false is accepted because only count==0 is checked. |
| 16 | `confirmed_zero` | `bcee3e098587fec8` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | Unconfirmed zero is rejected by confirmed is True; the alleged omission is absent. |
| 17 | `exposure_not_inferred` | `bc1f24b4d42cb851` | 不具合版 | 説明不一致・根拠不足 | 引用位置不合格 | Unknown exposure is accepted as a zero observation, but Qwen incorrectly argues that empty captures should return True; this explanation does not identify the actual violation. |
| 18 | `exposure_not_inferred` | `08917d60a0709b41` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | searched=false with empty captures is rejected; when searched=true with captures nonempty it is also rejected. |
| 19 | `path_traversal` | `6a2950a1a4e83611` | 不具合版 | 実行結果と方向性一致 | 引用位置不合格 | A path containing '..' is accepted unless it begins with '/'. |
| 20 | `path_traversal` | `73d232d631c08a20` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | The '..' path segment is explicitly rejected in the correct implementation. |
| 21 | `capture_limit` | `e22ae9a7a0701493` | 不具合版 | 実行結果と方向性一致 | 引用位置一致 | Count 101 passes the 0..999 check, violating the 0..100 limit. |
| 22 | `capture_limit` | `3b987235f93a1691` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | Count 101 fails the exact-int 0..100 check, contrary to the model. |
| 23 | `digest_equality` | `56d66ed9419624bb` | 不具合版 | 説明不一致・根拠不足 | 引用位置不合格 | Two distinct 64-character hashes are trusted by length equality; Qwen's stated reasoning about lengths differing while contents are equal is internally wrong. |
| 24 | `digest_equality` | `f8544edc13f9b299` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | Distinct equal-length digests are rejected by exact equality, the required behavior. |
| 25 | `gap_inclusive` | `aa48572f6eed538e` | 不具合版 | 実行結果と方向性一致 | 引用位置不合格 | At exactly 300 seconds a required new segment is omitted due to > rather than >=. |
| 26 | `gap_inclusive` | `22570ed2435be19c` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | Exactly 300 seconds is accepted by >=, contrary to the alleged missing boundary check. |
| 27 | `save_ack` | `f9b3c4fbd57552ed` | 不具合版 | 実行結果と方向性一致 | 引用位置不合格 | Failed durable write still yields saved=true. |
| 28 | `save_ack` | `4b180441648c1e3b` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | Failed write yields false with ===true, so the model's warning is not borne out. |
| 29 | `free_route_export` | `568dc5a6463ad176` | 不具合版 | 実行結果と方向性一致 | 引用位置一致 | FREE is in the permitted export set, violating the exclusion rule; model points at a comment instead of causal logic. |
| 30 | `free_route_export` | `9fb0507b611854d8` | 正常版 | 実行結果と矛盾 | 引用位置一致 | FREE is excluded by the implementation; a claim that it permits FREE is contradicted. |
| 31 | `owner_confirmation_boolean` | `d4e51c4bf5e02e4f` | 不具合版 | 実行結果と方向性一致 | 引用位置一致 | The string 'false' is truthy, leading to incorrectly confirmed=true. |
| 32 | `owner_confirmation_boolean` | `57afa9379da2d8f0` | 正常版 | 実行結果と矛盾 | 引用位置一致 | The exact boolean comparison rejects string 'false', contrary to the model. |
| 33 | `digest_hex` | `0bd3854e8d9eda61` | 不具合版 | 実行結果と方向性一致 | 引用位置一致 | A 64-letter nonhex value passes length-only SHA validation. |
| 34 | `digest_hex` | `880013143d45933f` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | Nonhex digest fails the regular expression, contrary to the model. |
| 35 | `distinct_same_time` | `386d0b6b0f1f290d` | 不具合版 | 実行結果と方向性一致 | 引用位置不合格 | Equal timestamp but different IDs are treated as duplicates. |
| 36 | `distinct_same_time` | `70577f7496bf4291` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | Different event IDs are not considered duplicates, contrary to the model. |
| 37 | `monthly_sum` | `842236fc6b030b3f` | 不具合版 | 実行結果と方向性一致 | 引用位置一致 | Monthly counts [2,3] produce max=3 rather than required sum=5. |
| 38 | `monthly_sum` | `7325dd62809a9cfc` | 正常版 | 実行結果と矛盾 | 引用位置一致 | The reduce sum returns 5, and including zero-count months is mathematically correct. |
| 39 | `privacy_export` | `66e24ad095c76d71` | 不具合版 | 説明不一致・根拠不足 | 引用位置不合格 | Record with lat key is accepted by return true, but Qwen instead complains that the function is not exported; the claimed fault is unrelated. |
| 40 | `privacy_export` | `2d89ab7f1f0b76a6` | 正常版 | 実行結果と矛盾 | 引用位置不合格 | A record containing lat is rejected; missing enforcement claim is contradicted. |

## 以降の品質ゲート

1. **証拠保全：** 実Qwenの40回答を `docs/qa/synthetic/qwen_claims_run_41369985317.json`、一次判定を `docs/qa/synthetic/qwen_claim_adjudications_run_41369985317.json` にバイト固定。後から評価結果を都合よく書き換えない。
2. **根拠段階の区分：** コード引用位置の照合、固定入力で実際に起きた誤動作、Qwenが表現した主張の真偽を別々に記録。
3. **一般化可能な検査：** 指摘をしてもソースのコメント行しか引用できない場合は、実行時不具合の証明として認めず拒否理由を残す。再現不能なものは無理に確定しない。
4. **未見評価：** 同じ40件への過剰適合を避け、評価手法が固まってから未見の別ケースと別実行条件で精度を検証する。現時点でモデルの正式品質ゲートはHOLD。

## 安全境界

本監査は合成コードだけを使用。個人の捕獲位置・GPS/GPX原本・個人情報を公開GitHubに追加しない。CodeRabbit/Copilotは再起動しない。main統合・本番公開・新規PR・課金・権限変更なし。
