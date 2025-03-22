#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BigQueryスキーマ作成およびテストプログラム

AE_CVresult_schema.csvファイルからBigQueryスキーマを作成し、
サンプルデータを使ってスキーマが正しく機能するかテストします。
"""

import os
import csv
import json
import tempfile
import datetime
import sys
from pathlib import Path
from typing import List, Dict, Any
import re

import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
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

def read_schema_csv(file_path: str) -> List[Dict[str, str]]:
    """スキーマCSVファイルを読み込みます"""
    schema_data = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            schema_data.append({
                "name": row["column_name_mod"],
                "type": row["data_type"],
                "sample": row["sample"]
            })
    
    return schema_data

def convert_to_bigquery_schema(schema_data: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    読み込んだスキーマデータをBigQuery形式に変換します
    CSVの型情報をBigQueryのデータ型に変換する処理を行います
    """
    bigquery_schema = []
    
    for field in schema_data:
        # データ型の変換
        if field["type"] == "str":
            bq_type = "STRING"
        elif field["type"] == "int":
            bq_type = "INTEGER"
        elif field["type"] == "timestamp":
            bq_type = "TIMESTAMP"
        else:
            # 未知の型はSTRINGとして扱う
            bq_type = "STRING"
        
        # フィールド名の特殊文字処理
        field_name = field["name"]
        
        # BigQueryの命名規則に合わせて特殊文字を置換
        # スペース、カッコ、その他の特殊文字をアンダースコアに置換
        # 無効な文字を全てアンダースコアに置換
        field_name = re.sub(r'[^\w]', '_', field_name)
        
        # 先頭が数字の場合、先頭にアンダースコアを追加
        if field_name and field_name[0].isdigit():
            field_name = '_' + field_name
        
        # BigQueryスキーマ定義の形式に変換
        bigquery_schema.append({
            "name": field_name,
            "type": bq_type,
            "mode": "NULLABLE"
        })
    
    return bigquery_schema

def create_sample_data(schema_data: List[Dict[str, str]]) -> Dict[str, Any]:
    """スキーマ情報からサンプルデータを作成します"""
    sample_data = {}
    
    for field in schema_data:
        field_name = field["name"]
        sample_value = field["sample"]
        
        # データ型に基づいてサンプル値を変換
        if field["type"] == "int" and sample_value:
            try:
                sample_data[field_name] = int(sample_value)
            except ValueError:
                sample_data[field_name] = None
        elif field["type"] == "timestamp" and sample_value:
            # Excelシリアル値からタイムスタンプに変換
            try:
                # Excelシリアル値は1900-01-01からの日数
                # ただし、1900年はうるう年ではないが、Excelはそのように扱っているため、調整が必要
                excel_date = float(sample_value)
                
                # 1900年のうるう年バグを調整（1900年3月1日以降の日付）
                if excel_date > 60:
                    excel_date -= 1
                
                # 日付部分と時間部分に分ける
                days = int(excel_date)
                fraction = excel_date - days
                
                # 日付部分を計算（1900年1月1日からの日数）
                date_part = datetime.datetime(1900, 1, 1) + datetime.timedelta(days=days-1)
                
                # 時間部分を計算（1日の割合から秒に変換）
                seconds = int(fraction * 86400)  # 24 * 60 * 60 = 86400 秒/日
                hour = seconds // 3600
                seconds %= 3600
                minute = seconds // 60
                second = seconds % 60
                
                # マイクロ秒部分を計算
                microsecond = int((fraction * 86400 - int(fraction * 86400)) * 1000000)
                
                # 最終的な日時
                excel_datetime = datetime.datetime(
                    date_part.year, date_part.month, date_part.day,
                    hour, minute, second, microsecond
                )
                
                # YYYY/MM/DD HH:MM 形式に変換
                formatted_date = excel_datetime.strftime("%Y/%m/%d %H:%M")
                sample_data[field_name] = formatted_date
            except (ValueError, TypeError) as e:
                print(f"タイムスタンプの変換エラー: {e}, 値: {sample_value}")
                sample_data[field_name] = None
        else:
            sample_data[field_name] = sample_value if sample_value else None
    
    return sample_data

