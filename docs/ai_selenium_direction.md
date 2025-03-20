## 1. login
--概要
ログインページのログイン
--url
https://id.ebis.ne.jp/
--ログインコード
src/modules/browser/login_page.py
--取得要素
アカウントID　入力フィールド
ログインID　入力フィールド
パスワード　入力フィールド
ログイン　クリックボタン

## 2. detail_analytics
--概要
詳細分析のcsvをダウンロード
--url
https://bishamon.ebis.ne.jp/dashboard
--前提操作
ログイン src/modules/browser/login_page.py
--取得要素
詳細分析　ボタン
全トラフィック　ボタン
カレンダー　ボタン
カレンダー　ボタン　ダイアログ
　期間開始　フィールド
　期間終了　フィールド
　適用　ボタン
ビュー　ボタン
プログラム用全項目ビュー　ボタン
エクスポート　ボタン
表を出力（CSV）　ボタン