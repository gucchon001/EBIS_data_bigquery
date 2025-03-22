# アドエビス詳細分析ページCSVダウンロード機能 実装ガイド

## 1. 概要

本ドキュメントは、アドエビス詳細分析ページからデータをCSVダウンロードする機能の実装について説明します。主に開発者向けの技術的な内容を記載しています。

## 2. 目標と要件

### 2.1 目標

- アドエビス詳細分析ページからのCSVダウンロードを自動化
- POMパターン（Page Object Model）に基づいた実装
- エラー耐性の高い堅牢な実装
- ブラウザインスタンスの効率的な共有

### 2.2 技術要件

- Python 3.9以上
- Selenium WebDriver 4.0以上
- Chrome/Chromium ブラウザとChromeDriver
- `webdriver_manager` ライブラリ（ドライバーの自動管理）
- `pandas` ライブラリ（CSVデータ処理）

## 3. ファイル構造

```
src/
├── modules/
│   ├── browser/
│   │   ├── browser.py              # ブラウザ操作の基底クラス
│   │   ├── login_page.py           # ログインページクラス
│   │   ├── login_page_template.py  # ログインページのテンプレートクラス
│   │   └── detailed_analysis_page.py  # 詳細分析ページクラス
│   └── ...
├── utils/
│   ├── environment.py              # 環境設定管理
│   ├── logging_config.py           # ログ設定
│   └── slack_notifier.py           # Slack通知
├── ebis_download_csv.py            # メインスクリプト
└── ...

config/
├── settings.ini                    # 設定ファイル
├── secrets.env                     # 秘密情報
└── selectors.csv                   # セレクタ情報
```

## 4. クラス実装

