# HUB NATURAL ダッシュボード / 導入・公開ゲート

## 現在の位置づけ

- PC / iPhone / Android 共通のレスポンシブWebアプリ (PWA)。
- ユーザー指定の HUB NATURAL ロゴ。ダーク＋ゴールドデザイン。
- 2026年4月の本人捕獲数**10匹**、8月の本人捕獲数**47匹**はいずれも本人が月間集計を確定。10月20日までの現在の累計は**243匹**。8月31日の2匹を旧45匹に新たに加算。個体IDと探索区間の独立審査は引き続き必要。
- 月別 4〜10月: 10,23,60,35,47,51,17。07:00 JSTで探索夜を区切る。
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


## 2026-10-23 訂正追補：4月17日は誤日付（Issue #55）

- 本人が旧DBの「4/17 2匹」を誤りと明言。4/17の**捕獲日別表示を0匹**に訂正する。ただし**探索実施・非捕獲のNegativeは未検証**であり学習/Exposureに転用しない。
- 旧DB ID54/55は生ログではなく派生DBなので、原記録を削除せず別日誤登録/ID56/57との重複を監査継続。自動で4/28に移動しない。
- 暫定月計11匹のうち日付付き整合数は9匹、差分2匹は `undated_captures` に暫定隔離。**実在する未登録2個体を立証したものではない**。
- 買い上げ証の本人報告は4/15=1、4/16=1、4/21=4、4/30=4、計10匹。買い上げは平日のみ、日付は捕獲日ではなく、4月捕獲分はすべて4月内に買い上げ、5月への持越しなし（本人申告）。
- 4/28の1匹は過去会話索引による候補。原文・個体原本の確認前には4/17の2匹を移して日付を生成しない。
- 4月月計11匹と10月20日まで累計241匹は一時的に**旧暫定表示**を維持。ただし買い上げ計10匹との齟齬があるため確定値とは扱わず、個体単位の照合後に正式変更する。
- Stage Gate・予測学習の正例、GPS・GPX・Negativeは未復元証拠をもって生成・昇格しない。
- 証拠ファイル：`data/reconstructions/habu_captures/2026-04-17-owner-correction.json`。


## 2026-10-23 現行訂正：4月10匹・累計240匹（旧記録は監査履歴）

**この節が現在の集計基準。上記の11匹/241匹は過去の訂正履歴であり、現行の集計値ではない。**

- 本人が4月の買い上げ証履歴（4/15=1、4/16=1、4/21=4、4/30=4、計10匹）、4月捕獲分の5月持ち越し買い上げなし、17日の誤日付を示し、4月の捕獲数を10匹に訂正することを明示的に依頼。
- 買い上げ日 ≠ 捕獲日。買い上げ証原本写真・元個体IDは未回収。本人指定の**暫定捕獲集計**として月10匹・10月20日まで240匹を採用し、全個体の科学的検証済みとは表記しない。
- 4/13=1、4/15=1、4/17=0（誤日付）、4/19=2、4/20=2、4/28=1（本人会話索引の報告。**報告時刻21:14:58は捕獲の実測時刻ではない**）、4/29=3（本人会話復元）。和は10匹。
- 4/28の1件は会話索引からの暫定復元。原文・正確な座標・サイズ・正式個体ID・GPXを未確認。正式学習/Stage Gate正例や探索Exposure/Negativeに使用しない。
- 旧4/17 ID54/55は日付誤りとして隔離。4/19のID56/57との重複や別日捕獲は未解決だが、差分2匹を「未復元2個体」として加算しない。従って `undated_captures=[]`、`undated_count=0`。
- 4/29の `data/reconstructions/habu_captures/2026-04-29-owner-chat.json` にある11匹/241匹は、作成時点の会話・月別集計の**歴史的な証拠**。改ざんしない。現行の正本数値は `dashboard/baseline_2026.json`、新しい訂正証拠は `data/reconstructions/habu_captures/2026-04-count-reconciliation-10.json`。
- 4〜10月の累計は10、33、93、128、173、223、240。その他月の月別捕獲数には変更なし。
- 正本数値訂正と同時に、ダッシュボード初期HTML、埋込スナップショット、ブラウザ/Pythonテストを同期。Issue #55で個体対応・書類原本照合を継続。


## 2026-10-23 本人による月間10匹の正式確定（現行優先）

