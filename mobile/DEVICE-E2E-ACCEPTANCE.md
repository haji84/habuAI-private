# HABU FIELD GPS 実機受入試験 v1（本人所有端末・追加課金なし）

この文書は **試験手順と合格ゲート**。実機の成功を主張するものではありません。原本GPX・座標・捕獲地点・経路・個人識別情報は Public GitHub、Issue、Actions artifacts、チャットへ無加工で共有しない。

## 前提条件

- Androidは GitHub Actions `Habu native background GPS candidate` の最新HEADで `source-contract`、`android-debug-build`、生成APKの `INTERNET` 権限不在チェックがPASS。Android Studio（またはGradle）で所有端末へ署名付きデバッグAPKを直接インストール。Public artifactsへのAPK/GPSアップロードは禁止。
- iOSは同じ最新HEADで `ios-swift-syntax` と `ios-simulator-build` がPASS。MacのXcode＋XcodeGenでプロジェクトを生成し、**本人のPersonal Teamで自分のiPhoneにのみ**署名して実行。Apple IDや署名証明書は外部に渡さない。
- **GPSによる位置取得は機内モードでも端末や場所によって失敗することがある。** 試験対象は実際の観測点と欠測の正しい記録。時刻やGPS軌跡を補完・生成してはいけない。
- 走行中の端末操作は禁止。安全な場所で操作し、固定・施錠して試験する。
- 原本は所有端末のローカルストレージに保存し、自分で暗号化した場所にバックアップ。端末喪失・アプリ削除・Personal Team署名失効はデータ保持を保証しない。

## 手順（OS別に同じ条件で別々に実施）

| # | 操作 | PASS判定 | 証拠 |
|---|---|---|---|
| 1 | アプリを前面にして「探索開始」、位置権限を許可。5分間測位 | 時刻付き実測GPSが記録される | 座標を除いた開始時刻・点数 |
| 2 | アプリを閉じずに**画面ロック30分** | ロック中の実測GPS点が存在し、時系列・欠測を確認できる | 点数増分・時間範囲・5分以上の欠測数 |
| 3 | 開始済みセッションを維持し、**機内モード10分**、ロック状態を保持 | 取得可能なGNSS点を記録。欠測は明示し、補完しない | 点数増分または欠測の明示 |
| 4 | 電波を戻して5分記録、アプリの「探索終了」 | 実測点が保持され、停止後に測位点が増えない | 停止前後の件数 |
| 5 | GPXと元ログを書き出し、**端末内で**再読み込み | XML/JSONL解析可。GPS点は実測のみ。5分以上の時間空白を直線でつながない | 総点数・セグメント数・ハッシュ（任意） |
| 6 | 位置許可を取り消して探索開始 | 本人に失敗を通知し、偽のGPS点を増やさない | PASS/FAILとエラー種別 |
| 7 | 測位中に位置サービスを無効化して戻す | 障害時に欠測または中断が分かる。自動補完しない | PASS/FAIL |
| 8 | 測位中にOSでアプリを強制終了、またはOSが停止した状態を再現し、アプリ再起動 | 勝手に秘密裏の測位再開をしない。未終了セッション・欠測を発見し、ユーザーの明示的な再開後のみ測位 | PASS/FAIL |
| 9 | ネットワーク接続なしで2件の観察記録を保存、ログ／GPX出力 | 捕獲と目撃は個別にローカル保持、バックアップ可能。ダッシュボード確定累計は勝手に増えない | 件数のみ |
| 10 | 既存記録を再インポートし重複を想定 | イベント識別子・探索夜を比較して重複を数えない（クラウド同期未完成なら**未実装のためFAIL/未実施**） | PASS/FAILまたは未実装 |

**実機合格条件**: iPhone・Androidの両方で1〜9を確認し、問題があれば修正→再テスト。#10は将来の認証付き同期とともに別ゲートとして扱い、未実装をPASSにしない。Android標準の位置 Foreground Service とiOSの Core Location Background Modesを前面で開始する方式に限る。OS終了後の永久連続記録は要求しない。

## 実機結果の安全な報告テンプレート

```text
OS：iOS または Android
アプリのHEAD：GitHub 40文字SHA
Xcode実機ビルド / Android debug build：PASS / FAIL
画面ロック30分：PASS / FAIL（実測点数の増加：　点）
機内モード10分：PASS / FAIL / GNSS受信不可（増加：　点）
GPX書き出しとXML解析：PASS / FAIL（点数：　、セグメント：　）
位置権限拒否：PASS / FAIL
サービス強制停止→再起動時の欠測：PASS / FAIL
ローカル観察2件・オフライン出力：PASS / FAIL
予期しない位置情報の外部送信：確認できず / 検出
備考：エラー文だけ（緯度・経度、経路、住所、写真は含めない）
```

個人GPSの実原本は安全な端末内に保管。**元GPXファイルをGitHubや他の公開サービスへ送らない**。この文書だけで「科学的なNegative/Exposure」「予測P0採点」「正式外部レビュー承認」まで合格したことにはならない。

公式参考:
- Apple Core Location: https://developer.apple.com/documentation/corelocation/cllocationmanager/allowsbackgroundlocationupdates
- Android location foreground service: https://developer.android.com/about/versions/14/changes/fgs-types-required
- GitHub public standard runners free: https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job
- Apple free Personal Team 7-day provisioning: https://developer.apple.com/help/account/basics/about-your-developer-account
