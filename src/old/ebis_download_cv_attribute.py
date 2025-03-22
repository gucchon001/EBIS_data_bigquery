#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AdEBiS CV属性レポートダウンロードスクリプト

指定した期間のCV属性レポートをCSVでダウンロードするスクリプトです。
コマンドライン引数で日付範囲やログイン情報などを指定できます。
"""

import os
import sys
import argparse
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.utils.logging_config import get_logger, LoggingConfig
from src.utils.environment import EnvironmentUtils as env
from src.modules.browser.login_page import LoginPage
from src.modules.browser.cv_attribute_page import CVAttributePage

# ロガーの取得
logger = get_logger(__name__)

def parse_arguments():
    """
    コマンドライン引数を解析します
    
    Returns:
        argparse.Namespace: 解析された引数オブジェクト
    """
    parser = argparse.ArgumentParser(description='AdEBiS CV属性レポートをCSVでダウンロードします')
    
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('-d', '--date', 
                          help='取得する日付（YYYY-MM-DD形式）。指定しない場合は前日')
    date_group.add_argument('-r', '--range', nargs=2, metavar=('START_DATE', 'END_DATE'),
                          help='取得する日付範囲（YYYY-MM-DD YYYY-MM-DD形式）')
    
    parser.add_argument('-a', '--account', help='アカウント番号')
    parser.add_argument('-o', '--output', help='出力ディレクトリのパス')
    parser.add_argument('--headless', action='store_true', help='ヘッドレスモードで実行')
    
    args = parser.parse_args()
    
    return args

def prepare_dates(args):
    """
    引数から日付情報を解析し、開始日と終了日を返します
    
    Args:
        args (argparse.Namespace): コマンドライン引数
        
    Returns:
        tuple: (開始日, 終了日) の形式の日付オブジェクトのタプル
    """
    today = datetime.now()
    
    if args.date:
        # 特定の日付が指定された場合
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d')
            return target_date, target_date
        except ValueError:
            logger.error(f"無効な日付形式です: {args.date}。YYYY-MM-DD形式で指定してください。")
            raise ValueError(f"無効な日付形式: {args.date}")
    elif args.range:
        # 日付範囲が指定された場合
        try:
            start_date = datetime.strptime(args.range[0], '%Y-%m-%d')
            end_date = datetime.strptime(args.range[1], '%Y-%m-%d')
            if start_date > end_date:
                logger.error(f"開始日({args.range[0]})が終了日({args.range[1]})より後になっています。")
                raise ValueError("開始日は終了日以前である必要があります")
            return start_date, end_date
        except ValueError as e:
            if "unconverted data remains" in str(e) or "does not match format" in str(e):
                logger.error(f"無効な日付形式です: {args.range}。YYYY-MM-DD形式で指定してください。")
                raise ValueError(f"無効な日付形式: {args.range}")
            else:
                raise
    else:
        # days_ago設定を取得
        days_ago_str = env.get_config_value("Download", "days_ago", "1")
        try:
            days_ago = int(days_ago_str)
        except ValueError:
            logger.warning(f"無効なdays_ago設定値です: {days_ago_str}。デフォルト値の1を使用します。")
            days_ago = 1
        
        # 指定された日数前の日付を計算
        target_date = today - timedelta(days=days_ago)
        logger.info(f"日付指定なし - デフォルト設定（{days_ago}日前）のデータを取得します: {target_date.strftime('%Y-%m-%d')}")
        return target_date, target_date

def run_cv_attribute_download(start_date, end_date, output_dir=None):
    """
    CV属性レポートのダウンロードを実行します
    
    Args:
        start_date (datetime): 開始日
        end_date (datetime): 終了日
        output_dir (str, optional): 出力ディレクトリ
        
    Returns:
        str: ダウンロードしたファイルのパス、失敗した場合はNone
    """
    login_page = None
    cv_attribute_page = None
    
    try:
        # ログインページのインスタンス化
        login_page = LoginPage()
        
        # ログイン実行
        if not login_page.execute_login_flow():
            logger.error("ログイン処理に失敗しました")
            return None
            
        logger.info("ログインに成功しました")
        
        # CV属性ページのインスタンス化（既存のブラウザインスタンスを使用）
        cv_attribute_page = CVAttributePage(browser=login_page.browser)
        
        # ダウンロードフロー実行
        result = cv_attribute_page.execute_download_flow(start_date, end_date, output_dir)
        
        if result:
            logger.info(f"CV属性レポートのダウンロードに成功しました: {result}")
            return result
        else:
            logger.error("CV属性レポートのダウンロードに失敗しました")
            return None
            
    except Exception as e:
        logger.error(f"CV属性レポートダウンロード中に予期せぬエラーが発生しました: {str(e)}")
        logger.error(traceback.format_exc())
        return None
        
    finally:
        # CV属性ページのブラウザインスタンスは終了しない（LoginPageのインスタンスが管理するため）
        if login_page:
            login_page.quit()

def main():
    """
    メイン処理
    """
    # 環境変数の読み込み
    env.load_env()
    
    # ログ設定
    log_dir = env.resolve_path(env.get_config_value("Log", "directory", "logs"))
    os.makedirs(log_dir, exist_ok=True)
    LoggingConfig()  # ロギング設定を初期化
    
    try:
        # コマンドライン引数の解析
        args = parse_arguments()
        
        # ヘッドレスモード設定
        if args.headless:
            env.set_config_value("BROWSER", "headless", "true")
        
        # アカウント番号設定
        if args.account:
            env.set_config_value("Login", "account", args.account)
        
        # 日付の準備
        start_date, end_date = prepare_dates(args)
        logger.info(f"取得対象期間: {start_date.strftime('%Y-%m-%d')} から {end_date.strftime('%Y-%m-%d')}")
        
        # 出力ディレクトリの設定
        output_dir = None
        if args.output:
            output_dir = args.output
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"出力ディレクトリ: {output_dir}")
        
        # ダウンロード実行
        result = run_cv_attribute_download(start_date, end_date, output_dir)
        
        if result:
            logger.info(f"処理が正常に完了しました。ファイル: {result}")
            sys.exit(0)
        else:
            logger.error("処理が失敗しました")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"予期せぬエラーが発生しました: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 