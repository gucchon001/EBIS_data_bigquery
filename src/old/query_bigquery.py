#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BigQueryからデータを取得するスクリプト
テーブル名をコマンドライン引数で受け取り、指定されたテーブルから先頭5行を取得して表示します。
"""

import sys
import argparse
from google.cloud import bigquery
from src.utils.environment import EnvironmentUtils as env

def query_bigquery_table(table_name, limit=5):
    """
    指定されたBigQueryテーブルからデータを取得する
    
    Args:
        table_name (str): クエリするテーブル名
        limit (int): 取得する行数
        
    Returns:
        None: 結果は標準出力に表示されます
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
    full_table_name = f"{project_id}.{dataset_id}.{table_name}"
    
    # クエリの構築
    query = f'SELECT * FROM `{full_table_name}` LIMIT {limit}'
    print(f"実行クエリ: {query}")
    
    try:
        # クエリの実行
        query_job = client.query(query)
        results = query_job.result()
        
        # 結果の取得と表示
        rows = list(results)
        
        if not rows:
            print(f"テーブル '{table_name}' にはデータがありません。")
            return
        
        # カラム名の表示
        print("\nカラム名:")
        for field in results.schema:
            print(f"- {field.name} ({field.field_type})")
        
        # データ行の表示
        print(f"\nデータ ({len(rows)}行):")
        for i, row in enumerate(rows, 1):
            print(f"\n--- 行 {i} ---")
            for key, value in row.items():
                print(f"{key}: {value}")
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")

def main():
    parser = argparse.ArgumentParser(description='BigQueryテーブルからデータを取得して表示します')
    parser.add_argument('table_name', help='クエリするテーブル名')
    parser.add_argument('--limit', type=int, default=5, help='取得する行数 (デフォルト: 5)')
    
    args = parser.parse_args()
    
    query_bigquery_table(args.table_name, args.limit)

if __name__ == '__main__':
    main() 