#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CVレポートデータの処理とBigQueryへの取り込みを行うモジュール

このモジュールは以下の機能を提供します：
1. CSVファイルの読み込みと前処理
2. カラム名のマッピングと型変換
3. BigQueryへのデータロード
"""

import os
import logging
from datetime import datetime
from src.utils.environment import EnvironmentUtils as env
from src.modules.bigquery.process_in_chunks import process_in_chunks
from src.modules.bigquery.column_mappings import get_cv_report_mappings

# ロガーの設定
logger = logging.getLogger(__name__)

def process_cv_data(csv_file, target_date=None):
    """
    CVレポートのCSVファイルを処理し、BigQueryにロードする
    
    Args:
        csv_file (str): 処理対象のCSVファイルパス
        target_date (datetime, optional): 処理対象日付
        
    Returns:
        bool: 処理が成功した場合はTrue、失敗した場合はFalse
    """
    try:
        # 環境設定の読み込み
        config = env.get_config_file()
        
        # BigQueryの設定を取得
        dataset = config.get('bigquery', 'dataset')
        table = config.get('bigquery', 'table')
        table_name = f"{dataset}.{table}"
        
        # BigQuery設定の取得
        bq_settings = {
            "chunk_size": int(config.get('bigquery', 'chunk_size', fallback='1000')),
            "write_disposition": config.get('bigquery', 'write_disposition', fallback='WRITE_TRUNCATE')
        }
        
        logger.info(f"BigQuery設定: テーブル={table_name}, チャンクサイズ={bq_settings['chunk_size']}")
        
        # ファイルの存在確認
        if not os.path.exists(csv_file):
            logger.error(f"CSVファイル '{csv_file}' が見つかりません")
            return False
            
        # カラムマッピングと型変換の設定を取得
        mappings = get_cv_report_mappings()
        
        logger.info(f"CSVファイル '{csv_file}' の処理を開始します")
        
        # CSVファイルを処理してBigQueryにロード
        success, failed = process_in_chunks(
            csv_file=csv_file,
            table_name=table_name,
            chunk_size=bq_settings["chunk_size"],
            column_mapping=mappings['column_mapping'],
            date_columns=mappings['date_columns'],
            integer_columns=mappings['integer_columns'],
            write_disposition=bq_settings["write_disposition"]
        )
        
        if failed > 0:
            logger.error(f"データ取り込み中にエラーが発生しました。失敗したチャンク数: {failed}")
            return False
        else:
            logger.info("データ取り込みが正常に完了しました")
            return True
            
    except Exception as e:
        logger.error(f"CVデータの処理中にエラーが発生しました: {e}", exc_info=True)
        return False 