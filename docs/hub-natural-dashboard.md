# HUB NATURAL ダッシュボード / 導入・公開ゲート

## 現在の位置づけ

- PC / iPhone / Android 共通のレスポンシブWebアプリ (PWA)。
- ユーザー指定の HUB NATURAL ロゴ。ダーク＋ゴールドデザイン。
- 2026年4月〜10月20日の暫定241匹。4〜8月は旧記録の原本再監査待ち。
- 月別 4〜10月: 11,23,60,35,45,50,17。07:00 JSTで探索夜を区切る。
- ハブ本人捕獲のみ。目撃・轢死・ヒメハブ・他人の捕獲は加算しない。
- baseline以前は凍結。後続の正規ログだけを自動集計し、原本を改変しない。
- 画面データ・JSONにはGPS・具体的地名・原文・認証情報を載せない。探索日と件数は含むので非公開を維持。

## ビルドと検証

Python 3.12+ / Pillow 11.3.0。
```sh
python -m pip install 'Pillow==11.3.0'
python -m unittest discover -s tests -p test_capture_dashboard.py -v
python scripts/build_capture_dashboard.py
python -m http.server 8080 --directory dashboard/dist
```
PCなら http://localhost:8080 へ。生成物 dashboard/dist/ はCI Artifactとして非公開保存。
正式アプリへの入口は dashboard/index.html。

## データ自動反映ルール

