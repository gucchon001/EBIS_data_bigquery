#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BigQueryのAE_CVresultテーブルにテストデータを挿入するスクリプト
テーブルの91列すべてに対応したテストデータを作成します
"""

import os
import pandas as pd
from datetime import datetime
from google.cloud import bigquery
from src.utils.environment import EnvironmentUtils as env

def insert_test_data_to_bigquery():
    """
    AE_CVresultテーブルにテストデータを挿入する
    """
    # 環境設定の読み込み
    env.load_env()
    
    # BigQuery設定の取得
    bigquery_settings = env.get_bigquery_settings()
    project_id = bigquery_settings["project_id"]
    dataset_id = bigquery_settings["dataset_id"]
    key_path = bigquery_settings["key_path"]
    
    # テーブル名の設定
    table_name = "AE_CVresult"
    full_table_name = f"{project_id}.{dataset_id}.{table_name}"
    
    # テストデータの基本情報（5行分）
    row_count = 5
    
    # BigQueryクライアントの初期化
    client = bigquery.Client.from_service_account_json(key_path)
    
    # テーブルのスキーマを取得
    try:
        table = client.get_table(full_table_name)
        schema = table.schema
        print(f"テーブル '{table_name}' のスキーマを取得しました（{len(schema)}列）")
        
        # スキーマから列名のリストを取得
        schema_field_names = [field.name for field in schema]
        schema_field_types = {field.name: field.field_type for field in schema}
        
        # 全ての列に対応するテストデータを作成
        test_data = {}
        
        # 基本データを作成
        for i, field_name in enumerate(schema_field_names):
            field_type = schema_field_types[field_name]
            
            if field_name == "CV名":
                test_data[field_name] = ["応募完了"] * row_count
            
            elif field_name == "CV時間":
                # TIMESTAMP型のデータ
                timestamps = [
                    "2023-04-01 10:30:00",
                    "2023-04-01 11:45:00",
                    "2023-04-02 09:15:00",
                    "2023-04-02 14:20:00",
                    "2023-04-03 16:05:00"
                ]
                test_data[field_name] = timestamps[:row_count]
            
            elif field_name == "ユーザーID":
                test_data[field_name] = [f"test{i+1:03d}" for i in range(row_count)]
            
            elif field_name == "ユーザー名":
                names = ["テスト太郎", "テスト花子", "テスト次郎", "テスト直子", "テスト三郎"]
                test_data[field_name] = names[:row_count]
            
            elif field_name == "応募ID":
                # INTEGER型のデータ
                test_data[field_name] = [i+1001 for i in range(row_count)]
            
            elif field_name == "項目1":
                schools = ["校舎A", "校舎B", "校舎C", "校舎D", "校舎E"]
                test_data[field_name] = schools[:row_count]
            
            elif field_name == "項目2":
                statuses = ["大学生", "社会人", "大学生", "高校生", "社会人"]
                test_data[field_name] = statuses[:row_count]
            
            elif field_name == "項目3":
                prefectures = ["東京都", "神奈川県", "埼玉県", "千葉県", "茨城県"]
                test_data[field_name] = prefectures[:row_count]
            
            elif field_name == "項目4":
                # DATE型のデータ
                dates = [
                    "2000-01-01",
                    "1998-05-10",
                    "2001-08-15",
                    "2005-03-20",
                    "1995-11-05"
                ]
                test_data[field_name] = dates[:row_count]
            
            elif field_name == "項目5":
                employment_types = ["アルバイト", "正社員", "契約社員", "学生", "パート"]
                test_data[field_name] = employment_types[:row_count]
            
            elif field_name == "デバイス":
                devices = ["PC", "スマートフォン", "PC", "スマートフォン", "タブレット"]
                test_data[field_name] = devices[:row_count]
            
            elif field_name == "潜伏期間":
                periods = ["1時間30分", "2日5時間", "15分", "3時間45分", "1日2時間30分"]
                test_data[field_name] = periods[:row_count]
            
            elif field_name == "潜伏期間_秒" or field_name == "接触回数":
                # INTEGER型のデータ
                if field_name == "潜伏期間_秒":
                    values = [5400, 183600, 900, 13500, 95400]  # 秒数
                else:
                    values = [3, 5, 2, 4, 7]  # 接触回数
                test_data[field_name] = values[:row_count]
            
            elif "発生日時" in field_name:
                # TIMESTAMP型のデータ（各効果の発生日時）
                if "直接効果" in field_name:
                    timestamps = [
                        "2023-04-01 10:00:00",
                        "2023-03-30 08:45:00",
                        "2023-04-02 09:00:00",
                        "2023-04-02 13:45:00",
                        "2023-04-03 15:30:00"
                    ]
                    test_data[field_name] = timestamps[:row_count]
                elif "初回接触" in field_name:
                    timestamps = [
                        "2023-03-31 09:00:00",
                        "2023-03-29 10:45:00",
                        "2023-04-02 08:30:00",
                        "2023-04-01 09:45:00",
                        "2023-04-02 14:30:00"
                    ]
                    test_data[field_name] = timestamps[:row_count]
                else:
                    # 間接効果の場合、一部の行のみデータを設定（他はNULL）
                    effect_num = int(field_name.split("_")[0].replace("間接効果", ""))
                    if effect_num <= 3:  # 最初の3つの効果のみデータを入れる
                        timestamps = [
                            "2023-03-31 15:00:00" if i % 2 == 0 else None
                            for i in range(row_count)
                        ]
                        test_data[field_name] = timestamps
                    else:
                        # それ以降はNULLのみ
                        test_data[field_name] = [None] * row_count
            
            elif "チャネル種別" in field_name:
                # チャネル種別データ
                if "直接効果" in field_name or "初回接触" in field_name:
                    channels = ["自然検索", "有料検索", "Webサイト", "SNS", "メール"]
                    test_data[field_name] = channels[:row_count]
                else:
                    effect_num = int(field_name.split("_")[0].replace("間接効果", ""))
                    if effect_num <= 3:
                        channels = [
                            "リファラル" if i % 2 == 0 else None
                            for i in range(row_count)
                        ]
                        test_data[field_name] = channels
                    else:
                        test_data[field_name] = [None] * row_count
            
            elif "カテゴリ" in field_name:
                # カテゴリデータ
                if "直接効果" in field_name:
                    categories = ["Google", "Yahoo!", "他サイト", "Twitter", "メルマガ"]
                    test_data[field_name] = categories[:row_count]
                elif "初回接触" in field_name:
                    categories = ["Yahoo!", "Google", "他サイト", "Instagram", "メルマガ"]
                    test_data[field_name] = categories[:row_count]
                else:
                    effect_num = int(field_name.split("_")[0].replace("間接効果", ""))
                    if effect_num <= 3:
                        categories = [
                            "友人紹介" if i % 2 == 0 else None
                            for i in range(row_count)
                        ]
                        test_data[field_name] = categories
                    else:
                        test_data[field_name] = [None] * row_count
            
            elif "広告グループ1" in field_name or "広告グループ2" in field_name:
                # 広告グループデータ
                if "直接効果" in field_name:
                    values = ["グループA", "グループB", "グループC", "グループD", "グループE"]
                    test_data[field_name] = values[:row_count]
                elif "初回接触" in field_name:
                    values = ["グループF", "グループG", "グループH", "グループI", "グループJ"]
                    test_data[field_name] = values[:row_count]
                else:
                    effect_num = int(field_name.split("_")[0].replace("間接効果", ""))
                    if effect_num <= 3:
                        values = [
                            "グループR" if i % 2 == 0 else None
                            for i in range(row_count)
                        ]
                        test_data[field_name] = values
                    else:
                        test_data[field_name] = [None] * row_count
            
            elif "広告ID" in field_name:
                # 広告IDデータ
                if "直接効果" in field_name:
                    ids = ["AD001", "AD002", "AD003", "AD004", "AD005"]
                    test_data[field_name] = ids[:row_count]
                elif "初回接触" in field_name:
                    ids = ["AD006", "AD007", "AD008", "AD009", "AD010"]
                    test_data[field_name] = ids[:row_count]
                else:
                    effect_num = int(field_name.split("_")[0].replace("間接効果", ""))
                    if effect_num <= 3:
                        ids = [
                            "ADR01" if i % 2 == 0 else None
                            for i in range(row_count)
                        ]
                        test_data[field_name] = ids
                    else:
                        test_data[field_name] = [None] * row_count
            
            elif "名称" in field_name:
                # 名称データ
                if "直接効果" in field_name:
                    names = ["検索広告A", "検索広告B", "バナー広告A", "Twitter広告", "メールマガジンA"]
                    test_data[field_name] = names[:row_count]
                elif "初回接触" in field_name:
                    names = ["検索広告C", "検索広告D", "バナー広告B", "Instagram広告", "メールマガジンB"]
                    test_data[field_name] = names[:row_count]
                else:
                    effect_num = int(field_name.split("_")[0].replace("間接効果", ""))
                    if effect_num <= 3:
                        names = [
                            "友人紹介キャンペーン" if i % 2 == 0 else None
                            for i in range(row_count)
                        ]
                        test_data[field_name] = names
                    else:
                        test_data[field_name] = [None] * row_count
            
            else:
                # その他の列はNULL値を設定
                test_data[field_name] = [None] * row_count
        
        # DataFrameの作成
        df = pd.DataFrame(test_data)
        print(f"テストデータのDataFrameを作成しました（{len(df)}行 x {len(df.columns)}列）")
        
        # 一時CSVファイルに保存
        temp_csv_path = "temp_test_data.csv"
        df.to_csv(temp_csv_path, index=False)
        print(f"一時ファイル '{temp_csv_path}' にデータを保存しました")
        
        # テーブルにデータをロード（上書きモード）
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,  # ヘッダー行をスキップ
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE  # テーブルを上書き
        )
        
        with open(temp_csv_path, "rb") as source_file:
            job = client.load_table_from_file(
                source_file, full_table_name, job_config=job_config
            )
        
        # ジョブの完了を待機
        job.result()
        
        # 一時ファイルを削除
        os.remove(temp_csv_path)
        print(f"一時ファイル '{temp_csv_path}' を削除しました")
        
        # 結果の表示
        print(f"テーブル '{table_name}' に {len(df)} 行のテストデータを挿入しました")
        
        # 挿入したデータを確認
        query = f"SELECT * FROM `{full_table_name}` LIMIT 2"
        query_job = client.query(query)
        results = query_job.result()
        
        rows = list(results)
        print(f"\n挿入されたデータ（表示: {len(rows)}行）:")
        for i, row in enumerate(rows, 1):
            print(f"\n--- 行 {i} ---")
            for key, value in row.items():
                print(f"{key}: {value}")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    insert_test_data_to_bigquery() 