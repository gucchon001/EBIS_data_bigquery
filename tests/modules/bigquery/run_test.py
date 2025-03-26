#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
詳細分析レポートデータローダーのテスト実行スクリプト

このスクリプトはdataフォルダにあるCSVをテスト的にBigQueryにロードします。
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from google.cloud import bigquery
from google.oauth2 import service_account

# パスの設定
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# データローダーのインポート
from src.modules.bigquery.data_loader import load_detailed_analysis_data, BigQueryDataLoader
from src.utils.environment import EnvironmentUtils
from src.utils.logging_config import configure_logging

def setup_logging():
    """ロギングの設定"""
    log_dir = os.path.join(project_root, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'test_data_loader_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    configure_logging(log_file, console_level='INFO')
    return logging.getLogger(__name__)

def create_bigquery_table_if_not_exists():
    """BigQueryのテーブルが存在しなければ作成する"""
    logger = logging.getLogger(__name__)
    
    # 環境変数から設定を取得
    project_id = EnvironmentUtils.get_env_var('BIGQUERY_PROJECT_ID')
    dataset_id = EnvironmentUtils.get_env_var('BIGQUERY_DATASET_ID')
    table_id = EnvironmentUtils.get_env_var('BIGQUERY_DETAILED_ANALYSIS_TABLE_ID')
    service_account_path = EnvironmentUtils.get_service_account_file()
    
    # スキーマファイルのパス
    schema_file_path = EnvironmentUtils.resolve_path('data/detailed_analysis_schema.json')
    
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
        return True
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
        return True

def main():
    """テスト実行のメイン処理"""
    logger = setup_logging()
    logger.info("詳細分析レポートデータローダーのテストを開始します")
    
    # 環境変数の読み込み
    try:
        EnvironmentUtils.load_env()
        logger.info("環境変数の読み込みが完了しました")
    except Exception as e:
        logger.error(f"環境変数の読み込みに失敗しました: {e}")
        return 1
    
    # テスト用CSVファイルのパス（2025cvreport.csvを使う）
    test_csv_path = 'data/2025cvreport.csv'
    resolved_path = EnvironmentUtils.resolve_path(test_csv_path)
    
    if not os.path.exists(resolved_path):
        logger.error(f"テスト用CSVファイルが見つかりません: {resolved_path}")
        return 1
    
    logger.info(f"テスト用CSVファイル: {test_csv_path}")
    
    try:
        # BigQueryテーブルの作成（存在しない場合）
        if not create_bigquery_table_if_not_exists():
            logger.error("BigQueryテーブルの作成に失敗しました")
            return 1
        
        # データロード処理の実行
        loaded_rows = load_detailed_analysis_data(test_csv_path)
        
        if loaded_rows > 0:
            logger.info(f"テスト成功: {loaded_rows} 行のデータをロードしました")
        else:
            logger.info("テスト成功: 新しくロードされたデータはありません（重複データのみ）")
        
        return 0
    
    except Exception as e:
        logger.exception(f"テスト実行中にエラーが発生しました: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 