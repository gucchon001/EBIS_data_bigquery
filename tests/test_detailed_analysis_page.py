#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
詳細分析ページクラスのユニットテスト
モックオブジェクトを使用してブラウザ操作をシミュレーションし、
各メソッドの機能を個別にテストします。
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.modules.browser.detailed_analysis_page import DetailedAnalysisPage

class TestDetailedAnalysisPage(unittest.TestCase):
    """DetailedAnalysisPageクラスのテストケース"""
    
    def setUp(self):
        """各テスト実行前の準備"""
        # Browserクラスのモック
        self.mock_browser = MagicMock()
        self.mock_browser.setup.return_value = True
        self.mock_browser.navigate_to.return_value = True
        self.mock_browser.wait_for_page_load.return_value = True
        self.mock_browser.click_element.return_value = True
        self.mock_browser.input_text_by_selector.return_value = True
        
        # 環境変数とパスの設定をパッチ
        self.env_patcher = patch('src.modules.browser.detailed_analysis_page.env')
        self.mock_env = self.env_patcher.start()
        self.mock_env.load_env.return_value = None
        self.mock_env.get_config_value.side_effect = self._mock_config_value
        
        # os.path.existsをパッチ
        self.path_exists_patcher = patch('os.path.exists')
        self.mock_path_exists = self.path_exists_patcher.start()
        self.mock_path_exists.return_value = True
        
        # os.path.isfileをパッチ
        self.path_isfile_patcher = patch('os.path.isfile')
        self.mock_path_isfile = self.path_isfile_patcher.start()
        self.mock_path_isfile.return_value = True
        
        # os.path.getmtimeをパッチ
        self.path_getmtime_patcher = patch('os.path.getmtime')
        self.mock_path_getmtime = self.path_getmtime_patcher.start()
        self.mock_path_getmtime.return_value = 1234567890
        
        # osモジュールの他の関数をパッチ
        self.makedirs_patcher = patch('os.makedirs')
        self.mock_makedirs = self.makedirs_patcher.start()
        
        self.listdir_patcher = patch('os.listdir')
        self.mock_listdir = self.listdir_patcher.start()
        self.mock_listdir.return_value = ['detail_analyze_20231201.csv']
        
        # shutilをパッチ
        self.shutil_patcher = patch('shutil.move')
        self.mock_shutil_move = self.shutil_patcher.start()
        
        # time.sleepをパッチ
        self.sleep_patcher = patch('time.sleep')
        self.mock_sleep = self.sleep_patcher.start()
        
        # DetailedAnalysisPageのインスタンスを作成
        self.page = DetailedAnalysisPage(browser=self.mock_browser)
    
    def tearDown(self):
        """各テスト実行後のクリーンアップ"""
        self.env_patcher.stop()
        self.path_exists_patcher.stop()
        self.path_isfile_patcher.stop()
        self.path_getmtime_patcher.stop()
        self.makedirs_patcher.stop()
        self.listdir_patcher.stop()
        self.shutil_patcher.stop()
        self.sleep_patcher.stop()
    
    def _mock_config_value(self, section, key, default):
        """設定値をモックするヘルパーメソッド"""
        config_values = {
            ("AdEBIS", "url_details"): "https://test.example.com/detail_analyze",
            ("Download", "timeout"): "30",
            ("Download", "directory"): "test_downloads",
            ("BROWSER", "headless"): "false"
        }
        return config_values.get((section, key), default)
    
    def test_init(self):
        """初期化メソッドのテスト"""
        # モックブラウザが使用されていることを確認
        self.assertEqual(self.page.browser, self.mock_browser)
        
        # 設定値が正しく読み込まれていることを確認
        self.assertEqual(self.page.detailed_analysis_url, "https://test.example.com/detail_analyze")
        self.assertEqual(self.page.download_timeout, 30)
        self.assertEqual(self.page.download_dir, "test_downloads")
        self.assertFalse(self.page.browser_created)
    
    def test_navigate_to_detailed_analysis(self):
        """詳細分析ページへの移動テスト"""
        # 関数を実行
        result = self.page.navigate_to_detailed_analysis()
        
        # 期待される動作を確認
        self.mock_browser.navigate_to.assert_called_once_with(self.page.detailed_analysis_url)
        self.mock_browser.wait_for_page_load.assert_called_once()
        self.assertTrue(result)
    
    def test_handle_popup(self):
        """ポップアップ処理のテスト"""
        # ポップアップが表示されるケース
        result = self.page.handle_popup()
        self.mock_browser.click_element.assert_called_once_with('popup', 'login_notice', ensure_visible=True)
        self.assertTrue(result)
        
        # ポップアップが表示されないケース
        self.mock_browser.click_element.side_effect = Exception("No popup")
        result = self.page.handle_popup()
        self.assertTrue(result)  # ポップアップがなくてもTrueを返す
    
    def test_select_date_range(self):
        """日付範囲選択のテスト"""
        # 要素を取得するためのモック
        start_element = MagicMock()
        end_element = MagicMock()
        self.mock_browser.get_element.side_effect = [start_element, end_element]
        self.mock_browser.execute_script.side_effect = [None, None, "2023/12/01", "2023/12/31"]
        
        # 関数を実行
        result = self.page.select_date_range("2023/12/01", "2023/12/31")
        
        # 期待される動作を確認
        self.mock_browser.click_element.assert_called_with('detailed_analysis', 'apply_button')
        self.mock_browser.input_text_by_selector.assert_any_call('detailed_analysis', 'start_date_input', "2023/12/01")
        self.mock_browser.input_text_by_selector.assert_any_call('detailed_analysis', 'end_date_input', "2023/12/31")
        self.assertTrue(result)
    
    def test_select_custom_view(self):
        """カスタムビュー選択のテスト"""
        # 関数を実行
        result = self.page.select_custom_view()
        
        # 期待される動作を確認
        self.mock_browser.click_element.assert_any_call('detailed_analysis', 'view_button', retry_count=2)
        self.mock_browser.click_element.assert_any_call('detailed_analysis', 'program_all_view', retry_count=2)
        self.assertTrue(result)
    
    def test_download_csv(self):
        """CSVダウンロードのテスト"""
        # 関数を実行
        result = self.page.download_csv()
        
        # 期待される動作を確認
        self.mock_browser.click_element.assert_any_call('detailed_analysis', 'import_button', retry_count=2)
        self.mock_browser.click_element.assert_any_call('detailed_analysis', 'download_button', retry_count=2)
        self.assertTrue(result)
    
    def test_wait_for_download_and_process(self):
        """ダウンロード待機とファイル処理のテスト"""
        # ファイルが存在するパスを設定
        self.mock_path_exists.return_value = True
        
        # ディレクトリにCSVファイルが存在するように設定
        csv_files = ['detail_analyze_20231201.csv']
        self.mock_listdir.return_value = csv_files
        
        # CSVファイルとして認識されるように設定
        def mock_isfile_side_effect(path):
            return 'detail_analyze' in path
            
        self.mock_path_isfile.side_effect = mock_isfile_side_effect
        
        # パッチを適用した状態でファイルパスが返されるか確認
        target_date = datetime(2023, 12, 1)
        output_dir = "output_dir"
        result = self.page.wait_for_download_and_process(target_date, output_dir)
        
        # 期待される動作を確認
        self.mock_sleep.assert_called_once_with(self.page.download_timeout)
        self.mock_listdir.assert_called_once_with(self.page.download_dir)
        
        # ファイルが移動されたことを確認
        source_path = os.path.join(self.page.download_dir, csv_files[0])
        target_filename = f"20231201_ebis_SS_CV.csv"
        target_path = os.path.join(output_dir, target_filename)
        self.mock_shutil_move.assert_called_once_with(source_path, target_path)
        
        self.assertIsNotNone(result)
    
    def test_execute_download_flow(self):
        """ダウンロードフロー全体のテスト"""
        # 各メソッドのモック
        with patch.object(self.page, 'navigate_to_detailed_analysis', return_value=True) as mock_navigate, \
             patch.object(self.page, 'handle_popup', return_value=True) as mock_popup, \
             patch.object(self.page, 'select_date_range', return_value=True) as mock_date, \
             patch.object(self.page, 'select_custom_view', return_value=True) as mock_view, \
             patch.object(self.page, 'download_csv', return_value=True) as mock_download, \
             patch.object(self.page, 'wait_for_download_and_process', return_value="/path/to/file.csv") as mock_wait:
            
            # 関数を実行
            start_date = datetime(2023, 12, 1)
            end_date = datetime(2023, 12, 31)
            result = self.page.execute_download_flow(start_date, end_date, "output_dir")
            
            # 各メソッドが呼ばれたことを確認
            mock_navigate.assert_called_once()
            mock_popup.assert_called_once()
            mock_date.assert_called_once_with("2023/12/01", "2023/12/31")
            mock_view.assert_called_once()
            mock_download.assert_called_once()
            mock_wait.assert_called_once_with(start_date, "output_dir")
            
            # 期待される戻り値
            self.assertEqual(result, "/path/to/file.csv")
    
    def test_quit(self):
        """終了メソッドのテスト"""
        # 関数を実行（自分で作成したブラウザではないケース）
        self.page.quit()
        self.mock_browser.quit.assert_not_called()
        
        # 自分で作成したブラウザのケース
        self.page.browser_created = True
        self.page.quit()
        self.mock_browser.quit.assert_called_once()

if __name__ == '__main__':
    unittest.main() 