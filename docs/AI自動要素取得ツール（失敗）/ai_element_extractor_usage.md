# AI要素抽出ツールの使用方法

このドキュメントでは、AI要素抽出ツール（`ai_element_extractor.py`）の使用方法について説明します。
このツールは指示ファイルからセクションを解析し、指定されたURLのページを解析して要素情報を抽出します。
さらに、ログイン後のページやポップアップなど、操作が必要な要素も抽出できます。

## 前提条件

- Python 3.6以上がインストールされていること
- Seleniumとその依存関係がインストールされていること
- 環境変数`OPENAI_API_KEY`が`config/secrets.env`で設定されていること
- 指示ファイル`docs/ai_selenium_direction.md`が存在すること

## 指示ファイルの形式

指示ファイル（`docs/ai_selenium_direction.md`）には、以下の形式でセクションを記述します：

```markdown
## 1. セクション名
--概要
セクションの概要説明
--url
https://example.com
--取得要素
要素1の名前
要素2の名前
要素3の名前
```

### 操作手順付きセクション

操作が必要な場合（ログイン後のページやポップアップなど）は、以下のように`--操作手順`セクションを追加します：

```markdown
## 5. popup_dialog
--概要
ポップアップダイアログの要素取得と操作
--url
https://example.com/dashboard
--操作手順
1. 設定メニューをクリック
2. アカウント設定をクリック
3. 5秒待機
--取得要素
ダイアログタイトル
閉じるボタン
設定フォーム要素
保存ボタン
```

**操作手順の記述形式**:

1. 各操作は番号付きリスト（`1.`, `2.` など）で記述
2. 以下の操作タイプがサポートされています：
   - クリック操作: `設定メニューをクリック`
   - 入力操作: `ユーザー名に「test」を入力`
   - 選択操作: `ドロップダウンから「オプション1」を選択`
   - 待機操作: `5秒待機`

## 実行方法

コマンドラインから以下のように実行します：

```bash
# 通常モード
python -m src.modules.browser.ai_element_extractor --section セクション名

# ヘッドレスモード
python -m src.modules.browser.ai_element_extractor --section セクション名 --headless

# 自動ログイン＋別セクション実行（ログイン済み状態での要素抽出）
python -m src.modules.browser.ai_element_extractor --auto-login --section セクション名
```

主なオプション：
- `--section セクション名` : 処理するセクション名を指定（デフォルト: login）
- `--headless` : ブラウザを表示せずにヘッドレスモードで実行
- `--auto-login` : 自動的にログイン処理を実行してからセクション処理を行う
- `--force-login` : Cookieが有効な場合も強制的に再ログインする
- `--keep-browser` : 処理完了後もブラウザを開いたままにする
- `--save-cookies` : 実行後にCookieを保存する（非推奨）

例：
```bash
# "login"セクションを解析（ログインページの要素を抽出）
python -m src.modules.browser.ai_element_extractor --section login

# ログイン処理を実行してから"dashboard"セクションを解析
python -m src.modules.browser.ai_element_extractor --auto-login --section dashboard

# "popup_dialog"セクションをヘッドレスモードで解析
python -m src.modules.browser.ai_element_extractor --section popup_dialog --headless
```

## 出力結果

ツールは以下の出力を生成します：

1. HTMLコンテンツの保存
   - `data/pages/`ディレクトリに保存されます
   - ファイル名は`{ドメイン}{パス}_{タイムスタンプ}.html`の形式

2. 操作実行時のスクリーンショット
   - 各操作の前後でスクリーンショットが撮影されます
   - ファイル名は`operation_{番号}_before.png`および`operation_{番号}_after.png`の形式

3. 抽出された要素情報
   - コンソールにログとして出力されます
   - 各要素について以下の情報が表示されます：
     - 要素名
     - 要素タイプ
     - セレクタ情報（ID, name, CSS, XPath）
     - 属性情報
     - 表示テキスト
     - 推奨操作方法

## 使用例

### ログインページの要素抽出

```bash
python -m src.modules.browser.ai_element_extractor --section login
```

この例では、`login`セクションを解析し、ログインページの要素（アカウントID入力フィールド、ログインID入力フィールド、パスワード入力フィールド、ログインボタンなど）を抽出します。ログインページの要素取得は通常1回だけ行えば十分です。

> **注意**: `--auto-login`オプションと`--section login`オプションを同時に使用すると、ログイン処理は実行されますが要素抽出は行われません。これは最初のログイン処理後に続けて別のセクションの要素抽出を行うことを意図したものです。純粋にログインページの要素を抽出したい場合は`--auto-login`オプションを使用しないでください。

### 操作を含む要素抽出

```bash
python -m src.modules.browser.ai_element_extractor --section popup_dialog
```

この例では、`popup_dialog`セクションを解析し、以下のステップを実行します：

1. 指定されたURLにアクセス
2. 「設定メニューをクリック」操作を実行
3. 「アカウント設定をクリック」操作を実行
4. 操作後のページからポップアップダイアログの要素を抽出

### ダッシュボードの要素抽出

```bash
python -m src.modules.browser.ai_element_extractor dashboard
```

この例では、`dashboard`セクションを解析し、ダッシュボードページの要素（ナビゲーションメニュー、ユーザー情報など）を抽出します。

## トラブルシューティング

- **操作に失敗する場合**:
  - 要素の特定方法を見直す
  - より具体的な要素名を使用する
  - 待機時間を追加する（例: `3秒待機`）

- **要素が見つからない場合**:
  - ページが完全に読み込まれているか確認
  - 操作手順が正しく実行されているか確認
  - ページのHTML構造を確認

- **OpenAI APIエラー**:
  - API KEY が正しく設定されているか確認
  - レート制限に達していないか確認

## 注意事項

- このツールはSeleniumを使用しているため、環境によっては適切なWebDriverが必要です
- 大規模なHTMLコンテンツの場合、OpenAI APIへの送信が制限される場合があります
- 認証が必要なページの場合、事前にログイン操作を行う必要があります 