### 4.1 DetailedAnalysisPage クラスの実装

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
アドエビス詳細分析ページ操作モジュール
詳細分析ページへのアクセスとCSVダウンロード機能を提供します。
POMパターン（Page Object Model）で実装し、Browser クラスの機能を活用します。
"""

import os
import time
import sys
import shutil
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent.parent.parent)
sys.path.append(project_root)

from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env
from src.modules.browser.browser import Browser
from src.modules.browser.login_page_template import handle_errors

logger = get_logger(__name__)

class DetailedAnalysisPage:
    """
    アドエビス詳細分析ページ操作を担当するクラス
    POMパターンに基づき、詳細分析ページ専用の操作メソッドを提供します
    """
    
    def __init__(self, browser=None):
        """
        初期化
        settings.iniの[AdEBIS]と[Download]セクションから設定を読み込みます
        Browser クラスのインスタンスを使用してブラウザ操作を行います
        
        Args:
            browser (Browser): 既存のブラウザインスタンス（省略時は新規作成）
        """
        # 環境変数を確実に読み込む
        env.load_env()
        
        # ブラウザインスタンスの初期化
        self.browser_created = False
        if browser is None:
            # ヘッドレスモード設定を取得
            headless_value = env.get_config_value("BROWSER", "headless", "false")
            headless = headless_value.lower() == "true" if isinstance(headless_value, str) else bool(headless_value)
            
            # セレクタファイルのパスを設定
            selectors_path = "config/selectors.csv"
            if not os.path.exists(selectors_path):
                logger.warning(f"セレクタファイルが見つかりません: {selectors_path}")
                selectors_path = None
            
            # ブラウザインスタンスを作成
            self.browser = Browser(selectors_path=selectors_path, headless=headless)
            if not self.browser.setup():
                logger.error("ブラウザのセットアップに失敗しました")
                raise RuntimeError("ブラウザのセットアップに失敗しました")
            
            self.browser_created = True
        else:
            # 既存のブラウザインスタンスを使用
            self.browser = browser
            
        # 設定の読み込み
        self.detailed_analysis_url = env.get_config_value("AdEBIS", "url_details", 
                                                          "https://bishamon.ebis.ne.jp/detail_analyze")
        
        # ダウンロード関連設定
        timeout_value = env.get_config_value("Download", "timeout", "90")
        self.download_timeout = int(timeout_value) if isinstance(timeout_value, str) else int(timeout_value or 90)
        
        self.download_dir = env.get_config_value("Download", "directory", "data/downloads")
        if not os.path.exists(self.download_dir):
            try:
                os.makedirs(self.download_dir, exist_ok=True)
                logger.info(f"ダウンロードディレクトリを作成しました: {self.download_dir}")
            except Exception as e:
                logger.error(f"ダウンロードディレクトリの作成に失敗しました: {str(e)}")
        
        logger.info("詳細分析ページクラスを初期化しました")
    
    @handle_errors(screenshot_name="navigate_error")
    def navigate_to_detailed_analysis(self):
        """
        詳細分析ページに移動します
        
        Returns:
            bool: 移動が成功した場合はTrue
        """
        if not self.detailed_analysis_url:
            logger.error("詳細分析ページのURLが設定されていません")
            return False
            
        try:
            logger.info(f"詳細分析ページへ移動します: {self.detailed_analysis_url}")
            
            # Browserクラスを使用してナビゲーション
            result = self.browser.navigate_to(self.detailed_analysis_url)
            
            # ページの読み込みを待機
            self.browser.wait_for_page_load()
            
            logger.info("詳細分析ページへの移動が完了しました")
            return result
            
        except Exception as e:
            logger.error(f"詳細分析ページへの移動中にエラーが発生しました: {str(e)}")
            return False
    
    @handle_errors(screenshot_name="handle_popup_error")
    def handle_popup(self):
        """
        ポップアップが存在する場合は閉じます
        
        Returns:
            bool: ポップアップ処理が成功した場合はTrue、ポップアップがない場合もTrue
        """
        try:
            # ポップアップの存在を短時間で確認
            result = self.browser.click_element('popup', 'login_notice', ensure_visible=True)
            if result:
                logger.info("ポップアップを閉じました")
            return True
        except Exception as e:
            logger.info("ポップアップは表示されていないか、すでに処理されています")
            return True
    
    @handle_errors(screenshot_name="date_picker_error")
    def select_date_range(self, start_date, end_date):
        """
        日付範囲を選択します
        
        Args:
            start_date (str): 開始日（YYYY/MM/DD形式）
            end_date (str): 終了日（YYYY/MM/DD形式）
            
        Returns:
            bool: 日付選択が成功した場合はTrue
        """
        try:
            # 日付カレンダーを開く
            logger.debug("日付カレンダーを開きます")
            self.browser.click_element('detailed_analysis', 'date_picker_trigger')
            time.sleep(2)
            
            # 開始日を入力
            logger.debug(f"開始日を入力します: {start_date}")
            start_element = self.browser.get_element('detailed_analysis', 'start_date_input')
            # 入力フィールドをクリア
            self.browser.execute_script("arguments[0].value = '';", start_element)
            time.sleep(1)
            self.browser.input_text_by_selector('detailed_analysis', 'start_date_input', start_date)
            
            # 終了日を入力
            logger.debug(f"終了日を入力します: {end_date}")
            end_element = self.browser.get_element('detailed_analysis', 'end_date_input')
            # 入力フィールドをクリア
            self.browser.execute_script("arguments[0].value = '';", end_element)
            time.sleep(1)
            self.browser.input_text_by_selector('detailed_analysis', 'end_date_input', end_date)
            
            # 入力値の確認
            actual_start = self.browser.execute_script("return arguments[0].value;", start_element)
            actual_end = self.browser.execute_script("return arguments[0].value;", end_element)
            
            if actual_start != start_date or actual_end != end_date:
                logger.warning(f"日付が正しく入力されていません。開始日: {actual_start}（期待値: {start_date}）、終了日: {actual_end}（期待値: {end_date}）")
            
            # 適用ボタンをクリック
            logger.debug("適用ボタンをクリックします")
            result = self.browser.click_element('detailed_analysis', 'apply_button')
            if result:
                logger.info(f"日付範囲を選択しました: {start_date} から {end_date}")
                time.sleep(3)  # ページ更新の待機
            return result
            
        except Exception as e:
            logger.error(f"日付範囲の選択中にエラーが発生しました: {str(e)}")
            return False
    
    @handle_errors(screenshot_name="download_error")
    def download_csv(self):
        """
        CSVをダウンロードします
        
        Returns:
            bool: ダウンロードが成功した場合はTrue
        """
        try:
            # インポートボタンをクリック
            logger.debug("インポートボタンをクリックします")
            if not self.browser.click_element('detailed_analysis', 'import_button', retry_count=2):
                logger.error("インポートボタンのクリックに失敗しました")
                return False
                
            time.sleep(1)
            
            # ダウンロードボタンをクリック
            logger.debug("ダウンロードボタンをクリックします")
            if not self.browser.click_element('detailed_analysis', 'download_button', retry_count=2):
                logger.error("ダウンロードボタンのクリックに失敗しました")
                return False
                
            logger.info("CSVのダウンロードを開始しました")
            return True
            
        except Exception as e:
            logger.error(f"CSVダウンロード中にエラーが発生しました: {str(e)}")
            return False
    
    @handle_errors(screenshot_name="process_file_error")
    def wait_for_download_and_process(self, target_date, output_dir=None):
        """
        ダウンロード完了を待機し、ファイル処理を行います
        
        Args:
            target_date (datetime): 対象日付
            output_dir (str, optional): 出力ディレクトリ
            
        Returns:
            str: 処理後のファイルパス、失敗した場合はNone
        """
        try:
            # 出力ディレクトリの設定
            if output_dir is None:
                output_dir = self.download_dir
                
            logger.info(f"ダウンロード完了を待機しています（タイムアウト: {self.download_timeout}秒）")
            time.sleep(self.download_timeout)
            
            # ダウンロードディレクトリの確認
            if not os.path.exists(self.download_dir):
                logger.error(f"ダウンロードディレクトリが存在しません: {self.download_dir}")
                return None
                
            # ダウンロードファイルを検索
            download_files = [f for f in os.listdir(self.download_dir) if os.path.isfile(os.path.join(self.download_dir, f))]
            csv_files = [s for s in download_files if 'detail_analyze' in s]
            
            if not csv_files:
                logger.error(f"ダウンロードされたCSVファイルが見つかりません。ディレクトリ内のファイル: {download_files}")
                return None
                
            # 最新のファイルを取得
            latest_file = sorted(csv_files, key=lambda x: os.path.getmtime(os.path.join(self.download_dir, x)), reverse=True)[0]
            source_path = os.path.join(self.download_dir, latest_file)
            
            logger.debug(f"ダウンロードファイルを特定しました: {source_path}")
            
            # 移動先のパスを作成
            date_str = target_date.strftime('%Y%m%d')
            target_filename = f"{date_str}_ebis_SS_CV.csv"
            target_path = os.path.join(output_dir, target_filename)
            
            # 出力ディレクトリが存在しない場合は作成
            os.makedirs(output_dir, exist_ok=True)
            
            # ファイルを移動
            shutil.move(source_path, target_path)
            
            logger.info(f"ダウンロードファイルを移動しました: {target_path}")
            return target_path
            
        except Exception as e:
            logger.error(f"ファイル処理中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    @handle_errors(screenshot_name="download_flow_error", raise_exception=True)
    def execute_download_flow(self, start_date, end_date=None, output_dir=None):
        """
        ダウンロードフロー全体を実行します
        
        Args:
            start_date (datetime): 開始日
            end_date (datetime, optional): 終了日（省略時は開始日と同じ）
            output_dir (str, optional): 出力ディレクトリ
            
        Returns:
            str: 処理後のファイルパス、失敗した場合はNone
        """
        if end_date is None:
            end_date = start_date
            
        try:
            # 詳細分析ページに移動
            if not self.navigate_to_detailed_analysis():
                logger.error("詳細分析ページへの移動に失敗しました")
                return None
                
            # ポップアップがあれば処理
            time.sleep(5)
            self.handle_popup()
                
            # 日付範囲選択
            start_date_str = start_date.strftime('%Y/%m/%d')
            end_date_str = end_date.strftime('%Y/%m/%d')
            
            if not self.select_date_range(start_date_str, end_date_str):
                logger.error("日付範囲の選択に失敗しました")
                return None
                
            # CSVダウンロード
            if not self.download_csv():
                logger.error("CSVのダウンロードに失敗しました")
                return None
                
            # ダウンロード完了待機とファイル処理
            result = self.wait_for_download_and_process(start_date, output_dir)
            if not result:
                logger.error("ダウンロードファイルの処理に失敗しました")
                return None
                
            logger.info("ダウンロードフローが正常に完了しました")
            return result
            
        except Exception as e:
            logger.error(f"ダウンロードフロー実行中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def quit(self):
        """
        ブラウザを終了します
        自分で作成したブラウザインスタンスのみ終了します
        """
        if self.browser and self.browser_created:
            self.browser.quit()
            logger.info("ブラウザを終了しました")
```

### 4.2 メインスクリプト（ebis_download_csv.py）の実装

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
アドエビス詳細分析ページからCSVをダウンロードするスクリプト
指定された日付範囲のデータをCSVとしてダウンロードします。
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env
from src.modules.browser.login_page import LoginPage
from src.modules.browser.detailed_analysis_page import DetailedAnalysisPage

logger = get_logger(__name__)

def parse_args():
    """コマンドライン引数を解析します"""
    parser = argparse.ArgumentParser(description='アドエビス詳細分析ページからCSVをダウンロードします')
    
    # 日付関連オプション
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--date', type=str, help='取得する日付 (YYYY-MM-DD形式)')
    date_group.add_argument('--start-date', type=str, help='取得開始日 (YYYY-MM-DD形式)')
    
    parser.add_argument('--end-date', type=str, help='取得終了日 (YYYY-MM-DD形式、--start-dateと共に使用)')
    
    # その他のオプション
    parser.add_argument('--account', type=str, default='1', help='使用するアカウント番号（デフォルト: 1）')
    parser.add_argument('--output-dir', type=str, help='出力ディレクトリ')
    parser.add_argument('--headless', action='store_true', help='ヘッドレスモードでブラウザを実行')
    parser.add_argument('--verify', action='store_true', help='検証モード（ダウンロードを実行せず）')
    
    return parser.parse_args()

def parse_date(date_str):
    """日付文字列をdatetimeオブジェクトに変換します"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        logger.error(f"無効な日付形式です: {date_str}（YYYY-MM-DD形式で入力してください）")
        return None

