#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BigQueryテーブルのスキーマを取得するスクリプト
"""

import argparse
from google.cloud import bigquery
from src.utils.environment import EnvironmentUtils as env

def get_table_schema(table_name):
    """
    指定されたBigQueryテーブルのスキーマを取得して表示する
    
    Args:
        table_name (str): スキーマを取得するテーブル名
    """
    # 環境設定の読み込み
    env.load_env()
    
    # BigQuery設定の取得
    bigquery_settings = env.get_bigquery_settings()
    project_id = bigquery_settings["project_id"]
    dataset_id = bigquery_settings["dataset_id"]
    key_path = bigquery_settings["key_path"]
    
    # 完全なテーブル名を構築
    full_table_name = f"{project_id}.{dataset_id}.{table_name}"
    
    try:
        # BigQueryクライアントの初期化
        client = bigquery.Client.from_service_account_json(key_path)
        
        # テーブルのスキーマを取得
        table = client.get_table(full_table_name)
        schema = table.schema
        
        print(f"テーブル '{table_name}' のスキーマ（{len(schema)}列）:\n")
        print("列番号, 列名, データ型, モード")
        print("-" * 60)
        
        for i, field in enumerate(schema, 1):
            print(f"{i:3d}, {field.name}, {field.field_type}, {field.mode}")
        
        # スキーマをCSV形式で出力（他のスクリプトで利用しやすいように）
        print("\nCSV形式でのスキーマ（コピー＆ペースト用）:")
        schema_csv = ",".join([field.name for field in schema])
        print(schema_csv)
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")

def main():
    parser = argparse.ArgumentParser(description='BigQueryテーブルのスキーマを取得して表示します')
    parser.add_argument('table_name', help='スキーマを取得するテーブル名')
    
    args = parser.parse_args()
    
    get_table_schema(args.table_name)

if __name__ == '__main__':
    main() 