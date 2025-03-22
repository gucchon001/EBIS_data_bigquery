#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
JSONファイルからBigQueryにデータをロードするスクリプト
引数としてJSONファイルのパスとテーブル名を受け取り、指定されたBigQueryテーブルにデータをロードします。
"""

import os
import sys
import argparse
import logging
import pandas as pd
import json
import re
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from src.utils.environment import EnvironmentUtils as env
from dotenv import load_dotenv

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

# カラム名を正規化する関数
def normalize_column_name(name):
    """
    BigQueryのカラム名の要件に合わせてカラム名を正規化する関数
    
    Parameters:
    -----------
    name : str
        正規化するカラム名
        
    Returns:
    --------
    str
        正規化されたカラム名
    """
    # カッコや特殊文字をアンダースコアに置換
    name = re.sub(r'[^\w\s]', '_', name)
    # 連続するアンダースコアを1つに
    name = re.sub(r'_+', '_', name)
    # 先頭と末尾のアンダースコアを削除
    name = name.strip('_')
    # 空白文字をアンダースコアに置換
    name = re.sub(r'\s+', '_', name)
    # 先頭が数字の場合、先頭に'f_'を追加
    if name and name[0].isdigit():
        name = 'f_' + name
    # 空文字列の場合はunknownとする
    if not name:
        name = 'unknown'
    return name

def load_json_to_bigquery(json_file_path, table_name, write_disposition='WRITE_APPEND'):
    """
    JSONファイルからBigQueryにデータをロードする
    
    Args:
        json_file_path (str): ロードするJSONファイルのパス
        table_name (str): データをロードするBigQueryテーブル名
        write_disposition (str): 書き込み方式 (WRITE_APPEND, WRITE_TRUNCATE, WRITE_EMPTY)
        
    Returns:
        bool: 処理が成功した場合はTrue、それ以外はFalse
    """
    # 環境変数とBigQuery設定の読み込み
    env.load_env()
    bigquery_settings = env.get_bigquery_settings()
    
    # BigQueryのクライアントを初期化
    client = bigquery.Client.from_service_account_json(bigquery_settings["key_path"])
    
    # プロジェクトIDとデータセットIDを取得
    project_id = bigquery_settings["project_id"]
    dataset_id = bigquery_settings["dataset_id"]
    
    # 完全なテーブル参照を作成
    table_ref = f"{project_id}.{dataset_id}.{table_name}"
    
    try:
        # JSONファイルを読み込む
        logger.info(f"JSONファイル '{json_file_path}' を読み込んでいます...")
        
        # JSONファイルをパンダスで読み込む（ndjson形式の場合は lines=True を指定）
        try:
            df = pd.read_json(json_file_path, lines=True, encoding='utf-8')
            logger.info(f"JSONファイルを正常に読み込みました。行数: {len(df)}")
        except Exception as e:
            logger.error(f"JSONファイルの読み込みに失敗しました: {str(e)}")
            # 通常のJSONとして読み込み試行
            try:
                df = pd.read_json(json_file_path, encoding='utf-8')
                logger.info(f"通常のJSONとして読み込みました。行数: {len(df)}")
            except Exception as e2:
                logger.error(f"通常のJSONとしての読み込みにも失敗しました: {str(e2)}")
                return False
        
        # データフレームの最初の数行を表示
        logger.info("データサンプル:")
        logger.info(df.head())
        
        # カラム名を正規化
        original_columns = df.columns.tolist()
        normalized_columns = {col: normalize_column_name(col) for col in original_columns}
        df = df.rename(columns=normalized_columns)
        
        # 正規化前後のカラム名のマッピングを表示
        for orig, norm in normalized_columns.items():
            if orig != norm:
                logger.info(f"カラム名を正規化: '{orig}' -> '{norm}'")
        
        # 一時的なJSONファイルに保存
        temp_json_file = "temp_json_data.json"
        df.to_json(temp_json_file, orient='records', lines=True, force_ascii=False)
        logger.info(f"一時ファイル {temp_json_file} にデータを保存しました。")
        
        # BigQueryのロード設定
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            autodetect=True,  # スキーマを自動検出（必要に応じてカスタムスキーマを指定可能）
        )
        
        # 書き込み方式の設定
        if write_disposition == 'WRITE_TRUNCATE':
            job_config.write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE
        elif write_disposition == 'WRITE_EMPTY':
            job_config.write_disposition = bigquery.WriteDisposition.WRITE_EMPTY
        else:
            job_config.write_disposition = bigquery.WriteDisposition.WRITE_APPEND
            
        # スキーマを自動検出せずに、既存のテーブルスキーマを使用するかどうかを確認
        try:
            table = client.get_table(table_ref)
            logger.info(f"既存のテーブル '{table_name}' のスキーマを使用します。")
            job_config.schema = table.schema
            job_config.autodetect = False
        except NotFound:
            logger.info(f"テーブル '{table_name}' が存在しないため、スキーマを自動検出します。")
            job_config.autodetect = True
        
        # BigQueryにデータをロード
        with open(temp_json_file, "rb") as source_file:
            job = client.load_table_from_file(
                source_file, 
                table_ref, 
                job_config=job_config
            )
        
        # ジョブの完了を待つ
        job.result()
        
        # ロード結果を確認
        if job.errors:
            logger.error(f"データロード中にエラーが発生しました: {job.errors}")
            return False
        
        logger.info(f"BigQueryテーブル '{table_name}' に {job.output_rows} 行のデータをロードしました。")
        
        # 一時ファイルの削除
        if os.path.exists(temp_json_file):
            os.remove(temp_json_file)
            logger.info(f"一時ファイル '{temp_json_file}' を削除しました。")
        
        return True
    
    except Exception as e:
        logger.error(f"データロード中に例外が発生しました: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='JSONファイルからBigQueryにデータをロードします')
    parser.add_argument('json_file', help='ロードするJSONファイルのパス')
    parser.add_argument('table_name', help='データをロードするBigQueryテーブル名')
    parser.add_argument('--write-disposition', choices=['WRITE_APPEND', 'WRITE_TRUNCATE', 'WRITE_EMPTY'], 
                        default='WRITE_APPEND', help='書き込み方式 (デフォルト: WRITE_APPEND)')
    
    args = parser.parse_args()
    
    # 引数の検証
    if not os.path.exists(args.json_file):
        logger.error(f"指定されたJSONファイル '{args.json_file}' が存在しません。")
        sys.exit(1)
    
    # データをロード
    success = load_json_to_bigquery(args.json_file, args.table_name, args.write_disposition)
    
    # 終了ステータスの設定
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main() 