def main():
    """メイン処理"""
    # コマンドライン引数の解析
    args = parse_args()
    
    # 環境変数の読み込み
    env.load_env()
    
    # アカウント番号の設定
    if args.account != '1':
        env.update_config_value("Login", "account_number", args.account)
    
    # ヘッドレスモードの設定
    if args.headless:
        env.update_config_value("BROWSER", "headless", "true")
    
    # 日付の設定
    if args.date:
        target_date = parse_date(args.date)
        if not target_date:
            return 1
        start_date = end_date = target_date
    elif args.start_date:
        start_date = parse_date(args.start_date)
        if not start_date:
            return 1
        
        if args.end_date:
            end_date = parse_date(args.end_date)
            if not end_date:
                return 1
        else:
            end_date = start_date
    else:
        # デフォルトは前日
        start_date = end_date = datetime.today() - timedelta(days=1)
    
    logger.info(f"対象期間: {start_date.strftime('%Y-%m-%d')} から {end_date.strftime('%Y-%m-%d')}")
    
    try:
        # ログイン処理
        login_page = LoginPage()
        
        if not login_page.execute_login_flow():
            logger.error("ログインに失敗しました")
            login_page.quit()
            return 1
        
        logger.info("ログインに成功しました")
        
        # 検証モードの場合はここで終了
        if args.verify:
            logger.info("検証モードのため、ダウンロード処理をスキップします")
            login_page.quit()
            return 0
        
        # 詳細分析ページ処理
        analysis_page = DetailedAnalysisPage(login_page.browser)
        result = analysis_page.execute_download_flow(start_date, end_date, args.output_dir)
        
        # ブラウザを終了（ログインページではなく分析ページから終了する）
        analysis_page.quit()
        
        if result:
            logger.info(f"CSVダウンロードが完了しました: {result}")
            return 0
        else:
            logger.error("CSVダウンロードに失敗しました")
            return 1
            
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

