#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CV属性レポートの自動ダウンロードとBigQueryへのロード

このスクリプトは以下の処理を行います：
1. EBISにログインしてCV属性レポートをダウンロード
2. ダウンロードしたCSVファイルをチャンク単位で処理
3. BigQueryにデータをロード
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent.parent.parent)
sys.path.append(project_root)

from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env
from src.modules.browser.login_page import LoginPage
from src.modules.browser.cv_attribute_page import CVAttributePage
from src.modules.bigquery.process_in_chunks import process_in_chunks

logger = get_logger(__name__)

def parse_args():
    """コマンドライン引数を解析する"""
    parser = argparse.ArgumentParser(description='CV属性レポートの自動ダウンロードとBigQueryロード')
    
    # 日付範囲の指定
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--date', type=str,
                        help='取得する日付（YYYY-MM-DD形式）')
    date_group.add_argument('--start-date', type=str,
                        help='取得対象の開始日（YYYY-MM-DD形式）')
    
    parser.add_argument('--end-date', type=str,
                        help='取得対象の終了日（YYYY-MM-DD形式）')
    
    # BigQuery関連のオプション
    parser.add_argument('--table-name', type=str, required=True,
                        help='BigQueryテーブル名（形式: データセット.テーブル）')
    parser.add_argument('--chunk-size', type=int, default=1000,
                        help='一度に処理する行数（デフォルト: 1000）')
    parser.add_argument('--write-disposition', default='WRITE_TRUNCATE',
                        choices=['WRITE_TRUNCATE', 'WRITE_APPEND', 'WRITE_EMPTY'],
                        help='テーブルへの書き込み方法（デフォルト: WRITE_TRUNCATE）')
    
    # その他のオプション
    parser.add_argument('--headless', action='store_true',
                        help='ヘッドレスモードで実行（ブラウザを表示せずに実行）')
    parser.add_argument('--output-dir', type=str, default='data/downloads',
                        help='ダウンロードしたデータの出力先ディレクトリ')
    
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
        
        # CV属性レポートのダウンロード
        try:
            logger.info("CV属性レポートのダウンロードを開始します")
            cv_attribute_page = CVAttributePage(login_page.browser)
            downloaded_file = cv_attribute_page.execute_download_flow(start_date, end_date, args.output_dir)
            
            if downloaded_file:
                logger.info(f"CV属性レポートのダウンロードが完了しました: {downloaded_file}")
            else:
                logger.error("CV属性レポートのダウンロードに失敗しました")
                login_page.quit()
                return 1
        except Exception as e:
            logger.error(f"CV属性レポートのダウンロード中にエラーが発生しました: {str(e)}")
            login_page.quit()
            return 1
        
        # ブラウザを終了
        login_page.quit()
        
        # BigQueryへのロード処理
        logger.info(f"BigQueryへのデータロードを開始します: テーブル {args.table_name}")
        
        # カラムマッピングの設定
        column_mapping = {
            '売上金額': '応募ID',
            # 必要に応じて他のカラム変換も追加可能
        }
        
        # 日付カラムの指定
        date_columns = ['CV時間']
        
        # 整数カラムの指定
        integer_columns = ['応募ID', '接触回数', '潜伏期間（秒）']
        
        # チャンク処理の実行
        success, failed = process_in_chunks(
            downloaded_file,
            args.table_name,
            args.chunk_size,
            None,  # max_chunks
            0,    # start_row
            column_mapping,
            date_columns,
            integer_columns,
            args.write_disposition
        )
        
        if failed > 0:
            logger.error(f"データロード中にエラーが発生しました: {failed}件のチャンクが失敗")
            return 1
        else:
            logger.info("すべてのデータが正常にロードされました")
            return 0
            
    except Exception as e:
        logger.error(f"処理中にエラーが発生しました: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 