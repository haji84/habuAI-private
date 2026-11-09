# ハブAI統合版 iPhone実機導入・Google Drive読戻し受入試験（2026-11-10）

**状態: 統合アプリの実機署名導入・Google Driveへの本物の到着・独立読戻しは未実証。** 既存PR #138で受け入れ済みの実機ロック／オフラインGPS試験の証拠は再利用し、録画器のコード経路を変更していない限り同じ30分試験を機械的に要求しない。統合アプリの追加経路だけを新たに検証する。正本はPR #92の同一HEADとする。

## 初回接続の条件

- すでにXcodeとiPhoneをWi-Fiペアリング済みなら、同じネットワーク内でワイヤレス接続できる可能性がある。
- **iOS 27以降と対応するXcode 27のDevice Hubなら初回もワイヤレスペアリング可能。** 同じWi-Fiに接続し、Device Hub → ＋ → Pair Nearby Deviceを使用。以前のOS／Xcodeはケーブルが必要になる場合がある。
- USB-CのMacとLightningのiPhoneならデータ通信対応USB-C→Lightningケーブルを借りるか用意する。充電専用は不可。
- Apple Developer Programの有料登録、TestFlight配布、外部公開、費用変更は本人の明示承認なしに行わない。
- 本人所有端末だけに署名して入れる。Apple Account、署名秘密情報、実測GPSを公開GitHubやチャットへ送らない。

Apple公式（Device Hub）: https://developer.apple.com/documentation/xcode/managing-your-simulated-and-physical-devices-in-device-hub/

## A. 画面ロック30分

1. 位置権限と正確な位置を許可し「探索開始」。最初のGPS点を端末内で確認、開始時刻・点数を控える。
2. アプリを強制終了せず、画面を30分以上ロック。ロックと解除の時刻を控える。
3. 「探索終了」後、対象セッションの「記録の検証サマリーを表示」で件数・時刻・5分以上の空白を確認。
4. 端末内のJSONL/GPXでロック区間に属する実測点の時刻、欠測時のセグメント分割を確認。

PASS: ロック中に実測点が保存され、時間・点数を原本と照合でき、補完点がない。
FAIL/保留: ロック中の点が0、時刻未照合、原本喪失、見かけ上の連続性しか確認できない。

## B. 通信オフ10分

1. 別セッションで正常な測位点を確認し、時刻を控える。
2. 機内モードに加えWi-Fi/モバイル通信が無いことを確かめ、10分以上ロック。遮断時刻・復帰時刻を控える。
3. 通信復帰後5分記録し、終了。元ログとGPXを端末内で確認。

PASS: GNSSが測位可能な環境では通信なしの実測点が保存され、欠測は補間されず保存される。
受信不可: GNSSが取得できず点が0の場合は環境・端末状態を残し、PASSにしない。
機内モードだけで無線が完全に遮断されていると誤認しない。

## C. 保存失敗→復旧

1. DEBUGビルドのみの「保存失敗→復旧を自己診断」を押す。GPS原本とは別の隔離フォルダに疑似STARTを書き、active marker保存失敗を注入する。
2. PASS: 孤立原本検出→同一バイトの原本バックアップ→別IDの新規セッション作成が成功した表示を確認。
3. 別の通常セッションを実機で開始しGPS点を保存後、アプリを強制終了して再起動。無断で測位再開しない・未終了の原本を保持・明示復旧/終了できることを確認。
4. 原本保護のため実機ディスクを満杯にしない。過去ログの削除・改変・アプリ削除はしない。

PASS: DEBUG隔離フォルト試験と実機強制終了/復旧試験の両方が成功。
ただし隔離フォルト試験は実ストレージ故障そのものを再現したわけではない。

## 必須ゲート