## 5. 主要な処理フロー

### 5.1 ダウンロードフローの手順

1. **初期化**：`DetailedAnalysisPage` クラスのインスタンス作成
2. **ページ移動**：詳細分析ページへのナビゲーション実行
3. **ポップアップ処理**：ページ移動後に表示されるポップアップ対応
4. **日付範囲選択**：日付ピッカーで対象期間を設定
5. **CSVダウンロード**：インポートボタン→ダウンロードボタンの順にクリック
6. **ファイル処理**：ダウンロード完了を待機、ファイルを目的の場所に移動
7. **終了処理**：ブラウザを適切に終了

### 5.2 エラー処理の実装

- 各メソッドには `handle_errors` デコレータを適用
- エラー発生時にはスクリーンショットを取得
- 適切なログメッセージを出力
- 必要に応じて上位層に例外を再送出

### 5.3 ブラウザインスタンス共有の実装

```python
# ログイン処理
login_page = LoginPage()
if login_page.execute_login_flow():
    # ログイン済みのブラウザインスタンスを共有
    analysis_page = DetailedAnalysisPage(login_page.browser)
    # ...
    
    # 親クラスではなく子クラスからブラウザを終了
    analysis_page.quit()
else:
    # エラー時は親クラスからブラウザを終了
    login_page.quit()
```

