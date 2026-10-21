# PR #32 限定修正の独立再レビュー

判定: **限定されたpreproduction入力ゲートの修正内容は承認可能。R32-1〜R32-4について追加のコード上blockerは見つからなかった。** GitHub exact-head CI成功と最終head照合は別の必須条件であり、Issue #34が継続する間はDraftを維持しmainへマージしない。公式P0発行やChampion承認を意味しない。

対象は元head `4ff01f4726d82901cdb69ecb0892d70119ab4c3d` に対する `/workspace/scratch/ded5451af149/pr32-fix` の最終候補。独立レビュー担当は実装コードを変更していない。最終候補はまだこのレポート自体ではGit commit SHAへ対応付けていないため、下表のファイルSHA-256を承認対象とする。push後のheadがこれらと一致することを確認する必要がある。

## 承認対象の正確な内容

| AllowedPath | SHA-256 |
| --- | --- |
| `src/prospective_inputs.py` | `d55bf669dbd5a2595674a13a257490bcd3557347fb826d43a868d19504ba039b` |
| `tests/test_prospective_inputs.py` | `6bf49e170aebc8b750d1dad804fe65f60f3684c94f357af4cc2e6fa5624d6e23` |
| `docs/specs/prospective-forecast-input-binding-v2.md` | `a9f032476b32de95bdfd26ced7cc0fbe93844c38255fa4fd2f61da9bc6275a7b` |

独立テスト実行の前後で3 SHA-256が不変だった。元headから差分を読み、既存AGENTS.mdと依存4モジュールのbytes不変も確認した。PRへ反映するファイルは上記3つだけとする。

## 再検証した内容

| 元の指摘 | 最終候補で確認した振る舞い | 判定 |
| --- | --- | --- |
| R32-1 outcome leakage | 既知9 outcome名のpredictor宣言を拒否。Universe row内とfeature metadata内のネストされたlabel/capture_countも拒否。通常のhistorical predictor名とrow IDの扱いは維持。 | 解消 |
| R32-2 timezone重複 | 同じ100m cellの19:00 JSTと10:00 UTCを同一instantとして重複拒否。 | 解消 |
| R32-3 実byte予算 | stat後の成長をPath.open時に再現。source上限、total上限、最終recheckすべてactual bytesによるbounded readで拒否。 | 解消 |
| R32-4 展開/実行予算 | 32 feature sources、400,000 numeric cells、30秒default/最大300秒の有限正数caller budgetを実装。feature数/cell数はsource join前に拒否。monotonic deadlineを初回/final read、nested metadata、row、numeric cellで再確認。 | 限定スライスの受入条件を満たす |

上限の明示値と親の300秒予算について、既存 `docs/plans/master-goal-1642-feature-models.md` の32 expanded columns案とparent wall-clock allowanceの記載も照合した。このvalidatorにモデル変換やtrainingを追加したものではない。

## 実行結果

- レビュー担当が独自に作成した最終再検証 **18/18 PASS**（0.084秒）。元の再現から、bounded readerへの変更に合わせてrace hookをPath.read_bytesからPath.openへ更新した。atomicity観察は拒否必須テストにせず、下記の保証範囲を確かめるpositive controlへ分離した。
- レビュー担当自身の候補targeted suite再実行 **41/41 PASS**（0.078秒）。
- 実装担当のmain snapshot + 最終3 files overlayでのfull suiteログを読み、**287/287 PASS**（49.180秒）を確認した。この287件全体はレビュー担当自身が再実行したものではなく、独立した18件と41件は上記のとおり当方実行した。
- 33 feature sourcesはUniverseを開く前に拒否。12,501 rows × 32 refs = **400,032 cells** はfeature sourceを読む前に拒否。
- 実際の境界 **12,500 rows × 32 features = 400,000 cells** をsynthetic inputsで独立実行し、成功を確認。参照raw input **7,058,388 bytes**、**0.899秒**、peak RSS **116,460 KiB**、読み取り前peakからのRSS増 **93,040,640 bytes**。`official_issuance_authorized=false`。この実測は特定環境の開発証拠であり、総メモリのhard upper boundや科学性能ではない。
- bool、NaN、±inf、0、負数、300秒超のcaller budgetを拒否。小さいcaller allowanceのdeadlineと最大300秒の受理をfake clockで確認した。実際にsleepして時間を消費するテストではない。
- 欠損cellをNegative/0に補完しないこと、07:00 JST境界、available_atがcutoffと同時刻なら拒否されることも独立確認した。

## 受け入れる保証範囲と残るproduction gate

最終の逐次hash scanはatomic filesystem snapshotを保証しない。snapshotを再確認した後に別fileの確認中にwriterがそのsnapshotを変える再現は依然可能だが、返る行は最初にhash検証したメモリ内bytes由来のままである。コード、仕様、回帰テストがこの限界を明示していることを確認した。mutable pathを後段で信頼して再読する設計には使えない。production immutable publicationは後続ゲートで必要。

deadlineはcooperative checkである。単一のblocking read/parse/hashをOSレベルで中断せず、次のcheckで超過を検出して成功returnを防ぐ。仕様もhard real-time保証としていない。source byte cap、32 source cap、400k numeric cell capは乗算的展開を抑えるが、任意metadata/JSON/runtimeを含む総RSSのhard capではない。

hashと自己申告available_atだけではsourceの真正性や実際のcutoff前availabilityは立証できない。trusted receipts、実環境/GIS入力、全域Universe、モデルidentity/registry、正式100m ±10分target、route、trusted promotionとimmutable ORIGINAL publicationの未実装は引き続き明示されている。`official_issuance_authorized=false` は固定され、現段階の公式要求は `PROVISIONAL_NOT_FREEZABLE` のままである。

## 証拠

独立証拠ディレクトリ: `/workspace/scratch/ded5451af149/pr32-fixed-review`。

- `test_fixed_independent.py`: 独立18テスト
- `independent-fixed-final.log`: 18/18結果
- `targeted-fixed-final.log`: 当方実行41/41結果
- `final-integrity.json`: 実行前後の3 SHA-256一致
- `unchanged-dependencies.json`: 既存AGENTS/依存モジュールのbytes不変
- `benchmark_fixed_boundary.py` / `benchmark-fixed-boundary.json`: 実400k cells/32 featuresの境界検証

実装担当のfull suite証拠: `/workspace/scratch/ded5451af149/pr32-fix/full-suite-final.log`。GitHub exact-head CIの代用とはしない。
