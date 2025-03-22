#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
シンプルなBigQueryロードテスト
日本語カラム名を含むCSVをBigQueryにロードします
"""

import os
import sys
import csv
import logging
import tempfile
from datetime import datetime
from google.cloud import bigquery  # 明示的にインポート

# プロジェクトルートへのパスを追加
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.utils.environment import EnvironmentUtils
from src.modules.bigquery.bigquery_client import BigQueryClient

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_sample_csv():
    """
    サンプルCSVファイルを作成します
    
    Returns:
        str: 作成したファイルのパス
    """
    # ファイルのフルパスを取得
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sample_test_{timestamp}.csv"
    filepath = os.path.join(tempfile.gettempdir(), filename)
    
    # ヘッダー設定 (日本語カラム名を含む)
    headers = ['ID', '名前', '年齢', '住所', '注文日', 'ステータス']
    
    # サンプルデータ
    data = [
        [1, '山田太郎', 30, '東京都新宿区', '2023-01-01', '完了'],
        [2, '佐藤花子', 25, '大阪府大阪市', '2023-01-02', '処理中'],
        [3, '鈴木一郎', 40, '北海道札幌市', '2023-01-03', '完了'],
        [4, '高橋次郎', 35, '福岡県福岡市', '2023-01-04', '処理中'],
        [5, '田中三郎', 45, '愛知県名古屋市', '2023-01-05', '完了']
    ]
    
    # CSVファイルを作成
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
    
    logger.info(f"サンプルCSVファイルを作成しました: {filepath}")
    return filepath

def load_to_bigquery(local_file):
    """
    ローカルCSVファイルをBigQueryに直接ロードします
    
    Args:
        local_file (str): ローカルCSVファイルのパス
        
    Returns:
        bool: 成功したかどうか
    """
    try:
        # 環境変数をロード
        EnvironmentUtils.load_env()
        
        # BigQueryクライアントを初期化
        client = BigQueryClient()
        
        # データセットとテーブル名を設定
        dataset_id = EnvironmentUtils.get_env_var("BIGQUERY_DATASET")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        table_id = f"test_simple_{timestamp}"
        
        # ローカルCSVファイルからスキーマを推測
        # (ここでは自動検出を使用)
        
        # ファイルを直接ロード
        with open(local_file, 'rb') as file_obj:
            # 直接bigqueryモジュールからLoadJobConfigを使用
            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.CSV,
                skip_leading_rows=1,
                autodetect=True,
            )
            
            # 文字マップV2を直接設定
            job_config._properties["useCharacterMapV2"] = True
            
            table_ref = client.client.dataset(dataset_id).table(table_id)
            job = client.client.load_table_from_file(
                file_obj, 
                table_ref, 
                job_config=job_config
            )
            
        # ジョブの完了を待機
        job.result()
        
        # テーブルの行数を取得
        table = client.client.get_table(table_ref)
        logger.info(f"BigQueryにロードしました: {table.num_rows} 行, テーブル: {dataset_id}.{table_id}")
        
        # クエリでデータを取得
        query = f"SELECT * FROM `{client.project_id}.{dataset_id}.{table_id}` LIMIT 5"
        query_job = client.client.query(query)
        
        rows = list(query_job.result())
        logger.info(f"クエリ結果: {len(rows)} 行取得")
        
        # 各行とカラム名を表示
        logger.info(f"テーブルのスキーマ: {[field.name for field in table.schema]}")
        for row in rows:
            logger.info(f"行データ: {dict(row.items())}")
        
        return True
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return False
    finally:
        # 一時ファイルを削除
        if os.path.exists(local_file):
            os.remove(local_file)
            logger.info(f"一時ファイルを削除しました: {local_file}")

def main():
    """メイン処理"""
    # サンプルCSVを作成
    csv_file = create_sample_csv()
    
    # BigQueryにロード
    if load_to_bigquery(csv_file):
        logger.info("テスト成功！")
        return 0
    else:
        logger.error("テスト失敗")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 