## 6. セレクタの設定

### 6.1 新しく追加するセレクタ

`config/selectors.csv` に以下のセレクタを追加します：

```csv
group,name,selector_type,selector_value,description
detailed_analysis,date_picker_trigger,xpath,/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[1]/div[2]/input,日付カレンダーを開くボタン
detailed_analysis,start_date_input,xpath,/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div[2]/div[1]/div[1]/input[1],開始日入力フィールド
detailed_analysis,end_date_input,xpath,/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div[2]/div[1]/div[1]/input[2],終了日入力フィールド
detailed_analysis,apply_button,xpath,/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div[2]/div[2]/button[2],適用ボタン
detailed_analysis,import_button,xpath,//*[@id="common-bar"]/div[2]/nav/div[2]/div[4]/div[1],インポートボタン
detailed_analysis,download_button,xpath,//*[@id="common-bar"]/div[2]/nav/div[2]/div[4]/div[2]/a,ダウンロードボタン
```

## 7. 設定ファイルの更新

### 7.1 settings.ini への追加設定

```ini
[AdEBIS]
url_details = https://bishamon.ebis.ne.jp/detail_analyze

[Download]
timeout = 90
directory = data/downloads
```

## 8. エラー処理のベストプラクティス

### 8.1 デコレータの活用

```python
@handle_errors(screenshot_name="download_error")
def download_csv(self):
    # ...
```

### 8.2 階層的な例外処理

