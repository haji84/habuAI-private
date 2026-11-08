# PR #32 独立レビュー

判定: **変更要求。Draftを維持し、mainへマージしない。**

対象は `haji84/habuAI-private` PR #32、head `4ff01f4726d82901cdb69ecb0892d70119ab4c3d`、base `27f4832a23f0a3826ce96b87afb4f2f1c58aa936`。2026-10-21にGitHub APIでhead不変・Draft・変更3ファイルのみを確認した。実装者とは別のレビュー担当が読み取りと独立テストだけを行い、原本、ORIGINAL、main、PR headのコードを変更していない。

## 確認結果

- GitHub toolsで最初にAGENTS.mdを確認した。raw保全、Unknown != Negative、07:00 JST日界、厳密cutoff、正式発行経路の規則を適用した。
- PRの追加3ファイルと実行に必要な既存5ファイルをexact headのAPIから取得。8ファイルのGit blob SHA-1がAPIのtree/PR filesと一致した。`pr32-independent/source-integrity.json`参照。
- PRの既存18テストは **18/18 PASS**。独立9テストはpositive control **3 PASS**、期待した拒否が発生しないケース **6 FAIL**。独立テストの失敗はこのレビューの再現証拠であり、既存CIでPython assertionが失敗したという意味ではない。
- `official_issuance_authorized=false` と `PREPRODUCTION_INPUT_INTEGRITY_ONLY` は維持される。実際のChampion、公式P0、100m ±10分の性能を検証したものではない。

## 修正要求

### R32-1 / P1: outcome禁止がUniverse直下のキー検査に限定される

箇所: `src/prospective_inputs.py` 126行、146行、159–173行。

`POST_OUTCOME_FIELDS` はUniverse各rowの直下にしか適用されない。feature sourceの `feature_name="label"` と `values={"a":1,"b":0}` を、`use_role="forecast_predictor"`、整合するschema hashとmodel_feature_namesで渡すと正常に受理され、返り値の `rows[*].features.label` に格納される。さらに `row.metadata={"label":1,"capture_count":3}` は146行のrow丸ごとコピーで返り値へ入る。feature source自体の `label` キーも拒否されない（これは返り値の数値特徴に直接使われないため、単独で実モデルの汚染を証明するものではない）。

仕様の「post-outcome fields ... reject the whole join」とPRのoutcome leakage拒否という受入条件に届かない。任意の特徴名が真の予測因子かを検証するには信頼されたprovenance/registryが別途必要だが、既知のoutcome名やネストされた明示labelを無条件で通す問題はこの入力ゲート内で修正できる。

再現: `test_known_label_feature_must_be_rejected`、`test_nested_outcome_must_not_be_copied_into_returned_rows`、`test_feature_source_outcome_field_must_be_rejected`。すべて `ValueError not raised`。

修正案: predictor名に予約outcome名を許可しない。Universe rowを許可フィールドの明示schemaにし、返り値も検証済みフィールドから構築する。拡張metadataを許可する場合は構造とoutcome項目を再帰的に検証する。feature documentにも禁止項目/schema検査を適用する。

### R32-2 / P2: 同一instantのtimezone表記差で100m × 10分の重複が通る

箇所: `src/prospective_inputs.py` 142行。

重複キーの時刻が `start.isoformat()` である。1行目を `2026-10-14T19:00:00+09:00`、2行目を同じ100m cellの `2026-10-14T10:00:00Z` とすると同一instantだが文字列が異なり、2つのforecast unitsとして返る。時間比較と日界チェックはinstantで正しく通るため、重複検査だけが抜ける。

再現: `test_same_instant_timezone_alias_must_not_duplicate_unit` が `ValueError not raised`。

修正案: キーを `start.astimezone(JST)` またはUTCに正規化したdatetime/文字列にする。返却するwindowも正規化すると後段の文字列joinが安定する。UTCの入力自体を禁止する必要はない。

### R32-3 / P2: 読み取り予算がstat値だけに依存し、実際の読込が無制限

箇所: `src/prospective_inputs.py` 55–60行、182–183行。

`stat().st_size` を確認した後に無制限の `read_bytes()` を呼び、実際の `len(raw)` をsource/total予算へ照合しない。stat後にファイルが大きくなり、snapshotに記録されたhashがその大きな内容を指す場合、上限超過の内容を読んで正常受理する。最終hash再確認も無制限readなので、変更を拒否できる場合でも先に巨大データをメモリへ取り込む。

