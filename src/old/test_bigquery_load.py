#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BigQueryへのデータロードをテストするスクリプト
日本語カラム名を含むCSVを作成し、GCSにアップロードしてからBigQueryにロードします
"""

import os
import sys
import csv
import logging
import argparse
import tempfile
from datetime import datetime

try:
    # pandas, pyarrowのインポート (オプション)
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    PARQUET_SUPPORT = True
except ImportError:
    PARQUET_SUPPORT = False
    logging.warning("pandas/pyarrowがインストールされていないため、Parquetテストはスキップされます")

# プロジェクトルートへのパスを追加
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.utils.environment import EnvironmentUtils
from src.modules.bigquery.bigquery_client import BigQueryClient
from src.gcs_uploader import GCSUploader

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_sample_csv(filename, japanese_headers=True):
    """
    サンプルCSVファイルを作成します
    
    Args:
        filename (str): 作成するファイル名
        japanese_headers (bool): 日本語ヘッダーを使用するかどうか
        
    Returns:
        str: 作成したファイルのパス
    """
    # ファイルのフルパスを取得
    if not os.path.isabs(filename):
        filepath = os.path.join(tempfile.gettempdir(), filename)
    else:
        filepath = filename
    
    # ヘッダー設定
    if japanese_headers:
        headers = ['ID', '名前', '年齢', '住所', '注文日', 'ステータス']
    else:
        headers = ['ID', 'Name', 'Age', 'Address', 'OrderDate', 'Status']
    
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

def convert_csv_to_parquet(csv_file, parquet_file=None):
    """
    CSVファイルをParquetファイルに変換します
    
    Args:
        csv_file (str): 入力CSVファイルのパス
        parquet_file (str, optional): 出力Parquetファイルのパス。Noneの場合は拡張子を変更
        
    Returns:
        str: 変換したParquetファイルのパス
    """
    if not PARQUET_SUPPORT:
        raise ImportError("pandas/pyarrowがインストールされていません。pip install pandas pyarrow を実行してください")
    
    # 出力ファイル名が指定されていない場合は拡張子を変更
    if parquet_file is None:
        parquet_file = os.path.splitext(csv_file)[0] + '.parquet'
    
    # CSVファイルを読み込み
    df = pd.read_csv(csv_file)
    
    # Parquetファイルに変換
    table = pa.Table.from_pandas(df)
    pq.write_table(table, parquet_file)
    
    logger.info(f"CSVファイルをParquetに変換しました: {csv_file} -> {parquet_file}")
    return parquet_file

def upload_to_gcs(local_file, gcs_bucket, gcs_path):
    """
    ファイルをGCSにアップロードします
    
    Args:
        local_file (str): ローカルファイルのパス
        gcs_bucket (str): GCSバケット名
        gcs_path (str): GCS内のパス
        
    Returns:
        str: アップロードしたGCSのURI
    """
    uploader = GCSUploader()
    gcs_uri = uploader.upload_file(local_file, gcs_bucket, gcs_path)
    logger.info(f"ファイルをGCSにアップロードしました: {gcs_uri}")
    return gcs_uri

def load_to_bigquery(gcs_uri, table_name, dataset_id=None, write_disposition="WRITE_TRUNCATE"):
    """
    GCSからBigQueryにデータをロードします
    
    Args:
        gcs_uri (str): GCSファイルのURI
        table_name (str): BigQueryテーブル名
        dataset_id (str, optional): BigQueryデータセットID
        write_disposition (str, optional): 書き込み設定
        
    Returns:
        bool: 成功したかどうか
    """
    try:
        client = BigQueryClient()
        load_job = client.load_from_gcs(
            source_uri=gcs_uri,
            table_id=table_name,
            dataset_id=dataset_id,
            write_disposition=write_disposition
        )
        
        # テーブルの行数を取得
        table_ref = client.client.dataset(dataset_id or client.dataset_id).table(table_name)
        table = client.client.get_table(table_ref)
        logger.info(f"BigQueryにロードしました: {table.num_rows} 行, テーブル: {dataset_id or client.dataset_id}.{table_name}")
        
        # クエリでデータを取得
        query_job = client.query_table(table_name, limit=10, dataset_id=dataset_id)
        rows = list(query_job.result())
        logger.info(f"クエリ結果: {len(rows)} 行取得")
        
        # 先頭の行を表示
        if rows:
            logger.info(f"サンプルデータ: {rows[0]}")
        
        return True
    except Exception as e:
        logger.error(f"BigQueryへのロード中にエラーが発生: {str(e)}")
        return False

def run_test(japanese_headers=True, file_format='csv'):
    """
    テスト全体を実行します
    
    Args:
        japanese_headers (bool): 日本語ヘッダーを使用するかどうか
        file_format (str): ファイル形式 ('csv' または 'parquet')
        
    Returns:
        bool: テストが成功したかどうか
    """
    try:
        # Parquetフォーマットの場合、必要なライブラリをチェック
        if file_format == 'parquet' and not PARQUET_SUPPORT:
            logger.error("Parquetテストはスキップされます。pandas/pyarrowをインストールしてください")
            return False
            
        # 環境変数の読み込み
        EnvironmentUtils.load_env()
        
        # GCS情報の取得
        gcs_bucket = EnvironmentUtils.get_env_var("GCS_BUCKET_NAME")
        
        # BigQuery情報の取得
        dataset_id = EnvironmentUtils.get_env_var("BIGQUERY_DATASET")
        
        # タイムスタンプつきのテーブル名を作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        header_type = "japanese" if japanese_headers else "english"
        table_name = f"test_{file_format}_{header_type}_{timestamp}"
        
        # ファイル名とGCSパスを設定
        csv_filename = f"sample_{header_type}_{timestamp}.csv"
        gcs_path = f"test/{timestamp}/"
        
        # サンプルCSVを作成
        csv_file = create_sample_csv(csv_filename, japanese_headers)
        
        # ファイル形式に応じて処理
        if file_format == 'csv':
            # CSVのままアップロード
            local_file = csv_file
            gcs_filename = os.path.basename(csv_file)
        else:
            # CSVをParquetに変換
            parquet_filename = f"sample_{header_type}_{timestamp}.parquet"
            local_file = convert_csv_to_parquet(csv_file, 
                                             os.path.join(tempfile.gettempdir(), parquet_filename))
            gcs_filename = os.path.basename(local_file)
        
        # GCSにアップロード
        gcs_uri = upload_to_gcs(local_file, gcs_bucket, gcs_path + gcs_filename)
        
        # BigQueryにロード
        success = load_to_bigquery(gcs_uri, table_name, dataset_id)
        
        # ローカルファイルを削除
        if os.path.exists(csv_file):
            os.remove(csv_file)
            logger.info(f"ローカルファイルを削除しました: {csv_file}")
            
        if file_format == 'parquet' and os.path.exists(local_file) and local_file != csv_file:
            os.remove(local_file)
            logger.info(f"ローカルファイルを削除しました: {local_file}")
        
        return success
    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生: {str(e)}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BigQueryへのデータロードをテストするスクリプト")
    parser.add_argument("--english-headers", action="store_true", help="英語のヘッダーを使用する（デフォルトは日本語）")
    parser.add_argument("--file-format", choices=['csv', 'parquet'], default='csv', help="ファイル形式（デフォルト: csv）")
    
    args = parser.parse_args()
    
    success = run_test(japanese_headers=not args.english_headers, file_format=args.file_format)
    
    if success:
        logger.info("テスト成功！")
        sys.exit(0)
    else:
        logger.error("テスト失敗")
        sys.exit(1) 