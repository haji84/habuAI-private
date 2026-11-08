# 私有GPX経路復元・捕獲参照・handoff診断の検証（2026-11-04）

**PARTIAL_BLOCKED。アクセスできる原本の復元とコード修復は実行・独立検証済み。正式学習、予測精度、本番稼働は未達です。**

既存Draft PR #136とIssue #86の[担当分離指示](https://github.com/haji84/habuAI-private/issues/86#issuecomment-6611188801)を継続します。別チャットが管理する最新154候補、空間prior、270個体の研究EventClockモデルは再生成・上書き・加算していません。

## 実装した処理

- `src/route_recovery.py`は原本順序、trk/trkseg、隔離点と測定値を保持。短区間補間、道路候補、活動仮説、未知区間を分離し、100m×10分へ分割します。速度単独では探索を認定しません。
- 同時刻の競合bracketは道路による除外より前に検出し、競合component中の補間を全て保留します。巨大数値は局所QCへ隔離。道路のbuffer付きindexは元の線分を保持し、容量超過は測定GPSの消去につなげません。不正geometryは容量降格より前に検証します。
- `src/capture_route_evidence.py`は時刻のみのPositive、数量不明、二個体、他種、逃逸、記入遅延を保持。不確かさnullを捏造せず、正式Negativeを生成しません。100mと±600秒は両条件のsample照合で、予測成功の認定ではありません。
- `scripts/recover_private_route_evidence.py`は原本manifestのSHA/size/受信時刻を検証し、Git外へ追記保存。原本・nativeコード・派生物・receiptを再読します。receiptのboolを0/1へ置換する反例と、原本受信以前の読取時刻を拒否。道路源なしと明示した空道路源も区別します。
- 既存`habu_private_model_link.py`に任意の診断参照を追加。canonical route/receipt、既存qualified-fit report、明示した候補SHAを検証し、status/hash/size等の限定メタデータをhandoffへ参照します。既存モデル2形式の受理条件・G0 selector/fitter・正式issuerは維持。FITTED参照には既存candidate readerを通る実体が必要です。BLOCKEDをモデル生成済みへ読み替えません。

私有handoff/fitのGit誤保存、junction/symlink、入力競合、派生物改変も回帰試験で検証しています。協調的なファイル再照合であり、敵対的同時置換に対する原子的隔離や所有者/機器認証を主張しません。

## 実データの結果

最終実行コードは`ce8028e5fa2588d91f64e4b00e14986b45d0eb7f`。v1〜v3を変更せずv4へ20処理を実行し、20成功・0実行BLOCKEDでした。**異なるGPX原本は14本**です。内訳は従来13夜、追加9月28日1夜、既存6夜に対する別の捕獲コホートの再照合6処理。20夜・47捕獲イベントへ加算しません。

| 対象 | 実測結果 |
|---|---|
| 測定原本 | 14 tracks / 17 trkseg / 266,737点を全保持 |
| QC | 通過258,672点、HDOP上限で隔離8,065点。原値を削除しない |
| 補間 | 231,510短区間。231,612.789秒は端点間proxyで、連続測定や実測探索時間ではない |
| 保留区間 | 道路曖昧26,488、品質隔離8,723、原本segment境界2 |
| 100m×10分 | 10,623窓。SEARCH_INFERRED 1,355、UNRESOLVED 9,268 |
| 時刻競合 | 実14本の道路フィルター前の時刻bracketでも重複0。合成反例の修復を実データの競合発見と混同しない |
| 原文30参照 | 基準13夜の30参照全てに両条件内の測定sample候補9,034件。数量明記1参照=2個体、残29参照の数量不明 |
| 別source-view | 6夜の既存17イベントと18 source-occurrence aliasを保持。全17に候補5,348件。恒久的な生物個体ID認定は0 |

原文30参照の記入時刻は`RECORDED_AT`、形式上の不確かさ60秒。別17イベントは`UNKNOWN`/不確かさnullです。いずれも`TIMING_AMBIGUOUS`。別コホートのCSV記載数量合計18は独立個体数量認証ではなく、原文で数量明記したものは1イベントです。18のaliasを既知生物個体IDへ移さず`individual_ids=[]`を維持しました。旧30・別17・最新154のID照合は未完了で、合算できません。

