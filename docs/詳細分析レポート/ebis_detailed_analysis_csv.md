# アドエビス詳細分析ページCSVダウンロード機能仕様書

## 1. 概要

このドキュメントでは、AD EBiS（アドエビス）の詳細分析ページにアクセスし、指定された日付範囲のデータをCSVとしてダウンロードする機能の実装仕様について説明します。この機能は既存のログイン処理を拡張し、詳細なアクセスデータの自動取得を可能にします。

## 2. 機能要件

### 2.1 基本機能

- アドエビスの詳細分析ページにアクセスする
- 指定された日付範囲のデータを選択する
- CSVダウンロード機能を実行する
- ダウンロードされたファイルを指定したディレクトリに移動・リネームする
- 処理結果をログに記録する

### 2.2 動作環境

- Python 3.9以上
- Selenium WebDriver
- Chrome/Chromium ブラウザ
- 必要なPythonパッケージ（requirements.txtに記載）

### 2.3 依存コンポーネント

- `LoginPage` クラス（ログイン処理）
- `Browser` クラス（ブラウザ操作の共通機能）
- `EnvironmentUtils` クラス（環境変数と設定ファイルの管理）

## 3. 設計仕様

### 3.1 クラス設計

#### 3.1.1 詳細分析ページクラス

```python
class DetailedAnalysisPage:
    """
    アドエビス詳細分析ページ操作を担当するクラス
    POMパターンに基づき、詳細分析ページ専用の操作メソッドを提供します
    """
    
    def __init__(self, browser=None):
        """詳細分析ページクラスの初期化"""
        # ブラウザインスタンスの初期化
        # 設定の読み込み
        
    def navigate_to_detailed_analysis(self):
        """詳細分析ページに移動"""
        
    def select_date_range(self, start_date, end_date):
        """日付範囲を選択"""
        
    def download_csv(self):
        """CSVをダウンロード"""
        
    def wait_for_download_and_process(self, target_date, output_dir=None):
        """ダウンロード完了を待機し、ファイル処理を行う"""
        
    def execute_download_flow(self, start_date, end_date=None, output_dir=None):
        """ダウンロードフロー全体を実行"""
        
    def quit(self):
        """ブラウザを終了"""
```

### 3.2 設定項目

#### 3.2.1 設定ファイル（settings.ini）の追加設定

```ini
[AdEBIS]
url_details = https://bishamon.ebis.ne.jp/detail_analyze

[Download]
timeout = 90
directory = data/downloads
```

#### 3.2.2 セレクタ情報（selectors.csv）の追加

```csv
group,name,selector_type,selector_value,description
detailed_analysis,date_picker_trigger,xpath,/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[1]/div[2]/input,日付カレンダーを開くボタン
detailed_analysis,start_date_input,xpath,/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div[2]/div[1]/div[1]/input[1],開始日入力フィールド
detailed_analysis,end_date_input,xpath,/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div[2]/div[1]/div[1]/input[2],終了日入力フィールド
detailed_analysis,apply_button,xpath,/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div[2]/div[2]/button[2],適用ボタン
detailed_analysis,import_button,xpath,//*[@id="common-bar"]/div[2]/nav/div[2]/div[4]/div[1],インポートボタン
detailed_analysis,download_button,xpath,//*[@id="common-bar"]/div[2]/nav/div[2]/div[4]/div[2]/a,ダウンロードボタン
```

## 4. 処理フロー

### 4.1 基本フロー

1. `LoginPage` クラスでログイン処理を実行
2. `DetailedAnalysisPage` クラスのインスタンスを作成（同じブラウザセッションを使用）
3. 詳細分析ページに移動
4. 指定された日付範囲を選択
5. CSVダウンロード処理を実行
6. ダウンロード完了まで待機
7. ダウンロードされたファイルを指定されたディレクトリに移動・リネーム
8. 処理結果をログに記録

### 4.2 ダウンロードフロー図

