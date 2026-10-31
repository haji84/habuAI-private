# MacBookからiPhone実機GPS試験を始める手順

本ファイルは2026年10月27日時点の個人向け開発メモ。完成アプリの配布手順ではありません。

## 1. Macの準備

Mac App Storeから対応するXcodeをインストールし、一度起動します。必要ならXcode > Settings > AccountsでApple Accountにサインインします。無料のPersonal Teamでも自分の端末に開発アプリをインストールして試験できますが、Apple公式によるとプロビジョニングの有効期限は7日間です。配布や長期間の利用は別途検討が必要です。

XcodeGenはXcodeプロジェクト生成ツールです。Homebrewをすでに使っている場合は次でインストールできます。

```bash
brew install xcodegen
```

MacのターミナルでGitHubの**開発ブランチ**を取得します。既存の作業ツリーを上書きしないよう、別のフォルダに浅いcloneを作ります。GitHubへraw GPSデータをpushしないでください。

```bash
mkdir -p ~/HabuField-test
cd ~/HabuField-test
git clone --depth 1 --single-branch --branch feature/native-screenoff-gps-20261027 https://github.com/haji84/habuAI-private.git
cd habuAI-private
zsh mobile/ios/check-mac.sh
```

「SIMULATOR_BUILD_PASS」が表示されたらiOS Simulator向けの**コンパイル**が成功しています。これは実機でロック中にGPSが取得できる証明ではありません。失敗した場合はコマンド出力の**最初のerror行と、その前後**だけを共有してください。Apple IDやトークンは共有しないこと。

## 2. 自分のiPhoneにインストール

1. MacのXcodeで `mobile/ios/HabuFieldRecorder.xcodeproj` を開きます。
2. Xcode > Settings > Accountsに自分のApple Accountを追加します。
3. 左側のプロジェクト > Targets > HabuFieldRecorder > Signing & Capabilitiesで「Automatically manage signing」を選択。Teamを自分のPersonal Teamにします。Bundle Identifierが他と衝突した場合は自分専用の識別子に変更してください。
4. Background Modesの「Location updates」が有効であることを確認。位置情報は本人が「探索開始」を押してから収集します。
5. iPhoneとMacを接続し、端末の「このコンピュータを信頼」やDeveloper Modeを必要に応じて設定。Xcode上の実行先で自分のiPhoneを選び、Runを押します。
6. iPhone側で位置情報の使用を許可し、GPS記録開始→画面ロック→再開→GPS点の時刻・精度確認→探索終了→GPX書き出しを試してください。

XcodeGenを再実行すると `project.yml` からInfo.plistが生成され直されます。Background Modesなど永続設定は必ず `project.yml` に反映してください。Info.plistだけ手修正しても保持されない場合があります。

## 3. 実機の合格条件

- 最初に位置情報を許可した状態で、前面アプリの開始後、30分以上ロックした間の実測GPS点が得られること
- ロック解除後のGPXに時刻・測位点が存在すること。5分以上の欠測は軌跡として直線補完されていないこと
- Wi-Fi・モバイル通信を切った場合にも、GNSSが測位可能なら実測点が残ること
- 強制終了、位置情報権限取り消し、測位不可、省電力状態では欠測を隠さないこと
- 捕獲・目撃は観察記録であり、確認済み249匹/97晩には自動加算されないこと
- 原本の位置座標をGitHub・Issue・CI・公開ダッシュボードへ送信しないこと

iOS構文チェックとAndroid CIはMacの実機テストの代わりにはなりません。クラウドへの認証付き同期、重複取込、既存PR #136のCIハッシュ不一致、PR #92の差分調整も別に残っています。

公式参考:
- Apple Personal Team: https://developer.apple.com/jp/help/account/basics/about-your-developer-account
- Apple 実機アプリ実行: https://developer.apple.com/documentation/xcode/running-your-app-on-simulated-or-physical-devices
- Apple バックグラウンド測位: https://developer.apple.com/documentation/corelocation/cllocationmanager/allowsbackgroundlocationupdates
- XcodeGen: https://github.com/yonaskolb/XcodeGen
