# EBiSログインツールの使い方

このツールは、EBiSのログインページにアクセスし、認証情報を入力してログインを行うためのPythonスクリプトです。

## 環境設定

1. 環境変数に認証情報を設定します：
   - `account_key1`: EBiSのアカウントID
   - `username1`: ログインユーザー名
   - `password1`: ログインパスワード

設定方法：
```bash
# Windowsの場合
set account_key1=あなたのアカウントID
set username1=あなたのユーザー名
set password1=あなたのパスワード

# または、config/secrets.envに設定する場合
```

## 実行方法

### コマンドライン引数を使用する場合

```bash
# 基本的な実行方法（環境変数から認証情報を取得）
python -m src.modules.browser.login_page

# 認証情報をコマンドラインで指定
python -m src.modules.browser.login_page --account_key アカウントID --username ユーザー名 --password パスワード

# ヘッドレスモードで実行（画面表示なし）
python -m src.modules.browser.login_page --headless
```

### Pythonコードから呼び出す場合

```python
from src.modules.browser.login_page import LoginPage

# ログインページクラスのインスタンスを作成
login_page = LoginPage(headless=False)

try:
    # ログインを実行
    success = login_page.login(
        account_key="アカウントID",
        username="ユーザー名",
        password="パスワード"
    )
    
    if success:
        print("ログイン成功！")
        # ログイン後の処理を追加
    else:
        print("ログイン失敗...")
        
finally:
    # ブラウザを閉じる
    login_page.close()
```

## スクリーンショットについて

ログイン処理中に以下のスクリーンショットが撮影されます：

1. `login_page.png`: ログインページにアクセスした直後
2. `login_before.png`: 認証情報を入力した後、ログインボタンをクリックする前
3. `login_after.png`: ログイン処理完了後

エラーが発生した場合は、以下のようなスクリーンショットも撮影されます：

- `error_account_key_not_found.png`: アカウントID入力欄が見つからない場合
- `error_username_not_found.png`: ユーザー名入力欄が見つからない場合
- `error_password_not_found.png`: パスワード入力欄が見つからない場合
- `error_login_button_not_found.png`: ログインボタンが見つからない場合
- `error_login.png`: その他のログイン処理でエラーが発生した場合

これらのスクリーンショットは `logs/screenshots/[タイムスタンプ]/` ディレクトリに保存されます。

## 注意事項

- ブラウザの動作は `settings.ini` の `[BROWSER]` セクションの設定に影響されます
- ヘッドレスモードでは画面表示がなく、バックグラウンドで動作します
- ログインに失敗した場合、エラーメッセージがログに出力されます 