原文の開始/終了マーカーが一意な8夜のみ研究contextを採用し、6夜はscopeを作りません。130窓の`NO_CAPTURE_RECORDED_DURING_INFERRED_SEARCH`は供給原本範囲の研究信号で、完全結果やabsenceを認定せず、正式Negativeは0です。

9月28日は既存24分割archiveから6,068,111Bを原本SHA`2e9fde7aa459fc100abf8014d95635e697a638679cc9df731f4e0f6a80fb62f3`と同一バイトで復元。私有出力で22,990点・913窓を確認しました。道路源なしの別実行916窓とは入力条件が異なり、加算・置換しません。

道路は個人座標を送らず既存の公開島bboxで取得したOSM原形から6,313 LineString/94,092区間を作成。14本の参照残差は中央値3.67m/P95 13.12mですが、GNSS精度、通行権、真の走行経路の誤差認定ではありません。**11月4日JST取得の補助資料を過去P0の事前入力にしません。**

## 独立検証と証拠

- R2 core独立レビュー：46試験、32時刻順序ケース、4,800道路距離照合を通過。先行レビューの2件の実反例は両入力順で修復確認済み。
- 最終route/capture/CLIは95試験PASS。関連16 modulesは**362件=350PASS/12Windows依存SKIP/0FAIL/0ERROR**。全Windows合格とは扱いません。
- v4基準14本：14組のartifact/receipt、72入力、126コードSHA、型・自己seal・実読取時刻順序を独立照合。v3と点・窓・区間・捕獲参照が同一、旧v1〜v3の138ファイル不変、最終182ファイル再照合。
- 別6出力も16,880項目で独立監査し、17イベントの全5,348候補を距離・時刻の両条件で再計算一致、233ファイル不変を確認。actual BLOCKED reportと組み合わせた診断参照は6/6成功です。
- 別6view入力は54 source refsのnative bytes、既存CSV行/原文span、17既存ID/18出現aliasを531項目で独立確認し、私有adapter最終再読91項目を通過。provenance ZIPは元member bytesを保持する派生containerで、raw認証や正式資格ではありません。
- 診断参照の独立レビューは55件=53PASS/2Windows依存SKIPと6追加反例を通過。実v2の13組すべてを受理・再走査し、26ファイル不変を確認。原本PDCA+NightCountモデルを使うhandoff全体の実行は未検証です。

| 証拠 | SHA-256 |
|---|---|
| 実v4 run receipt | `2437b630077bd53bf3eb8335af67ce1843cc9be3f06352008e673a66cf69db9a` |
| 実v4私有集計 | `816ce6f19e9e5bf59109395d0c841f12a582ed4f08888685383c6013100ba1af` |
| v4基準14本独立監査 | `1c76a6b9f85a7cd73fca55ff506e184e773c92f2666d88449b7ee1d8f1b1ceb6` |
| v4別6出力独立監査 | `70b931943751ff37c40934f64bd81f858b6d43bb7cdcfe84c89dedf3ab3a300d` |
| TRAIN_ONLY readiness棚卸し | `e9da29256b345547160a13a807c3adfa0dfe234dc35040ca6565a7e9ae18a983` |
| R2 core独立監査 | `9ec054fd8c6525b59e8500172c606a72b660a380a19ed1aaabd253bbae7e58f1` |
| 531項目のsource-view監査 | `55d74b7cf874a5c93d03d07f8be44101bd7d667d861bd11a790a4687e0138966` |
| 訂正版DB独立棚卸 | `caa6a7dd82a6edb7484a72540c005c592fc596f5da1fc414adc45135b7d84542` |
| 関連回帰log | `e79d2ad355cb36754fb83d0f705e090f3bfd93141c2d3e179411e4d30a0d8391` |
| current cycle manifest-file | `6f1597757f36a1e750b3504739b25059c0d6fcafcd79a8d4697a4c3d37f4cc71` |
| cursor raw-file bytes | `4a8716a266f97507a9d8f5df4db320086f6c68c7401797bb5d5b9a0fa9af9f8e` |
| 122コードのclosure | `36f35e73df4da3aae1387defe2df9ddb7ba05b010a95f5f2a0fd60ed7f0cde66` |

