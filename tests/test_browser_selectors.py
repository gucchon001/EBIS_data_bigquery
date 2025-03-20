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

logger = get_logger('browser_selector_test')

class BrowserSelectorTest(unittest.TestCase):
    """セレクタ関連のメソッドをテストするクラス"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラスの初期化時に実行"""
        logger.info("======== セレクタテスト開始 ========")
        
        # テスト用セレクタファイルのパス
        cls.selectors_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "selectors.csv")
        
        # セレクタファイルの存在確認
        if not os.path.exists(cls.selectors_path):
            raise FileNotFoundError(f"セレクタファイルが見つかりません: {cls.selectors_path}")
        
        logger.info(f"セレクタファイル: {cls.selectors_path}")
    
    @classmethod
    def tearDownClass(cls):
        """テストクラスの終了時に実行"""
        logger.info("======== セレクタテスト終了 ========")
    
    def setUp(self):
        """各テスト実行前に実行"""
        # Browserインスタンスを初期化
        self.browser = Browser(selectors_path=self.selectors_path, headless=False)
        
        # WebDriverをセットアップ
        self.browser.setup()
    
    def tearDown(self):
        """各テスト実行後に実行"""
        # ブラウザを終了
        if self.browser:
            self.browser.quit()
    
    def test_load_selectors(self):
        """セレクタの読み込みをテストする"""
        logger.info("セレクタの読み込みをテスト")
        
        # セレクタの読み込み確認
        self.assertIsNotNone(self.browser.selectors)
        self.assertGreater(len(self.browser.selectors), 0)
        
        # 各グループのセレクタを確認
        groups = ["example", "w3schools", "login"]
        for group in groups:
            self.assertIn(group, self.browser.selectors)
        
        # 特定のセレクタが正しく読み込まれているか確認
        self.assertIn("title", self.browser.selectors["example"])
        self.assertEqual("css", self.browser.selectors["example"]["title"]["selector_type"])
        self.assertEqual("h1", self.browser.selectors["example"]["title"]["selector_value"])
        
        logger.info(f"セレクタの読み込みテスト成功: {len(self.browser.selectors)} グループ")
    
    def test_get_element(self):
        """get_element メソッドをテストする"""
        logger.info("get_element メソッドをテスト")
        
        # example.com に移動
        self.browser.navigate_to("https://www.example.com")
        time.sleep(2)
        
        # h1要素を取得
        element = self.browser.get_element("example", "title")
        self.assertIsNotNone(element)
        self.assertEqual("Example Domain", element.text)
        
        # リンク要素を取得
        element = self.browser.get_element("example", "more_info")
        self.assertIsNotNone(element)
        self.assertEqual("More information...", element.text)
        
        # 存在しない要素の場合はNoneが返ることを確認
        element = self.browser.get_element("example", "nonexistent")
        self.assertIsNone(element)
        
        logger.info("get_element メソッドのテスト成功")
    
    def test_click_element(self):
        """click_element メソッドをテストする"""
        logger.info("click_element メソッドをテスト")
        
        # example.com に移動
        self.browser.navigate_to("https://www.example.com")
        time.sleep(2)
        
        # クリック前のURLを保存
        before_url = self.browser.get_current_url()
        
        # more_infoリンクをクリック
        result = self.browser.click_element("example", "more_info")
        self.assertTrue(result)
        
        # 新しいページに移動したことを確認
        time.sleep(3)
        after_url = self.browser.get_current_url()
        self.assertNotEqual(before_url, after_url)
        
        logger.info(f"クリック後の移動を確認: {after_url}")
        
        # 存在しない要素をクリックした場合はFalseが返ることを確認
        result = self.browser.click_element("example", "nonexistent")
        self.assertFalse(result)
        
        logger.info("click_element メソッドのテスト成功")
    
    def test_w3schools_form(self):
        """W3Schoolsのフォームでセレクタをテストする"""
        logger.info("W3Schoolsフォームでセレクタをテスト")
        
        # W3Schoolsのフォームページに移動
        self.browser.navigate_to("https://www.w3schools.com/html/html_forms.asp")
        time.sleep(2)
        
        # フォームが表示されるまでスクロール
        form_element = self.browser.wait_for_element(
            By.CSS_SELECTOR, "form[action='/action_page.php']"
        )
        self.assertIsNotNone(form_element)
        self.browser.scroll_to_element(form_element)
        
        # First nameフィールドを取得してテキストを入力
        fname = self.browser.get_element("w3schools", "input_firstname")
        self.assertIsNotNone(fname)
        fname.clear()
        fname.send_keys("Test")
        
        # Last nameフィールドを取得してテキストを入力
        lname = self.browser.get_element("w3schools", "input_lastname")
        self.assertIsNotNone(lname)
        lname.clear()
        lname.send_keys("User")
        
        # スクリーンショットを撮影
        self.browser.save_screenshot("w3schools_form_filled.png")
        
        logger.info("W3Schoolsフォームのセレクタテスト成功")
    
    def test_fallback_selectors(self):
        """フォールバックセレクタをテストする"""
        logger.info("フォールバックセレクタをテスト")
        
        # フォールバックセレクタの確認
        self.assertIn("login", self.browser.selectors)
        self.assertIn("username", self.browser.selectors["login"])
        self.assertIn("password", self.browser.selectors["login"])
        self.assertIn("submit", self.browser.selectors["login"])
        
        logger.info("フォールバックセレクタのテスト成功")

if __name__ == "__main__":
    unittest.main() 