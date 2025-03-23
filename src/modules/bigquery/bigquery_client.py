#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BigQueryクライアント

Google BigQueryとの連携を行うユーティリティクラスを提供します。
環境変数から設定を読み込み、BigQueryへのデータロードや操作を行います。
"""

import os
import sys
from pathlib import Path
from loguru import logger
from google.cloud import bigquery
from google.oauth2 import service_account
from google.cloud.exceptions import NotFound

# プロジェクトのルートディレクトリをシステムパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.utils.environment import EnvironmentUtils

class BigQueryClient:
    """Google BigQueryとの連携を行うユーティリティクラス"""

    def __init__(self):
        """
        BigQueryClientの初期化
        環境変数を読み込み、BigQueryクライアントを初期化します
        """
        # 環境変数の取得
        self.project_id = EnvironmentUtils.get_env_var("BIGQUERY_PROJECT_ID")
        self.dataset_id = EnvironmentUtils.get_env_var("BIGQUERY_DATASET")
        self.dataset_mt_id = EnvironmentUtils.get_env_var("BIGQUERY_DATASET_MT")
        self.log_table = EnvironmentUtils.get_env_var("LOG_TABLE")
        self.gcs_key_path = EnvironmentUtils.get_env_var("GCS_KEY_PATH")
        
        # GCSキーファイルのパスを解決
        key_path = Path(EnvironmentUtils.get_project_root()) / self.gcs_key_path
        
        if not key_path.exists():
            raise FileNotFoundError(f"認証キーファイルが見つかりません: {key_path}")
        
        # 認証情報を作成
        credentials = service_account.Credentials.from_service_account_file(
            key_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        
        # BigQueryクライアントを初期化
        self.client = bigquery.Client(credentials=credentials, project=self.project_id)
        
        logger.info(f"BigQueryクライアントを初期化しました: プロジェクト={self.project_id}, データセット={self.dataset_id}")

    def dataset_exists(self, dataset_id=None):
        """
        指定されたデータセットが存在するか確認します
        
        Args:
            dataset_id (str, optional): 確認するデータセットID。デフォルトはNone（デフォルトのデータセットを使用）
            
        Returns:
            bool: データセットが存在する場合はTrue、それ以外はFalse
        """
        dataset_id = dataset_id or self.dataset_id
        dataset_ref = self.client.dataset(dataset_id)
        
        try:
            self.client.get_dataset(dataset_ref)
            return True
        except NotFound:
            return False

    def table_exists(self, table_id, dataset_id=None):
        """
        指定されたテーブルが存在するか確認します
        
        Args:
            table_id (str): 確認するテーブルID
            dataset_id (str, optional): テーブルが属するデータセットID。デフォルトはNone（デフォルトのデータセットを使用）
            
        Returns:
            bool: テーブルが存在する場合はTrue、それ以外はFalse
        """
        dataset_id = dataset_id or self.dataset_id
        table_ref = self.client.dataset(dataset_id).table(table_id)
        
        try:
            self.client.get_table(table_ref)
            return True
        except NotFound:
            return False

    def create_dataset_if_not_exists(self, dataset_id=None, location="asia-northeast1"):
        """
        データセットが存在しない場合に新規作成します
        
        Args:
            dataset_id (str, optional): 作成するデータセットID。デフォルトはNone（デフォルトのデータセットを使用）
            location (str, optional): データセットのロケーション。デフォルトは東京リージョン
            
        Returns:
            google.cloud.bigquery.dataset.Dataset: 作成または取得したデータセット
        """
        dataset_id = dataset_id or self.dataset_id
        dataset_ref = self.client.dataset(dataset_id)
        
        try:
            return self.client.get_dataset(dataset_ref)
        except NotFound:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = location
            
            logger.info(f"データセット '{dataset_id}' を作成します（ロケーション: {location}）")
            return self.client.create_dataset(dataset)

    def check_for_not_supported_properties(self, obj, property_name):
        """
        指定されたオブジェクトでプロパティがサポートされているかを確認します
        
        Args:
            obj: チェック対象のオブジェクト
            property_name (str): 確認するプロパティ名
            
        Returns:
            bool: プロパティがサポートされていればTrue、それ以外はFalse
        """
        try:
            # プロパティが存在するか確認
            getattr(obj, property_name)
            return True
        except (AttributeError, TypeError):
            logger.warning(f"プロパティ {property_name} は {type(obj).__name__} でサポートされていません")
            return False

    def load_from_gcs(self, source_uri, table_id, schema=None, dataset_id=None, write_disposition="WRITE_TRUNCATE"):
        """
        Google Cloud Storageからデータをロードし、BigQueryテーブルに格納します
        
        Args:
            source_uri (str): ロードするGCSファイルのURI（例: gs://bucket_name/path/to/file.csv）
            table_id (str): ロード先のテーブルID
            schema (list, optional): BigQueryのスキーマ定義。Noneの場合は自動検出
            dataset_id (str, optional): ロード先のデータセットID。デフォルトはNone（デフォルトのデータセットを使用）
            write_disposition (str, optional): テーブルが既に存在する場合の動作。
                WRITE_TRUNCATE: テーブルを削除して新しくデータをロード
                WRITE_APPEND: 既存のテーブルにデータを追加
                WRITE_EMPTY: テーブルが空の場合のみロード
                
        Returns:
            google.cloud.bigquery.job.LoadJob: ロードジョブ
        """
        dataset_id = dataset_id or self.dataset_id
        
        # データセットが存在することを確認
        self.create_dataset_if_not_exists(dataset_id)
        
        # テーブル参照を作成
        table_ref = self.client.dataset(dataset_id).table(table_id)
        
        # ジョブ設定
        job_config = bigquery.LoadJobConfig()
        
        # ファイル形式に基づいて設定
        if source_uri.endswith('.csv'):
            job_config.source_format = bigquery.SourceFormat.CSV
            job_config.skip_leading_rows = 1  # ヘッダー行をスキップ
            job_config.allow_quoted_newlines = True
            job_config.allow_jagged_rows = True
            # エンコーディング指定
            if self.check_for_not_supported_properties(job_config, 'encoding'):
                job_config.encoding = 'UTF-8'
        elif source_uri.endswith('.parquet'):
            job_config.source_format = bigquery.SourceFormat.PARQUET
        elif source_uri.endswith('.json'):
            job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
        else:
            raise ValueError(f"サポートされていないファイル形式です: {source_uri}")
        
        # スキーマが指定されている場合は設定
        if schema:
            # スキーマが指定されている場合、日本語カラム名をバッククオートで囲む
            modified_schema = []
            for field in schema:
                if any(ord(c) > 127 for c in field.name):  # 日本語文字が含まれるか確認
                    # バッククオートで囲んだフィールド名を持つ新しいSchemaFieldを作成
                    try:
                        new_field = bigquery.SchemaField(
                            name=f"`{field.name}`",
                            field_type=field.field_type,
                            mode=field.mode,
                            description=field.description,
                            fields=field.fields
                        )
                        modified_schema.append(new_field)
                    except Exception as e:
                        logger.warning(f"日本語フィールド名の処理中にエラーが発生: {str(e)}")
                        # エラーの場合は元のフィールドを使用
                        modified_schema.append(field)
                else:
                    modified_schema.append(field)
            job_config.schema = modified_schema
        else:
            job_config.autodetect = True
        
        # 書き込み設定
        job_config.write_disposition = getattr(bigquery.WriteDisposition, write_disposition)
        
        # 日本語フィールド名対応のために文字マップV2を使用（直接プロパティ設定）
        # 条件を削除し、常に設定するように変更
        job_config._properties["useCharacterMapV2"] = True
        
        # ロードジョブを実行
        logger.info(f"BigQueryへのロードを開始: {source_uri} -> {dataset_id}.{table_id} ({write_disposition})")
        try:
            # スキーマ自動検出モードでロード
            load_job = self.client.load_table_from_uri(
                source_uri,
                table_ref,
                job_config=job_config
            )
            
            # ジョブの完了を待機
            load_job.result()
            
            # 結果のログ出力
            destination_table = self.client.get_table(table_ref)
            logger.info(f"ロード完了: {destination_table.num_rows} 行がロードされました")
            
            return load_job
        except Exception as e:
            error_message = str(e)
            logger.error(f"ロード処理中にエラーが発生: {error_message}")
            
            # 特定のエラーに対する処理
            if "character map V2" in error_message or "schema update options" in error_message or "Field name" in error_message:
                # Character Map V2オプションでの再試行
                logger.info(f"Character Map V2オプションを使用して再試行します: {source_uri}")
                
                # 設定をコピー（重要なオプションは保持）
                retry_job_config = bigquery.LoadJobConfig()
                retry_job_config.source_format = job_config.source_format
                retry_job_config.write_disposition = job_config.write_disposition
                retry_job_config.autodetect = True
                
                # CSVファイル特有の設定
                if source_uri.endswith('.csv'):
                    retry_job_config.skip_leading_rows = 1
                    retry_job_config.allow_quoted_newlines = True
                    retry_job_config.allow_jagged_rows = True
                
                # 明示的にCharacter Map V2を使用
                # _propertiesは非公式APIですが、現時点で唯一の方法
                retry_job_config._properties["useCharacterMapV2"] = True
                
                try:
                    # 再試行
                    retry_job = self.client.load_table_from_uri(
                        source_uri,
                        table_ref,
                        job_config=retry_job_config
                    )
                    
                    # ジョブの完了を待機
                    retry_job.result()
                    
                    # 結果のログ出力
                    destination_table = self.client.get_table(table_ref)
                    logger.info(f"Character Map V2オプションでロード完了: {destination_table.num_rows} 行がロードされました")
                    
                    return retry_job
                except Exception as retry_error:
                    retry_error_message = str(retry_error)
                    logger.error(f"Character Map V2オプションでの再試行にも失敗: {retry_error_message}")
                    
                    # 最後の手段：さらに最小設定で再試行
                    logger.info("最小設定で再試行します")
                    
                    # 最小限の設定でジョブを再作成
                    minimal_job_config = bigquery.LoadJobConfig()
                    minimal_job_config.autodetect = True
                    minimal_job_config.source_format = retry_job_config.source_format
                    minimal_job_config.write_disposition = retry_job_config.write_disposition
                    
                    # CSVファイル特有の最小設定
                    if source_uri.endswith('.csv'):
                        minimal_job_config.skip_leading_rows = 1
                    
                    # Character Map V2を設定
                    minimal_job_config._properties["useCharacterMapV2"] = True
                    
                    try:
                        # 最終再試行
                        final_retry_job = self.client.load_table_from_uri(
                            source_uri,
                            table_ref,
                            job_config=minimal_job_config
                        )
                        
                        # ジョブの完了を待機
                        final_retry_job.result()
                        
                        # 結果のログ出力
                        destination_table = self.client.get_table(table_ref)
                        logger.info(f"最小設定でロード完了: {destination_table.num_rows} 行がロードされました")
                        
                        return final_retry_job
                    except Exception as final_error:
                        logger.error(f"最小設定での再試行にも失敗: {str(final_error)}")
                        logger.error(f"Character Map V2を使用した再試行でもエラー: {source_uri}, エラー: {str(final_error)}")
                        raise
            
            # その他のエラーはそのまま再発生
            raise

    def execute_query(self, query, destination_table=None, destination_dataset=None, write_disposition="WRITE_TRUNCATE"):
        """
        SQLクエリを実行し、結果を取得または指定したテーブルに保存します
        
        Args:
            query (str): 実行するSQLクエリ
            destination_table (str, optional): 結果を保存するテーブルID。指定しない場合は結果を返却
            destination_dataset (str, optional): 結果を保存するデータセットID。デフォルトはNone（デフォルトのデータセットを使用）
            write_disposition (str, optional): テーブルが既に存在する場合の動作
            
        Returns:
            google.cloud.bigquery.job.QueryJob: クエリジョブ
        """
        # ジョブ設定
        job_config = bigquery.QueryJobConfig()
        
        # 結果の保存先が指定されている場合
        if destination_table:
            dataset_id = destination_dataset or self.dataset_id
            
            # データセットが存在することを確認
            self.create_dataset_if_not_exists(dataset_id)
            
            # 保存先テーブル参照を作成
            table_ref = self.client.dataset(dataset_id).table(destination_table)
            job_config.destination = table_ref
            job_config.write_disposition = getattr(bigquery.WriteDisposition, write_disposition)
            
            logger.info(f"クエリ結果を保存: {dataset_id}.{destination_table} ({write_disposition})")
        
        # クエリを実行
        query_job = self.client.query(query, job_config=job_config)
        
        # ジョブの完了を待機
        query_job.result()
        
        # 結果のログ出力
        if destination_table:
            destination_table_obj = self.client.get_table(job_config.destination)
            logger.info(f"クエリ完了: {destination_table_obj.num_rows} 行が生成されました")
        else:
            logger.info("クエリ完了")
        
        return query_job

    def quote_japanese_column_names(self, column_names):
        """
        日本語を含むカラム名をバッククオートで囲みます
        
        Args:
            column_names (list): カラム名のリスト
            
        Returns:
            list: 処理後のカラム名リスト
        """
        return [f"`{col}`" if any(ord(c) > 127 for c in col) else col for col in column_names]
        
    def get_table_schema(self, table_id, dataset_id=None):
        """
        テーブルのスキーマを取得します
        
        Args:
            table_id (str): 取得するテーブルID
            dataset_id (str, optional): テーブルが属するデータセットID
            
        Returns:
            list: BigQueryのスキーマ情報
        """
        dataset_id = dataset_id or self.dataset_id
        table_ref = self.client.dataset(dataset_id).table(table_id)
        
        try:
            table = self.client.get_table(table_ref)
            return table.schema
        except Exception as e:
            logger.error(f"テーブルスキーマの取得中にエラーが発生: {str(e)}")
            raise
            
    def generate_query_with_japanese_columns(self, query, table_id, dataset_id=None):
        """
        日本語カラム名を含むクエリを生成します。
        日本語カラム名は自動的にバッククオートで囲まれます。
        
        Args:
            query (str): 元のクエリテンプレート
            table_id (str): テーブルID
            dataset_id (str, optional): データセットID
            
        Returns:
            str: 処理後のクエリ
        """
        # テーブルの完全修飾名を作成
        dataset_id = dataset_id or self.dataset_id
        fully_qualified_table = f"`{self.project_id}.{dataset_id}.{table_id}`"
        
        # テーブルスキーマを取得
        schema = self.get_table_schema(table_id, dataset_id)
        
        # スキーマからカラム名を抽出し、日本語カラム名をバッククオートで囲む
        column_names = [field.name for field in schema]
        quoted_column_names = self.quote_japanese_column_names(column_names)
        
        # カラム名のマッピングを作成
        column_mapping = dict(zip(column_names, quoted_column_names))
        
        # クエリにマッピングを適用
        modified_query = query
        for original, quoted in column_mapping.items():
            if original != quoted:  # 日本語カラム名の場合のみ置換
                modified_query = modified_query.replace(original, quoted)
        
        return modified_query
        
    def query_table(self, table_id, columns=None, where=None, order_by=None, limit=None, dataset_id=None):
        """
        テーブルに対するSELECTクエリを生成し実行します。
        日本語カラム名は自動的にバッククオートで囲まれます。
        
        Args:
            table_id (str): クエリ対象のテーブルID
            columns (list, optional): 取得するカラム名のリスト。Noneの場合は全カラム
            where (str, optional): WHERE句の条件文字列
            order_by (str, optional): ORDER BY句の条件文字列
            limit (int, optional): 取得する最大行数
            dataset_id (str, optional): データセットID
            
        Returns:
            google.cloud.bigquery.job.QueryJob: クエリジョブ
        """
        dataset_id = dataset_id or self.dataset_id
        
        # テーブルスキーマを取得
        schema = self.get_table_schema(table_id, dataset_id)
        
        # カラム一覧を取得
        all_columns = [field.name for field in schema]
        
        # SELECTに含めるカラム
        if columns is None:
            # 全カラムを使用
            columns_to_select = all_columns
        else:
            # 指定されたカラムのみ使用
            columns_to_select = columns
        
        # 日本語カラム名をバッククオートで囲む
        quoted_columns = self.quote_japanese_column_names(columns_to_select)
        
        # クエリの構築
        query = f"SELECT {', '.join(quoted_columns)} FROM `{self.project_id}.{dataset_id}.{table_id}`"
        
        # WHERE句の追加
        if where:
            # WHEREにも日本語カラム名があれば、バッククオートを追加
            for col, quoted in zip(all_columns, self.quote_japanese_column_names(all_columns)):
                if col != quoted and col in where:
                    where = where.replace(col, quoted)
            query += f" WHERE {where}"
        
        # ORDER BY句の追加
        if order_by:
            # ORDER BYにも日本語カラム名があれば、バッククオートを追加
            for col, quoted in zip(all_columns, self.quote_japanese_column_names(all_columns)):
                if col != quoted and col in order_by:
                    order_by = order_by.replace(col, quoted)
            query += f" ORDER BY {order_by}"
        
        # LIMIT句の追加
        if limit:
            query += f" LIMIT {limit}"
        
        # クエリを実行
        logger.debug(f"生成されたクエリ: {query}")
        return self.execute_query(query)

    def log_operation(self, operation_type, target_table, status, details=None):
        """
        操作ログをBigQueryのログテーブルに記録します
        
        Args:
            operation_type (str): 操作の種類（例: 'LOAD', 'QUERY', 'EXPORT'）
            target_table (str): 対象テーブル名
            status (str): 操作のステータス（例: 'SUCCESS', 'FAILURE'）
            details (str, optional): 詳細情報
            
        Returns:
            google.cloud.bigquery.job.QueryJob: INSERTクエリのジョブ
        """
        if not self.log_table:
            logger.warning("ログテーブルが設定されていないため、操作ログは記録されません")
            return None
        
        # ログテーブルが存在することを確認
        if not self.table_exists(self.log_table):
            logger.info(f"ログテーブル {self.log_table} を作成します")
            
            # ログテーブルのスキーマ
            schema = [
                bigquery.SchemaField("timestamp", "TIMESTAMP"),
                bigquery.SchemaField("operation_type", "STRING"),
                bigquery.SchemaField("target_table", "STRING"),
                bigquery.SchemaField("status", "STRING"),
                bigquery.SchemaField("details", "STRING"),
            ]
            
            # テーブル作成
            table = bigquery.Table(self.client.dataset(self.dataset_id).table(self.log_table), schema=schema)
            self.client.create_table(table, exists_ok=True)
        
        # ログレコードの挿入クエリ（ログテーブルには日本語カラム名がないため、
        # 単純にテーブル参照のみバッククオートで囲む）
        query = f"""
        INSERT INTO `{self.project_id}.{self.dataset_id}.{self.log_table}` 
        (timestamp, operation_type, target_table, status, details)
        VALUES (CURRENT_TIMESTAMP(), '{operation_type}', '{target_table}', '{status}', '{details or ''}')
        """
        
        # クエリ実行
        return self.execute_query(query) 