cycle122-03は開発用`CONTRACT_VALIDATED`、science=`NOT_VALIDATED`、fit/production=false。旧cycle・policyは不変。STATEの旧再開ポインタとruntime制御値を履歴に保全し、現在のmain/122-03/11月4日/GPS source資格工程へ更新しました。他の歴史的contextは不変で、台帳から背景実行を主張しません。最終公開HEADのUbuntu CIは**当該HEADの実ログ**をPR Conversationへ記録し、3e8e165の旧2,401件成功を新HEADへ継承しません。[安全な集計JSON](../../reports/private-route-recovery-20261104-summary.json)も更新しました。

## 私有実行

```sh
python scripts/recover_private_route_evidence.py \
  --manifest /private/intake/source-manifest.json \
  --manifest-sha256 <actual_manifest_bytes_sha256> \
  --private-output /private/route-evidence/new-generation
```

manifestは`habu-private-route-source-manifest-v1`。各sourceの`source_id/kind/path/sha256/size_bytes/source_identity/received_at/original_timezone/correction_revision`を要求します。wrapperの`original_source_id`も同じclosureへ束縛。private outputは全Git作業領域の外です。

既存`habu_private_model_link.py`の追加任意引数は`--route-evidence/--route-receipt/--qualified-fit-report/--candidate-model`と、各々の`-sha256`です。routeはartifact+receipt両組を明示。参照されるPDCAのGPX SHAがrouteのsource/memberに必要です。BLOCKED reportに候補は付けられません。出力に私有座標や候補model bodyは埋め込みません。

## 残ゲート

- 旧9月51匹訂正版workbookの実byteは既存capsuleから取得・独立照合済み（SHA`ead12df59799d607a93814d91e5ed719bbc955cda3a8cf2410f22d42214d7054`）。13シート・3,853レコードをcompanion CSVと照合し、時刻解析3,833件/隔離20件、探索夜2025-09-17〜2026-10-20を確認。これは学習件数ではありません。最新154候補や11/1・11/3原本の取得とは区別します。
- 最新154候補と11/1・11/3 GPX/原本ログ、およびlegacy handoffに必要な原本PDCA/NightCount bodyは現接続で未取得。Drive/Pages/許可済みローカル探索と論理Library参照を区別し、架空payloadを作りません。
- 独立探索scope、完全結果、個体同一性、as-of特徴量の資格が不足。284項目の実在入力棚卸しで、利用可能なTRAIN_ONLY manifest/corpus・独立探索/完全結果receiptは0と確認しました。既存selectorには3 prior nights・2 Positive・2 Negative以上が必要で、欠けた宣言を作って通しません。既存qualified-fit CLIを実行し`MISSING_SOURCE_QUALIFIED_G0_MANIFEST`でBLOCKED、eligible corpus=null、selector/fitter未実行、output directory未作成を確認しました。正式学習追加0、実Fit行0、モデル生成0です。
- Stage1 1km Top10 Recall、100m±10分、校正、Champion比較、モデル改善は未評価。未閲覧の将来評価と信頼できる事前issuerが必要です。過去P0の復元発行はしません。
- 11/3の本人確認済み停止29分12秒は合成反例で検証済みですが、その夜の実GPX処理は未実施です。
- main統合/本番公開/Champion昇格は未実施。Cloudflare preview=none/production branch=mainをread-only確認し、課金・権限・公開設定を変更していません。実機background GPSとAccess実稼働は未認証です。

今回確認したGPXの探索夜は2026-08-12〜09-28で、2025〜11/1の全原本統合は未完了です。

Master Goal #1642は未完了です。正式P0→実探索→帰着GPX/ログ→正式採点の実地E2E成功は主張しません。
