# Webサイトログイン自動化ツール仕様書

## 1. 概要

このドキュメントでは、さまざまなWebサイトのログインページへのアクセス方法と、自動ログイン機能の実装仕様について説明します。ログインページの要素抽出からログイン処理の実装までの手順を示します。このツールは特定のサイトに依存せず、設定ファイルを変更することで様々なサイトのログイン処理に対応できます。

## 2. 要素抽出の手順

### 2.1 AI要素抽出ツールの概要

AI要素抽出ツール（`ai_element_extractor.py`）は、AIを活用してWebページの要素を解析・抽出するツールです。このツールを使用して、ログインページの要素（入力フィールド、ボタンなど）を特定します。指示ファイルに基づいてページにアクセスし、AIを活用して要素を識別します。

抽出ツールの主な機能：
- 指示ファイルからセクションを解析
- 指定されたURLにアクセスしてHTMLを取得
- OpenAI APIを使用して要素を抽出・識別
- 抽出した要素情報をJSON形式で保存
- 必要に応じてログイン処理を実行

### 2.2 指示ファイルの作成

`docs/ai_selenium_direction.md` に以下のような指示を記述します：

```markdown
## 1. login
--概要
ログインページのログイン
--url
https://example.com/login
--ログインコード
src/modules/browser/login_page.py
--取得要素
アカウント入力フィールド
ユーザーID入力フィールド
パスワード入力フィールド
ログインボタン
```

### 2.3 要素抽出の実行

コマンドラインから以下のコマンドを実行して、ログインページの要素を抽出します：

```bash
python -m src.modules.browser.ai_element_extractor --section login
```

このコマンドにより、以下の処理が行われます：

1. 指示ファイルからセクション「login」の情報を読み取る
2. 指定されたURL（例: https://example.com/login）にアクセス
3. ページのHTMLを取得して解析
4. OpenAI APIを使用して要素を抽出
5. 抽出結果をJSON形式で `data/elements/login.json` に保存

追加のオプション：
- `--headless`: ヘッドレスモードでブラウザを実行
- `--auto-login`: 自動的にログイン処理を実行
- `--keep-browser`: ブラウザを開いたままにする
- `--save-cookies`: Cookieを保存する

### 2.4 抽出される要素情報

抽出される主な要素の例：

- アカウント入力フィールド（例: `#account_id`）
- ユーザーID入力フィールド（例: `#username`）
- パスワード入力フィールド（例: `#password`）
- ログインボタン（例: `.login-button`）

抽出される要素情報の例（JSON形式）：
```json
{
  "elements": [
    {
      "element_name": "アカウント入力フィールド",
      "element_type": "input",
      "selectors": {
        "id": "account_id",
        "name": "account_id",
        "css": "#account_id",
        "xpath": "//input[@id='account_id']"
      },
      "attributes": {
        "type": "text",
        "placeholder": "アカウントID"
      },
      "visible_text": "",
      "recommendations": "WebDriverWait と presence_of_element_located を使用し、テキストを送信する"
    }
  ]
}
```

## 3. ログインモジュールの実装仕様

### 3.1 ファイル構造

- **メインスクリプト**: `src/web_login.py`
- **ログインページクラス**: `src/modules/browser/login_page.py`
- **AIエレメント抽出**: `src/modules/browser/ai_element_extractor.py`
- **ブラウザ操作クラス**: `src/modules/browser/browser.py`
- **設定ファイル**: `config/settings.ini`
- **秘密情報ファイル**: `config/secrets.env`
- **セレクタ情報**: `config/selectors.csv`

### 3.2 設定ファイル（settings.ini）

```ini
[Login]
url = https://example.com/login
success_url = https://example.com/dashboard

# ベーシック認証設定
basic_auth_enabled = false
basic_auth_username = 
basic_auth_password = 

# ログイン判定用の要素
success_elements = ダッシュボード,ログアウト,マイアカウント
login_elements = loginForm,ログインする,ログインページ,ユーザー名,パスワード

[Cookies]
# 関連するドメイン（カンマ区切り）
related_domains = login.example.com,app.example.com

[BROWSER]
headless = false
auto_screenshot = true
screenshot_dir = logs/screenshots
screenshot_format = png
screenshot_quality = 100
screenshot_on_error = true
```

### 3.3 秘密情報ファイル（secrets.env）

```env
# サイト1のログイン情報
account_id1 = アカウントID
username1 = ユーザー名
password1 = パスワード

# サイト2のログイン情報
account_id2 = アカウントID2
username2 = ユーザー名2
password2 = パスワード2

# OpenAI API設定
OPENAI_API_KEY = sk-your-api-key
```

### 3.4 セレクタ情報（selectors.csv）

```csv
group,name,selector_type,selector_value,description
login,account_id,id,account_id,アカウントID入力欄
login,username,id,username,ユーザー名入力欄
login,password,id,password,パスワード入力欄
login,login_button,css,.login-button,ログインボタン
```

## 4. ログイン処理の流れ

### 4.1 基本的な処理フロー

