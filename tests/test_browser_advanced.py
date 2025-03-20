import unittest
import os
import sys
import time
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.modules.browser.browser import Browser
from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env

logger = get_logger('browser_advanced_test')

class BrowserAdvancedTest(unittest.TestCase):
    """Browser クラスの高度な機能をテストするクラス"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラスの初期化時に実行"""
        logger.info("======== 高度機能テスト開始 ========")
    
    @classmethod
    def tearDownClass(cls):
        """テストクラスの終了時に実行"""
        logger.info("======== 高度機能テスト終了 ========")
    
    def setUp(self):
        """各テスト実行前に実行"""
        # Browserインスタンスを初期化
        self.browser = Browser(headless=False)
        
        # WebDriverをセットアップ
        self.browser.setup()
    
    def tearDown(self):
        """各テスト実行後に実行"""
        # ブラウザを終了
        if self.browser:
            self.browser.quit()
    
    def test_set_headless_mode(self):
        """set_headless_mode メソッドをテストする"""
        logger.info("set_headless_mode メソッドをテスト")
        
        # 現在のheadless設定を確認
        current_setting = self.browser.headless
        logger.info(f"現在のheadless設定: {current_setting}")
        
        # headless設定を反転
        new_setting = not current_setting
        result = self.browser.set_headless_mode(new_setting)
        self.assertTrue(result)
        
        # 設定が変更されたか確認
        self.assertEqual(new_setting, self.browser.headless)
        
        # settings.iniからも設定を確認
        config_headless = env.get_config_value("BROWSER", "headless", default="false")
        
        # boolオブジェクトにlowerメソッドがないため、文字列比較に修正
        if isinstance(config_headless, bool):
            self.assertEqual(new_setting, config_headless)
        else:
            # 文字列の場合は小文字に変換して比較
            self.assertEqual(str(new_setting).lower(), config_headless.lower())
        
        logger.info(f"headless設定を {new_setting} に変更しました")
        
        # 元の設定に戻す
        self.browser.set_headless_mode(current_setting)
        logger.info(f"headless設定を元に戻しました: {current_setting}")
        
        logger.info("set_headless_mode メソッドのテスト成功")
    
    def test_find_elements_by_tag(self):
        """find_elements_by_tag メソッドをテストする"""
        logger.info("find_elements_by_tag メソッドをテスト")
        
        # example.com に移動
        self.browser.navigate_to("https://www.example.com")
        time.sleep(2)
        
        # タグで要素を検索
        paragraphs = self.browser.find_elements_by_tag("p")
        self.assertIsNotNone(paragraphs)
        self.assertGreater(len(paragraphs), 0)
        
        # テキストでフィルタリング
        filtered_paragraphs = self.browser.find_elements_by_tag("p", "information")
        self.assertIsNotNone(filtered_paragraphs)
        self.assertGreater(len(filtered_paragraphs), 0)
        
        # 存在しないテキストでフィルタリングすると空リストが返ることを確認
        empty_result = self.browser.find_elements_by_tag("p", "nonexistenttext123456789")
        self.assertEqual(0, len(empty_result))
        
        logger.info("find_elements_by_tag メソッドのテスト成功")
    
    def test_get_chrome_version(self):
        """get_chrome_version メソッドをテストする"""
        logger.info("get_chrome_version メソッドをテスト")
        
        # Chromeバージョンを取得
        version = self.browser.get_chrome_version()
        self.assertIsNotNone(version)
        self.assertGreater(len(version), 0)
        
        # バージョン番号のフォーマット確認（数字.数字.数字.数字）
        import re
        version_pattern = re.compile(r'^\d+\.\d+\.\d+\.\d+$')
        self.assertTrue(version_pattern.match(version), f"バージョン '{version}' が期待するフォーマットではありません")
        
        logger.info(f"検出されたChromeバージョン: {version}")
        logger.info("get_chrome_version メソッドのテスト成功")

if __name__ == "__main__":
    unittest.main() 