```
[ログイン処理]
       ↓
[詳細分析ページに移動]
       ↓
[ポップアップ処理（存在する場合）]
       ↓
[日付範囲選択]  → [日付選択エラー]
       ↓           ↓
[CSVダウンロード] → [ダウンロードエラー]
       ↓           ↓
[ファイル処理]   → [ファイル処理エラー]
       ↓
[処理完了]
```

## 5. エラー処理

### 5.1 エラー種別と対応

| エラー種別 | 原因 | 対応方法 |
|----------|------|---------|
| ナビゲーションエラー | URLが無効、ネットワークエラー | URLの確認、再試行 |
| 日付選択エラー | セレクタの変更、日付形式エラー | セレクタの更新、日付形式の確認 |
| ダウンロードエラー | ボタンセレクタの変更、権限エラー | セレクタの更新、ユーザー権限の確認 |
| ファイル処理エラー | ダウンロード未完了、ファイル形式変更 | タイムアウト値の増加、ファイル形式の確認 |

### 5.2 例外処理

- 全ての操作メソッドは `handle_errors` デコレータでラップし、例外発生時にはスクリーンショットを取得
- クリティカルなエラーは上位レベルで捕捉し、Slack通知などで管理者に通知
- エラー発生時も可能な限り処理を継続し、最終的な結果を返却

## 6. 実装例

### 6.1 モジュールの使用例

```python
from datetime import datetime, timedelta
from src.modules.browser.login_page import LoginPage
from src.modules.browser.detailed_analysis_page import DetailedAnalysisPage

# 日付の設定
target_date = datetime.today() - timedelta(days=1)  # 前日

# ログイン処理
login_page = LoginPage()
if login_page.execute_login_flow():
    # 詳細分析ページ処理
    analysis_page = DetailedAnalysisPage(login_page.browser)
    result = analysis_page.execute_download_flow(target_date)
    
    if result:
        print(f"CSVダウンロードが完了しました: {result}")
    else:
        print("CSVダウンロードに失敗しました")
    
    # ブラウザ終了（分析ページからのみ終了すれば良い）
    analysis_page.quit()
else:
    print("ログインに失敗しました")
    login_page.quit()
```

### 6.2 コマンドライン実行例

```bash
# 前日のデータをダウンロード（デフォルト）
python src/ebis_download_csv.py

# 指定日のデータをダウンロード
python src/ebis_download_csv.py --date 2023-03-15

# 日付範囲を指定してダウンロード
python src/ebis_download_csv.py --start-date 2023-03-01 --end-date 2023-03-31

# アカウント指定
python src/ebis_download_csv.py --account 2

# 出力先ディレクトリ指定
python src/ebis_download_csv.py --output-dir data/reports
```

## 7. テスト方法

### 7.1 単体テスト

- 日付選択機能のテスト
- ダウンロード処理のテスト
- ファイル処理のテスト

### 7.2 結合テスト

- ログイン処理から詳細分析ページの遷移テスト
- 全体フローのテスト（モック使用）

### 7.3 検証モード

検証モードを実装し、実際のダウンロードを行わずに動作確認が可能：

```bash
python src/ebis_download_csv.py --verify
```

## 8. 運用とメンテナンス

### 8.1 定期実行

- cron（Linux）やタスクスケジューラ（Windows）で毎日実行するよう設定
- 実行結果をログファイルに記録し、エラー時には管理者に通知

### 8.2 セレクタの更新

ウェブサイトの変更があった場合は、セレクタを更新する必要があります：

1. AI要素抽出ツールで新しいセレクタを抽出
2. `selectors.csv` を更新
3. 検証モードで動作確認

### 8.3 ダウンロードファイル形式の変更対応

ダウンロードされるCSVファイルの形式が変更された場合：

1. ファイル名パターンを確認
2. ファイル処理ロジックを更新

## 9. セキュリティ考慮事項

- 認証情報は環境変数または暗号化された設定ファイルで管理
- ダウンロードしたファイルには機密情報が含まれる可能性があるため、適切なアクセス制限を設定
- ブラウザのセキュリティ設定を適切に構成

## 10. 将来拡張

- 複数種類のレポートダウンロードに対応
- データの自動分析・集計機能
- レポート生成機能の追加
- 並列ダウンロード処理の実装 