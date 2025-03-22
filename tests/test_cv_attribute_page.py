#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CV属性レポートページモジュールの単体テスト
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.modules.browser.cv_attribute_page import CVAttributePage

class TestCVAttributePage(unittest.TestCase):
    """CV属性レポートページクラスのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.mock_browser = MagicMock()
        self.mock_browser.setup.return_value = True
        
        # 環境変数のパッチ
        self.env_patcher = patch('src.modules.browser.cv_attribute_page.env')
        self.mock_env = self.env_patcher.start()
        
        # 数値が必要な設定値のモック
        self.mock_env.get_config_value.side_effect = self._mock_config_value
        self.mock_env.resolve_path.return_value = "/test/path"
        
        # os.pathのパッチ
        self.os_path_patcher = patch('src.modules.browser.cv_attribute_page.os.path')
        self.mock_os_path = self.os_path_patcher.start()
        self.mock_os_path.exists.return_value = True
        self.mock_os_path.join.side_effect = lambda *args: '/'.join(str(arg) for arg in args)
        
        # os.makedirsのパッチ
        self.os_makedirs_patcher = patch('src.modules.browser.cv_attribute_page.os.makedirs')
        self.mock_os_makedirs = self.os_makedirs_patcher.start()
        
        # osのパッチ
        self.os_patcher = patch('src.modules.browser.cv_attribute_page.os')
        self.mock_os = self.os_patcher.start()
        self.mock_os.path = self.mock_os_path
        self.mock_os.makedirs = self.mock_os_makedirs
        self.mock_os.listdir.return_value = ['test_cv_attr.csv']
        self.mock_os.path.isfile.return_value = True
        
        # shutilのパッチ
        self.shutil_patcher = patch('src.modules.browser.cv_attribute_page.shutil')
        self.mock_shutil = self.shutil_patcher.start()
        
        # sleepのパッチ
        self.sleep_patcher = patch('src.modules.browser.cv_attribute_page.time.sleep')
        self.mock_sleep = self.sleep_patcher.start()
        
        # インスタンス作成
        self.cv_attribute_page = CVAttributePage(browser=self.mock_browser)
    
    def _mock_config_value(self, section, key, default=None):
        """設定値に応じた値を返すモック関数"""
        if section == "Download" and key == "timeout":
            return "30"
        elif section == "AdEBIS" and key == "url_cvrepo":
            return "https://test.example.com/cv-attributes"
        else:
            return "test_value"
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.env_patcher.stop()
        self.os_path_patcher.stop()
        self.os_makedirs_patcher.stop()
        self.os_patcher.stop()
        self.shutil_patcher.stop()
        self.sleep_patcher.stop()
    
    def test_init(self):
        """初期化のテスト"""
        # 既存のブラウザを使用した場合
        self.assertEqual(self.cv_attribute_page.browser, self.mock_browser)
        self.assertFalse(self.cv_attribute_page.browser_created)
        
        # 新規ブラウザを作成する場合
        with patch('src.modules.browser.cv_attribute_page.Browser') as mock_browser_class:
            mock_browser_instance = MagicMock()
            mock_browser_instance.setup.return_value = True
            mock_browser_class.return_value = mock_browser_instance
            
            cv_attribute_page = CVAttributePage()
            
            mock_browser_class.assert_called_once()
            self.assertTrue(cv_attribute_page.browser_created)
    
    def test_navigate_to_cv_attribute(self):
        """CV属性レポートページへの遷移テスト"""
        self.mock_browser.navigate_to.return_value = True
        result = self.cv_attribute_page.navigate_to_cv_attribute()
        
        self.mock_browser.navigate_to.assert_called_once()
        self.mock_browser.wait_for_page_load.assert_called_once()
        self.assertTrue(result)
        
        # 失敗ケース
        self.mock_browser.navigate_to.return_value = False
        result = self.cv_attribute_page.navigate_to_cv_attribute()
        self.assertFalse(result)
    
    def test_handle_popup(self):
        """ポップアップ処理のテスト"""
        # ポップアップが存在する場合
        self.mock_browser.click_element.return_value = True
        result = self.cv_attribute_page.handle_popup()
        
        self.mock_browser.click_element.assert_called_with('popup', 'login_notice', ensure_visible=True)
        self.assertTrue(result)
        
        # ポップアップが存在しない場合（例外が発生する）
        self.mock_browser.click_element.side_effect = Exception("No popup")
        result = self.cv_attribute_page.handle_popup()
        self.assertTrue(result)  # ポップアップがなくてもTrueを返す
    
    def test_select_date_range(self):
        """日付範囲選択のテスト"""
        # 要素の取得とスクリプト実行のモック
        mock_start_element = MagicMock()
        mock_end_element = MagicMock()
        self.mock_browser.get_element.side_effect = [mock_start_element, mock_end_element]
        self.mock_browser.execute_script.side_effect = [None, None, "2023/03/01", "2023/03/31"]
        self.mock_browser.click_element.return_value = True
        
        result = self.cv_attribute_page.select_date_range("2023/03/01", "2023/03/31")
        
        # 各メソッドが正しく呼ばれたか検証
        self.mock_browser.click_element.assert_any_call('cv_attribute', 'date_picker_trigger')
        self.mock_browser.input_text_by_selector.assert_any_call('cv_attribute', 'start_date_input', "2023/03/01")
        self.mock_browser.input_text_by_selector.assert_any_call('cv_attribute', 'end_date_input', "2023/03/31")
        self.mock_browser.click_element.assert_any_call('cv_attribute', 'apply_button')
        self.assertTrue(result)
        
        # 失敗ケース
        self.mock_browser.click_element.return_value = False
        result = self.cv_attribute_page.select_date_range("2023/03/01", "2023/03/31")
        self.assertFalse(result)
    
    def test_select_all_traffic_tab(self):
        """全トラフィックタブ選択のテスト"""
        self.mock_browser.click_element.return_value = True
        result = self.cv_attribute_page.select_all_traffic_tab()
        
        self.mock_browser.click_element.assert_called_with('cv_attribute', 'all_traffic_tab', retry_count=2)
        self.assertTrue(result)
        
        # 失敗ケース
        self.mock_browser.click_element.return_value = False
        result = self.cv_attribute_page.select_all_traffic_tab()
        self.assertFalse(result)
    
    def test_download_csv(self):
        """CSVダウンロードのテスト"""
        self.mock_browser.click_element.return_value = True
        result = self.cv_attribute_page.download_csv()
        
        self.mock_browser.click_element.assert_any_call('cv_attribute', 'csv_button', retry_count=2)
        self.mock_browser.click_element.assert_any_call('cv_attribute', 'download_button', retry_count=2)
        self.assertTrue(result)
        
        # CSV選択失敗ケース
        self.mock_browser.click_element.side_effect = [False, True]
        result = self.cv_attribute_page.download_csv()
        self.assertFalse(result)
        
        # ダウンロードボタンクリック失敗ケース
        self.mock_browser.click_element.side_effect = [True, False]
        result = self.cv_attribute_page.download_csv()
        self.assertFalse(result)
    
    def test_wait_for_download_and_process(self):
        """ダウンロード待機とファイル処理のテスト"""
        # ファイル取得と移動のテスト
        target_date = datetime(2023, 3, 1)
        
        # os.listdir と sorted をパッチ
        with patch('src.modules.browser.cv_attribute_page.sorted') as mock_sorted:
            mock_sorted.return_value = ['test_cv_attr.csv']
            
            result = self.cv_attribute_page.wait_for_download_and_process(target_date)
            
            self.mock_sleep.assert_called_with(self.cv_attribute_page.download_timeout)
            self.mock_os.listdir.assert_called_once()
            self.mock_shutil.move.assert_called_once()
            self.assertEqual(result, '/test/path/20230301_ebis_CVrepo.csv')
            
        # ファイルが見つからない場合
        self.mock_os.listdir.return_value = []
        result = self.cv_attribute_page.wait_for_download_and_process(target_date)
        self.assertIsNone(result)
    
    def test_execute_download_flow(self):
        """ダウンロードフロー全体のテスト"""
        # メソッドのモック
        with patch.object(self.cv_attribute_page, 'navigate_to_cv_attribute') as mock_navigate, \
             patch.object(self.cv_attribute_page, 'handle_popup') as mock_handle_popup, \
             patch.object(self.cv_attribute_page, 'select_date_range') as mock_select_date, \
             patch.object(self.cv_attribute_page, 'select_all_traffic_tab') as mock_select_tab, \
             patch.object(self.cv_attribute_page, 'download_csv') as mock_download, \
             patch.object(self.cv_attribute_page, 'wait_for_download_and_process') as mock_wait:
            
            # 全て成功するケース
            mock_navigate.return_value = True
            mock_select_date.return_value = True
            mock_select_tab.return_value = True
            mock_download.return_value = True
            mock_wait.return_value = "/path/to/result.csv"
            
            start_date = datetime(2023, 3, 1)
            end_date = datetime(2023, 3, 31)
            
            result = self.cv_attribute_page.execute_download_flow(start_date, end_date)
            
            mock_navigate.assert_called_once()
            mock_handle_popup.assert_called_once()
            mock_select_date.assert_called_with("2023/03/01", "2023/03/31")
            mock_select_tab.assert_called_once()
            mock_download.assert_called_once()
            mock_wait.assert_called_once()
            self.assertEqual(result, "/path/to/result.csv")
            
            # 終了日が省略された場合
            mock_select_date.reset_mock()
            result = self.cv_attribute_page.execute_download_flow(start_date)
            mock_select_date.assert_called_with("2023/03/01", "2023/03/01")
            
            # ナビゲーション失敗ケース
            mock_navigate.return_value = False
            result = self.cv_attribute_page.execute_download_flow(start_date, end_date)
            self.assertIsNone(result)
            
            # 日付選択失敗ケース
            mock_navigate.return_value = True
            mock_select_date.return_value = False
            result = self.cv_attribute_page.execute_download_flow(start_date, end_date)
            self.assertIsNone(result)
    
    def test_quit(self):
        """ブラウザ終了のテスト"""
        # 自分で作成したブラウザの場合
        cv_attribute_page = CVAttributePage(browser=self.mock_browser)
        cv_attribute_page.browser_created = True
        cv_attribute_page.quit()
        
        self.mock_browser.quit.assert_called_once()
        
        # 外部から渡されたブラウザの場合
        self.mock_browser.reset_mock()
        cv_attribute_page = CVAttributePage(browser=self.mock_browser)
        cv_attribute_page.browser_created = False
        cv_attribute_page.quit()
        
        self.mock_browser.quit.assert_not_called()

if __name__ == '__main__':
    unittest.main() 