1. 環境変数とコンフィグファイルの読み込み
2. ブラウザの初期化とセットアップ
3. ログインページへのアクセス
4. フォームへの入力（アカウントID、ユーザー名、パスワード）
5. ログインボタンのクリック
6. ログイン成功の確認（リダイレクト先URLまたは特定の要素の確認）
7. 処理の終了（ブラウザの終了）

### 4.2 環境変数とコンフィグファイルの読み込み

`EnvironmentUtils` クラスを使用して、設定ファイルと秘密情報を読み込みます：

```python
# 環境変数をロード
env.load_env()

# 設定ファイルから値を取得
login_url = env.get_config_value("Login", "url", "")
success_url = env.get_config_value("Login", "success_url", "")

# 秘密情報から値を取得
account_number = env.get_config_value("Login", "account_number", "1")
account_id = env.get_env_var(f"account_id{account_number}", "")
username = env.get_env_var(f"username{account_number}", "")
password = env.get_env_var(f"password{account_number}", "")
```

### 4.3 ログインページへのアクセスと入力

`LoginPage` クラスを使用して、ログインページにアクセスし、フォームに入力します：

```python
# LoginPageクラスのインスタンスを作成
login_page = LoginPage(selector_group='login')

# ログインページに移動
login_page.navigate_to_login_page()

# フォームに入力
login_page.fill_login_form()

# ログインボタンをクリック
login_page.submit_login_form()

# ログイン成功の確認
success = login_page.check_login_success()
```

### 4.4 エラー処理とリトライ

ログイン処理は複数回試行する仕組みを実装しています：

- 最大試行回数：設定ファイルの `max_attempts` 値（デフォルト: 3）
- タイムアウト時間：設定ファイルの `redirect_timeout` 値（デフォルト: 30秒）
- エラー発生時にスクリーンショットを保存

## 5. 実行方法

### 5.1 コマンドラインからの実行

```bash
# 基本的な実行方法（環境変数から認証情報を取得）
python src/web_login.py

# アカウント番号を指定して実行
python src/web_login.py --account 2

# ヘッドレスモードで実行（画面表示なし）
python src/web_login.py --headless
```

### 5.2 Pythonコードからの呼び出し

```python
from src.modules.browser.login_page import LoginPage

# ログインページクラスのインスタンスを作成
login_page = LoginPage(selector_group='login')

try:
    # ログイン処理を実行
    success = login_page.execute_login_flow()
    
    if success:
        print("ログイン成功！")
        # ログイン後の処理
    else:
        print("ログイン失敗...")
        
finally:
    # ブラウザを終了
    login_page.quit()
```

### 5.3 AI要素抽出ツールと組み合わせた実行

```python
from src.modules.browser.ai_element_extractor import AIElementExtractor

# AIエレメント抽出ツールのインスタンスを作成
extractor = AIElementExtractor(headless=False)

# ログイン処理を実行して、要素抽出
extractor.execute_login_if_needed(login_section="login")
extractor.execute_extraction(section_name="dashboard")
```

## 6. エラー処理とトラブルシューティング

### 6.1 エラータイプと対応

| エラータイプ | 原因 | 対処方法 |
|------------|------|---------|
| 要素が見つからない | セレクタの変更 | セレクタの更新（selectors.csv） |
| タイムアウト | ネットワーク遅延 | タイムアウト値の増加（settings.ini） |
| 認証エラー | 認証情報の誤り | 環境変数の確認（secrets.env） |
| ページ構造の変更 | サイトの更新 | AI要素抽出ツールで再抽出 |

### 6.2 スクリーンショット

トラブルシューティング用にログイン処理の各段階でスクリーンショットが保存されます：

- `login_page.png`: ログインページにアクセスした直後
- `login_form_filled.png`: フォーム入力後
- `after_login.png`: ログイン処理完了後
- エラー時: `login_page_error.png`, `login_form_error.png`, `login_submit_error.png`

## 7. メンテナンス

### 7.1 セレクタの更新

ログインページの変更があった場合は、AI要素抽出ツールを再実行して最新のセレクタを取得します：

```bash
python -m src.modules.browser.ai_element_extractor --section login
```

取得したセレクタ情報を `config/selectors.csv` に反映します。

### 7.2 ログインエラーの監視

ログイン処理の成功率を監視し、エラーが増加した場合はページの変更がないか確認します。このモニタリングによって、サイトの変更に迅速に対応できます。

## 8. セキュリティ考慮事項

- 認証情報は環境変数またはセキュアな設定ファイルに保存
- ヘッドレスモードでの実行を推奨（本番環境）
- パスワードなどの機密情報はログに出力しない
- スクリーンショットから機密情報が漏れないよう注意
- 秘密情報ファイルは適切なアクセス権限で保護

## 9. カスタマイズと拡張

### 9.1 新しいサイトへの対応

1. 新しいサイト用のセクションを指示ファイルに追加
2. AI要素抽出ツールでセレクタを取得
3. 設定ファイルにサイト固有の設定を追加
4. セレクタ情報をselectors.csvに追加
5. 必要に応じてログイン処理の拡張（2要素認証対応など）

### 9.2 拡張機能

- 複数アカウントの管理
- 2要素認証への対応
- ログイン後の操作の自動化
- ログイン状態の保持（Cookieの保存と再利用）
- ロギング機能のカスタマイズ
- 失敗時の自動リトライ設定 