本人が「暫定じゃなくて確定でいいよ」と明示したため、**2026年4月の本人捕獲数10匹を本人確定の月間集計**とする。4月10匹採用後の2026年10月20日までの累計は240匹。以前の11匹・241匹は旧履歴として保存するが、現行値として採用しない。

- 管理範囲：`dashboard/baseline_2026.json` の `owner_confirmed_monthly_counts["2026-04"]` が月間10匹 `OWNER_CONFIRMED`。生成JSONにも同属性を引き継ぐ。
- 買い上げ証4件・計10匹は本人提供の内訳情報。書類現物を直接照合した事実とは区別。買い上げ日と捕獲日は異なる可能性があり、元日付へ逆算しない。
- 個体ごとの時刻、場所、GPS、GPX、別夜の同一性は**未検証のものを未検証のまま管理**。月計の確定は個体単位の観測証拠を創作したり、Stage Gateやモデル学習に未検証データを昇格させたりする意味ではない。
- 4/17は誤日付として0匹、4/28の本人会話索引1匹・4/29の会話復元3匹は原文・GPS等の追加照合対象。旧4/17個体ID54/55と4/19 ID56/57はIssue #55で継続監査。
- 現行の確定区分を記録した証拠：`data/reconstructions/habu_captures/2026-04-count-reconciliation-10.json`。過去の復元JSONにある旧集計値は歴史的証拠として書き換えない。


## 2026-10-24 当時の正本：9月28日の5イベント＝本人捕獲6個体に訂正（次の8月訂正により更新）

**この節の累計241匹と8月45匹は、同日後続の本人確定訂正より前の履歴。現在の正本は最後の節および `dashboard/baseline_2026.json` の8月47匹・累計243匹。** 4月10匹の本人確定集計は不変。

- 9月28日5件の捕獲イベントは本人捕獲**6匹**を含む。9/29 00:00（07:00日界では9/28探索夜）に**同時刻同一地点で2匹**と原本ハブログに記録され、Processed capture_events.csvも1イベント2個体、個体DBにも異なる2つの個体IDが紐付く。他の4イベントは各1匹。
- 原本GPX 22,990測位点・SHA `2e9fde7aa459fc100abf8014d95635e697a638679cc9df731f4e0f6a80fb62f3` をbyte-exact復元し、捕獲イベント全5件の時空間位置を実データで照合済み。実証Actions： https://github.com/haji84/habuAI-private/actions/runs/39986753487 。GPX近接が個体2匹の画像証拠になるわけではない。2匹という個体数の直接根拠は本人原本ハブログ・本人の個体DB。
- 誤計上の原因：5**イベント**と6**個体**の取り違え。9月28日=5→6匹、9月月計=50→51匹、2026年10月20日まで累計=240→241匹。**これは4月の10匹を11匹に戻した結果ではない。** 月次系列10/23/60/35/45/51/17。
- ただしGPXを通過しただけでは探索努力・発見可能性や完全Negativeの確認ができない。HDOP品質通過21,852点と100m×10分GPS通過906単位は診断結果、Negativeや科学的なStage Gate母集団に昇格しない。現在の `model_learning.json` 未生成、正式P0未発行。
- 証拠追跡：`data/reconstructions/habu_captures/2026-09-28-count-correction.json` と `scripts/reconcile_actual_gpx_exposure.py`。過去の4月訂正監査ファイルにある旧累計240は作成当時の値として保存し、書き換えない。

## 2026-10-24 本人確定訂正：8月47匹、8月31日2匹を追加（現行優先）

本人が8月の月間捕獲数について「45匹維持、47匹への訂正保留ではなく確定」と明示した。このため**2026年8月は本人確定の47匹**を正式な月計として採用した。旧45匹の集計は履歴として残し、現行値には使用しない。

- 旧8月日別16夜の合計45匹は変更しない。旧日別集計に存在しなかった8月31日の探索夜に2匹を追加し、8月の17夜の合計を47匹とする。07:00 JSTの日界により、翌9月1日01:17の捕獲記述も8月31日の探索夜。
- 本人の8月月計47匹という確定申告は、各個体の科学的認証とは区別する。8月31日には原文の捕獲記述が2件あり、どちらもGPX時空間近接照合に成功。独立した正式個体ID、原TXTのバイト単位検証、探索結果の完全性については未認証。
- 月末累計は8月175匹、9月226匹、10月20日時点243匹。9月月計51匹・10月月計17匹は変更しない。
- `dashboard/baseline_2026.json` に `owner_confirmed_monthly_counts["2026-08"]` を追加し、`count=47` と `status=OWNER_CONFIRMED` を設定。4月10匹の本人確定はそのまま。
- 補正根拠 `data/reconstructions/habu_captures/2026-08-count-correction-owner-confirmed-47.json`。旧45匹を記録したGPX監査証拠JSON、GPX原本、過去のPDCAログを上書きしない。
- GPS通過のみ、または本人が月計47匹と認定した事実から、道路区間の探索実施、捕獲結果網羅性、Negativeの正解ラベルを生成してはならない。正式学習Positive/NegativeとStage Gateの認定は従来どおりブロック。
- 内蔵ダッシュボード初期スナップショット、集計テスト、8月GPX監査の読み替えを同じPRで更新し、新しい累計が反映されたことを確認する。

