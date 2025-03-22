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
                           upsert=True, key_column='応募ID', encoding='cp932'):
    """
    CSVファイルをJSONに変換し、BigQueryテーブルにロードする一連の処理を行う
    
    Args:
        csv_file (str): 入力CSVファイルのパス
        table_name (str): ロード先のテーブル名（形式: データセット.テーブル）
        nrows (int, optional): 処理する行数（デフォルト: 全行）
        write_disposition (str, optional): 書き込み方法（デフォルト: WRITE_TRUNCATE）
        upsert (bool, optional): アップサート（更新/挿入）を行うかどうか（デフォルト: True）
        key_column (str, optional): アップサート時のキーカラム名（デフォルト: 応募ID）
        encoding (str, optional): CSVファイルのエンコーディング（デフォルト: cp932）
        
    Returns:
        bool: 処理が成功した場合はTrue、失敗した場合はFalse
    """
    try:
        # 環境変数の読み込み
        env.load_env()
        
        # CSVファイルの存在確認
        if not os.path.exists(csv_file):
            logger.error(f"CSVファイル '{csv_file}' が見つかりません")
            return False
            
        # 一時JSONファイル用のパス
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            temp_json_file = tmp.name
        
        try:
            # ステップ1: CSVファイルをJSONに変換
            logger.info("ステップ1: CSVファイルをJSONに変換します")
            json_file = convert_csv_to_json(
                csv_file=csv_file,
                json_file=temp_json_file,
                encoding=encoding,
                nrows=nrows,
                orient='records',
                lines=True
            )
            
            if not json_file:
                logger.error("CSVからJSONへの変換に失敗しました")
                return False
                
            # ステップ2: JSONファイルをBigQueryにロード
            logger.info("ステップ2: JSONファイルをBigQueryにロードします")
            if upsert:
                # アップサート（更新/挿入）モード
                logger.info(f"アップサートモード（キー: {key_column}）でロードします")
                success = upsert_data_to_bigquery(
                    file_path=json_file,
                    table_name=table_name,
                    key_column=key_column
                )
            else:
                # 通常のロードモード
                logger.info(f"通常モード（{write_disposition}）でロードします")
                success = load_data_to_bigquery(
                    file_path=json_file,
                    table_name=table_name,
                    write_disposition=write_disposition
                )
                
            if not success:
                logger.error("BigQueryへのデータロードに失敗しました")
                return False
                
            logger.info(f"CSVデータをテーブル '{table_name}' に正常にロードしました")
            return True
            
        finally:
            # 一時JSONファイルの削除
            if os.path.exists(temp_json_file):
                try:
                    os.remove(temp_json_file)
                    logger.info(f"一時JSONファイル '{temp_json_file}' を削除しました")
                except Exception as e:
                    logger.warning(f"一時JSONファイルの削除に失敗しました: {e}")
    
    except Exception as e:
        logger.error(f"処理中にエラーが発生しました: {e}")
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
    parser.add_argument('--encoding', default='cp932', help='CSVファイルのエンコーディング（デフォルト: cp932）')
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