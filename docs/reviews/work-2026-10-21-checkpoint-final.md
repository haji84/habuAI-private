# Work checkpoint 最終独立QA

**判定: PASS（documentation/evidence checkpointの保存に限る）。** 最終scope、出典、科学未検証の扱いに追加のblocking不整合は見つからなかった。Hosted CI復旧、main merge、canonical label admission、Champion/P0、科学性能、自動継続実行を承認するものではない。

レビュー対象: `/workspace/scratch/ded5451af149/work-checkpoint`。実装担当と別のレビュー担当がread-onlyで確認し、候補ファイルを変更していない。

承認した入力manifest:

`evidence/master-goal-1642/work-2026-10-21/manifest.json`

SHA-256 **`c756e6efd15dbf439cb9dbfca2f5e17557f839186d2ab09aa910458f3775d518`**

このmanifestは自身を除く**81ファイル**を列挙する。全81件の実bytes、SHA-256、Git blob SHA-1を当方で再計算して一致を確認し、未掲載ファイル/欠損/重複pathはない。自身のhashは外部に置く方針と整合する。本QAレポートを追加してmanifestを更新する場合、この承認は上記81件の内容不変とレポート追加・目録再生成に限定する。更新後の全ファイルhash照合とGit保存先照合は別途行う。

## 内容と分類

- CSVはR001〜R112を各1回、元の順序で維持。requirement本文と既存implementation/master/real-data validationは全112件不変。master_validationは112件NOT_VALIDATED、real_data_validationは101件NOT_VALIDATED/11件NOT_APPLICABLE。新科学完了を加算していない。
- 旧15 columnsの変更はR110.missing_data_or_executorのstaleなTask6a NOT_IMPLEMENTED訂正1 cellのみ。4つのlatest audit columnsが追加され、全112行が実在するmanifestとWORK_CHECKPOINTへ参照する。旧科学状態やTask7/Task8未完了は維持される。
- WORK_CHECKPOINT、AUTONOMOUS_EXECUTION、status最新節はmainと候補、過去milestoneと現在、active Work sessionと未実装のdurable controllerを区別している。mainはcanonicalのままであり、wake-up/無人実行の新たな保証はない。
- 当方のGitHub API再取得でもmain=`27f4832a23f0a3826ce96b87afb4f2f1c58aa936`、PR32=`123109a630b16f7af4e5cc41482ddd10839351b5`、PR33=`cd97e69a2d1cfb160b21f33a3e561be989d5ba8d`、PR43=`76680cba924b72a9069a4d12b0819cae95fd5349`を確認。3 PRともDraft/open/merged=false、base=同main。本文の非merge状態に整合する。
- CIはFree included2,000/2,000 minutes、Actions budget$0、Usage blockedという親の認証済account観測に基づくblockとして記録される。generic annotationのpayment failureは未立証と明記されており、支払失敗・設定変更・復旧済みの主張はない。
- 67 events/68 individuals、11 events/12 individualsの既存view overlap、101 legacy display夜界誤り、23 ambiguous display times、3,834 parseable/19 unparseable master rowsの分母をdata証拠と照合した。GPX67/67はhistorical associationで、予測的中・Negative/Gold・観測分母の証明に昇格していない。
- 15 September GPX sourceの保存も新規観測/label admissionとはしていない。PR43 source8+GPX3はincoming/限定derived candidateでありcanonical_promotion=false、source_staging_added_observations=0を維持する。

## 参照・schema・実行証拠

- 全**47 JSON**をstrict parseし、duplicate keysとNaN/Infinityを含まないことを確認。CSVの列幅、112 ID、task必須fields、relative evidence paths、preflight superseding pathsを確認した。独立したJSON Schemaファイルを新設したという意味ではなく、保存formatの構造と型/値/参照を点検した結果である。
- 19件のhistorical runtime path → durable repository path mappingはすべて実在する。PR32/33/dataの再現script/log supporting evidenceも保存され、scratch absolute pathsを現在の永続locationとして扱っていない。
- pinned runtimeは既存requirementsのnumpy2.2.6/scipy1.15.3/scikit-learn1.5.2/pandas2.2.3/pyarrow21.0.0に整合。PR32 **287 PASS**、PR33 **263 PASS**、最終PR43 **269 PASS**のexit0、ログ末尾、log SHA-256、expected count、pre/post file hash equalityを当方で再検算した。PR43は11 manifest filesと281 workspace filesが検査対象。各task actual_changed_filesのbytes/hash/Git blobも対象workspaceと一致した。本QA中にsuiteを再実行したとは主張しない。
- 歴史的global-runtimeのPR43 **266 tests**はGPX追加前のscopeとして明示され、最終11-file候補の269件に流用されていない。
- `selected-final-hash-checks.json` 内のPR43 all_match=falseを当方が指摘した。親はその失敗receiptを消さず、`preflight-qualification.json`で2 ancillary filesの古いlocalコピー、再同期、後続11-file pre/post manifestsおよび269-test exitへのsupersessionを明示した。現在の本文/manifestにも同区別があり、false receiptを最終PASS証拠としていないことを確認した。
- secret-pattern検査でtoken/private-key/credential URLの一致はなかった。原本、ORIGINAL、main、モデル、依存、workflow、permissionの変更や私的データの外部公開を、このcheckpoint作成の成果として認めていない。

初期QAで挙げた旧PR43 head/runtime scopeと、scratch参照の保存不足も修正されている。残る科学・production・CI・integration gatesはcheckpointに明示され、完了扱いされていない。

独立検査の補助結果は候補外の `checkpoint-final-validation-refreshed.json`、`checkpoint-final-semantic-validation.json`、`checkpoint-review-remote-observations.json` に記録した。本レポートは候補外に保存し、manifestとの自己参照を作っていない。
