# -*- coding: utf-8 -*-
"""
概要:
    Browser クラスの機能テストを行うスクリプトです。
主な仕様:
    - 実際のWebサイトに接続して操作をテスト
    - 検索機能
    - フォーム入力
    - ウィンドウ操作
    - スクリーンショット機能
制限事項:
    - ネットワーク接続が必要
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
logger = logging.getLogger('browser_functional_test')

# テスト対象のクラスをインポート
from src.modules.browser.browser import Browser
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


class TestBrowserFunctional(unittest.TestCase):
    """Browser クラスの機能テストを行うテストケース"""
    
    def setUp(self):
        """各テスト前に実行される処理"""
        logger.info("======== 機能テスト開始 ========")
        # ヘッドレスモードはテスト時に false とする
        self.browser = Browser(selectors_path=None, headless=False, timeout=10)
        self.browser.setup()
        
    def tearDown(self):
        """各テスト後に実行される処理"""
        if hasattr(self, 'browser') and self.browser.driver:
            self.browser.quit()
        logger.info("======== 機能テスト終了 ========\n")
        
    def test_website_navigation(self):
        """基本的なウェブサイト操作をテストする"""
        try:
            # 安定したテストサイトにアクセス
            self.browser.navigate_to("https://www.example.com")
            
            # タイトルを確認
            title = self.browser.get_page_title()
            self.assertEqual("Example Domain", title, "ページタイトルが期待と異なります")
            
            # ページソースを取得して内容を確認
            page_source = self.browser.get_page_source()
            self.assertIn("Example Domain", page_source, "ページソースに期待されるテキストが含まれていません")
            
            # リンクを探す
            link = self.browser.wait_for_element(
                By.CSS_SELECTOR, "a",
                condition=EC.presence_of_element_located
            )
            self.assertIsNotNone(link, "リンクが見つかりませんでした")
            self.assertEqual("More information...", link.text, "リンクのテキストが期待と異なります")
            
            # スクリーンショットを撮影
            self.browser.save_screenshot("example_site.png")
            
            # 現在のURLを確認
            current_url = self.browser.get_current_url()
            self.assertEqual("https://www.example.com/", current_url, "現在のURLが期待と異なります")
            
            logger.info(f"ウェブサイト操作テストが成功しました: {title}")
            
        except Exception as e:
            self.browser.save_screenshot("website_navigation_error.png")
            self.fail(f"ウェブサイト操作テスト中に例外が発生しました: {str(e)}")
    
    def test_multiple_tabs(self):
        """複数タブの操作をテストする"""
        try:
            # 最初のページを開く
            self.browser.navigate_to("https://www.example.com")
            
            # 現在のウィンドウハンドルを保存
            current_handles = self.browser.get_window_handles()
            self.assertEqual(1, len(current_handles), "初期ウィンドウ数が1ではありません")
            
            # JavaScriptで新しいタブを開く
            self.browser.execute_script("window.open('https://www.google.com', '_blank');")
            
            # 新しいタブに切り替え
            result = self.browser.switch_to_new_window(current_handles)
            self.assertTrue(result, "新しいタブへの切り替えに失敗しました")
            
            # 新しいタブのURLを確認
            time.sleep(1)  # ページ読み込みを待機
            current_url = self.browser.get_current_url()
            self.assertIn("google.com", current_url, "新しいタブのURLが期待と異なります")
            
            # スクリーンショットを撮影
            self.browser.save_screenshot("new_tab.png")
            
            # 最初のタブに戻る
            self.browser.driver.switch_to.window(current_handles[0])
            
            # URLを確認
            time.sleep(1)
            current_url = self.browser.get_current_url()
            self.assertIn("example.com", current_url, "元のタブのURLが期待と異なります")
            
            logger.info("複数タブのテストが成功しました")
            
        except Exception as e:
            self.browser.save_screenshot("multiple_tabs_error.png")
            self.fail(f"複数タブのテスト中に例外が発生しました: {str(e)}")
    
    def test_form_interaction(self):
        """フォーム入力と送信をテストする"""
        try:
            # フォームがあるテスト用サイトにアクセス
            self.browser.navigate_to("https://www.w3schools.com/html/html_forms.asp")
            
            # フォームの入力フィールドを探す
            form_fields = self.browser.find_elements(By.CSS_SELECTOR, "form[action='/action_page.php'] input")
            
            # フォームが存在するか確認
            self.assertGreater(len(form_fields), 0, "フォームの入力フィールドが見つかりませんでした")
            
            # スクロールしてフォームを表示
            if len(form_fields) > 0:
                # スクリーンショットを撮影
                self.browser.scroll_to_element(form_fields[0])
                self.browser.save_screenshot("form_before_input.png")
                
                # テキストボックスに値を入力
                form_fields[0].clear()
                form_fields[0].send_keys("テストユーザー")
                
                # 入力後のスクリーンショット
                self.browser.save_screenshot("form_after_input.png")
            
            logger.info("フォーム操作テストが成功しました")
            
        except Exception as e:
            self.browser.save_screenshot("form_interaction_error.png")
            self.fail(f"フォーム操作テスト中に例外が発生しました: {str(e)}")
    
    def test_page_analysis(self):
        """ページ解析機能をテストする"""
        try:
            # テスト用のページにアクセス
            self.browser.navigate_to("https://www.example.com")
            
            # ページのHTMLソースを取得
            page_source = self.browser.get_page_source()
            self.assertIsNotNone(page_source, "ページソースの取得に失敗しました")
            self.assertGreater(len(page_source), 0, "ページソースが空です")
            
            # BeautifulSoupを使用してページを解析
            analysis_result = self.browser.analyze_page_content(page_source)
            
            # 解析結果の検証
            self.assertIsNotNone(analysis_result, "ページ解析結果がNoneです")
            self.assertIn('page_title', analysis_result, "解析結果にページタイトルが含まれていません")
            self.assertIn('main_heading', analysis_result, "解析結果にメイン見出しが含まれていません")
            
            # タイトルが正しく抽出されているか確認
            self.assertEqual("Example Domain", analysis_result['page_title'], "ページタイトルが正しく抽出されていません")
            
            logger.info(f"ページ解析テストが成功しました: {analysis_result['page_title']}")
            
        except Exception as e:
            self.browser.save_screenshot("page_analysis_error.png")
            self.fail(f"ページ解析テスト中に例外が発生しました: {str(e)}")
    
    def test_javascript_execution(self):
        """JavaScriptの実行機能をテストする"""
        try:
            # テスト用のページにアクセス
            self.browser.navigate_to("https://www.example.com")
            
            # JavaScriptでページのスタイルを変更
            self.browser.execute_script("""
                document.body.style.backgroundColor = 'lightblue';
                document.body.style.color = 'darkred';
                return document.title;
            """)
            
            # スクリーンショットで変更を確認
            self.browser.save_screenshot("js_style_change.png")
            
            # JavaScriptでページ情報を取得
            page_info = self.browser.execute_script("""
                return {
                    'title': document.title,
                    'url': document.URL,
                    'domain': document.domain,
                    'elements': document.getElementsByTagName('*').length
                };
            """)
            
            # 結果を検証
            self.assertIsNotNone(page_info, "JavaScriptの実行結果がNoneです")
            self.assertIn('title', page_info, "JavaScriptの実行結果にtitleが含まれていません")
            self.assertEqual("Example Domain", page_info['title'], "タイトルが期待と異なります")
            self.assertGreater(page_info['elements'], 0, "ページの要素数が0です")
            
            logger.info(f"JavaScript実行テストが成功しました: {page_info}")
            
        except Exception as e:
            self.browser.save_screenshot("javascript_error.png")
            self.fail(f"JavaScript実行テスト中に例外が発生しました: {str(e)}")


if __name__ == "__main__":
    unittest.main() 