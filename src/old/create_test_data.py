#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BigQueryテスト用サンプルデータ作成スクリプト

AE_CVresult_schema.csvをもとにサンプルデータを作成し、
BigQueryスキーマテスト用のCSVファイルを生成します。
"""

import os
import csv
import json
import datetime
import random
import sys
import re
from pathlib import Path

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

def create_test_data():
    """テスト用サンプルデータを作成します"""
    # 環境変数を読み込み
    EnvironmentUtils.load_env()
    
    # スキーマCSVファイルのパス
    schema_csv_path = "data/SE_SSresult/AE_CVresult_schema.csv"
    
    # 出力ディレクトリの作成
    output_dir = Path("data/SE_SSresult/test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 現在時刻を含むファイル名を生成
    now = datetime.datetime.now()
    date_str = now.strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"test_data_{date_str}.csv"
    
    # スキーマCSVファイルを読み込み
    schema_data = []
    with open(schema_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            schema_data.append(row)
    
    # column_name_modをヘッダーとして使用
    header = [row["column_name_mod"] for row in schema_data]
    
    # サンプルデータを生成
    sample_rows = []
    
    # 元のサンプルデータ行を追加
    sample_row = [row["sample"] for row in schema_data]
    sample_rows.append(sample_row)
    
    # 追加のサンプルデータ行を生成（5行）
    for i in range(5):
        row = []
        for schema_item in schema_data:
            data_type = schema_item["data_type"]
            sample = schema_item["sample"]
            
            # データ型に基づいてランダム値を生成
            if not sample:
                row.append("")  # 空の値はそのまま空で
            elif data_type == "int":
                try:
                    base_value = int(sample)
                    # ±20%のランダム値
                    value = base_value + int(base_value * random.uniform(-0.2, 0.2))
                    row.append(str(value))
                except ValueError:
                    row.append(sample)  # 変換できない場合はそのまま
            elif data_type == "timestamp":
                try:
                    # 元のExcelシリアル値を少しずらす
                    base_value = float(sample)
                    # ±0.01日（約15分）のランダム値
                    value = base_value + random.uniform(-0.01, 0.01)
                    
                    # 日時に変換してCSV用にフォーマット
                    dt = excel_to_datetime(value)
                    # YYYY/MM/DD HH:MM 形式で出力
                    row.append(dt.strftime("%Y/%m/%d %H:%M"))
                except ValueError:
                    row.append(sample)  # 変換できない場合はそのまま
            elif "ユーザーID" in schema_item["column_name"]:
                # ユーザーIDは新しいランダムな値
                random_suffix = ''.join([str(random.randint(0, 9)) for _ in range(5)])
                row.append(f"v{random_suffix}.{int(datetime.datetime.now().timestamp())}")
            else:
                # 文字列はそのまま
                row.append(sample)
        
        sample_rows.append(row)
    
    # CSVファイルに書き込み
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in sample_rows:
            writer.writerow(row)
    
    print(f"テスト用CSVファイルを保存しました: {output_file}")
    
    # BigQueryスキーマを生成してJSONファイルに保存
    bq_schema = []
    for item in schema_data:
        field_name = item["column_name_mod"]
        
        # BigQueryの命名規則に合わせて特殊文字を置換
        # スペース、カッコ、その他の特殊文字をアンダースコアに置換
        field_name = re.sub(r'[^\w]', '_', field_name)
        
        # 先頭が数字の場合、先頭にアンダースコアを追加
        if field_name and field_name[0].isdigit():
            field_name = '_' + field_name
        
        # データ型の変換
        if item["data_type"] == "str":
            bq_type = "STRING"
        elif item["data_type"] == "int":
            bq_type = "INTEGER"
        elif item["data_type"] == "timestamp":
            bq_type = "TIMESTAMP"
        else:
            # 未知の型はSTRINGとして扱う
            bq_type = "STRING"
        
        bq_schema.append({
            "name": field_name,
            "type": bq_type,
            "mode": "NULLABLE"
        })
    
    # スキーマをJSONファイルとして保存
    schema_json_path = output_dir / f"test_schema_{date_str}.json"
    with open(schema_json_path, "w", encoding="utf-8") as f:
        json.dump(bq_schema, f, ensure_ascii=False, indent=2)
    
    print(f"BigQueryスキーマをJSONファイルに保存しました: {schema_json_path}")
    
    # 設定情報を表示
    bq_settings = EnvironmentUtils.get_bigquery_settings()
    print(f"BigQuery設定:")
    print(f"- プロジェクトID: {bq_settings['project_id']}")
    print(f"- データセットID: {bq_settings['dataset_id']}")
    
    return {
        "csv_file": str(output_file),
        "schema_file": str(schema_json_path),
        "row_count": len(sample_rows),
        "project_id": bq_settings["project_id"],
        "dataset_id": bq_settings["dataset_id"]
    }

# ユーティリティ関数を追加
def excel_to_datetime(excel_date):
    """
    Excelのシリアル値を日時に変換する関数
    
    Args:
        excel_date: Excelシリアル値
        
    Returns:
        datetime: 変換された日時オブジェクト
    """
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
    return datetime.datetime(
        date_part.year, date_part.month, date_part.day,
        hour, minute, second, microsecond
    )

if __name__ == "__main__":
    result = create_test_data()
    print(f"テストデータ作成完了: {result['row_count']}行のデータ") 