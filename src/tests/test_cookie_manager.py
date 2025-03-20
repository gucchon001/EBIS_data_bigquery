import unittest
import os
import sys
import pickle
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse

# モジュールのインポートパスを設定
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テスト対象のモジュールをインポート
from modules.browser.ai_element_extractor import AIElementExtractor

class TestCookieManager(unittest.TestCase):
    """
    AIElementExtractorのCookie関連機能をテストするクラス
    """

    def setUp(self):
        """テスト前の準備"""
        # テスト用の一時ディレクトリを作成
        self.test_cookies_dir = tempfile.mkdtemp()
        self.test_cookies_path = os.path.join(self.test_cookies_dir, "cookies")
        os.makedirs(self.test_cookies_path, exist_ok=True)
        
        # テスト用のAIElementExtractorインスタンスを作成
        self.extractor = AIElementExtractor()
        self.extractor.logger = MagicMock()
        
        # モックブラウザの設定
        self.extractor.browser = MagicMock()
        self.mock_driver = MagicMock()
        self.extractor.browser.driver = self.mock_driver
        self.extractor.browser.get_current_url.return_value = "https://id.ebis.ne.jp/login"
        self.mock_driver.current_url = "https://id.ebis.ne.jp/login"
        self.mock_driver.get_cookies.return_value = [
            {"name": "session", "value": "test_value", "domain": "id.ebis.ne.jp"},
            {"name": "token", "value": "auth_token", "domain": "id.ebis.ne.jp"}
        ]
        
        # オリジナルのCookieディレクトリを保存
        self.original_cookies_dir = self.extractor.cookies_dir
        
        # テスト用のCookiesパスを設定
        self._set_cookies_path(self.test_cookies_path)

    def tearDown(self):
        """テスト後のクリーンアップ"""
        # 一時ディレクトリを削除
        shutil.rmtree(self.test_cookies_dir)
        
        # オリジナルのCookieパスを復元
        self._set_cookies_path(self.original_cookies_dir)

    def _set_cookies_path(self, path):
        """テスト用にextractorのcookies_dirを変更する"""
        self.extractor.cookies_dir = path

    def _create_test_cookies(self, domain, cookies):
        """テスト用のCookieファイルを作成する"""
        cookie_file = os.path.join(self.test_cookies_path, f"cookies_{domain}.pkl")
        with open(cookie_file, 'wb') as f:
            pickle.dump(cookies, f)
        return cookie_file

    def test_save_cookies(self):
        """Cookieの保存機能をテストする"""
        # テスト実行
        result = self.extractor.save_cookies("id.ebis.ne.jp")
        
        # 結果の検証
        self.assertTrue(result)  # 成功したことを確認
        
        # ファイルが作成されたことを確認
        cookie_file = os.path.join(self.test_cookies_path, "cookies_id.ebis.ne.jp.pkl")
        self.assertTrue(os.path.exists(cookie_file))
        
        # 保存されたCookieの内容を確認
        with open(cookie_file, 'rb') as f:
            saved_cookies = pickle.load(f)
        self.assertEqual(len(saved_cookies), 2)
        self.assertEqual(saved_cookies[0]["name"], "session")
        self.assertEqual(saved_cookies[1]["name"], "token")

    def test_load_cookies(self):
        """Cookieのロード機能をテストする"""
        # テスト用のCookieファイルを作成
        test_cookies = [
            {"name": "session", "value": "test_session", "domain": "id.ebis.ne.jp"},
            {"name": "token", "value": "test_token", "domain": "id.ebis.ne.jp"}
        ]
        self._create_test_cookies("id.ebis.ne.jp", test_cookies)
        
        # _find_related_cookie_domainsをモック
        self.extractor._find_related_cookie_domains = MagicMock()
        self.extractor._find_related_cookie_domains.return_value = {
            "id.ebis.ne.jp": os.path.join(self.test_cookies_path, "cookies_id.ebis.ne.jp.pkl")
        }
        
        # テスト実行
        result = self.extractor.load_cookies("id.ebis.ne.jp")
        
        # 結果の検証
        self.assertTrue(result)  # 成功したことを確認
        
        # ドライバーにCookieが追加されたことを確認
        self.mock_driver.add_cookie.assert_called()
        self.assertEqual(self.mock_driver.add_cookie.call_count, 2)

    def test_clear_domain_cookies(self):
        """Cookieのクリア機能をテストする"""
        # テスト用のCookieファイルを作成
        domain = "id.ebis.ne.jp"
        test_cookies = [{"name": "session", "value": "test", "domain": domain}]
        cookie_file = self._create_test_cookies(domain, test_cookies)
        
        # テスト実行
        self.extractor._clear_domain_cookies(domain)
        
        # 結果の検証
        self.assertFalse(os.path.exists(cookie_file))  # ファイルが削除されたか確認
        self.mock_driver.delete_all_cookies.assert_called_once()  # ブラウザのCookieがクリアされたか確認

    def test_cross_domain_cookies(self):
        """クロスドメイン間のCookie処理をテストする"""
        # 2つのドメイン用のCookieを作成
        login_domain = "id.ebis.ne.jp"
        dashboard_domain = "bishamon.ebis.ne.jp"
        
        # ログインドメインのCookie
        login_cookies = [
            {"name": "session", "value": "login_session", "domain": login_domain}
        ]
        self._create_test_cookies(login_domain, login_cookies)
        
        # ダッシュボードドメインのCookie
        dashboard_cookies = [
            {"name": "dashboard_token", "value": "dash_token", "domain": dashboard_domain}
        ]
        self._create_test_cookies(dashboard_domain, dashboard_cookies)
        
        # _find_related_cookie_domainsをモック
        self.extractor._find_related_cookie_domains = MagicMock()
        self.extractor._find_related_cookie_domains.return_value = {
            login_domain: os.path.join(self.test_cookies_path, f"cookies_{login_domain}.pkl"),
            dashboard_domain: os.path.join(self.test_cookies_path, f"cookies_{dashboard_domain}.pkl")
        }
        
        # ドライバーのURLを更新
        self.extractor.browser.get_current_url.return_value = f"https://{login_domain}/login"
        
        # テスト実行
        result = self.extractor.load_cookies(login_domain)
        
        # 結果の検証
        self.assertTrue(result)  # 成功したことを確認
        self.assertTrue(self.mock_driver.add_cookie.call_count >= 2)  # 両方のドメインのCookieが追加されたことを確認

    @patch('modules.browser.ai_element_extractor.time.sleep')
    def test_check_login_status(self, mock_sleep):
        """ログイン状態の検証機能をテストする"""
        # パラメータ設定
        login_url = "https://id.ebis.ne.jp/login"
        dashboard_url = "https://bishamon.ebis.ne.jp/dashboard"
        
        # ケース1: ダッシュボードURLにいる場合（ログイン済み）
        self.extractor.browser.get_current_url.return_value = dashboard_url
        self.mock_driver.page_source = "<html><body>ダッシュボード ログアウト</body></html>"
        
        result1 = self.extractor.check_login_status(login_url, dashboard_url)
        self.assertTrue(result1)
        
        # ケース2: ログインURLにリダイレクトされる場合（未ログイン）
        self.extractor.browser.get_current_url.return_value = login_url
        self.mock_driver.page_source = "<html><body>ログインページ パスワード</body></html>"
        
        result2 = self.extractor.check_login_status(login_url, dashboard_url)
        self.assertFalse(result2)

    @patch('modules.browser.ai_element_extractor.time.sleep')
    def test_execute_login_if_needed(self, mock_sleep):
        """ログイン処理の実行をテストする"""
        # モックの準備
        self.extractor.parse_direction_file = MagicMock()
        self.extractor.parse_direction_file.return_value = {"url": "https://id.ebis.ne.jp/login"}
        
        self.extractor.execute_extraction = MagicMock(return_value=True)
        self.extractor.check_login_status = MagicMock()
        self.extractor.save_cookies = MagicMock(return_value=True)
        self.extractor.load_cookies = MagicMock(return_value=True)
        self.extractor._clear_domain_cookies = MagicMock()
        
        # テストパラメータ
        login_section = "login"
        dashboard_url = "https://bishamon.ebis.ne.jp/dashboard"
        
        # ケース1: ログイン済みの場合
        self.extractor.check_login_status.return_value = True
        result1 = self.extractor.execute_login_if_needed(login_section, dashboard_url)
        self.assertTrue(result1)
        self.extractor.execute_extraction.assert_not_called()  # ログイン処理は実行されない
        
        # executeセクションのモックをリセット
        self.extractor.execute_extraction.reset_mock()
        
        # ケース2: ログインが必要な場合
        self.extractor.check_login_status.return_value = False
        result2 = self.extractor.execute_login_if_needed(login_section, dashboard_url)
        self.assertTrue(result2)
        self.extractor.execute_extraction.assert_called_once()  # ログイン処理が実行される
        
        # ケース3: 強制ログインの場合
        self.extractor.execute_extraction.reset_mock()
        
        result3 = self.extractor.execute_login_if_needed(login_section, dashboard_url, force_login=True, clear_cookies=True)
        self.assertTrue(result3)
        self.extractor._clear_domain_cookies.assert_called()  # Cookieがクリアされる
        self.extractor.execute_extraction.assert_called_once()  # ログイン処理が実行される

if __name__ == "__main__":
    unittest.main() 