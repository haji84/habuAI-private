# HUB NATURAL ダッシュボード / 導入・公開ゲート

## 現在の位置づけ

- PC / iPhone / Android 共通のレスポンシブWebアプリ (PWA)。
- ユーザー指定の HUB NATURAL ロゴ。ダーク＋ゴールドデザイン。
- 2026年4月〜10月20日の暫定238匹。4〜8月は旧記録の原本再監査待ち。
- 月別 4〜10月: 8,23,60,35,45,50,17。07:00 JSTで探索夜を区切る。
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
