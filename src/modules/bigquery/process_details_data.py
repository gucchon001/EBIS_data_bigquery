#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
詳細分析レポートデータの処理とBigQueryへの取り込みを行うモジュール

このモジュールは以下の機能を提供します：
1. CSVファイルの読み込みと前処理
2. カラム名のマッピングと型変換
3. BigQueryへのデータロード
"""

import os
import logging
from datetime import datetime, timedelta
from src.utils.environment import EnvironmentUtils as env
from src.modules.bigquery.process_in_chunks import process_in_chunks
from src.modules.bigquery.column_mappings import get_detailed_analysis_mappings
import re
from google.cloud import bigquery
import pandas as pd
from .process_in_chunks import process_in_chunks
from ..utils.logger import get_logger

# ロガーの設定
logger = get_logger(__name__)

def extract_date_from_filename(filename):
    """
    ファイル名から日付を抽出する
    
    Args:
        filename: ファイル名（例: 20250325_ebis_SS_CV.csv）
    
    Returns:
        datetime: 抽出された日付
    """
    # ファイル名から日付部分を抽出
    match = re.search(r'(\d{8})', os.path.basename(filename))
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            logger.error(f"ファイル名から抽出した日付 '{date_str}' の解析に失敗しました")
    return None

def process_details_data(csv_file, target_date=None):
    """
    詳細分析レポートのCSVファイルを処理し、BigQueryにロードする
    
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
        dataset = env.get_env_var('BIGQUERY_DATASET')
        table = 'details_analysis_report'
        table_name = f"{dataset}.{table}"
        
        # BigQuery設定の取得
        bq_settings = {
            "chunk_size": int(config.get('bigquery', 'chunk_size', fallback='1000')),
            "write_disposition": config.get('bigquery', 'write_disposition', fallback='WRITE_APPEND')
        }
        
        logger.info(f"BigQuery設定: テーブル={table_name}, チャンクサイズ={bq_settings['chunk_size']}")
        
        # ファイルの存在確認
        if not os.path.exists(csv_file):
            logger.error(f"CSVファイル '{csv_file}' が見つかりません")
            return False
            
        # ファイル名から日付を抽出
        target_date = extract_date_from_filename(csv_file)
        if target_date:
            logger.info(f"ファイル名から抽出した日付: {target_date.strftime('%Y-%m-%d')}")
        elif target_date is None:
            target_date = datetime.now() - timedelta(days=1)
            logger.info(f"デフォルトの日付を使用: {target_date.strftime('%Y-%m-%d')}")
        
        # 重複チェック用のクエリを実行
        client = bigquery.Client()
        query = f"""
        SELECT COUNT(*) as count
        FROM `{table_name}`
        WHERE `日付` = PARSE_DATE('%Y-%m-%d', '{target_date.strftime('%Y-%m-%d')}')
        """
        
        try:
            query_job = client.query(query)
            results = query_job.result()
            row_count = list(results)[0].count
            
            if row_count > 0:
                logger.warning(f"日付 {target_date.strftime('%Y-%m-%d')} のデータは既に存在します。スキップします。")
                return True
        except Exception as e:
            logger.error(f"重複チェッククエリの実行中にエラーが発生しました: {str(e)}")
            # 重複チェックに失敗した場合でも処理は続行
            
        # カラムマッピングと型変換の設定
        mappings = get_detailed_analysis_mappings()
        
        # 日付カラムの値を設定
        mappings['column_mapping'].update({
            '日付': target_date.strftime('%Y-%m-%d'),
            'データ取得日': datetime.now().strftime('%Y-%m-%d')
        })
        
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
        
        logger.info("データ取り込みが正常に完了しました")
        return True
        
    except Exception as e:
        logger.error(f"データ処理中にエラーが発生しました: {str(e)}")
        return False 