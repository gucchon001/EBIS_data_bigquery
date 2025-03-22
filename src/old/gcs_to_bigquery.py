#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GCSからBigQueryへのデータロード

Google Cloud Storage上の指定されたファイルをBigQueryテーブルにロードします。
環境変数から設定を読み込み、データロードを実行します。
"""

import os
import sys
from pathlib import Path

# プロジェクトのルートディレクトリをシステムパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import argparse
from loguru import logger
from google.cloud import storage
from google.oauth2 import service_account
from google.cloud import bigquery

from src.utils.environment import EnvironmentUtils
from src.modules.bigquery.bigquery_client import BigQueryClient

def setup_logger():
    """ロガーの設定を行います"""
    log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    logger.remove()
    logger.add(sys.stderr, format=log_format, level="INFO")
    logger.add(
        os.path.join(EnvironmentUtils.get_project_root(), "logs", "gcs_to_bigquery_{time:YYYY-MM-DD}.log"),
        format=log_format,
        rotation="1 day",
        level="DEBUG"
    )

def get_gcs_files(bucket_name, prefix=None):
    """
    指定されたGCSバケット内のファイル一覧を取得します
    
    Args:
        bucket_name (str): GCSバケット名
        prefix (str, optional): ファイルプレフィックス（フォルダパス）
        
    Returns:
        list: ファイルのURIリスト（gs://bucket_name/file_path 形式）
    """
    try:
        # GCSキーファイルのパスを解決
        gcs_key_path = EnvironmentUtils.get_env_var("GCS_KEY_PATH")
        key_path = Path(EnvironmentUtils.get_project_root()) / gcs_key_path
        
        if not key_path.exists():
            raise FileNotFoundError(f"GCS認証キーファイルが見つかりません: {key_path}")
        
        # 認証情報とクライアントを作成
        credentials = service_account.Credentials.from_service_account_file(key_path)
        storage_client = storage.Client(credentials=credentials)
        
        # バケットとブロブを取得
        bucket = storage_client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=prefix))
        
        # URIリストを作成して返却
        return [f"gs://{bucket_name}/{blob.name}" for blob in blobs if not blob.name.endswith('/')]
    
    except Exception as e:
        logger.error(f"GCSファイル一覧の取得中にエラーが発生しました: {str(e)}")
        raise

def load_gcs_files_to_bigquery(file_uris, table_name_prefix="", dataset_id=None, write_disposition="WRITE_TRUNCATE", use_character_map_v2=True):
    """
    GCSファイルのリストをBigQueryに読み込みます
    
    Args:
        file_uris (list): GCSファイルURIのリスト
        table_name_prefix (str, optional): 作成するテーブル名のプレフィックス
        dataset_id (str, optional): ロード先のデータセットID。Noneの場合は環境変数のデフォルト値を使用
        write_disposition (str, optional): テーブル書き込み設定。デフォルトはWRITE_TRUNCATE
        use_character_map_v2 (bool, optional): Character Map V2を使用するかどうか。デフォルトはTrue
        
    Returns:
        dict: ファイルURIをキー、ステータスを値とする辞書
    """
    results = {}
    
    # BigQueryクライアントを初期化
    client = BigQueryClient()
    
    logger.info(f"BigQueryクライアントを初期化しました: プロジェクト={client.project_id}, データセット={client.dataset_id}")
    
    # 各ファイルを処理
    for uri in file_uris:
        # GCSパスからファイル名を抽出 (例: gs://bucket_name/path/to/file.csv -> file)
        filename = os.path.basename(uri)
        filename_without_ext = os.path.splitext(filename)[0]
        
        # テーブル名を作成（プレフィックスがある場合は付加）
        if table_name_prefix:
            if table_name_prefix.endswith("_"):
                table_name = f"{table_name_prefix}{filename_without_ext}"
            else:
                table_name = f"{table_name_prefix}_{filename_without_ext}"
        else:
            table_name = filename_without_ext
            
        # BigQueryテーブル名で使用できない文字を置き換え
        table_name = table_name.replace("-", "_").replace(".", "_")
        
        # ロード処理を実行
        logger.info(f"ファイルのロードを開始: {uri} -> {table_name}")
        try:
            # BigQueryClientクラスでCharacter Map V2が常に有効になるように修正したため、
            # 直接load_from_gcsを呼び出す
            load_job = client.load_from_gcs(
                source_uri=uri,
                table_id=table_name,
                dataset_id=dataset_id,
                write_disposition=write_disposition
            )
            
            # 成功した場合
            if load_job is not None:
                logger.info(f"ファイル {uri} のロードに成功しました")
                results[uri] = "SUCCESS"
            else:
                # 成功したはずなのにNoneが返った場合はエラーと見なす
                logger.warning(f"ファイル {uri} のロードが不完全に終了した可能性があります")
                results[uri] = "WARNING: Incomplete operation"
                
        except Exception as e:
            error_message = str(e)
            logger.error(f"ファイルのロード中にエラーが発生: {uri}, エラー: {error_message}")
            
            # エラーメッセージをシンプルにして記録
            if "character map V2" in error_message.lower():
                error_code = "ERROR (Character Map V2)"
            elif "schema update options" in error_message.lower():
                error_code = "ERROR (Schema Update Options)"
            elif "field name" in error_message:
                error_code = "ERROR (Japanese Field Name)"
            else:
                error_code = f"ERROR: {error_message[:100]}..."  # 長いエラーメッセージを短縮
                
            results[uri] = error_code
            
            # 操作ログを記録
            try:
                client.log_operation(
                    operation_type="LOAD_FILE",
                    target_table=table_name,
                    status="ERROR",
                    details=error_message
                )
            except Exception:
                logger.warning("ログテーブルが設定されていないため、操作ログは記録されません")
    
    return results

def parse_arguments():
    """コマンドライン引数をパースします"""
    parser = argparse.ArgumentParser(description="GCSからBigQueryへのデータロード")
    
    # 必須引数
    parser.add_argument("--gcs-path", required=True, help="GCSのパス（例: gs://bucket_name/folder または bucket_name/folder）")
    
    # オプション引数
    parser.add_argument("--table-prefix", help="テーブル名のプレフィックス")
    parser.add_argument("--dataset", help="BigQueryデータセット名")
    parser.add_argument("--write-disposition", default="WRITE_TRUNCATE", 
                      choices=["WRITE_TRUNCATE", "WRITE_APPEND", "WRITE_EMPTY"],
                      help="書き込み設定（デフォルト: WRITE_TRUNCATE）")
    parser.add_argument("--file-pattern", help="ファイル名のパターン（例: *.csv, *.parquet）")
    
    return parser.parse_args()

def main():
    """メイン実行関数"""
    try:
        # 環境変数をロード
        EnvironmentUtils.load_env()
        
        # ロガーを設定
        setup_logger()
        
        logger.info("GCSからBigQueryへのデータロード処理を開始します")
        
        # コマンドライン引数を解析
        args = parse_arguments()
        
        # GCSパスを解析（gs://bucket_name/path または bucket_name/path の形式）
        if args.gcs_path.startswith("gs://"):
            bucket_path = args.gcs_path[5:]  # "gs://" を削除
            parts = bucket_path.split("/", 1)
            bucket_name = parts[0]
            prefix = parts[1] if len(parts) > 1 else None
        else:
            parts = args.gcs_path.split("/", 1)
            bucket_name = parts[0]
            prefix = parts[1] if len(parts) > 1 else None
        
        # 環境変数がない場合はデフォルトを使用
        if not bucket_name:
            bucket_name = EnvironmentUtils.get_env_var("GCS_BUCKET_NAME")
        
        logger.info(f"GCSバケット: {bucket_name}, パス: {prefix or '(ルート)'}")
        
        # GCSファイル一覧を取得
        file_uris = get_gcs_files(bucket_name, prefix)
        
        # ファイルパターンでフィルタリング
        if args.file_pattern:
            import fnmatch
            filtered_uris = []
            for uri in file_uris:
                file_name = os.path.basename(uri)
                if fnmatch.fnmatch(file_name, args.file_pattern):
                    filtered_uris.append(uri)
            file_uris = filtered_uris
        
        if not file_uris:
            logger.warning("指定されたパスにファイルが見つかりませんでした")
            return
        
        logger.info(f"ロード対象ファイル数: {len(file_uris)}")
        for uri in file_uris:
            logger.info(f"  - {uri}")
        
        # ファイルをBigQueryにロード
        results = load_gcs_files_to_bigquery(
            file_uris,
            table_name_prefix=args.table_prefix,
            dataset_id=args.dataset,
            write_disposition=args.write_disposition
        )
        
        # 結果サマリーをログに出力
        success_count = sum(1 for status in results.values() if status == "SUCCESS")
        logger.info(f"処理完了: 成功={success_count}/{len(file_uris)}")
        
        # エラーがあれば詳細を出力
        errors = {uri: error for uri, error in results.items() if error != "SUCCESS"}
        if errors:
            logger.error("エラーが発生したファイル:")
            for uri, error in errors.items():
                logger.error(f"  - {uri}: {error}")
    
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 