#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EBIS自動操作メインスクリプト
Seleniumを使用してEBISのデータダウンロードを自動化します。
操作モードを引数で指定可能で、CSVデータをダウンロードします。
"""

import os
import sys
from pathlib import Path
import argparse
import traceback
from datetime import datetime, timedelta

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env
from src.modules.browser.browser import Browser
from src.modules.browser.login_page import LoginPage
from src.modules.browser.detail_analytics_page import DetailAnalyticsPage
from src.modules.browser.cv_attribute_page import CvAttributePage

logger = get_logger(__name__)

def parse_args():
    """
    コマンドライン引数を解析する
    
    Returns:
        argparse.Namespace: 解析された引数
    """
    parser = argparse.ArgumentParser(description='EBIS自動データ取得ツール')
    
    # 操作モードの指定
    parser.add_argument('--mode', type=str, default='detail_analytics',
                        choices=['login', 'detail_analytics', 'cv_attribute', 'all'],
                        help='実行する操作モード（login, detail_analytics, cv_attribute, all）')
    
    # 日付範囲の指定
    parser.add_argument('--start-date', type=str,
                        help='取得対象の開始日（YYYY-MM-DD形式）')
    parser.add_argument('--end-date', type=str,
                        help='取得対象の終了日（YYYY-MM-DD形式）')
    
    # ヘッドレスモードの指定
    parser.add_argument('--headless', action='store_true',
                        help='ヘッドレスモードで実行（ブラウザを表示せずに実行）')
    
    # 出力先の指定
    parser.add_argument('--output-dir', type=str, default='data',
                        help='ダウンロードしたデータの出力先ディレクトリ')
    
    return parser.parse_args()

def login_only():
    """
    ログインのみを実行する
    
    Returns:
        bool: 成功した場合はTrue、失敗した場合はFalse
    """
    try:
        # 環境変数を読み込む
        env.load_env()
        
        # ログインページインスタンスを作成
        login_page = LoginPage()
        
        # ログインを実行
        success = login_page.execute_login_flow()
        
        if success:
            logger.info("ログインに成功しました")
        else:
            logger.error("ログインに失敗しました")
            
        # ブラウザを終了
        login_page.browser.quit()
        
        return success
        
    except Exception as e:
        logger.error(f"ログイン処理中にエラーが発生しました: {str(e)}")
        traceback.print_exc()
        return False

def run_detail_analytics(browser=None, start_date=None, end_date=None):
    """
    詳細分析データのダウンロードを実行する
    
    Args:
        browser (Browser): 既存のブラウザインスタンス（省略時は新規作成）
        start_date (str or datetime): 開始日
        end_date (str or datetime): 終了日
        
    Returns:
        bool: 成功した場合はTrue、失敗した場合はFalse
    """
    detail_analytics = None
    try:
        # 詳細分析ページインスタンスを作成
        detail_analytics = DetailAnalyticsPage(browser=browser, login_first=(browser is None))
        
        # ダウンロードフローを実行
        success = detail_analytics.execute_download_flow(start_date, end_date)
        
        if success:
            logger.info("詳細分析データのダウンロードに成功しました")
        else:
            logger.error("詳細分析データのダウンロードに失敗しました")
            
        return success
        
    except Exception as e:
        logger.error(f"詳細分析処理中にエラーが発生しました: {str(e)}")
        traceback.print_exc()
        return False
        
    finally:
        # 新規にブラウザを作成した場合は終了
        if browser is None and detail_analytics is not None:
            detail_analytics.quit()

def run_cv_attribute(browser=None, start_date=None, end_date=None):
    """
    コンバージョン属性データのダウンロードを実行する
    
    Args:
        browser (Browser): 既存のブラウザインスタンス（省略時は新規作成）
        start_date (str or datetime): 開始日
        end_date (str or datetime): 終了日
        
    Returns:
        bool: 成功した場合はTrue、失敗した場合はFalse
    """
    cv_attribute = None
    try:
        # コンバージョン属性ページインスタンスを作成
        cv_attribute = CvAttributePage(browser=browser, login_first=(browser is None))
        
        # ダウンロードフローを実行
        success = cv_attribute.execute_download_flow(start_date, end_date)
        
        if success:
            logger.info("コンバージョン属性データのダウンロードに成功しました")
        else:
            logger.error("コンバージョン属性データのダウンロードに失敗しました")
            
        return success
        
    except Exception as e:
        logger.error(f"コンバージョン属性処理中にエラーが発生しました: {str(e)}")
        traceback.print_exc()
        return False
        
    finally:
        # 新規にブラウザを作成した場合は終了
        if browser is None and cv_attribute is not None:
            cv_attribute.quit()

def run_all(start_date=None, end_date=None, headless=False):
    """
    すべての操作を一連のフローとして実行する
    
    Args:
        start_date (str or datetime): 開始日
        end_date (str or datetime): 終了日
        headless (bool): ヘッドレスモードで実行するかどうか
        
    Returns:
        bool: すべての処理が成功した場合はTrue、いずれかが失敗した場合はFalse
    """
    browser = None
    try:
        # 環境変数を読み込む
        env.load_env()
        
        # ブラウザインスタンスの作成
        browser = Browser(selectors_path="config/selectors.csv", headless=headless)
        if not browser.setup():
            logger.error("ブラウザのセットアップに失敗しました")
            return False
            
        # ログインを実行
        login_page = LoginPage(browser=browser)
        if not login_page.execute_login_flow():
            logger.error("ログインに失敗しました")
            return False
            
        logger.info("ログインに成功しました")
        
        # 詳細分析データのダウンロードを実行
        if not run_detail_analytics(browser=browser, start_date=start_date, end_date=end_date):
            logger.error("詳細分析データのダウンロードに失敗しました")
            return False
            
        # コンバージョン属性データのダウンロードを実行
        if not run_cv_attribute(browser=browser, start_date=start_date, end_date=end_date):
            logger.error("コンバージョン属性データのダウンロードに失敗しました")
            return False
            
        logger.info("すべての処理が正常に完了しました")
        return True
        
    except Exception as e:
        logger.error(f"処理中にエラーが発生しました: {str(e)}")
        traceback.print_exc()
        return False
        
    finally:
        # ブラウザを終了
        if browser is not None:
            browser.quit()

def main():
    """メイン実行関数"""
    try:
        # 引数を解析
        args = parse_args()
        
        # 環境変数を読み込む
        env.load_env()
        
        # 出力ディレクトリの作成
        os.makedirs(args.output_dir, exist_ok=True)
        
        # 日付範囲の設定
        start_date = args.start_date
        end_date = args.end_date
        
        # 日付が指定されていない場合は、デフォルトで先月1日から末日までを設定
        if start_date is None or end_date is None:
            today = datetime.now()
            last_month = today.replace(day=1) - timedelta(days=1)
            if start_date is None:
                start_date = last_month.replace(day=1).strftime("%Y-%m-%d")
            if end_date is None:
                end_date = last_month.strftime("%Y-%m-%d")
        
        logger.info(f"操作モード: {args.mode}")
        logger.info(f"取得期間: {start_date} から {end_date}")
        logger.info(f"ヘッドレスモード: {args.headless}")
        logger.info(f"出力先ディレクトリ: {args.output_dir}")
        
        # モードに応じた処理を実行
        if args.mode == 'login':
            success = login_only()
        elif args.mode == 'detail_analytics':
            success = run_detail_analytics(start_date=start_date, end_date=end_date)
        elif args.mode == 'cv_attribute':
            success = run_cv_attribute(start_date=start_date, end_date=end_date)
        elif args.mode == 'all':
            success = run_all(start_date=start_date, end_date=end_date, headless=args.headless)
        else:
            logger.error(f"不明な操作モード: {args.mode}")
            success = False
        
        # 結果を出力
        if success:
            logger.info("処理が正常に完了しました")
            print("処理が正常に完了しました")
            return 0
        else:
            logger.error("処理に失敗しました")
            print("処理に失敗しました")
            return 1
            
    except Exception as e:
        logger.error(f"メイン処理中にエラーが発生しました: {str(e)}")
        traceback.print_exc()
        print(f"エラーが発生しました: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
