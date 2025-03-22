#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
アドエビス詳細分析ページからCSVをダウンロードするスクリプト
指定された日付範囲のデータをCSVとしてダウンロードします。
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env
from src.modules.browser.login_page import LoginPage
from src.modules.browser.detailed_analysis_page import DetailedAnalysisPage

logger = get_logger(__name__)

def parse_args():
    """コマンドライン引数を解析します"""
    parser = argparse.ArgumentParser(description='アドエビス詳細分析ページからCSVをダウンロードします')
    
    # 日付関連オプション
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--date', type=str, help='取得する日付 (YYYY-MM-DD形式)')
    date_group.add_argument('--start-date', type=str, help='取得開始日 (YYYY-MM-DD形式)')
    
    parser.add_argument('--end-date', type=str, help='取得終了日 (YYYY-MM-DD形式、--start-dateと共に使用)')
    
    # その他のオプション
    parser.add_argument('--account', type=str, default='1', help='使用するアカウント番号（デフォルト: 1）')
    parser.add_argument('--output-dir', type=str, help='出力ディレクトリ')
    parser.add_argument('--headless', action='store_true', help='ヘッドレスモードでブラウザを実行')
    parser.add_argument('--verify', action='store_true', help='検証モード（ダウンロードを実行せず）')
    
    return parser.parse_args()

def parse_date(date_str):
    """日付文字列をdatetimeオブジェクトに変換します"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        logger.error(f"無効な日付形式です: {date_str}（YYYY-MM-DD形式で入力してください）")
        return None

def main():
    """メイン処理"""
    # コマンドライン引数の解析
    args = parse_args()
    
    # 環境変数の読み込み
    env.load_env()
    
    # アカウント番号の設定
    if args.account != '1':
        env.update_config_value("Login", "account_number", args.account)
    
    # ヘッドレスモードの設定
    if args.headless:
        env.update_config_value("BROWSER", "headless", "true")
    
    # 日付の設定
    if args.date:
        target_date = parse_date(args.date)
        if not target_date:
            return 1
        start_date = end_date = target_date
    elif args.start_date:
        start_date = parse_date(args.start_date)
        if not start_date:
            return 1
        
        if args.end_date:
            end_date = parse_date(args.end_date)
            if not end_date:
                return 1
        else:
            end_date = start_date
    else:
        # デフォルトは前日
        start_date = end_date = datetime.today() - timedelta(days=1)
    
    logger.info(f"対象期間: {start_date.strftime('%Y-%m-%d')} から {end_date.strftime('%Y-%m-%d')}")
    
    try:
        # ログイン処理
        login_page = LoginPage()
        
        if not login_page.execute_login_flow():
            logger.error("ログインに失敗しました")
            login_page.quit()
            return 1
        
        logger.info("ログインに成功しました")
        
        # 検証モードの場合はここで終了
        if args.verify:
            logger.info("検証モードのため、ダウンロード処理をスキップします")
            login_page.quit()
            return 0
        
        # 詳細分析ページ処理
        analysis_page = DetailedAnalysisPage(login_page.browser)
        result = analysis_page.execute_download_flow(start_date, end_date, args.output_dir)
        
        # ブラウザを終了（ログインページではなく分析ページから終了する）
        analysis_page.quit()
        
        if result:
            logger.info(f"CSVダウンロードが完了しました: {result}")
            return 0
        else:
            logger.error("CSVダウンロードに失敗しました")
            return 1
            
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 