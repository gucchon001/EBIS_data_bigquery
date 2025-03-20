# -*- coding: utf-8 -*-
"""
概要:
    Browser クラスの単体テストを行うスクリプトです。
主な仕様:
    - Browserクラスの基本機能をテスト
    - WebDriverのセットアップ
    - URL移動
    - 要素取得
    - スクリーンショット撮影
制限事項:
    - モック化していないためネットワーク接続が必要
    - テスト実行中は実際にブラウザが起動する
"""

import os
import sys
import time
import unittest
import logging
from pathlib import Path

# プロジェクトルートへのパスを追加して、src からのインポートを可能にする
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# ロガーを設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('browser_test')

# テスト対象のクラスをインポート
from src.modules.browser.browser import Browser


class TestBrowser(unittest.TestCase):
    """Browser クラスの単体テストを行うテストケース"""
    
    def setUp(self):
        """各テスト前に実行される処理"""
        logger.info("======== テスト開始 ========")
        # セレクタのパスを設定（存在しない場合はNone）
        self.selectors_path = None
        # ヘッドレスモードはテスト時に false とする
        self.browser = Browser(selectors_path=self.selectors_path, headless=False, timeout=10)
        
    def tearDown(self):
        """各テスト後に実行される処理"""
        if hasattr(self, 'browser') and self.browser.driver:
            self.browser.quit()
        logger.info("======== テスト終了 ========\n")
        
    def test_setup_browser(self):
        """ブラウザのセットアップをテストする"""
        try:
            # WebDriverをセットアップ
            result = self.browser.setup()
            
            # セットアップが成功したことを確認
            self.assertTrue(result, "ブラウザのセットアップに失敗しました")
            self.assertIsNotNone(self.browser.driver, "ドライバーがNoneです")
            
            # ドライバーが正しく初期化されたか確認
            logger.info("ドライバー情報: " + str(self.browser.driver.capabilities))
            
            # Chrome のバージョン情報を出力
            browser_version = self.browser.driver.capabilities['browserVersion']
            driver_version = self.browser.driver.capabilities['chrome']['chromedriverVersion'].split(' ')[0]
            logger.info(f'Chromeバージョン: {browser_version}, ChromeDriverバージョン: {driver_version}')
            
        except Exception as e:
            self.fail(f"ブラウザのセットアップ中に例外が発生しました: {str(e)}")
            
    def test_navigate_to_url(self):
        """URLへの移動をテストする"""
        try:
            # WebDriverをセットアップ
            self.browser.setup()
            
            # テスト用URLへナビゲート
            test_url = "https://www.google.com"
            result = self.browser.navigate_to(test_url)
            
            # ナビゲーションが成功したことを確認
            self.assertTrue(result, f"URL {test_url} への移動に失敗しました")
            
            # 現在のURLが期待通りか確認
            current_url = self.browser.get_current_url()
            self.assertIn("google.com", current_url, f"現在のURL {current_url} が期待値と異なります")
            
            # ページタイトルが正しいか確認
            title = self.browser.get_page_title()
            self.assertIn("Google", title, f"ページタイトル {title} が期待値と異なります")
            
        except Exception as e:
            self.fail(f"URL移動テスト中に例外が発生しました: {str(e)}")
            
    def test_save_screenshot(self):
        """スクリーンショット保存機能をテストする"""
        try:
            # WebDriverをセットアップ
            self.browser.setup()
            
            # テスト用URLへナビゲート
            self.browser.navigate_to("https://www.google.com")
            
            # スクリーンショットを保存
            screenshot_file = "test_screenshot.png"
            result = self.browser.save_screenshot(screenshot_file)
            
            # スクリーンショットの保存が成功したことを確認
            self.assertTrue(result, "スクリーンショットの保存に失敗しました")
            
            # スクリーンショットファイルが存在するか確認
            screenshot_path = os.path.join(self.browser.screenshot_dir, screenshot_file)
            self.assertTrue(os.path.exists(screenshot_path), f"スクリーンショットファイル {screenshot_path} が存在しません")
            
            logger.info(f"スクリーンショットが保存されました: {screenshot_path}")
            
        except Exception as e:
            self.fail(f"スクリーンショットテスト中に例外が発生しました: {str(e)}")
            
    def test_javascript_execution(self):
        """JavaScriptの実行をテストする"""
        try:
            # WebDriverをセットアップ
            self.browser.setup()
            
            # テスト用URLへナビゲート
            self.browser.navigate_to("https://www.google.com")
            
            # JavaScriptを実行してタイトルを取得
            title = self.browser.execute_script("return document.title;")
            
            # タイトルが正しく取得できたか確認
            self.assertIn("Google", title, f"JavaScript から取得したタイトル {title} が期待値と異なります")
            
            # ページの背景色を一時的に変更
            self.browser.execute_script("document.body.style.backgroundColor = 'yellow';")
            
            # 変更を確認するためにスクリーンショットを撮影
            self.browser.save_screenshot("js_background_change.png")
            
            logger.info("JavaScriptの実行テストが成功しました")
            
        except Exception as e:
            self.fail(f"JavaScript実行テスト中に例外が発生しました: {str(e)}")


if __name__ == "__main__":
    unittest.main() 