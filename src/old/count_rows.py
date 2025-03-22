#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BigQueryテーブルの行数をカウントするスクリプト
テーブル名をコマンドライン引数で受け取り、指定されたテーブルの行数を表示します。
"""

import sys
import argparse
from google.cloud import bigquery
from src.utils.environment import EnvironmentUtils as env

def count_bigquery_rows(table_name):
    """
    指定されたBigQueryテーブルの行数をカウントする
    
    Args:
        table_name (str): カウントするテーブル名
        
    Returns:
        int: テーブルの行数
    """
    # 環境設定の読み込み
    env.load_env()
    
    # BigQuery設定の取得
    bigquery_settings = env.get_bigquery_settings()
    project_id = bigquery_settings["project_id"]
    dataset_id = bigquery_settings["dataset_id"]
    key_path = bigquery_settings["key_path"]
    
    # service account認証情報を使用してクライアントを初期化
    client = bigquery.Client.from_service_account_json(key_path)
    
    # 完全なテーブル名を構築
    full_table_name = f"`{project_id}.{dataset_id}.{table_name}`"
    
    # クエリの構築と実行
    query = f"SELECT COUNT(*) as row_count FROM {full_table_name}"
    
    try:
        # クエリの実行
        query_job = client.query(query)
        result = list(query_job.result())[0]
        
        row_count = result.row_count
        print(f"テーブル '{table_name}' の行数: {row_count}")
        return row_count
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='BigQueryテーブルの行数をカウントします')
    parser.add_argument('table_name', help='カウントするテーブル名')
    
    args = parser.parse_args()
    
    count_bigquery_rows(args.table_name)

if __name__ == '__main__':
    main() 