# HUB NATURAL: GPS原本の私有移行と公開Git履歴の是正

状態: **RELEASE_HOLD / 原本移行未完了 / 履歴修復未完了**。これはリリース許可ではなく、安全な実行手順の準備である。

対象: GitHub `haji84/habuAI-private`、既存Draft PR #92、私有Library `/ハブAI/Raw/`。確認時点でGitHubはPUBLIC。名前にprivateとあっても非公開ではない。認証されたCloudflare Pagesも公開Gitソース、過去のコミット、forkを守るものではない。

## 実行する順序

1. **直ちに新たな公開を止める。** PR #92はDraftのまま、`PUBLIC_SOURCE_AUDIT_HOLD`の安全ゲートを解除しない。公開GitにGPS、捕獲・目撃地点、路線、位置付き原文、鍵、復号パスフレーズを追加しない。
2. **所有者の管理権限で既存GitHub repoを一時的にPrivateへ変更。** これはChatGPTの現在のGitHub接続で実行できない。GitHub > Settings > General > Danger Zone > Change repository visibility。公開forkはPrivate化されず残る可能性がある。GitHub Actionsの使用量/機能やCloudflare連携への影響も確認する。
3. 私有Libraryの原本とGitの元データを原本バイトのSHA-256で照合。Libraryに一部GPXが存在するだけでは全期間・全バイトのバックアップを証明できない。欠けた夜やログを補間しない。
4. **信頼できるMac/PC**で全ブランチ・タグをfetchしたローカルcloneから、現在の機微原本とGit履歴全体をそれぞれ暗号化した私有保管物へ移す。パスフレーズは端末で対話入力し、GitHub、Actions、このチャットには送信しない。元のGit sourceは消さない。
5. 復号・独立読戻し・原本SHA-256・`git bundle verify`に合格した後、研究/ダッシュボードが必要とする入力を別の私有データ経路へ移す。地点のない確認済み集計だけを公開コードから参照する。集計数・重複防止・モデル入力・例外を変更しない。
6. 履歴中の機微ファイル・過去のリネーム・PR参照とforkを確認し、所有者の別承認後に`git-filter-repo`やGitHub Supportの手順へ。全ての関連クローンとPRも調整する。**現在、履歴書換/force push/削除は未実施。**
7. 公開Gitの全refs、Actionsログ/配布物、Pages配信物、匿名化集計、私有保管物を独立に確認してから、PR #92の統合を判断する。第三者が既に取得した原本まで消去できたとは断定しない。

## Mac/PCのオフライン移行ツール

`tools/gps_private_vault.py` は、既存の `scripts/private_dashboard_crypto.py` のAES-256-GCM認証付き暗号を使用する。パスフレーズからPBKDF2-HMAC-SHA256を600,000回適用して32バイト鍵を作る。salt/nonceは毎回乱数、チャンクごとのSHA-256と認証タグを照合する。原本名や座標を含むmanifestは暗号化され、出力ファイル名はランダム。パスフレーズをGitや環境変数に保存しない。**実際の原本を使うGitHub Actionsでの実行は禁止。**

`archive` は現在のHEADの原本候補を暗号化、`history-archive` は**ローカルで取得済みの全Git refs**をGit bundleのまま直接暗号化する（平文bundleの一時ファイルなし）。`verify` は全暗号化チャンクを独立に復号・整合性確認。`restore` のみ明示された私有フォルダへ平文復元し、既存ファイルの上書きを拒否する。`history-scan` と `history-pathlist` は履歴修正の候補を調べるが、自動書換しない。

ローカルでの実行例:

```bash
cd /path/to/trusted-local-clone
git fetch --all --tags --prune

mkdir -p "$HOME/HABU-PRIVATE-VAULT"
chmod 700 "$HOME/HABU-PRIVATE-VAULT"

python3 -m pip install -r requirements-private-dashboard.txt

# 公開ログに個別のファイル名を出さない棚卸し
python3 tools/gps_private_vault.py scan --repo "$PWD"
python3 tools/gps_private_vault.py history-scan --repo "$PWD"

# パスフレーズはターミナルで対話入力
python3 tools/gps_private_vault.py archive \
  --repo "$PWD" --out "$HOME/HABU-PRIVATE-VAULT/current-raw"
python3 tools/gps_private_vault.py history-archive \
  --repo "$PWD" --out "$HOME/HABU-PRIVATE-VAULT/all-fetched-history"

# 実際の復号検証（アーカイブと鍵は別々に保管）
python3 tools/gps_private_vault.py verify \
  --vault "$HOME/HABU-PRIVATE-VAULT/current-raw"
python3 tools/gps_private_vault.py verify \
  --vault "$HOME/HABU-PRIVATE-VAULT/all-fetched-history"

# 元Git bundleの検証には私有領域での明示的復元が必要
python3 tools/gps_private_vault.py restore \
  --vault "$HOME/HABU-PRIVATE-VAULT/all-fetched-history" \
  --out "$HOME/HABU-PRIVATE-VAULT/verify-history"
git bundle verify "$HOME/HABU-PRIVATE-VAULT/verify-history/internal/all-fetched-refs.bundle"

# 機微ファイルの履歴削除候補を私有ファイルにだけ出力
python3 tools/gps_private_vault.py history-pathlist \
  --repo "$PWD" --out "$HOME/HABU-PRIVATE-VAULT/history-review-paths.txt"
```

**注意点**

- ローカルcloneのrefが不足している場合、history-archiveはその未取得refsを含まない。GitHub内部PR refs、外部fork、キャッシュ、第三者cloneは別に確認が必要。
- history-pathlistはパス名に基づく候補であり、無害そうな名前に入った過去の秘密GPSや他のリポジトリは除外され得る。実行前に独立にレビューする。
- 暗号化の証明は原本移行の準備であり、公開履歴が消えた証明ではない。出力は必ず公開Gitの外に保管する。パスフレーズを紛失すると復元できない。
- 旧研究処理やテストが原本を直接読む場合、プライベート入力経路と統計を確認してからGitから切り離す。現在のコードだけで履歴を消すと既存の学習・監査が壊れる可能性がある。
- 公開forkと第三者が過去に持ち帰ったコピーは履歴を書き換えても自動消去されない。GitHub Supportとのやりとり、関連PRの調整は別工程。
- 本資料に具体的な所有者GPS座標、捕獲地点、実原本パス、暗号鍵、ソース本文を載せない。

GitHub公式資料:
- https://docs.github.com/ja/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility
- https://docs.github.com/ja/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository

実施完了の判断は、暗号化した正本の私有保存、鍵の分離、復号読戻し、全期間の照合、履歴修復、GitHub Supportの処理、それぞれ独立した証拠が揃ってから。
