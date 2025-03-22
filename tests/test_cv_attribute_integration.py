#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CV属性レポート ダウンロードフローの統合テスト
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

# logging_configをパッチ
with patch('src.utils.logging_config.LoggingConfig'):
    from src.ebis_download_cv_attribute import run_cv_attribute_download, parse_arguments, prepare_dates

from src.modules.browser.login_page import LoginPage
from src.modules.browser.cv_attribute_page import CVAttributePage

class TestCVAttributeIntegration(unittest.TestCase):
    """CV属性レポートダウンロードの統合テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        # 一時ディレクトリを作成
        self.test_dir = tempfile.mkdtemp()
        
        # ログインページのパッチ
        self.login_patcher = patch('src.ebis_download_cv_attribute.LoginPage')
        self.mock_login_class = self.login_patcher.start()
        self.mock_login = MagicMock()
        self.mock_login_class.return_value = self.mock_login
        self.mock_login.execute_login_flow.return_value = True
        self.mock_login.browser = MagicMock()
        
        # CV属性ページのパッチ
        self.cv_patcher = patch('src.ebis_download_cv_attribute.CVAttributePage')
        self.mock_cv_class = self.cv_patcher.start()
        self.mock_cv = MagicMock()
        self.mock_cv_class.return_value = self.mock_cv
        self.mock_cv.execute_download_flow.return_value = os.path.join(self.test_dir, "20230301_ebis_CVrepo.csv")
        
        # 環境変数のパッチ
        self.env_patcher = patch('src.ebis_download_cv_attribute.env')
        self.mock_env = self.env_patcher.start()
        
        # ログ設定のパッチ
        self.log_patcher = patch('src.ebis_download_cv_attribute.LoggingConfig')
        self.mock_log = self.log_patcher.start()
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # 一時ディレクトリを削除
        shutil.rmtree(self.test_dir)
        
        # パッチを停止
        self.login_patcher.stop()
        self.cv_patcher.stop()
        self.env_patcher.stop()
        self.log_patcher.stop()
    
    def test_run_cv_attribute_download_success(self):
        """ダウンロード実行関数（成功ケース）のテスト"""
        # テスト日付
        start_date = datetime(2023, 3, 1)
        end_date = datetime(2023, 3, 31)
        
        # 関数実行
        result = run_cv_attribute_download(start_date, end_date, self.test_dir)
        
        # 検証
        self.mock_login_class.assert_called_once()
        self.mock_login.execute_login_flow.assert_called_once()
        self.mock_cv_class.assert_called_once_with(browser=self.mock_login.browser)
        self.mock_cv.execute_download_flow.assert_called_once_with(start_date, end_date, self.test_dir)
        self.mock_login.quit.assert_called_once()
        self.assertEqual(result, os.path.join(self.test_dir, "20230301_ebis_CVrepo.csv"))
    
    def test_run_cv_attribute_download_login_failure(self):
        """ダウンロード実行関数（ログイン失敗ケース）のテスト"""
        # ログイン失敗を設定
        self.mock_login.execute_login_flow.return_value = False
        
        # テスト日付
        start_date = datetime(2023, 3, 1)
        end_date = datetime(2023, 3, 31)
        
        # 関数実行
        result = run_cv_attribute_download(start_date, end_date, self.test_dir)
        
        # 検証
        self.mock_login_class.assert_called_once()
        self.mock_login.execute_login_flow.assert_called_once()
        self.mock_cv_class.assert_not_called()
        self.mock_login.quit.assert_called_once()
        self.assertIsNone(result)
    
    def test_run_cv_attribute_download_download_failure(self):
        """ダウンロード実行関数（ダウンロード失敗ケース）のテスト"""
        # ダウンロード失敗を設定
        self.mock_cv.execute_download_flow.return_value = None
        
        # テスト日付
        start_date = datetime(2023, 3, 1)
        end_date = datetime(2023, 3, 31)
        
        # 関数実行
        result = run_cv_attribute_download(start_date, end_date, self.test_dir)
        
        # 検証
        self.mock_login_class.assert_called_once()
        self.mock_login.execute_login_flow.assert_called_once()
        self.mock_cv_class.assert_called_once_with(browser=self.mock_login.browser)
        self.mock_cv.execute_download_flow.assert_called_once_with(start_date, end_date, self.test_dir)
        self.mock_login.quit.assert_called_once()
        self.assertIsNone(result)
    
    def test_run_cv_attribute_download_exception(self):
        """ダウンロード実行関数（例外発生ケース）のテスト"""
        # 例外を発生させる
        self.mock_cv.execute_download_flow.side_effect = Exception("Test exception")
        
        # テスト日付
        start_date = datetime(2023, 3, 1)
        end_date = datetime(2023, 3, 31)
        
        # 関数実行
        result = run_cv_attribute_download(start_date, end_date, self.test_dir)
        
        # 検証
        self.mock_login_class.assert_called_once()
        self.mock_login.execute_login_flow.assert_called_once()
        self.mock_cv_class.assert_called_once_with(browser=self.mock_login.browser)
        self.mock_cv.execute_download_flow.assert_called_once_with(start_date, end_date, self.test_dir)
        self.mock_login.quit.assert_called_once()
        self.assertIsNone(result)
    
    def test_parse_arguments_default(self):
        """コマンドライン引数解析（デフォルト）のテスト"""
        # 引数なしの場合
        with patch('sys.argv', ['ebis_download_cv_attribute.py']):
            args = parse_arguments()
            self.assertIsNone(args.date)
            self.assertIsNone(args.range)
            self.assertIsNone(args.account)
            self.assertIsNone(args.output)
            self.assertFalse(args.headless)
    
    def test_parse_arguments_with_options(self):
        """コマンドライン引数解析（オプション指定）のテスト"""
        # 全オプション指定の場合
        with patch('sys.argv', [
            'ebis_download_cv_attribute.py',
            '-d', '2023-03-01',
            '-a', '12345',
            '-o', '/path/to/output',
            '--headless'
        ]):
            args = parse_arguments()
            self.assertEqual(args.date, '2023-03-01')
            self.assertIsNone(args.range)
            self.assertEqual(args.account, '12345')
            self.assertEqual(args.output, '/path/to/output')
            self.assertTrue(args.headless)
        
        # 日付範囲指定の場合
        with patch('sys.argv', [
            'ebis_download_cv_attribute.py',
            '-r', '2023-03-01', '2023-03-31'
        ]):
            args = parse_arguments()
            self.assertIsNone(args.date)
            self.assertEqual(args.range, ['2023-03-01', '2023-03-31'])
    
    def test_prepare_dates_single_date(self):
        """日付準備関数（単一日付）のテスト"""
        # 引数オブジェクトを作成
        args = MagicMock()
        args.date = '2023-03-01'
        args.range = None
        
        # 関数実行
        start_date, end_date = prepare_dates(args)
        
        # 検証
        self.assertEqual(start_date, datetime(2023, 3, 1))
        self.assertEqual(end_date, datetime(2023, 3, 1))
    
    def test_prepare_dates_date_range(self):
        """日付準備関数（日付範囲）のテスト"""
        # 引数オブジェクトを作成
        args = MagicMock()
        args.date = None
        args.range = ['2023-03-01', '2023-03-31']
        
        # 関数実行
        start_date, end_date = prepare_dates(args)
        
        # 検証
        self.assertEqual(start_date, datetime(2023, 3, 1))
        self.assertEqual(end_date, datetime(2023, 3, 31))
    
    def test_prepare_dates_default(self):
        """日付準備関数（デフォルト日付）のテスト"""
        # 引数オブジェクトを作成
        args = MagicMock()
        args.date = None
        args.range = None
        
        # 関数実行
        with patch('src.ebis_download_cv_attribute.datetime') as mock_datetime:
            mock_today = datetime(2023, 3, 2)
            mock_datetime.now.return_value = mock_today
            mock_datetime.strptime.side_effect = datetime.strptime
            
            start_date, end_date = prepare_dates(args)
            
            # 検証（前日の日付）
            expected_date = datetime(2023, 3, 1)
            self.assertEqual(start_date, expected_date)
            self.assertEqual(end_date, expected_date)
    
    def test_prepare_dates_invalid_format(self):
        """日付準備関数（不正な日付形式）のテスト"""
        # 引数オブジェクトを作成（不正な日付）
        args = MagicMock()
        args.date = '2023/03/01'  # 正しくは YYYY-MM-DD
        args.range = None
        
        # 関数実行と例外確認
        with self.assertRaises(ValueError):
            prepare_dates(args)
        
        # 不正な日付範囲
        args.date = None
        args.range = ['2023/03/01', '2023-03-31']
        
        with self.assertRaises(ValueError):
            prepare_dates(args)
    
    def test_prepare_dates_invalid_range(self):
        """日付準備関数（不正な日付範囲）のテスト"""
        # 引数オブジェクトを作成（終了日が開始日より前）
        args = MagicMock()
        args.date = None
        args.range = ['2023-03-31', '2023-03-01']
        
        # 関数実行と例外確認
        with self.assertRaises(ValueError):
            prepare_dates(args)

if __name__ == '__main__':
    unittest.main() 