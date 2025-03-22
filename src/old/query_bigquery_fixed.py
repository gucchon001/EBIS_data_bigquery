#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BigQueryテーブルをクエリするためのスクリプト。
"""

import argparse
import logging
import os
from dotenv import load_dotenv
from google.cloud import bigquery

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_env_vars(env_file='config/secrets.env'):
    """環境変数ファイルを読み込む"""
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"環境変数ファイル {env_file} を読み込みました。")
    else:
        print(f"警告: 環境変数ファイル {env_file} が見つかりません。")

def query_bigquery(query):
    """
    BigQueryにSQLクエリを実行する
    
    Args:
        query (str): 実行するSQLクエリ
    
    Returns:
        list: クエリ結果の行リスト
    """
    try:
        # BigQueryクライアントを初期化
        client = bigquery.Client()
        
        # クエリを実行
        print(f"実行クエリ: {query}")
        query_job = client.query(query)
        
        # 結果を取得
        results = query_job.result()
        
        return results
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return None

def display_results(results):
    """
    クエリ結果を表示する
    
    Args:
        results: BigQueryクエリ結果
    """
    if not results:
        print("クエリ結果が空です。")
        return
    
    # カラム名の表示
    schema = results.schema
    print("\nカラム名:")
    for field in schema:
        print(f"- {field.name} ({field.field_type})")
    
    # データ行の表示
    rows = list(results)
    print(f"\nデータ ({len(rows)}行):\n")
    
    # 各行を表示
    for i, row in enumerate(rows):
        print(f"--- 行 {i + 1} ---")
        for field in schema:
            field_name = field.name
            value = row[field_name]
            print(f"{field_name}: {value}")
        print()

def main():
    parser = argparse.ArgumentParser(description='BigQueryテーブルをクエリする')
    parser.add_argument('table_name', help='クエリするテーブル名')
    parser.add_argument('--limit', type=int, default=5, help='返す行数の上限（デフォルト: 5）')
    parser.add_argument('--where', help='WHERE句を追加（例: "column = value"）')
    parser.add_argument('--env-file', default='config/secrets.env', help='環境変数ファイルのパス（デフォルト: config/secrets.env）')
    
    args = parser.parse_args()
    
    # 環境変数を読み込む
    load_env_vars(args.env_file)
    
    # クエリを構築
    query = f"SELECT * FROM `{args.table_name}`"
    
    if args.where:
        query += f" WHERE {args.where}"
    
    if args.limit:
        query += f" LIMIT {args.limit}"
    
    # クエリを実行
    results = query_bigquery(query)
    
    if results:
        display_results(results)

if __name__ == '__main__':
    main() 