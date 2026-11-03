# Codex引き継ぎ: HABU FIELD / MacBook / iPhone 13 Pro 実機署名復旧

作成: 2026-11-02。対象: haji84/habuAI-private、既存PR #138、ブランチ `feature/native-screenoff-gps-20261027`。実行時には**必ずGitHubの最新PR HEADを読み直す**。この文書の作成時点の基準HEADは `4ec1e8114afd575d38add283b9d9aca0521098d6`。

## 最上位GOAL

MacBookから、本人所有のiPhone 13 Proへ「HABU FIELD GPS」開発版をWi-Fi経由で安全に署名・インストールし、実機でロック中30分、通信オフ10分、強制終了からの復旧、隔離保存失敗の自己診断、GPX/元ログ書き出しを検証する。**未検証はPASSにしない**。既存ソース・個人GPS原本・ジャービス開発環境を守る。実機検証まで、PR #138はDraft、main統合・公開禁止。

## 確認済みの事実

- MacBookにGit 2.51、Xcode 27、XcodeGen 2.46、Python 3.10がある。
- ローカル作業ツリー: `~/HabuField-test/habuAI-private`。以前 `mobile/ios/HabuFieldRecorder/Info.plist` に未コミットの変更があった。削除・上書き不可。
- Device Hub / `devicectl` はiPhone 13 Pro（製品型番 `iPhone14,2`）を1台検出、`pairingState=paired`、`tunnelState=connected`、`transportType=localNetwork`。ケーブルは今不要の見込み。
- GitHub CIとSimulatorでは模擬GPSの保存・GPX書き出しはPASSしたが、実iPhone上のGPSは未検証。
- `mobile/ios/install-owned-iphone-wireless.sh` を実行すると、署名証明書からTeamを検出し、iPhone用Debugビルドで停止。詳細診断 `TEAM_ACCOUNT_MISMATCH`。
- これはビルドログの `No Account for Team` 系に該当することを意味する。**XcodeにApple Accountが未登録と確定したわけではない**。古い証明書のTeamをスクリプトが誤選択している可能性もある。
- MacBookの**左半分が見えない**。外部モニターなし。XcodeのSettingsを開く/右半分に移すAppleScriptは以前成功しなかった。可能な限りCLIとアクセシビリティ権限内のUI自動化で解決。
- Userは安全に使える完成品を希望。繰り返しMac手操作を要求しないこと。

## Codexの権限境界・禁止事項

- 作業はユーザー本人のMac上のCodexで実施。このChatGPT会話からMacを遠隔操作できるものではない。
- **絶対禁止**: Apple ID/パスワード/2FAコード/証明書秘密鍵/Team ID/端末UDID/位置原本をチャット、PR、CI、GitHub、外部サイトに掲載。鍵を読み出したりバックアップ・共有しない。
- Apple Accountのログイン、2FA、OSアクセシビリティ権限の許可など本人認証・同意は自動迂回禁止。必要なら本人への**1件の短い操作指示**のみ。
- `git reset --hard` / `git clean -fd` / 既存 `Info.plist` の上書き / ジャービスのファイル変更 / 署名証明書・プロビジョニングプロファイルの削除 / 既存アプリのアンインストールをしない。Macユーザー全体の設定変更、OS更新、Xcode再インストール、料金発生を勝手に実施しない。
- 既存PR #138のみを修正。新しいPRを増やさない。独立レビュー・最新HEAD CI・Human Gateの確認なくmain統合や本番公開はしない。安全に必要な変更以外は加えない。
- 公開リポジトリが実際にpublicなので、原本GPX、緯度経度、Apple IDなど個人データはコミットしない。

## 自律実行フロー

### 1. 安全な現状監査