main に data/raw/habu_logs/** の正規化されたログまたは
data/processed/individuals/** の本人が明示された個体データが加わると再集計する。
原本受付だけで正規フォーマットに自動変換されるわけではない。
次のルールに違反するログは集計しない、またはビルドを止める。

- 07:00 JST境界、本人捕獲とその他反応の分離、一意イベントIDを検証。
- baseline 2026-10-20より前の新規投入は過去集計に重複加算しない。
- Raw/Processedで同一夜の匹数が食い違えば停止する。
- 同じ匹数でも個体ID照合が済んだとは断定しない。
- 2026-09-28はGitHub原本6個体／統合baseline5匹の既知差異がある。
  自動で6匹に修正せず、一次資料の突合を別工程で行う。

## 24時間アクセスするための保護付き公開（まだ未完了）

Private GitHub のActions ArtifactはiPhone/Androidで常時アクセスできるURLではない。
静的サイト配信には Cloudflare Pages を用いる計画。アクセス保護を検証するまでは
自動公開ジョブは明示的に無効としている。

1. Cloudflare Pages: project `hub-natural-private` を作成する。
2. Zero Trust Accessで本人メールだけAllowする。**本番とプレビューの両方**を保護する。
3. プライベートブラウザで本番URLとプレビューURLが未認証時に拒否されることを確認する。
4. GitHub Secrets `CLOUDFLARE_API_TOKEN` と `CLOUDFLARE_ACCOUNT_ID` を安全に登録。
5. ここまで検証してから repository variable `HUB_NATURAL_ACCESS_VERIFIED=true` を設定。
6. main統合後にGitHub Actionsを実行し、実機で更新・インストール・ログアウトを確認する。

ホーム画面への登録:
iPhone Safari: 共有→ホーム画面に追加。Android Chrome: アプリをインストール/ホーム画面に追加。

## 現時点の未達

- PRの承認とmainへの統合、対象headのActions PASS確認
- Cloudflare PagesとAccess本人認証、HTTPS URLの有効化
- iPhone / Android実機からのアクセス・更新確認
- 2026-10-21以降の新規ハブログ正規取込のエンドツーエンド検証

## 2026-10-21 CI障害の再現確認（原因はGitHub側のアカウント設定確認待ち）

- PR #48のダッシュボード CI は、ジョブ実行ステップ0件で失敗。
- 独立のRunnerテスト `HUB NATURAL runner admission smoke` を作成。Run https://github.com/haji84/habuAI-private/actions/runs/39619492540 も、Runner未割当で実行前失敗。
- 別の開発PRも同じ症状。したがって、今回のPython/HTML/ワークフロー内容を原因とする証拠はない。
- 請求・Actions利用枠・支払方法・アカウント制限が**最優先の調査候補**。未確認のため断定しない。
- GitHubで Settings → Billing and licensing → Usage (Actions) / Budgets and alerts / Payment information を確認。追加課金を承認なしに設定しない。
- 請求・上限に問題がない場合、GitHub SupportにRun IDとRunner ID=0、steps=0、ジョブログ404を提出する。

## Cloudflare接続・公開停止条件

- ChatGPT側Cloudflare連携は whoami、docs、API検索の独立リクエストがすべて内部失敗。アカウント内の実態を確認できない。
- ダッシュボードのURLが存在するとは報告しない。Cloudflare PagesおよびAccessの本人認証の実設定は未実施。
- 両URLが作成済みなら、GitHub Variables `HUB_NATURAL_PRODUCTION_URL` に本番サイトURL（例 https://hub-natural-private.pages.dev）、`HUB_NATURAL_PREVIEW_URL` に実在するプレビューURLを設定する。
- デプロイ前に `scripts/verify_pages_access.py` が、未ログインHTTPアクセスの両URLでCloudflare Accessへのログイン遷移を確認する。**HTTP 200は公開状態として即失敗**。403等だけでは安全性の証拠とはしない。
- `HUB_NATURAL_ACCESS_VERIFIED=true` のHuman Gateは従来どおり維持する。ツール単独のHTTP確認だけでは本人限定ポリシーの設定は立証できない。
- Cloudflare公式仕様により、プレビュー保護だけでは本番 pages.dev は保護されない。Cloudflare Access設定で両方を保護してから配信する。

## Cloudflareネイティブビルド（GitHub Actions利用枠制限時の代替）

Cloudflare Pages のGit連携ビルドはGitHub-hosted Actionsランナーを使用しないため、利用枠によるテスト開始前停止と切り離せる。
Cloudflare公式v3ビルド画像はPython・pipに対応（実稼働は要検証）。

**ただし、Git連携直後のプレビュー公開が危険。最初はプレビュー生成を無効化し、本人Accessを先に設定すること。**
実データの初回ビルドは、次の3変数が揃い、Accessの本番とプレビューが未ログイン認証誘導を返すまで停止する。

- `HUB_NATURAL_ACCESS_VERIFIED=true`
- `HUB_NATURAL_PRODUCTION_URL=https://hub-natural-private.pages.dev`
- `HUB_NATURAL_PREVIEW_URL=https://<実在するpreviewサブドメイン>.hub-natural-private.pages.dev`

Cloudflare Pages Git連携設定:
- 対象Private repo: `haji84/habuAI-private`、ブランチ `main`
- Root directory: `/`
- Build command: `bash scripts/build_cloudflare_pages.sh`
- Build output directory: `dashboard/dist`
- `PYTHON_VERSION=3.13.3`（v3ビルド環境に合わせて固定）
- GitHub Actionsのdeploy-protectedは従来どおり保護付きの代替経路として残すが、両経路を同時に有効化して同一プロジェクトを二重デプロイしない。

Access適用前にPR内データがプレビュー公開されないよう、Cloudflare側のGit連携・プレビュー自動デプロイ設定を**先に**監査する。未確認なら公開しない。

## 2026-10-22 ユーザー本人のGitHub Billing画面で上限を確認

- GitHub Free 個人アカウント。
- Actions minutes: **2,000 min used / 2,000 min included (100%)**。
- Actions Billable usage: **$0**、gross metered usage **$108.09**、included usage discounts **$108.11**。金額の差を未払い請求と解釈しない。
- 使用枠リセットまで画面表示で「11 days」（スクリーンショット時点）。
- Runner ID=0・steps=0 の独立スモークテストの実行前失敗は、無料枠使い切りと整合。
- 追加課金が必要なら本人判断に委ねる。**予算上限や支払方法を自動変更しない**。
- Runner smoke workflow は原因を切り分け終えたため削除し、無料枠復活後の不要な起動を減らす。
- 解消の選択肢は (A) 無料枠リセットを待つ、(B) 保護済みCloudflare Pagesネイティブビルドへ移行。いずれもmainに未検証のままマージしない。

## 初回Cloudflare Pagesデプロイの条件（2026-10-23修正）

旧手順には、**初回配信より前に存在しないプレビューURLを要求する循環依存**があったため修正した。
Cloudflareの**実アカウントAPI**で以下を先に独立検証する。

- Access application `HUB NATURAL - Owner only`、本番 `hub-natural-private.pages.dev`、プレビュー `*.hub-natural-private.pages.dev` の両方が保護対象
- Access policy `allow` は指定本人のメール1件のみ。Everyone/bypassポリシーなし
- Cloudflare Pages の `preview_deployment_setting=none` とプロダクションブランチ `main`
- 初回の `HUB_NATURAL_BOOTSTRAP_DEPLOYMENT=true` は上述の検証後に限り使い、**配信が成功したら直ちにfalseに変更する**。

Pagesのビルド環境変数:

```text
HUB_NATURAL_ACCESS_VERIFIED=true
HUB_NATURAL_PREVIEWS_DISABLED=true
HUB_NATURAL_BOOTSTRAP_DEPLOYMENT=true  # 初回だけ
HUB_NATURAL_PRODUCTION_URL=https://hub-natural-private.pages.dev
```

Git連携のbuild command: `bash scripts/build_cloudflare_pages.sh`、output: `dashboard/dist`。
本番配信後は `HUB_NATURAL_BOOTSTRAP_DEPLOYMENT=false` にし、以後のビルドで本番Accessログイン遷移をネットワークから確認する。プレビュー配信は今後も無効のままとする。
初回デプロイ後に匿名リクエストがHTTP 200を返す、またはAccessアプリ設定が変わっていれば**直ちにサイトを停止し、公開設定を再点検**する。

この設定はWebアプリへのアクセス保護であり、**Public GitHubリポジトリのGPX原本・捕獲データ・コミット履歴を非公開には戻さない**。

## 2026-10-23 本人申告に基づく4月月計の訂正

- 旧ダッシュボードの2026年4月 **8匹** は、後日作成した旧DB日付付きラベル（4/13=1、4/15=1、4/17=2、4/19=2、4/20=2）の和。
- 2026年5月25日の `ハブDB_2025-2026_復旧版.xlsx`（捕獲DB）には、`2026-04-UNK-01〜11` として「4月捕獲11匹の復旧枠。日付/時刻/座標は未復元」が保存されている。これは**個別日付が確認された11件ではなく月別記憶統計**。
- 本人が2026-10-23に「4月は11匹」と訂正。月別表示はこの過去の記憶統計に合わせ、**11匹（暫定）**とする。日付付き8匹との差分 **3匹** は `undated_captures` に保存し、捕獲日の創作や日付付き8匹との二重計上はしない。
- 月別合計 **241匹（暫定）** = 旧238 + 日付未復元3。他月は据え置き。日付が確認できる4月のカレンダーは従来の8匹のまま。3匹は日付未復元として別に表示、CSVにも日付なし行を追加。
- Stage Gate / 予測学習には未知日時3匹を特定日時の正例として使わない。原本が見つかったらイベント照合・重複排除・日付復元・再集計を行い、月計11匹との整合性を再検証する。
- 2026-09-28の5件/6個体の差は今回の修正対象外。別途監査する。

## 2026-10-23 4月29日探索夜の3匹を本人の過去会話から復元

- 4月の月計11匹は変更しない。既存の旧DBラベル8匹に加え、**2026-04-29探索夜に本人捕獲3匹**という過去の本人会話を確認した。
- 旧 `undated_captures` の3匹をこの探索夜へ移動し、`undated_captures` を空にする。**同じ3匹を再追加して月計14匹にしない**。累計は241匹のまま。
- 当該3匹の会話上の捕獲時刻は4月29日の20時台〜23時台のため、07:00 JSTの探索夜区切りでも4月29日に属する。4月30日00時台の会話上の確認発言を捕獲と誤認しない。
- データ区分は「本人会話からの日付と匹数の復元」。個体ID、GPX、原本ログとの独立照合は未完了。**正式学習、Negative/Exposure、Stage Gateの検証済み正例には未採用**。
- 4月17日の旧DBラベル2匹と過去本人発言0匹の矛盾は継続監査事項。今回それを勝手に0匹へ変更しない。
- 公開され得るGitHubには具体的な発見地点・座標・個人情報を追加しない。

## 2026-10-23 4月29日3匹の復元IDとGPX欠損の確定区分

- 3匹の本人会話を根拠とする復元証拠は、Private repo の `data/reconstructions/habu_captures/2026-04-29-owner-chat.json` に保存する。
- 各個体へ `RECON-20260429-01`、`02`、`03` を割り当てた。これは**照合用の仮ID**であり元のイベントID／正式個体IDではない。
- 観測時刻は本人会話上の「頃」であってGPS測定時刻ではない。地域・状況は証拠ファイル内のみ保持し、Webダッシュボードには出さない。
- 実測GPX、GPS座標、速度、走行経路は未確認。地名を直線で結ぶ等の人工GPXは作成しない。対応が確認できる元ログ／GPXが見つかるまで100mセル、探索Exposure、Negative、Stage Gate正式正例への使用を禁止する。
- 旧未復元3匹を4月29日の3匹に紐付けただけで新たな3匹は計上しない。2026年4月=11匹、10月20日まで累計=241匹の暫定値は不変。
- 4月17日の旧DB2匹／本人発言0匹の矛盾、原本個体IDとの重複照合は未解決として残す。