```python
try:
    # 主要な処理
    if not self.navigate_to_detailed_analysis():
        return None
    
    # 個別の処理で失敗しても継続
    try:
        self.handle_popup()
    except Exception as e:
        logger.warning(f"ポップアップ処理中にエラーが発生しましたが続行します: {str(e)}")
    
    # 重要な処理
    if not self.download_csv():
        return None
        
except Exception as e:
    # 最上位レベルでの例外処理
    logger.error(f"重大なエラーが発生しました: {str(e)}")
    self.browser.save_screenshot("critical_error.png")
    raise
```

## 9. テスト手法

### 9.1 単体テスト

```python
def test_select_date_range(self):
    """日付範囲選択のテスト"""
    page = DetailedAnalysisPage(self.mock_browser)
    
    # モックの設定
    self.mock_browser.click_element.return_value = True
    self.mock_browser.get_element.return_value = MagicMock()
    self.mock_browser.input_text_by_selector.return_value = True
    
    # テスト実行
    result = page.select_date_range("2023/01/01", "2023/01/31")
    
    # アサーション
    self.assertTrue(result)
    self.mock_browser.click_element.assert_any_call('detailed_analysis', 'date_picker_trigger')
    self.mock_browser.click_element.assert_any_call('detailed_analysis', 'apply_button')
```

### 9.2 結合テスト

```python
def test_execute_download_flow(self):
    """ダウンロードフロー全体のテスト"""
    # テスト用の日付設定
    test_date = datetime(2023, 1, 1)
    
    # モックの設定
    mock_login_page = MagicMock()
    mock_login_page.browser = MagicMock()
    mock_login_page.execute_login_flow.return_value = True
    
    with patch('src.modules.browser.detailed_analysis_page.DetailedAnalysisPage') as mock_analysis_page_class:
        mock_analysis_page = MagicMock()
        mock_analysis_page_class.return_value = mock_analysis_page
        mock_analysis_page.execute_download_flow.return_value = "path/to/downloaded.csv"
        
        # テスト対象の処理を実行
        result = main()
        
        # アサーション
        self.assertEqual(result, 0)
        mock_login_page.execute_login_flow.assert_called_once()
        mock_analysis_page.execute_download_flow.assert_called_once()
        mock_analysis_page.quit.assert_called_once()
```

## 10. よくあるトラブルと対策

### 10.1 セレクタ変更への対応

ページ構造が変更された場合、セレクタを更新する必要があります：

1. `ai_element_extractor.py` を実行して最新のセレクタを取得
   ```powershell
   python -m src.modules.browser.ai_element_extractor --section detailed_analysis
   ```

2. 出力された結果を `config/selectors.csv` に反映

### 10.2 タイムアウトの調整

ネットワーク環境によってダウンロード完了時間が変わる場合は、タイムアウト値を調整します：

```ini
[Download]
timeout = 120  # より長いタイムアウト（秒）
```

### 10.3 ページ構造の大幅な変更があった場合

1. 新しいセレクタを抽出
2. 必要に応じて `DetailedAnalysisPage` クラスのメソッドを更新
3. 検証モードで動作確認

## 11. 今後の拡張性

### 11.1 他のレポートダウンロードにも対応

- `BaseReportPage` クラスを作成し、共通処理を抽象化
- 各レポートタイプごとに専用のページクラスを実装
- ファクトリーパターンでレポートタイプに応じたインスタンスを作成

### 11.2 並列ダウンロード

- マルチスレッドまたはマルチプロセスによる並列ダウンロード
- ダウンロード状態を監視する機能
- 並列ダウンロード用の調整可能なパラメータ

## 12. 参考資料

- [Selenium公式ドキュメント](https://www.selenium.dev/documentation/)
- [Python WebDriverWaitの使用方法](https://www.selenium.dev/documentation/webdriver/waits/)
- [ページオブジェクトモデル（POM）パターン](https://www.selenium.dev/documentation/test_practices/encouraged/page_object_models/)
- [Pythonログ管理のベストプラクティス](https://docs.python.org/3/howto/logging.html)
- [ファイル操作のベストプラクティス](https://docs.python.org/3/library/shutil.html) 