再現: `test_growth_between_stat_and_read_must_not_bypass_byte_budget`。安全のため上限を1024 bytesへ縮小し、最初のfeature read直前に約2.2 KiBの正しいhashを持つJSONへ変更する。巨大ファイルは作成せず、`ValueError not raised` を再現した。

修正案: sourceあたり `MAX_SOURCE_BYTES + 1` 等のbounded readで上限を検査し、実バイト数をtotalへ加算する。最終再確認もbounded streaming hashまたは同じbounded readerを使う。ファイルdescriptorでの型/サイズ確認も行うとstat/openの間の対象差し替えを狭められる。

### R32-4 / P2: source byte上限がjoin後のメモリ/処理量上限になっていない

箇所: `src/prospective_inputs.py` 20–22行、146行、151–173行。

行数上限とsource byte上限はあるが、feature数、`rows × features` のjoinセル数、処理時間、展開後メモリに上限がない。各セルはfloatと3つのrow辞書の項目、source参照listへ展開されるためJSONより大きくなる。

独立の小さなsynthetic benchmarkでは2000 rows × 200 features = 400,000 cells、参照入力 **5,002,376 bytes** に対し、プロセスpeak RSS **102,400 KiB**、読み取り前peakからのRSS増 **86,507,520 bytes**、join時間 **0.671秒**だった。これはこの環境の測定値で、上限でのOOM/時間超過を実行した結果ではない。最大384 MiBをこの率で単純外挿すると数GiBへ広がりうるため、現状の定数だけで安全な実行予算が保証されるとは判断できない。

修正案: join開始前にfeature数と `N_rows * N_features` を上限判定し、拒否する。deadlineまたは定期的なbudget callbackを設ける。参照listを各セルへ複製せず、snapshot単位の共有lineageへ正規化することも検討する。予算はconfig/仕様に明記し、境界を小さい値でテストする。

## 追加観察と適切に残っている制限

- 最終hash scanは複数ファイルを逐次確認するためatomic snapshotではない。snapshot再確認後、次のuniverse再確認中にsnapshotを書き換えるとreturnが成功する独立再現を残した。**既に読み取って検証されたメモリ内の行とhashの整合性はこの再現で壊れない**。返却時に全パスが一斉に同一hashであることまで必要なら、immutable staging、cooperative lock、content-addressed読み取りなどが必要で、単なる再hash回数追加では解決しない。現スライスでは保証をbyte-consistent loaded valuesに限定して明記し、後段でmutable pathを再読して使わない契約にするのが妥当。
- available_atは自己申告であり、hashがsourceの真正な過去availabilityを証明しない点は仕様に明記されている。trusted receipt/real source provenance/production registryは後続の明示ゲートなので、それら未実装だけを新規欠陥とはしていない。
- feature cellの集合がUniverse row IDsと厳密一致する点、欠損が0やNegativeに補完されない点、cutoffと同時刻のavailable_atを拒否する点、07:00 JST日界はpositive controlで確認した。これは地理的なUniverseの網羅性やroad domainの真正性を証明しない。
- 正式100m ±10分のtarget semantics、Champion登録、real environmental/GIS入力、route executor、ORIGINAL freeze/publishはこのPRで実装されない。P0は引き続き `PROVISIONAL_NOT_FREEZABLE`。
- exact-head GitHub CIはIssue #34の障害を解消して再実行する必要がある。このローカル確認をその代用にしない。

## 再現ファイルとコマンド

作業ディレクトリ: `/workspace/scratch/ded5451af149/pr32-independent`。

```bash
python -m unittest discover -s tests -p test_prospective_inputs.py -v
python -m unittest discover -s tests -p test_pr32_independent_review.py -v
python benchmark_budget.py
```

証拠:

- `github-metadata.json`: exact-head/Draft/変更ファイルのAPI記録
- `source-integrity.json`: 8ファイルのexpected/actual Git blob SHA-1
- `tests/test_pr32_independent_review.py`: 独立再現9テスト
- `baseline-tests.log`: 既存18/18 PASS
- `independent-review.log`: 独立3 PASS/6 FAILと具体的assertion
- `benchmark_budget.py` と `budget-benchmark.json`: 小規模の実測

独立テストはPRの既存コードを変更せずに実行した。既存18テストだけの実行と独立テスト実行を分けているため、意図的に赤い再現テストを通常suiteへ追加済みという意味ではない。
