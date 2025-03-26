#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
詳細分析レポートデータをBigQueryにロードするスクリプト

指定されたCSVファイルから詳細分析レポートデータを読み込み、
BigQueryにロードする処理を実行します。
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# プロジェクトルートへのパスをsys.pathに追加
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

# 必要なモジュールをインポート
from google.cloud import bigquery
from google.oauth2 import service_account

def setup_logging():
    """ロギングの設定"""
    log_dir = os.path.join(current_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'detailed_analysis_load_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # フォーマッタの作成
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソールハンドラの追加
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # ファイルハンドラの追加
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    return logging.getLogger(__name__)

def load_env():
    """環境変数を読み込む"""
    logger = logging.getLogger(__name__)
    env_file = os.path.join(current_dir, 'config', 'secrets.env')
    
    # 環境変数の初期化
    env_vars = {}
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                parts = line.split('=', 1)
                if len(parts) == 2:
                    key, value = parts
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    
                    # 環境変数に設定
                    os.environ[key] = value
                    env_vars[key] = value
        
        logger.info(f"環境変数ファイル {env_file} を読み込みました")
        return env_vars
    except Exception as e:
        logger.error(f"環境変数ファイルの読み込みに失敗しました: {e}")
        raise

def resolve_path(relative_path):
    """相対パスを絶対パスに解決する"""
    return os.path.join(current_dir, relative_path)

def get_env_var(var_name, default=None):
    """環境変数を取得する"""
    value = os.environ.get(var_name, default)
    if value is None:
        raise ValueError(f"環境変数 {var_name} が設定されていません。")
    return value

def create_bigquery_table_if_not_exists():
    """BigQueryのテーブルが存在しなければ作成する"""
    logger = logging.getLogger(__name__)
    
    # 環境変数から設定を取得
    project_id = get_env_var('BIGQUERY_PROJECT_ID')
    dataset_id = get_env_var('BIGQUERY_DATASET_ID')
    table_id = get_env_var('BIGQUERY_DETAILED_ANALYSIS_TABLE_ID')
    service_account_path = resolve_path(get_env_var('BIGQUERY_KEY_PATH'))
    
    # スキーマファイルのパス
    schema_file_path = resolve_path('data/detailed_analysis_schema.json')
    
    # スキーマの読み込み
    with open(schema_file_path, 'r', encoding='utf-8') as f:
        schema_data = json.load(f)
    
    # BigQueryクライアントの初期化
    credentials = service_account.Credentials.from_service_account_file(
        service_account_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    client = bigquery.Client(credentials=credentials, project=project_id)
    
    # データセットの取得または作成
    try:
        dataset_ref = client.dataset(dataset_id)
        client.get_dataset(dataset_ref)
        logger.info(f"データセット {dataset_id} が存在します")
    except Exception:
        logger.info(f"データセット {dataset_id} を作成します")
        dataset = bigquery.Dataset(f"{project_id}.{dataset_id}")
        dataset.location = "asia-northeast1"  # 東京リージョン
        client.create_dataset(dataset, exists_ok=True)
    
    # テーブルの取得または作成
    table_ref = client.dataset(dataset_id).table(table_id)
    
    try:
        client.get_table(table_ref)
        logger.info(f"テーブル {table_id} が存在します")
    except Exception:
        logger.info(f"テーブル {table_id} を作成します")
        
        # スキーマの変換
        schema_fields = []
        for field in schema_data:
            schema_fields.append(
                bigquery.SchemaField(
                    name=field['name'],
                    field_type=field['type'],
                    mode=field['mode'],
                    description=field['description']
                )
            )
        
        # テーブルの作成
        table = bigquery.Table(table_ref, schema=schema_fields)
        client.create_table(table, exists_ok=True)
        logger.info(f"テーブル {table_id} を作成しました")

def load_detailed_analysis_data(csv_file_path):
    """詳細分析レポートのデータをBigQueryにロードする"""
    logger = logging.getLogger(__name__)
    
    # CSVファイルの存在確認
    csv_file_path = resolve_path(csv_file_path)
    if not os.path.exists(csv_file_path):
        logger.error(f"CSVファイルが見つかりません: {csv_file_path}")
        return 0
    
    # BigQueryクライアントの初期化
    project_id = get_env_var('BIGQUERY_PROJECT_ID')
    dataset_id = get_env_var('BIGQUERY_DATASET_ID')
    table_id = get_env_var('BIGQUERY_DETAILED_ANALYSIS_TABLE_ID')
    service_account_path = resolve_path(get_env_var('BIGQUERY_KEY_PATH'))
    
    # サービスアカウント認証を使用
    credentials = service_account.Credentials.from_service_account_file(
        service_account_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    client = bigquery.Client(credentials=credentials, project=project_id)
    
    # テーブル参照
    table_ref = client.dataset(dataset_id).table(table_id)
    
    # CSVの読み込み設定
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,  # ヘッダー行をスキップ
        encoding="SHIFT_JIS",  # エンコーディングを指定
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,  # 既存データに追記
        allow_quoted_newlines=True,  # 引用符で囲まれた改行を許可
        allow_jagged_rows=True,  # 不揃いな行を許可
    )
    
    # CSVファイルを開いてロード
    with open(csv_file_path, "rb") as source_file:
        job = client.load_table_from_file(
            source_file,
            table_ref,
            job_config=job_config
        )
    
    # ジョブの完了を待つ
    job.result()
    
    # 結果を出力
    table = client.get_table(table_ref)
    logger.info(f"テーブル {table_id} に {job.output_rows} 行のデータをロードしました")
    
    return job.output_rows

def main():
    """メイン処理"""
    # ロギングの設定
    logger = setup_logging()
    logger.info("詳細分析レポートデータのロード処理を開始します")
    
    try:
        # 環境変数の読み込み
        load_env()
        
        # テスト用CSVファイルのパス
        csv_file_path = 'data/downloads/20250325_ebis_SS_CV.csv'
        
        # BigQueryテーブルの作成（存在しない場合）
        create_bigquery_table_if_not_exists()
        
        # データロード処理の実行
        loaded_rows = load_detailed_analysis_data(csv_file_path)
        
        if loaded_rows > 0:
            logger.info(f"正常に {loaded_rows} 行のデータをロードしました")
        else:
            logger.info("新しくロードされたデータはありません")
        
        return 0
        
    except Exception as e:
        logger.exception(f"データロード中にエラーが発生しました: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 