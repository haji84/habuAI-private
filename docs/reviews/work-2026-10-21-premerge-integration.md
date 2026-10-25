# Local premerge composition 独立QA

**判定: PASS（凍結候補のlocal compositionとPR33→PR32入力interfaceに限定）。** 追加のblocking不整合は見つからなかった。Hosted CI、main merge、fresh-main E2E、scientific performance、production Champion/公式P0は引き続き未達であり、この確認をその代用としない。

対象task: `HABU-WORK-20261021-PREMERGE-INTEGRATION`、attempt `20261021-combined-candidate-1`。候補は `/workspace/scratch/ded5451af149/premerge-integration-20261021`、証拠は `premerge-integration-evidence/`。レビュー担当はread-onlyで確認し、候補編集、GitHub書込、suite/producer/consumerの再実行をしていない。保存されたファイルとreceiptを再計算し、実OSM由来の数値も別に照合した。

## Compositionと保全

GitHub APIを再取得してmain=`27f4832a23f0a3826ce96b87afb4f2f1c58aa936`、PR32=`123109a630b16f7af4e5cc41482ddd10839351b5`、PR33=`cd97e69a2d1cfb160b21f33a3e561be989d5ba8d`、PR43=`76680cba924b72a9069a4d12b0819cae95fd5349`を確認した。3 PRともDraft/open/merged=false、base=同mainである。

最終PR43 pinned proofの**281-file** after-mapへ、以前に承認されたPR32/PR33の各AllowedPaths3 files、合計**6 files**を正確に重ねた期待mapを当方で作り、combined before-mapおよび現在の**287 files**と完全一致した。overlay6 filesはsize、SHA-256、Git blob SHA-1も一致する。既存ファイルの追加変更、欠落、別versionの混入はなかった。これはhydrated snapshot compositionであり、完全なmain raw-data cloneやGit上のmerge結果ではない。

前回checkpointのmanifest（SHA-256 `99f53394c44b93fb08c7dae5bb1b0c3f34751af0215fe6fd732566211e48b1b4`、自身を除く82 files）も全列挙hashが現在のwork-checkpointと一致した。今回の証拠は新しいappendixとして追加し、前回checkpoint本文・manifest・過去の失敗記録を置換しないこと。

## Full suite

親が既存のfixed-dependency-profile Pythonで実行したreceiptとログは**327 tests PASS / 57.399秒 / exit0**で整合する。driver全体の経過時間は58.963秒。287-file before/after mapは一致し、当方が再計算した現在のcandidate hashも同一だった。PR43最終269件 + PR32 41件 + PR33 17件という構成とも整合する。receiptのexpected count、末尾OK、exit0、log hash、source hash一致を確認したもので、レビュー担当が327件を再実行したという意味ではない。

full-suite log SHA-256:

`b966833920b61c5c33c5dabe7e62a9b748a5265671b12430025a25b3828f64f1`

## 実OSM producer→consumer

fix_pr33の診断driverはcombined candidate内の実producer `33d4e466ed8720d58d1bb5adc654b1fbbee36c0148e4b81713293cd34321c888` と実consumer `d55bf669dbd5a2595674a13a257490bcd3557347fb826d43a868d19504ba039b` を直接importする。依存moduleも同candidate由来であり、そのbytes/hashを当方でも確認した。driverは他のforecast実装やmodelを代用していない。

33 base64 partsから復元した実OSM ZIPとCSVのhashを当方で再計算した。ZIPは4,845,515 bytes / SHA-256 `f4d7a9925c98830a0b6918f756abe49b2b0f2eb935fc49c2d4eb42a732884c17`、road CSVは4,408,826 bytes / `33ea1df38351d9c2454bf2efc9b00432119e484d5d549a567bc8fd2d337151a4`で診断証拠に一致する。

実sourceの**16,990 cells × 6 windows = 101,940 rows**を出力し、同じsnapshot path/hashを変更せずconsumerへ渡して受理した。consumerは305,820 numeric cellsを取り込み、全元rowと6窓それぞれの全cellを保つ。レビュー担当も保持されたproducer filesから全row座標と3特徴 **305,820値**を元CSVに対して別計算し、road length、axial cos/sin、各窓cell集合を一致確認した。producer/consumer receipt、5 consumed file hashes、source/lineage参照は整合する。

