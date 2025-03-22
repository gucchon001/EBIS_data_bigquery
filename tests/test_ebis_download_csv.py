#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ebis_download_csv.pyスクリプトのユニットテスト
コマンドライン引数の解析、日付処理、メイン処理フローをテストします。
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta
from pathlib import Path
import argparse

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

# テスト対象のモジュールをインポート
import src.ebis_download_csv as ebis_csv
from src.modules.browser.login_page import LoginPage
from src.modules.browser.detailed_analysis_page import DetailedAnalysisPage

class TestEbisDownloadCsv(unittest.TestCase):
    """ebis_download_csv.pyのテストケース"""
    
    def setUp(self):
        """各テスト実行前の準備"""
        # コマンドライン引数をパッチ
        self.args_patcher = patch('sys.argv', ['ebis_download_csv.py'])
        self.args_patcher.start()
        
        # 環境変数とパスの設定をパッチ
        self.env_patcher = patch('src.ebis_download_csv.env')
        self.mock_env = self.env_patcher.start()
        self.mock_env.load_env.return_value = None
        self.mock_env.update_config_value.return_value = None
        
        # LoginPageクラスをパッチ
        self.login_page_patcher = patch('src.ebis_download_csv.LoginPage')
        self.mock_login_page = self.login_page_patcher.start()
        self.mock_login_instance = MagicMock()
        self.mock_login_instance.execute_login_flow.return_value = True
        self.mock_login_page.return_value = self.mock_login_instance
        
        # DetailedAnalysisPageクラスをパッチ
        self.analysis_page_patcher = patch('src.ebis_download_csv.DetailedAnalysisPage')
        self.mock_analysis_page = self.analysis_page_patcher.start()
        self.mock_analysis_instance = MagicMock()
        self.mock_analysis_instance.execute_download_flow.return_value = "/path/to/downloaded.csv"
        self.mock_analysis_page.return_value = self.mock_analysis_instance
        
        # os.makedirsをパッチ
        self.makedirs_patcher = patch('os.makedirs')
        self.mock_makedirs = self.makedirs_patcher.start()
    
    def tearDown(self):
        """各テスト実行後のクリーンアップ"""
        self.args_patcher.stop()
        self.env_patcher.stop()
        self.login_page_patcher.stop()
        self.analysis_page_patcher.stop()
        self.makedirs_patcher.stop()
    
    def test_parse_args(self):
        """コマンドライン引数の解析テスト"""
        # 標準オプションのテスト
        with patch('sys.argv', ['ebis_download_csv.py', '--date', '2023-12-01', '--account', '2', '--headless']):
            args = ebis_csv.parse_args()
            self.assertEqual(args.date, '2023-12-01')
            self.assertEqual(args.account, '2')
            self.assertTrue(args.headless)
            self.assertIsNone(args.start_date)
            self.assertIsNone(args.end_date)
        
        # 日付範囲のテスト
        with patch('sys.argv', ['ebis_download_csv.py', '--start-date', '2023-12-01', '--end-date', '2023-12-31']):
            args = ebis_csv.parse_args()
            self.assertIsNone(args.date)
            self.assertEqual(args.start_date, '2023-12-01')
            self.assertEqual(args.end_date, '2023-12-31')
            self.assertEqual(args.account, '1')  # デフォルト値
            self.assertFalse(args.headless)      # デフォルト値
    
    def test_parse_date(self):
        """日付文字列の解析テスト"""
        # 有効な日付
        date_obj = ebis_csv.parse_date('2023-12-01')
        self.assertIsInstance(date_obj, datetime)
        self.assertEqual(date_obj.year, 2023)
        self.assertEqual(date_obj.month, 12)
        self.assertEqual(date_obj.day, 1)
        
        # 無効な日付
        with patch('src.ebis_download_csv.logger.error') as mock_error:
            date_obj = ebis_csv.parse_date('invalid-date')
            self.assertIsNone(date_obj)
            mock_error.assert_called_once()
        
        # Noneの場合
        date_obj = ebis_csv.parse_date(None)
        self.assertIsNone(date_obj)
    
    def test_main_with_date_option(self):
        """main関数テスト - 日付オプション指定ケース"""
        # --dateオプションのテスト
        with patch('sys.argv', ['ebis_download_csv.py', '--date', '2023-12-01', '--output-dir', 'test_output']):
            result = ebis_csv.main()
            self.assertEqual(result, 0)  # 成功を示す終了コード
            
            # ログイン処理が呼ばれたか
            self.mock_login_instance.execute_login_flow.assert_called_once()
            
            # ダウンロード処理が呼ばれたか（日付と出力ディレクトリを確認）
            args = self.mock_analysis_instance.execute_download_flow.call_args[0]
            self.assertEqual(args[0].year, 2023)
            self.assertEqual(args[0].month, 12)
            self.assertEqual(args[0].day, 1)
            self.assertEqual(args[1].year, 2023)
            self.assertEqual(args[1].month, 12)
            self.assertEqual(args[1].day, 1)
            self.assertEqual(args[2], 'test_output')
    
    def test_main_with_date_range(self):
        """main関数テスト - 日付範囲指定ケース"""
        # --start-date と --end-date オプションのテスト
        with patch('sys.argv', ['ebis_download_csv.py', '--start-date', '2023-12-01', '--end-date', '2023-12-31']):
            result = ebis_csv.main()
            self.assertEqual(result, 0)
            
            # ダウンロード処理が呼ばれたか（日付範囲を確認）
            args = self.mock_analysis_instance.execute_download_flow.call_args[0]
            self.assertEqual(args[0].year, 2023)
            self.assertEqual(args[0].month, 12)
            self.assertEqual(args[0].day, 1)
            self.assertEqual(args[1].year, 2023)
            self.assertEqual(args[1].month, 12)
            self.assertEqual(args[1].day, 31)
    
    def test_main_with_default_date(self):
        """main関数テスト - デフォルト日付ケース"""
        # 日付指定なしのテスト（前日のデータを取得）
        yesterday = datetime.today() - timedelta(days=1)
        
        with patch('sys.argv', ['ebis_download_csv.py']):
            result = ebis_csv.main()
            self.assertEqual(result, 0)
            
            # デフォルト日付（前日）が使用されたか確認
            args = self.mock_analysis_instance.execute_download_flow.call_args[0]
            self.assertEqual(args[0].year, yesterday.year)
            self.assertEqual(args[0].month, yesterday.month)
            self.assertEqual(args[0].day, yesterday.day)
    
    def test_main_verify_mode(self):
        """main関数テスト - 検証モードケース"""
        # --verify オプションのテスト
        with patch('sys.argv', ['ebis_download_csv.py', '--verify']):
            result = ebis_csv.main()
            self.assertEqual(result, 0)
            
            # ログイン処理が呼ばれたか
            self.mock_login_instance.execute_login_flow.assert_called_once()
            
            # 検証モードなのでダウンロード処理は呼ばれないことを確認
            self.mock_analysis_instance.execute_download_flow.assert_not_called()
    
    def test_main_login_failure(self):
        """main関数テスト - ログイン失敗ケース"""
        # ログイン失敗のケース
        self.mock_login_instance.execute_login_flow.return_value = False
        
        with patch('sys.argv', ['ebis_download_csv.py']):
            result = ebis_csv.main()
            self.assertEqual(result, 1)  # エラーを示す終了コード
            
            # ログイン後の処理が呼ばれないことを確認
            self.mock_analysis_instance.execute_download_flow.assert_not_called()
    
    def test_main_download_failure(self):
        """main関数テスト - ダウンロード失敗ケース"""
        # ダウンロード失敗のケース
        self.mock_analysis_instance.execute_download_flow.return_value = None
        
        with patch('sys.argv', ['ebis_download_csv.py']):
            result = ebis_csv.main()
            self.assertEqual(result, 1)  # エラーを示す終了コード
    
    def test_main_exception_handling(self):
        """main関数テスト - 例外処理ケース"""
        # 例外発生のケース
        self.mock_login_instance.execute_login_flow.side_effect = Exception("テスト例外")
        
        # traceback モジュールをモック
        with patch('traceback.format_exc', return_value="モックされたトレースバック") as mock_traceback:
            with patch('src.ebis_download_csv.logger.error') as mock_error:
                result = ebis_csv.main()
                self.assertEqual(result, 1)  # エラーを示す終了コード
                
                # エラーログが出力されたか確認
                mock_error.assert_called()
                # traceback.format_exc が呼ばれたことを確認
                mock_traceback.assert_called_once()
                # エラーメッセージに例外情報が含まれているか確認
                self.assertTrue(any("テスト例外" in str(args[0]) for args, _ in mock_error.call_args_list))

if __name__ == '__main__':
    unittest.main() 