1. `git status --short`、現在ブランチ・HEAD・PR #138の最新HEADを確認。既存の変更は**退避・上書きせず保持**。必要なら別ディレクトリに`git clone --single-branch --branch feature/native-screenoff-gps-20261027` した隔離作業ツリーを使用。
2. `xcodebuild -version`、`xcrun devicectl list devices` を**ローカルだけ**で調べる。UDIDや端末名は報告に出さず、唯一のpaired/connected iPhone13 Proだけに対象限定。
3. `xcodebuild` の失敗を端末内で保護し、発生箇所を「Xcodeにアカウントなし」「選択Teamが利用不可」「プロファイル/Bundle ID不整合」「実際のSwiftコンパイルエラー」に分解する。秘密値を出力しない。現在の単純なエラー分類が誤解を招くなら修正テスト追加。

### 2. 署名とアカウントの整合性

1. キーチェーンのApple Development証明書に紐づくTeam候補と、**Xcodeに現在ログインし、使用可能なTeam**を端末内で突合する。証明書の存在だけで適切なTeamが使えると判断しない。Xcodeのアカウント情報がCLIから安全に取得できない場合は勝手に推測しない。
2. 旧ジャービス用の古いTeamを選んでいるだけなら、既存アカウントで実際に利用できるTeamへの開発設定変更を**このアプリだけ**に限定する。ダミーTeam IDや別人のTeam IDは使用しない。
3. Apple Accountのサインイン/2FAが実際に必要なら、Xcode設定ウィンドウを**見える右半分**に移す方法を診断して試す。アクセシビリティが許可されなければ権限要求を説明、許可抜きの回避はしない。試した方法・実際の結果を区別。
4. Personal Teamが使える場合、本人所有iPhoneへの無料開発用ビルドのみ。新しい有料開発プログラム、TestFlight配布、公開App ID作成など不要な手順を押し進めない。
5. 最終的に `xcodebuild` のDebug実機署名ビルドに成功したら、対応Bundle IDだけをインストール。過去アプリや他のプロファイルは触らない。

### 3. 品質ゲートと実機試験

1. HEAD固定のCI/関連テスト、本人端末へのビルド・インストール・起動、GPS取得を分けて記録する。
2. 本人によるロック操作が必要な場面は簡単に案内。30分画面ロック、10分Wi-Fi/モバイル通信オフ（機内モードのみで完全遮断と断定しない）、強制終了→再起動、DEBUG隔離復旧を順番に試す。
3. 書き出したGPS原本は本人端末内だけで検査。結果報告には点数・区間数・PASS/FAILだけ。実GPS座標は出さない。
4. `mobile/ios/OWNED_IPHONE_TEST_RUNBOOK.md`を試験正本として参照。実機試験はCodexが走っているだけで完了したことにしない。
5. 問題が実装由来なら、既存PR #138に対して最小修正→テスト→独立レビュー→必要なら同一PR更新→最新HEADで再テスト。認証や課金、公開・統合など重大な変更はユーザーの明示承認待ち。

## 合格ライン / 報告

- `SIGNED_BUILD_PASS`, `OWNED_IPHONE_INSTALL_PASS`, `OWNED_IPHONE_LAUNCHED` を実際に確認。
- `LOCK_30`, `OFFLINE_10`, `CRASH_RECOVERY`, `STORAGE_FAULT_SIM`, `EXPORT`, `PRIVACY` を真偽と根拠で別々に報告。未実施は明示。
- 本人のApple Accountログインがブロッカーなら、認証を要求する時点で安全に停止し、画面左半分が見えない制約に合わせた最小限の操作を提示。
- 発生エラーは短い**秘匿済み分類と次アクション**として報告。raw build.logや認証情報のコピーは要求しない。

## 関係ファイル

- `mobile/ios/install-owned-iphone-wireless.sh`
- `mobile/ios/signing_failure_classifier.py`
- `mobile/ios/project.yml`
- `mobile/ios/OWNED_IPHONE_TEST_RUNBOOK.md`
- `tests/test_owned_iphone_installer.py`
- `tests/test_signing_failure_classifier.py`

**最初にやること**: この文書を理解し、Macのローカル環境で実際にXcodeのTeam不一致の原因を精査・解消できる部分を実行。一般的な設定説明を繰り返すだけで終了しない。
