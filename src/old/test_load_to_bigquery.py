#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BigQueryテスト用データロードスクリプト

作成したテストデータをBigQueryにロードしてスキーマの検証を行います。
"""

import os
import sys
import re
import json
from pathlib import Path
from google.cloud import bigquery
from google.oauth2 import service_account

# utils パッケージへのパスを追加
script_dir = Path(__file__).resolve().parent
src_dir = script_dir
if script_dir.name == 'bigquery':
    src_dir = script_dir.parent
if src_dir.name == 'modules':
    src_dir = src_dir.parent
if src_dir.name != 'src':
    src_dir = src_dir / 'src'
sys.path.insert(0, str(src_dir.parent))

# 環境変数ユーティリティのインポート
from src.utils.environment import EnvironmentUtils

def load_test_data_to_bigquery(csv_file_path, schema_file_path):
    """テストデータをBigQueryに読み込みます"""
    # 環境変数を読み込み
    EnvironmentUtils.load_env()
    
    # BigQuery設定を取得
    bq_settings = EnvironmentUtils.get_bigquery_settings()
    project_id = bq_settings['project_id']
    dataset_id = bq_settings['dataset_id']
    key_path = bq_settings['key_path']
    
    # サービスアカウントの認証情報を取得
    credentials = service_account.Credentials.from_service_account_file(
        key_path, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    
    # BigQueryクライアントを初期化
    client = bigquery.Client(credentials=credentials, project=project_id)
    
    # テーブル名を生成（CSVファイル名に基づく）
    csv_filename = Path(csv_file_path).stem
    table_id = f"{project_id}.{dataset_id}.{csv_filename}"
    
    # ジョブ設定
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,  # ヘッダー行をスキップ
        autodetect=False,  # スキーマを自動検出しない
    )
    
    # スキーマが指定されている場合は使用
    if schema_file_path:
        with open(schema_file_path, "r", encoding="utf-8") as f:
            schema_json = json.load(f)
            job_config.schema = [
                bigquery.SchemaField(field["name"], field["type"], field["mode"])
                for field in schema_json
            ]
    
    # ファイルをオープンしてBigQueryにロード
    with open(csv_file_path, "rb") as source_file:
        load_job = client.load_table_from_file(
            source_file, table_id, job_config=job_config
        )
    
    # ジョブの完了を待機
    load_job.result()  # エラーがあれば例外が発生
    
    # テーブル情報を取得して結果を表示
    table = client.get_table(table_id)
    print(f"BigQueryにテーブルをロードしました: {table_id}")
    print(f"テーブル行数: {table.num_rows}行")
    print(f"テーブルスキーマ: {len(table.schema)}列")
    
    return {
        "table_id": table_id,
        "project_id": project_id,
        "dataset_id": dataset_id,
        "row_count": table.num_rows,
        "schema_fields": len(table.schema)
    }

if __name__ == "__main__":
    # コマンドライン引数からCSVファイルとスキーマファイルのパスを取得
    import argparse
    parser = argparse.ArgumentParser(description="テストデータをBigQueryにロードします")
    parser.add_argument("csv_file", help="ロードするCSVファイルのパス")
    parser.add_argument("--schema", help="BigQueryスキーマJSONファイルのパス")
    args = parser.parse_args()
    
    result = load_test_data_to_bigquery(args.csv_file, args.schema)
    print(f"BigQueryへのデータロード完了: {result['row_count']}行のデータ") 