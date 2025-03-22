#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BigQueryのテーブル一覧を表示するスクリプト
"""

from google.cloud import bigquery
from src.utils.environment import EnvironmentUtils as env

def list_bigquery_tables():
    """
    BigQueryのテーブル一覧を取得して表示する
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
    
    # テーブル一覧を取得
    dataset_ref = f"{project_id}.{dataset_id}"
    print(f"データセット: {dataset_ref}")
    
    try:
        tables = list(client.list_tables(dataset_ref))
        
        if not tables:
            print("データセット内にテーブルが存在しません。")
            return
        
        print(f"\nテーブル一覧（{len(tables)}件）:")
        for i, table in enumerate(tables, 1):
            table_ref = f"{project_id}.{dataset_id}.{table.table_id}"
            table_obj = client.get_table(table_ref)
            row_count = table_obj.num_rows
            print(f"{i}. {table.table_id} (行数: {row_count})")
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == '__main__':
    list_bigquery_tables() 