## 2026-10-26 本人確定の捕獲・探索稼働集計を別レイヤーとして追加

- 本人確定の累計捕獲 **249匹**、稼働 **97晩**、捕獲あり **86晩**、捕獲ゼロ **11晩**、1稼働あたり平均 **249/97 ≒ 2.57匹**。対象最終探索夜は2026-10-24。
- 日付基準は Asia/Tokyo の午前7時。4/12と4/17は捕獲0匹・本人確認済み稼働。8/30は本人が勤務中で探索なし、9/20は帰宅途中の偶発目撃で探索なし。いずれも稼働に足さない。
- 10/22夜2匹、10/24夜4匹は、既存の10/20までの243匹に加え、月計23匹・累計249匹とする。10/26ハブセンター持込2匹は過去捕獲に計上済みのため、追加しない。
- 元の `dashboard/baseline_2026.json` と原本データは変更せず、`dashboard/owner_effort_2026-10-26.json` の本人確認済み日付だけを使う。ゼロ匹の無記録日は稼働日と推定しない。
- 過去のゼロ晩6件と10月の捕獲夜2件を追加、元データの9/20は残したまま `EXCLUDED_NOT_SEARCH` と分類し、合計は97晩とする。
- 集計画面では稼働晩数、捕獲あり・ゼロ晩数、一晩平均、捕獲できた夜の割合、月別稼働・月別平均を表示し、CSVに稼働分類を含める。スマートフォンでも閲覧可能なレスポンシブUIとする。
- 新しい本人捕獲ログは従来の `data/raw/habu_logs` から追加可能。同じ捕獲夜の本人確定数と正規ログ数に矛盾があればビルドを停止し、二重加算しない。
- 今後の捕獲ゼロ探索は `data/raw/habu_effort/<year>/*.json` に、`schema_version=habu-effort-night-v1`、`source=user Habu log`、`operational_date=YYYY-MM-DD`、`owner_confirmed=true`、`search_performed=true`、`capture_count=0` を記録する。本人確認がないゼロ夜は無効。既存集計より前の日付は自動追加しない。
- 人が確認した稼働統計は個人の活動記録であり、AIモデル用のNegative、探索Exposure、GPS/GPXの科学的検証として使わない。捕獲日時・場所を推定生成しない。
- リポジトリの可視性がpublicであるため、捕獲地点、座標、具体的な移動経路、個人情報、認証情報を追加していない。公開サイトの本人認証・実機表示・CIパスは別途確認するまでは未完了。修正は分岐上に置き、独立レビューを経ずmainへ反映しない。


## 2026-10-26以降の確定記録の自動反映（レビュー中）

### 仕組み

- 2026-10-24までの確定済み集計（249匹、97晩、捕獲あり86晩、捕獲ゼロ11晩）は `dashboard/owner_effort_2026-10-26.json` に固定して保持する。これは監査用の起点であり、今後の追加や訂正のたびに数字を直接書き換えない。
- それ以降の本人確認済み探索は、個体時刻・位置情報を求めない**日別合計**のファイル `data/raw/habu_owner_nights/2026/YYYY-MM-DD.json` で登録する。1探索夜＝1ファイル。合計0匹も `search_performed=true` で稼働晩として数える。探索しなかった日はファイルを作らない。
- JST午前07:00が探索夜の境界。たとえば10月28日00:30の捕獲は10月27日の探索夜として記録する。日付と実際の夜を本人に確認してから保存する。
- 形式例。**以下は架空の入力例で実績ではない。** データの公開リポジトリには住所・GPS・画像・詳細な探索経路・個人識別情報・鍵を含めない。

```json
{
  "schema_version": "habu-owner-night-v1",
  "source": "user Habu log",
  "operational_date": "2026-10-27",
  "owner_confirmed": true,
  "search_performed": true,
  "capture_count": 3,
  "revision": 1
}
```

