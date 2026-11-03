# 私有GPX経路復元・既存捕獲参照の実行検証（2026-11-04）

**PARTIAL_BLOCKED。実データの経路復元は実行・独立検証済み。正式学習・予測精度・本番稼働の完成宣言ではありません。**

既存Draft PR #136とIssue #86の[担当分離指示](https://github.com/haji84/habuAI-private/issues/86#issuecomment-6611188801)を継続します。別チャットが管理する154捕獲候補、空間prior、270個体の研究用EventClockモデルは再生成・上書き・累計加算していません。

## 実装と実データ

既存のGPX QC、UTM52N投影、道路幾何を再利用しました。厳密G0 selector/fitterの資格ゲートは維持し、今回は実行していません。

- `src/route_recovery.py`：原本順序・trk/trkseg・測定値を保持。短区間の直線補間、道路参照候補、活動仮説、未観測区間を別型で出力します。道路は空間indexで照合し、曖昧な道路間を確定経路として埋めません。
- `src/capture_route_evidence.py`：既存イベントIDを参照する私有サイドカー。時刻のみのPositive、数量不明、他種、二個体、逃逸、記入遅延、局所時計異常を保持します。±600秒と100mは両条件の照合基準であり、予測成功や発見時刻の認定ではありません。
- `scripts/recover_private_route_evidence.py`：明示した原本manifestのSHA・size・受信時刻・source closureを検証し、全Git作業領域の外へ追記保存します。成功前に原本・コード・派生物・receiptを再読検証。実読取時刻とnative code hashを保持し、同一再実行では元receiptを変更しません。
- 既存の私有モデルlink/qualified-fit CLIも、別Git worktreeへの誤保存、junction/symlink、入力との競合を拒否するよう修復。既存研究payloadと正式学習ゲートは維持しました。

現有の原本GPXは2026年8月12日以降の**13夜分・13 tracks・16 trkseg・243,747点**です。原本/Git native bytes/旧QCを照合して私有領域へ同一バイトでコピーしました。今回新しく捕獲地点やGPS原本をGitへ追加していません。

原本ログで同一探索夜に開始・終了マーカーが各1件ある8夜に限り、その間を研究用contextに採用。5夜はscopeを作りません。マーカーは探索範囲・完全結果の独立科学認定ではありません。

| 実行結果 | 実測値と意味 |
|---|---|
| 原本点の保持 | 243,747 / 243,747。隔離点も原値・理由を保持 |
| QC通過 | 236,820点。6,927点はHDOP上限で隔離し、削除しない |
| 短い隣接点間の復元 | 212,203区間。30秒以内の端点間補間で、連続測定や実測探索努力ではない |
| 保留した隣接区間 | 道路曖昧24,040、品質隔離7,489、原本segment境界2。夜全体を捨てない |
| 100m×10分 | 9,710窓。実測点・補間時間・通過/再訪・活動仮説を分離 |
| 活動の研究仮説 | SEARCH_INFERRED 1,355窓、UNRESOLVED_ACTIVITY 8,355窓。速度単独では探索確定しない |
| 推定探索時間のproxy | 46,727.577077秒。未校正ルールの結果であり、実測active秒ではない |
| 既存捕獲記述 | 30参照。数量明記1件（2個体）、数量不明29件、認証済み個体IDなし。30匹とは数えない |
| GPXとの照合 | 30参照すべてに両条件内の測定sample候補。候補は9,034件で、多数の通過候補を保持 |

道路参照は、個人の座標を送信せず、既存コードの公開島bboxで取得したOSM原形11,338,659Bから6,313 LineString / 94,092区間を再構成しました。参照までの残差は中央値3.67m・P95 13.17mですが、GNSS精度・通行可能性・真の走行経路の誤差認定ではありません。**11月4日JST取得の補助資料を過去P0の事前入力にしません。**

捕獲時刻は元のHH:MM記入を保持する`RECORDED_AT`、形式上の不確かさ60秒として扱い、全30参照は`TIMING_AMBIGUOUS`です。記入遅延の有限上限は作らず、位置/時刻が未確定のPositiveを「捕獲記録なし」に反転しません。近いGPSとの整合性は、独立測量の誤差でも予測精度でもありません。

130窓の`NO_CAPTURE_RECORDED_DURING_INFERRED_SEARCH`は、供給原本に記録された範囲の研究用信号です。完全な結果記録や生態学的absenceを認定せず、正式Negativeは0です。原本が未供給の2夜はその欠損理由を保持します。

## 再現性・独立検証

実行コードのGit snapshotは`eab4f8b867c20ae903eb1bef4c8c3e9df936e79b`。私有出力v1を保全したまま、受信時刻ゲート修復後にv2へ13夜を再実行しました。両世代の全payloadは実行コードSHA以外完全同一で、26夜・60捕獲参照へ加算しません。

