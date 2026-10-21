# HUB NATURAL ダッシュボード：導入・公開ゲート

## 基準
PC・iPhone・Android共通のレスポンシブPWA。元画像のHUB NATURALロゴ、暗色＋落ち着いたゴールドを使用。
2026年4月〜10月20日の暫定238匹をベースラインに固定。月別: 8,23,60,35,45,50,17。
2026年8月までの旧DBは原本再照合待ち。朝07:00 JSTの日界で本人捕獲だけ加算。
目撃・轢死・他人捕獲・ヒメハブは加算しない。未探索は0件ではなく不明。

## 実行
Python 3.12+、Pillow 11.3.0が必要。
1. python -m pip install Pillow==11.3.0
2. python -m unittest discover -s tests -p test_capture_dashboard.py -v
3. python scripts/build_capture_dashboard.py
4. python -m http.server 8080 --directory dashboard/dist
5. PCで http://localhost:8080/ を開き、スマホもHTTPS配信後に同じWebアプリを使う。

## GitHub自動集計
mainに data/raw/habu_logs 以下の正規のhabu-night-log-v2、または data/processed/individuals 以下の個人所有者明記のCSVが追加されるとCIで再計算。
baseline探索夜以前のログを再加算しない。重複ID・07:00区切り不一致・Raw/Processed集計不一致で更新を止める。
原本の任意テキストを置くだけでは自動追加にならず、正規化・照合工程が必要。
CIのArtifactはプライベートであり、配信URLを意味しない。
JSONにGPS座標、地名、元ログ、秘密情報は含めない。ただし探索夜別の件数は含まれるため閲覧認証が必要。
生成物 dashboard/dist はコミットしない。

## 公開前の必須Human Gate（未完了）
1. Cloudflare Pages上に project hub-natural-private を本人アカウントで作る。
2. Cloudflare Accessで *.pages.dev の本番と *.<project>.pages.dev の全プレビューを保護する。
3. AccessのAllow対象は本人の確認済みメールアドレスのみ。他人には公開しない。
4. プライベートブラウザから本番・プレビューの未認証アクセスが拒否されることを確認する。
5. GitHub repository secrets に CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID を登録。トークン権限は最小限。
6. 上記全部の実証後にownerが repository variable HUB_NATURAL_ACCESS_VERIFIED=true を設定。
7. mainに統合されるとActionsがビルドし、保護済みPagesへ配信する。
8. iPhoneはSafariの「共有→ホーム画面に追加」、AndroidはChromeの「アプリをインストール」でホーム画面から利用する。

**重要:** PagesのプレビューだけのAccessでは本番pages.devは公開されてしまう。
Accessを確認できない限り自動デプロイは無効。Private repoのデータを勝手にPublic Pagesへ出さない。

## 残る実機検証
PRレビュー・CI成功・mainマージ・Cloudflare Access設定・実在のHTTPS URL取得・iPhone/Androidからログインと更新を確認する。
10月21日以降の実績も、正本取込後の件数検証が必要。