- 後から3匹→4匹と訂正する場合は**同じ日付のファイルを4匹、revision=2に更新**する。ファイルを追加して7匹にすることは禁止。Gitのコミット履歴が差分と変更者を保持する。
- 個体イベントの正規ログ `data/raw/habu_logs` または処理済み個体DBが同じ日を含む場合は、**一致する件数を一度だけ反映**。不一致ならビルドを失敗させる。既存のPR #92の10/22・10/24登録との混在も自動停止し、事前の統合判断が必要。
- 2026-10-24以前の既存日を訂正したい場合は、過去データを書き換えず `data/raw/habu_owner_amendments/2026/YYYY-MM-DD.json` に本人確認の訂正ファイルを置く。元の匹数・稼働状態との照合を必須にし、任意の新規日付を創作することは禁止。

```json
{
  "schema_version": "habu-owner-amendment-v1",
  "source": "user Habu log",
  "operational_date": "2026-10-24",
  "revision": 1,
  "owner_confirmed": true,
  "original_captures": 4,
  "original_search_performed": true,
  "capture_count": 3,
  "search_performed": true,
  "reason": "本人確認による匹数訂正"
}
```

- 上の訂正例も**架空の操作例**であり、10/24の確定4匹を実際に変更しない。
- 不確かな報告、機械学習用Exposure/Negative、捕獲場所などから探索晩を推定しない。本人確認・日別合計は個体別GPS検証の代用としない。

### 集計更新と承認境界

1. チャットやアプリで当日の探索有無と捕獲数の確認が取れたら、対応する日別JSONを作成または更新する（**会話をしただけではGitHubには保存されない**。接続済みGitHubへの書き込み処理が必要）。
2. GitHubで新規捕獲・ゼロ匹探索・訂正のいずれかが更新されると、`.github/workflows/hub-natural-dashboard.yml` がビルドを起動する。テストでは日付検査、0匹、重複、旧値照合、年・月集計、JS構文、公開する情報の範囲を検証する。
3. 結果は `dashboard/dist/data/capture_summary.json` とHTMLへ書き出され、稼働日数・捕獲あり/ゼロ・平均・月別・CSVが一致することを検査する。更新のない凍結ベースラインは残す。
4. 作業PRのCI成功は**本番反映ではない**。独立レビュー、他PRとの統合点検、Cloudflare Accessの実際の保護確認、本人の重大変更の明示承認が済むまではmainへ統合・デプロイしない。
5. デプロイ後のスマホ向けService Workerは最新HTML/JSONのオンライン取得を優先し、接続不能時に限り前回取得分を表示する。画面の最終探索夜が想定と一致するかを利用者が確認する。

## 2026-10-26 複数日混在の生ログ一括確認画面

- HUB NATURAL の「ログ取込」から `dashboard/intake.html` を開く。UTF-8テキストファイルを複数選択または全文貼り付け。生ログの内容はブラウザから外部APIに送らない。
- ファイル名や取り込み日でなく、各イベントに書かれた日時を使う。07:00 JST以前は前探索夜に分類し、一つのログに複数夜があれば別行に表示する。読めない日時は自動補完しない。
- ファイルのSHA-256で同一セッションの再送を除外。日時・ブロック本文が完全一致するイベントも重複候補にする。同時刻の異なる記録は警告し、別個体か重複かを決めつけない。目撃、持込、轢死、他種の匹数を捕獲数へ足さない。
- 最新の `dashboard/data/capture_summary.json` が取れない場合、確認パッケージの出力を禁止。過去日・登録済み夜は新規登録できず、別の承認済み訂正経路で照合する。
- 本人が新規夜について探索実施・捕獲数・登録意図を明示して初めて、地点・座標を含まない日別確認パッケージをダウンロードできる。ゼロ匹の探索夜にも対応。
- ダウンロードはGitHubへの登録ではない。承認済みfeature branchで `python scripts/import_owner_batch.py --batch PATH --repo-root .` を実行して照合後、`--apply` で新規日別確定値ファイルを作る。既存と同一ならスキップ、不一致は停止、mainへの直接投入は拒否する。原本は別途 byte-preserving intake で安全に保全する。
- UIのデータ確認、インポートとプライバシーは `tests/test_log_intake_ui.py` で検証。PR #92との二重加算防止、独立レビュー、Access、CI、mainデプロイの確認が済むまでは本番反映と呼ばない。