cutoffには実clockを使い、producer completed `2026-10-21T12:44:47.590710+00:00` < cutoff `12:45:06.613552+00:00`、18.626秒の実待機後のconsumer as_of `12:45:06.613696+00:00` < first window `21:50:00+09:00` の順序を確認した。source mtime <= observed ref availability <= producer completed < cutoffも保持された。時刻を過去へ偽装したreplayではない。これは今回生成した入力の観測時刻整合で、trusted availability receiptや歴史的forecast-time accessの証明ではない。

出力snapshot SHA-256は `22b3da557c72db38c785f7519363f2d45ee9ddc5ebe72e9fce934377e7c92b75`。producerの `official_prediction_eligible=false`、consumerの `official_issuance_authorized=false` / `PREPRODUCTION_INPUT_INTEGRITY_ONLY` を確認した。candidate287 filesと入力archive33 partsのbefore/afterは完全一致した。全7 diagnostic artifactsのsize/hashも再計算一致した。

## 追加証拠の正確な識別

| Artifact | SHA-256 |
| --- | --- |
| `check_real_producer_consumer.py` | `c95d34008522dd3685a141c1ceb0b54d33b107310ac19e22b6fc66dfdbfbdba2` |
| `real-producer-consumer-result.json` | `24d4ae5b35fb90f15888c874381a32fcfb9ad665f55052b4c4316e02e1d53a5e` |
| `real-producer-consumer.log` | `a18c2275a9bb8adbbd99f328b7233259712d57b5befa17e32fded2bc95375ef9` |

レビュー担当の補助結果は候補外の `review-premerge-composition-check.json`、`review-premerge-evidence-check.json`、`review-premerge-remote-observations.json` に保存した。generated producer outputはpreproduction診断の入力artifactであり、正式predictionではない。appendix保存時は、生成payloadを保存する範囲とhash/receiptだけを保存する範囲を明示すること。

## Addendum文書と保存scope

`integration-checkpoint-addendum/docs/work/WORK_CONTINUATION_20261021_INTEGRATION.md`（SHA-256 `9b945140932d2a885b5b472cde88397c3b7d2d1a4e181ed2f3112c358608e065`）も独立に読んだ。327件のlocal composition、実source→input binding、CI/main非復旧、scientific NOT_VALIDATEDを区別し、完了を誤加算していない。既存monitorのprompt更新も登録成功までに限定し、future run成功やTask7/Task8完成を示すものではないと明記する。receipt自体のこの行政scopeは読んだが、automationの将来実行を当方が認証したわけではない。

現在の追加packageは新doc1件と新evidence17件の18 filesで、前回checkpointとのpath衝突はない。コピー元のある証拠は原本bytesと一致し、保存された1,137-byte `diagnostic-snapshot.json` のSHA-256もproducerのsnapshot hashに一致した。約41MBのgenerated universe/feature payloadをtransient workspaceに残し、hash/size/source/parametersだけを保存する区分と、fresh real-clock再実行ではtime/hashが変わる点が本文に明記されている。これは正式prediction recordの保存とはしていない。

APIでPR44もhead=`5a38e6d755bddd9c3bfb6beeaff6ae9fcf797e7c`、Draft/open/unmerged/base27fを確認した。親がこの新18 filesに当レビューと独立manifestだけを追加して同PRへappendし、旧83 checkpoint filesを変更しないなら、保存scopeはレビュー結果と整合する。新packageの最終manifest生成後とGitHub書込後には親が全bytes/hash・追加pathのみであることを照合する必要がある。18-file目録は候補外の `review-premerge-addendum-files.json` に記録した。

## 残る境界

対象は静的auxiliary OSMの最大6窓shardであり、full-night universe、実気象/環境/DEM/terrain-wind、登録済みtrained Champion、正式100m ±10分targets、route optimizer、Task8 trusted issuanceを実装/検証していない。実road passability、Stage1 Recall>=90%、最終時空間精度、canonical capture/Negative/Gold admissionも証明していない。

Hosted CIのpreallocation failureとmain非mergeは変わらない。次はexact final-head hosted CIと独立scope reviewのgate、承認済みordinary merge、その後にfresh main integration/smokeが必要である。親から別途報告された既存monitor automationの別行政receiptはこのコード/科学検証の承認対象に含めない。新しい無人Task7 controllerや実行継続保証の成立とは扱わない。