def initialize_bigquery_client(key_path: str):
    """BigQueryクライアントを初期化します"""
    credentials = service_account.Credentials.from_service_account_file(
        key_path, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return bigquery.Client(credentials=credentials, project=credentials.project_id)

def create_or_update_table(client, project_id: str, dataset_id: str, table_name: str, schema: List[Dict[str, str]]):
    """BigQueryのテーブルを作成または更新します"""
    dataset_ref = client.dataset(dataset_id)
    
    # スキーマをBigQuery形式に変換
    table_schema = []
    for field in schema:
        table_schema.append(bigquery.SchemaField(
            field["name"], 
            field["type"],
            mode=field["mode"]
        ))
    
    # テーブル参照を作成
    table_ref = dataset_ref.table(table_name)
    
    try:
        # テーブルが存在するか確認
        client.get_table(table_ref)
        print(f"テーブル {project_id}.{dataset_id}.{table_name} は既に存在します。上書きします。")
        
        # テーブルを削除して再作成
        client.delete_table(table_ref)
        print(f"テーブル {project_id}.{dataset_id}.{table_name} を削除しました。")
    except NotFound:
        print(f"テーブル {project_id}.{dataset_id}.{table_name} は存在しません。新規作成します。")
    
    # テーブルを作成
    table = bigquery.Table(table_ref, schema=table_schema)
    table = client.create_table(table)
    print(f"テーブル {project_id}.{dataset_id}.{table_name} を作成しました。")
    
    return table

def load_sample_data_to_bigquery(client, table_ref, sample_data: Dict[str, Any]):
    """サンプルデータをBigQueryにロードします"""
    # サンプルデータをJSONL形式で一時ファイルに保存
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".jsonl", delete=False) as temp_file:
        json.dump(sample_data, temp_file)
        temp_file_path = temp_file.name
    
    # ロードジョブの設定
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema_update_options=[
            bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION,
            bigquery.SchemaUpdateOption.ALLOW_FIELD_RELAXATION,
        ],
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    
    # データをロード
    with open(temp_file_path, "rb") as source_file:
        load_job = client.load_table_from_file(
            source_file, table_ref, job_config=job_config
        )
    
    # ジョブの完了を待機
    load_job.result()
    
    # 一時ファイルを削除
    os.unlink(temp_file_path)
    
    # ロード結果を取得
    destination_table = client.get_table(table_ref)
    print(f"テーブル {destination_table.full_table_id} にロードしました。行数: {destination_table.num_rows}")
    
    return destination_table

def test_bigquery_schema():
    """BigQueryスキーマをテストします"""
    # 環境変数を読み込み
    EnvironmentUtils.load_env()
    
    # BigQuery設定を取得
    bq_settings = EnvironmentUtils.get_bigquery_settings()
    project_id = bq_settings["project_id"]
    dataset_id = bq_settings["dataset_id"]
    key_path = bq_settings["key_path"]
    
    print(f"プロジェクトID: {project_id}")
    print(f"データセットID: {dataset_id}")
    print(f"サービスアカウントキーファイル: {key_path}")
    
    # スキーマCSVファイルのパス
    schema_csv_path = "data/SE_SSresult/AE_CVresult_schema.csv"
    
    # スキーマCSVファイルを読み込み
    print(f"スキーマCSVファイル {schema_csv_path} を読み込みます...")
    schema_data = read_schema_csv(schema_csv_path)
    print(f"スキーマ定義: {len(schema_data)}フィールド")
    
    # BigQueryスキーマ形式に変換
    bq_schema = convert_to_bigquery_schema(schema_data)
    print("BigQueryスキーマに変換しました。")
    
    # サンプルデータを作成
    sample_data = create_sample_data(schema_data)
    print("サンプルデータを作成しました。")
    
    # BigQueryクライアントを初期化
    client = initialize_bigquery_client(key_path)
    print("BigQueryクライアントを初期化しました。")
    
    # テーブル名を設定
    table_name = "ae_cvresult_test"
    
    # テーブルを作成または更新
    table = create_or_update_table(
        client, 
        project_id, 
        dataset_id, 
        table_name, 
        bq_schema
    )
    
    # サンプルデータをロード
    print("サンプルデータをBigQueryにロードします...")
    table_ref = client.dataset(dataset_id).table(table_name)
    destination_table = load_sample_data_to_bigquery(client, table_ref, sample_data)
    
    # ロードされたデータを確認
    print("ロードされたデータを確認します...")
    query = f"""
    SELECT * FROM `{project_id}.{dataset_id}.{table_name}`
    LIMIT 10
    """
    query_job = client.query(query)
    rows = query_job.result()
    
    # データフレームに変換して表示
    df = rows.to_dataframe()
    if not df.empty:
        print("\nロードされたデータのサンプル:")
        print(df.head())
        print("\nデータ型情報:")
        print(df.dtypes)
        print("\nロードテストは成功しました！")
    else:
        print("データが正しくロードされていないようです。詳細を確認してください。")

    # スキーマをJSONファイルとして保存
    schema_json_path = f"data/SE_SSresult/{table_name}_schema.json"
    with open(schema_json_path, "w", encoding="utf-8") as f:
        json.dump(bq_schema, f, ensure_ascii=False, indent=2)
    print(f"BigQueryスキーマをJSONファイルに保存しました: {schema_json_path}")
    
    return {
        "schema": bq_schema,
        "sample_data": sample_data,
        "table_name": table_name,
        "project_id": project_id,
        "dataset_id": dataset_id,
    }

if __name__ == "__main__":
    try:
        test_result = test_bigquery_schema()
        print("BigQueryスキーマのテストが完了しました。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc() 