- 入力v1：265項目、活動scope v2：200項目、捕獲参照v3：416項目を独立照合。
- 出力v1：745項目。全点、全道路候補を別200m indexと直接距離計算で再検算。全時間窓を独立に切断し、全9,034捕獲sample候補を両条件で確認。
- 最終v2：689項目。旧世代の不変性、全payload同値性、現行native 9ファイル、全receiptと実時刻の順序まで再検証。
- 新しいroute/capture/CLIは76テスト。関連16 modulesは**326件＝314PASS／12SKIP／0FAIL／0ERROR**。WindowsのPOSIX/権限依存skipを隠さず、全体Windows合格とは扱いません。Ubuntuの最終実HEAD CI結果はPR Conversationへ記録します。
- 反例から修復した内容：UTF-16のDTD/entity、孤立した未来時計値、途中の派生物改変、未来の受信時刻、時刻のみ/遅延Positiveの誤ったno-capture化、時計不確実性の照合先への伝播。生データを直してテストを通していません。

| 証拠 | SHA-256 |
|---|---|
| 実v2 run receipt | `e371f502c8ae615faaec5592ca34d432edb409109bca060a39235fe09bc39ff4` |
| 実v2集計 | `de9e78ff345b663e0b4c4d5121920b24164292231806da2ac43aae65ee8cdb05` |
| 独立v2監査 | `03029c62432383b3371f10b7d352e939cb4c52a989d0a5ea35e9f0323b159bc6` |
| 関連回帰log | `01f475a3393d3b702f181730c0042b589e09116dbfd013eecd53df451c4cdead` |
| current cycle manifest-file | `37201dbd1b8deaece9584a79a91bf0e89767c7f49af7ff511461814dbb079b13` |
| cursor JSON-document | `3d6625b8871a0ffccdfe2ef9d997bb5367dd17ad8c559fe57faf50a3980e7fb5` |
| 122コードのclosure | `960c7fd4241af2b2561af30328437c0ac045424269bd3e3701e4d074f67b2ea9` |

cycle122-02は開発用`CONTRACT_VALIDATED`で、fit/production authority=false、science=`NOT_VALIDATED`。旧cycle・policy・原本・ORIGINAL・モデルは不変です。機械可読の安全な結果は[集計JSON](../../reports/private-route-recovery-20261104-summary.json)に保存しました。

## 私有実行インターフェース

```sh
python scripts/recover_private_route_evidence.py \
  --manifest /private/intake/source-manifest.json \
  --manifest-sha256 <actual_manifest_bytes_sha256> \
  --private-output /private/route-evidence/new-generation
```

manifestは`habu-private-route-source-manifest-v1`。各sourceには`source_id/kind/path/sha256/size_bytes/source_identity/received_at/original_timezone/correction_revision`を指定します。相対pathだけを受け付け、重複・重なったGPX源・改変を拒否します。kindはgpx、field-session、jsonl、roads、captures、activity、evidence。任意のmodel bodyを取り込む口はありません。

道路/活動/捕獲のwrapperには`original_source_id`を指定し、その原本もevidenceとして同じclosureへ束縛します。捕獲イベントは明示した宣言schemaのみ受理し、未取得の最新154 JSONの構造を推測しません。`individual_ids=[]`と`count=null`を保持し、元候補や研究モデルへ書き戻しません。正式資格が揃った後は既存`habu_qualified_fit_cycle.py → select_g0_training_rows → fit_candidate`を利用し、既存の`habu_private_model_link.py`も研究用handoffのまま維持します。

私有処理の隔離・最終再照合は協調的なファイルシステム検証です。敵対的な同時置換に対する原子的隔離や、署名付き機器/所有者認証を主張しません。

## 残ゲート

- 最新154候補と研究モデル4JSON、11/1・11/3のGPX/ログ/DBは、会話の論理Library参照まで確認できましたが、現connectorで取得できるfile ID/URLがありません。Drive/Pagesと許可済みローカル範囲でも原本未取得です。現有30参照と最新154候補のID照合は未実施。
- 個体同一性、数量、独立探索範囲、完全な捕獲結果、as-of特徴量の資格が不足。今回の正式学習追加は0件、コーパス全体の適格件数は未検証のnullです。別チャットの研究モデルを再学習・性能認定しません。
- Stage1 1km Top10 Recall、100m±10分、校正、Champion比較、モデル改善は未評価。未来未閲覧データと信頼できる事前発行が必要です。
- 11/3の本人確認済み29分12秒停止は合成反例で正確に除外しましたが、その夜の実GPXを処理したとは主張しません。
- main統合・本番公開・Champion昇格は未実施。Cloudflare Pagesはpreview=none、production branch=mainをread-only再確認し、設定・課金・権限を変更していません。実機background GPSとAccess実稼働も未認証です。

Master Goal #1642は未完了です。正式P0→実探索→帰着GPX/ログ→正式採点の実地E2E成功は主張しません。
