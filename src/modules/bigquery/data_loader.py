#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BigQueryへのデータロードを行うモジュール

CSVデータを読み込み、指定されたスキーマに合わせてBigQueryにロードします。
既存データのチェックや日付によるフィルタリングを行います。
"""

import os
import json
import csv
import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple
from google.cloud import bigquery
from google.oauth2 import service_account

from src.utils.environment import EnvironmentUtils
from src.modules.bigquery.column_mappings import get_detailed_analysis_mappings

# ロガーの設定
logger = logging.getLogger(__name__)

class BigQueryDataLoader:
    """
    BigQueryへのデータロードを行うクラス
    
    CSVデータの読み込み、変換、BigQueryへのロードを担当します。
    """
    
    def __init__(self, project_id: str, dataset_id: str, table_id: str, service_account_path: str):
        """
        BigQueryDataLoaderの初期化
        
        Args:
            project_id: BigQueryプロジェクトID
            dataset_id: BigQueryデータセットID
            table_id: BigQueryテーブルID
            service_account_path: サービスアカウントキーファイルのパス
        """
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.service_account_path = service_account_path
        
        # BigQueryクライアントの初期化
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self.client = bigquery.Client(credentials=credentials, project=project_id)
        
        # スキーマ情報の取得
        self.table_ref = self.client.dataset(dataset_id).table(table_id)
        
        # カラムマッピングの取得
        self.mappings = get_detailed_analysis_mappings()
        
    def _load_schema_from_file(self, schema_file_path: str) -> List[Dict[str, Any]]:
        """
        JSONファイルからスキーマ情報を読み込む
        
        Args:
            schema_file_path: スキーマJSONファイルのパス
            
        Returns:
            スキーマ情報のリスト
        """
        schema_path = EnvironmentUtils.resolve_path(schema_file_path)
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_data = json.load(f)
        return schema_data
    
    def _convert_schema_to_bigquery_format(self, schema_data: List[Dict[str, Any]]) -> List[bigquery.SchemaField]:
        """
        スキーマ情報をBigQueryのSchemaField形式に変換
        
        Args:
            schema_data: JSONから読み込んだスキーマ情報
            
        Returns:
            BigQueryのSchemaFieldのリスト
        """
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
        return schema_fields
    
    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """
        日付文字列をdatetime.date形式にパース
        
        Args:
            date_str: 日付文字列（YYYY-MM-DD または YYYY/MM/DD 形式）
            
        Returns:
            パースした日付オブジェクト、失敗した場合はNone
        """
        date_formats = ['%Y-%m-%d', '%Y/%m/%d']
        
        for date_format in date_formats:
            try:
                return datetime.datetime.strptime(date_str, date_format).date()
            except ValueError:
                continue
        
        logger.warning(f"日付のパースに失敗しました: {date_str}")
        return None
    
    def _get_existing_dates(self) -> List[datetime.date]:
        """
        BigQueryテーブルから既存の日付リストを取得
        
        Returns:
            テーブルに存在する日付のリスト
        """
        query = f"""
        SELECT DISTINCT date
        FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
        """
        
        query_job = self.client.query(query)
        results = query_job.result()
        
        return [row.date for row in results]
    
    def _read_csv_data(self, csv_file_path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        CSVファイルからデータを読み込む
        
        Args:
            csv_file_path: CSVファイルのパス
            
        Returns:
            (読み込んだデータのリスト, 日付のリスト)
        """
        csv_data = []
        dates = []
        
        # エンコーディングを試す順序
        encodings = ['utf-8-sig', 'utf-8', 'shift-jis', 'cp932', 'euc-jp', 'iso-2022-jp']
        
        # 各エンコーディングを試す
        for encoding in encodings:
            try:
                with open(csv_file_path, 'r', encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # 日付の取得と変換
                        if '日付' in row:
                            date_str = row['日付']
                            date_obj = self._parse_date(date_str)
                            if date_obj:
                                dates.append(date_obj)
                        
                        # CSVのカラム名をBigQueryのカラム名にマッピング
                        mapped_row = {}
                        for csv_col, csv_val in row.items():
                            if csv_col in self.mappings['column_mapping']:
                                bq_col = self.mappings['column_mapping'][csv_col]
                                mapped_row[bq_col] = csv_val
                        
                        if mapped_row:
                            csv_data.append(mapped_row)
                
                # エンコーディングが見つかった場合、ループを抜ける
                logger.info(f"CSVファイルをエンコーディング '{encoding}' で読み込みました")
                break
            
            except UnicodeDecodeError:
                # エンコーディングが合わない場合、次のエンコーディングを試す
                continue
            except Exception as e:
                # その他のエラー
                logger.error(f"CSVファイルの読み込み中にエラーが発生しました: {e}")
                raise
        
        # すべてのエンコーディングを試しても失敗した場合
        if not csv_data:
            logger.error("CSVファイルの読み込みに失敗しました。サポートされていないエンコーディングの可能性があります。")
            raise ValueError("CSVファイルの読み込みに失敗しました")
        
        return csv_data, list(set(dates))  # 重複を除去した日付リスト
    
    def _transform_data(self, csv_data: List[Dict[str, Any]], schema: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        データをBigQueryのスキーマに合わせて変換
        
        Args:
            csv_data: CSVから読み込んだデータ
            schema: スキーマ情報
            
        Returns:
            変換後のデータ
        """
        transformed_data = []
        
        # スキーマからフィールド名と型の辞書を作成
        schema_types = {field['name']: field['type'] for field in schema}
        
        for row in csv_data:
            transformed_row = {}
            
            for bq_field, value in row.items():
                field_name = bq_field
                
                # スネークケースに変換（BigQueryのフィールド名と一致させる）
                field_name = ''.join(['_' + c.lower() if c.isupper() else c for c in field_name]).lstrip('_')
                
                # 空の文字列はNoneに変換
                if value == '':
                    transformed_row[field_name] = None
                    continue
                
                # スキーマに基づいてデータ型を変換
                if field_name in schema_types:
                    field_type = schema_types[field_name]
                    
                    if field_type == 'INTEGER' and field_name in self.mappings['integer_columns']:
                        try:
                            # カンマ区切りの数値を処理
                            value = value.replace(',', '')
                            transformed_row[field_name] = int(value) if value else None
                        except (ValueError, TypeError):
                            transformed_row[field_name] = None
                            logger.warning(f"整数変換に失敗: {field_name}={value}")
                    
                    elif field_type == 'FLOAT':
                        try:
                            # パーセント記号や単位を除去
                            if isinstance(value, str):
                                value = value.replace('%', '').replace(',', '')
                            transformed_row[field_name] = float(value) if value else None
                        except (ValueError, TypeError):
                            transformed_row[field_name] = None
                            logger.warning(f"浮動小数点数変換に失敗: {field_name}={value}")
                    
                    elif field_type == 'DATE' and field_name in self.mappings['date_columns']:
                        date_obj = self._parse_date(value) if value else None
                        transformed_row[field_name] = date_obj
                    
                    else:
                        transformed_row[field_name] = value
                else:
                    # スキーマに存在しないフィールドは無視
                    continue
            
            transformed_data.append(transformed_row)
        
        return transformed_data
    
    def _filter_new_data(self, data: List[Dict[str, Any]], existing_dates: List[datetime.date]) -> List[Dict[str, Any]]:
        """
        既存の日付データを除外して新しいデータのみをフィルタリング
        
        Args:
            data: 変換済みのデータ
            existing_dates: 既存の日付のリスト
            
        Returns:
            フィルタリング後の新しいデータ
        """
        filtered_data = []
        
        for row in data:
            if 'date' in row and row['date'] not in existing_dates:
                filtered_data.append(row)
        
        return filtered_data
    
    def load_data(self, csv_file_path: str, schema_file_path: str) -> int:
        """
        CSVデータをBigQueryにロード
        
        Args:
            csv_file_path: CSVファイルのパス
            schema_file_path: スキーマJSONファイルのパス
            
        Returns:
            ロードされた行数
        """
        # 1. スキーマの読み込み
        schema_data = self._load_schema_from_file(schema_file_path)
        bq_schema = self._convert_schema_to_bigquery_format(schema_data)
        
        # 2. 既存の日付データの取得
        existing_dates = self._get_existing_dates()
        logger.info(f"既存の日付データ数: {len(existing_dates)}")
        
        # 3. CSVデータの読み込み
        csv_data, csv_dates = self._read_csv_data(csv_file_path)
        logger.info(f"CSVデータの行数: {len(csv_data)}")
        logger.info(f"CSVに含まれる日付数: {len(csv_dates)}")
        
        # 4. データの変換
        transformed_data = self._transform_data(csv_data, schema_data)
        
        # 5. 既存データのフィルタリング
        new_data = self._filter_new_data(transformed_data, existing_dates)
        logger.info(f"ロード対象の新しいデータ行数: {len(new_data)}")
        
        if not new_data:
            logger.info("ロードするデータがありません。すべてのデータは既に存在します。")
            return 0
        
        # 6. BigQueryにデータをロード
        job_config = bigquery.LoadJobConfig(
            schema=bq_schema,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND
        )
        
        load_job = self.client.load_table_from_json(
            new_data,
            self.table_ref,
            job_config=job_config
        )
        
        # ジョブの完了を待つ
        load_job.result()
        
        logger.info(f"データのロードが完了しました: {len(new_data)} 行")
        return len(new_data)


def load_detailed_analysis_data(csv_file_path: str) -> int:
    """
    詳細分析レポートのデータをBigQueryにロードする
    
    Args:
        csv_file_path: CSVファイルのパス
        
    Returns:
        ロードされた行数
    """
    # 環境変数から設定を取得
    project_id = EnvironmentUtils.get_env_var('BIGQUERY_PROJECT_ID')
    dataset_id = EnvironmentUtils.get_env_var('BIGQUERY_DATASET_ID')
    table_id = EnvironmentUtils.get_env_var('BIGQUERY_DETAILED_ANALYSIS_TABLE_ID')
    service_account_path = EnvironmentUtils.get_service_account_file()
    
    # スキーマファイルのパスを解決
    schema_file_path = EnvironmentUtils.resolve_path('data/detailed_analysis_schema.json')
    
    # CSVファイルのパスを解決
    csv_file_path = EnvironmentUtils.resolve_path(csv_file_path)
    
    # ローダーの初期化とデータロード
    loader = BigQueryDataLoader(project_id, dataset_id, table_id, service_account_path)
    return loader.load_data(csv_file_path, schema_file_path) 