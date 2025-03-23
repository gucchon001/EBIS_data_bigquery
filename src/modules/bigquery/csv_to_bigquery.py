#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CSVファイルをJSONに変換し、BigQueryテーブルにロードする一連の処理を行うスクリプト。
指定した行数のみを処理することも可能です。
デフォルトではアップサートモード（応募IDをキーとして更新/挿入）を使用します。
"""

import os
import sys
import argparse
import logging
import tempfile
import uuid
import pandas as pd
from src.modules.bigquery.convert_csv_to_json import convert_csv_to_json
from src.modules.bigquery.load_to_bigquery_fixed import load_data_to_bigquery
from src.modules.bigquery.upsert_to_bigquery import upsert_data_to_bigquery
from src.utils.environment import EnvironmentUtils as env

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_csv_to_bigquery(csv_file, table_name, nrows=None, write_disposition='WRITE_TRUNCATE', 
                           upsert=True, key_column='応募ID', encoding='auto'):
    """
    CSVファイルをBigQueryテーブルに読み込む処理フローを実行します
    
    Args:
        csv_file: 入力CSVファイルのパス
        table_name: ロード先のテーブル名（形式: データセット.テーブル）
        nrows: 読み込む行数（None=全行）
        write_disposition: アップサートしない場合の書き込み方法
        upsert: アップサートモードで実行するかどうか（Trueの場合）
        key_column: アップサートのキーカラム名（デフォルトは応募ID）
        encoding: CSVファイルのエンコーディング ('auto'の場合は自動判定)
        
    Returns:
        bool: 処理が成功した場合はTrue、失敗した場合はFalse
    """
    logger.info("ステップ1: CSVファイルをJSONに変換します")
    # 一時JSONファイルを作成
    temp_json = os.path.join(tempfile.gettempdir(), f"tmp{uuid.uuid4().hex[:8]}.json")
    
    try:
        # エンコーディングの自動判定
        csv_encoding = encoding
        if encoding == 'auto':
            try:
                # まずUTF-8で試す
                with open(csv_file, 'r', encoding='utf-8') as f:
                    f.read(1024)  # 先頭の一部だけ読み込む
                csv_encoding = 'utf-8'
                logger.info(f"エンコーディングをUTF-8と判定しました")
            except UnicodeDecodeError:
                try:
                    # UTF-8で失敗した場合はcp932（Shift-JIS）で試す
                    with open(csv_file, 'r', encoding='cp932') as f:
                        f.read(1024)
                    csv_encoding = 'cp932'
                    logger.info(f"エンコーディングをcp932（Shift-JIS）と判定しました")
                except UnicodeDecodeError:
                    # それでも失敗する場合はlatin1（どんなバイト列も読める）でフォールバック
                    csv_encoding = 'latin1'
                    logger.info(f"エンコーディングの自動判定に失敗しました。latin1でフォールバックします")
        
        # CSVをJSONに変換
        try:
            convert_csv_to_json(csv_file, temp_json, encoding=csv_encoding, nrows=nrows)
        except Exception as e:
            logger.error(f"CSVからJSONへの変換に失敗しました: {str(e)}")
            # エラー詳細を出力
            import traceback
            logger.error(f"エラー詳細: {traceback.format_exc()}")
            return False
        
        logger.info("ステップ2: JSONファイルをBigQueryにロードします")
        
        if upsert:
            # アップサートモードで実行
            logger.info(f"アップサートモード（キー: {key_column}）でロードします")
            result = upsert_data_to_bigquery(temp_json, table_name, key_column)
        else:
            # 通常モードで実行
            logger.info(f"通常モード（{write_disposition}）でロードします")
            result = load_data_to_bigquery(temp_json, table_name, write_disposition)
        
        if result:
            logger.info(f"CSVデータをテーブル '{table_name}' に正常にロードしました")
        else:
            logger.error(f"BigQueryへのデータロードに失敗しました")
            
        # 一時ファイルの削除
        if os.path.exists(temp_json):
            os.remove(temp_json)
            logger.info(f"一時JSONファイル '{temp_json}' を削除しました")
            
        return result
    except Exception as e:
        logger.error(f"処理中にエラーが発生しました: {str(e)}")
        # エラー詳細を出力
        import traceback
        logger.error(f"エラー詳細: {traceback.format_exc()}")
        
        # 一時ファイルの削除
        if os.path.exists(temp_json):
            os.remove(temp_json)
            logger.info(f"一時JSONファイル '{temp_json}' を削除しました")
            
        logger.error("処理に失敗しました")
        return False

def main():
    """メイン処理関数"""
    # 引数の解析
    parser = argparse.ArgumentParser(description='CSVファイルをJSONに変換し、BigQueryテーブルにロードします')
    parser.add_argument('csv_file', help='入力CSVファイルのパス')
    parser.add_argument('table_name', help='ロード先のテーブル名（形式: データセット.テーブル）')
    parser.add_argument('--nrows', type=int, help='処理する行数（デフォルト: 全行）')
    parser.add_argument('--write-disposition', choices=['WRITE_TRUNCATE', 'WRITE_APPEND', 'WRITE_EMPTY'], 
                        default='WRITE_TRUNCATE', help='書き込み方法（デフォルト: WRITE_TRUNCATE、upsert=Falseの場合のみ使用）')
    parser.add_argument('--no-upsert', action='store_true', help='通常モード（アップサートを使用しない）')
    parser.add_argument('--key-column', default='応募ID', help='アップサート時のキーカラム名（デフォルト: 応募ID）')
    parser.add_argument('--encoding', default='auto', help='CSVファイルのエンコーディング（デフォルト: auto）')
    parser.add_argument('--env-file', default='config/secrets.env', help='環境変数ファイルのパス（デフォルト: config/secrets.env）')
    
    args = parser.parse_args()
    
    # 環境変数を読み込む
    env.load_env(args.env_file)
    
    # 処理を実行
    success = process_csv_to_bigquery(
        csv_file=args.csv_file,
        table_name=args.table_name,
        nrows=args.nrows,
        write_disposition=args.write_disposition,
        upsert=not args.no_upsert,
        key_column=args.key_column,
        encoding=args.encoding
    )
    
    if success:
        logger.info("処理が正常に完了しました")
        return 0
    else:
        logger.error("処理に失敗しました")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 