| Gate | 合格に必要な証拠 |
| --- | --- |
| BUILD | 最新HEAD CI全必須PASS、実機インストール |
| LOCK_30 | ロック中30分以上の実測GPS・時刻確認 |
| OFFLINE_10 | オフライン10分以上の実測または正しい欠測判定 |
| CRASH_RECOVERY | 強制終了/再起動/無断再開なし/原本保持 |
| STORAGE_FAULT_SIM | 隔離保存失敗・復旧・バイト一致 |
| EXPORT | GPX/JSONLの点数、時間、空白の整合 |
| PRIVACY | GPS原本の予期しない外部送信なし |

既に受け入れ済みのLOCK_30・OFFLINE_10等の証拠は保存して再利用する。統合シェルの追加によってGPS取得／保存処理が変わらない限り再試験を自動要求しない。新たに導入する3タブ操作・探索完了時の暗号化ファイル生成・Google Driveへの実到着と別経路の読戻し・復号検証だけは実機で必須。Android実機・独立審査・認証付き学習の本番接続・main統合は別ゲート。

## 個人情報を含めない報告

HEAD:
iPhone OS:
実機署名インストール: PASS / FAIL
LOCK_30: PASS / FAIL / 未実施（増分 点、欠測 回）
OFFLINE_10: PASS / FAIL / 受信不可 / 未実施（増分 点）
CRASH_RECOVERY: PASS / FAIL / 未実施
STORAGE_FAULT_SIM: PASS / FAIL / 未実施
EXPORT: PASS / FAIL / 未実施（点数、区間数のみ）
PRIVACY: PASS / FAIL / 未実施


## D. 3タブ統合版の最小追加試験

1. 対象HEADのsource-contract、ios-swift-syntax、ios-simulator-build（新しいUI／unit含む）が成功しているか確認する。PR #92のPrivacy HOLDや未合格の必須項目を隠さない。
2. MacBookで既存の \`mobile/ios/check-iphone-wireless.sh\` を実行し、端末接続状態を確認する。XcodeのApple Accountと自分のTeamは端末で設定。Apple ID／Team ID／証明書／GPS座標をチャットへ送らない。
3. 自分の端末から \`bash mobile/ios/install-owned-iphone-wireless.sh\` を実行。新しい署名版を上書き導入できたら、アプリ名「ハブAI」と3つのタブ（探索・ハブAI・ダッシュボード）を確認。既存アプリ／過去原本はアンインストールしない。
4. **初回のみ** iPhoneのGoogle Driveアプリへログインし、「ファイル」アプリ内でGoogle Driveが表示されることを確認。iPhoneアプリの「探索」画面にある「同期フォルダを選ぶ」から、非共有の \`HabuAI_Encrypted_Inbox\` を選ぶ。
5. **新規の短い安全な試験セッション**で、探索開始 → GPS実測1点以上 → 安全に停車してテスト観察（本物の生体捕獲は創作しない） → 探索終了。選択フォルダへの暗号化書込み結果を確認する。
6. iPhoneのアプリ内の「書込み・読戻し済み」は **File Provider上のローカル検証** であり、Google Driveの遠隔アップロード成功ではない。別セッション／別端末の認証済みGoogle Driveから \`.habuenc\` 到着を確認する。
7. 別の読取経路で暗号化ファイルのSHA-256、\`habu-device-inbox-v1\` 形式、想定した受信者のKey ID、サイズ、同一ファイルの二重送信抑止を確認する。復号には私有の受信鍵が必要。秘密鍵・生GPS・平文原本を公開Git、チャット、ログ、Actionsアーティファクトへ貼らない。
8. 安全に許可された非公開環境だけで暗号認証・元JSONLのSHA-256・セッションID・終了マーカーを独立検証する。成功するまで「本番同期合格」にしない。もしクラウドに到着しても、ダッシュボード確定反映や学習は別の検証ゲート。

**結果判定は分離する：** \`LOCAL_ORIGINAL_SAVED\`、\`DEVICE_ENCRYPTED_STAGED\`、\`DRIVE_REMOTE_RECEIVED\`、\`PRIVATE_DECRYPT_AND_SOURCE_SHA_PASS\`、\`DASHBOARD_RECONCILED\`、\`TRAINING_ELIGIBLE\`。前段階の成功から後段階を推測してはいけない。
