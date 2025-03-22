#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EBIS自動操作メインスクリプト
Seleniumを使用してEBISのデータダウンロードを自動化します。
ログイン後、詳細分析ページからCSVデータをダウンロードし、続いてCV属性レポートをダウンロードします。
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
from src.modules.browser.login_page import LoginPage
from src.modules.browser.detailed_analysis_page import DetailedAnalysisPage
from src.modules.browser.cv_attribute_page import CVAttributePage

logger = get_logger(__name__)

def parse_args():
    """
    コマンドライン引数を解析する
    
    Returns:
        argparse.Namespace: 解析された引数
    """
    parser = argparse.ArgumentParser(description='EBIS自動データ取得ツール')
    
    # 日付範囲の指定
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--date', type=str,
                        help='取得する日付（YYYY-MM-DD形式）')
    date_group.add_argument('--start-date', type=str,
                        help='取得対象の開始日（YYYY-MM-DD形式）')
    
    parser.add_argument('--end-date', type=str,
                        help='取得対象の終了日（YYYY-MM-DD形式）')
    
    # その他の基本オプション
    parser.add_argument('--headless', action='store_true',
                        help='ヘッドレスモードで実行（ブラウザを表示せずに実行）')
    parser.add_argument('--output-dir', type=str, default='data/downloads',
                        help='ダウンロードしたデータの出力先ディレクトリ')
    parser.add_argument('--account', type=str, default='1',
                        help='使用するアカウント番号（デフォルト: 1）')
    parser.add_argument('--skip-detailed', action='store_true',
                        help='詳細分析レポートのダウンロードをスキップする')
    parser.add_argument('--skip-cv-attr', action='store_true',
                        help='CV属性レポートのダウンロードをスキップする')
    parser.add_argument('--test', action='store_true',
                        help='テストモードで実行（開発環境用）')
    
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
    """メイン実行関数"""
    try:
        # 引数を解析
        args = parse_args()
        
        # 環境変数を読み込む
        env.load_env()
        
        # アカウント番号の設定
        if args.account != '1':
            env.update_config_value("Login", "account_number", args.account)
        
        # ヘッドレスモードの設定
        if args.headless:
            env.update_config_value("BROWSER", "headless", "true")
        
        # 出力ディレクトリの作成
        os.makedirs(args.output_dir, exist_ok=True)
        
        # 日付設定の処理
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
            # days_ago設定を取得
            days_ago_str = env.get_config_value("Download", "days_ago", "1")
            try:
                days_ago = int(days_ago_str)
            except ValueError:
                logger.warning(f"無効なdays_ago設定値です: {days_ago_str}。デフォルト値の1を使用します。")
                days_ago = 1
            
            # 指定された日数前の日付を計算
            start_date = end_date = datetime.today() - timedelta(days=days_ago)
        
        logger.info(f"取得期間: {start_date.strftime('%Y-%m-%d')} から {end_date.strftime('%Y-%m-%d')}")
        logger.info(f"ヘッドレスモード: {args.headless}")
        logger.info(f"出力先ディレクトリ: {args.output_dir}")
        
        # ログイン処理
        login_page = LoginPage()
        
        if not login_page.execute_login_flow():
            logger.error("ログインに失敗しました")
            login_page.quit()
            return 1
        
        logger.info("ログインに成功しました")
        
        # 各レポートのダウンロード処理結果を保持
        detailed_result = None
        cv_attr_result = None
        
        # 詳細分析レポートのダウンロード
        if not args.skip_detailed:
            try:
                logger.info("詳細分析レポートのダウンロードを開始します")
                analysis_page = DetailedAnalysisPage(login_page.browser)
                detailed_result = analysis_page.execute_download_flow(start_date, end_date, args.output_dir)
                
                if detailed_result:
                    logger.info(f"詳細分析レポートのダウンロードが完了しました: {detailed_result}")
                else:
                    logger.error("詳細分析レポートのダウンロードに失敗しました")
            except Exception as e:
                logger.error(f"詳細分析レポートのダウンロード中にエラーが発生しました: {str(e)}")
                logger.error(traceback.format_exc())
        else:
            logger.info("詳細分析レポートのダウンロードはスキップされました")
        
        # CV属性レポートのダウンロード
        if not args.skip_cv_attr:
            try:
                logger.info("CV属性レポートのダウンロードを開始します")
                cv_attribute_page = CVAttributePage(login_page.browser)
                cv_attr_result = cv_attribute_page.execute_download_flow(start_date, end_date, args.output_dir)
                
                if cv_attr_result:
                    logger.info(f"CV属性レポートのダウンロードが完了しました: {cv_attr_result}")
                else:
                    logger.error("CV属性レポートのダウンロードに失敗しました")
            except Exception as e:
                logger.error(f"CV属性レポートのダウンロード中にエラーが発生しました: {str(e)}")
                logger.error(traceback.format_exc())
        else:
            logger.info("CV属性レポートのダウンロードはスキップされました")
        
        # ブラウザを終了
        login_page.quit()
        
        # 処理結果の判定
        if (not args.skip_detailed and detailed_result) or (not args.skip_cv_attr and cv_attr_result):
            logger.info("少なくとも1つのレポートダウンロードが成功しました")
            print("処理が正常に完了しました")
            return 0
        else:
            logger.error("すべてのレポートダウンロードが失敗しました")
            print("処理に失敗しました")
            return 1
            
    except Exception as e:
        logger.error(f"メイン処理中にエラーが発生しました: {str(e)}")
        traceback.print_exc()
        print(f"エラーが発生しました: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
