#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
前処理済みGCSファイルのBigQueryロード

GCSファイルのカラム名を前処理してからBigQueryにロードします。
カッコや特殊文字を含むカラム名を修正し、BigQueryでのロードエラーを回避します。
"""

import os
import sys
import argparse
from loguru import logger

# プロジェクトのルートディレクトリをシステムパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.utils.environment import EnvironmentUtils
from src.modules.bigquery.preprocess_gcs_files import GCSFilePreprocessor
from src.old.gcs_to_bigquery import get_gcs_files, load_gcs_files_to_bigquery, setup_logger

def load_preprocessed_files_to_bigquery(gcs_path, table_prefix=None, dataset_id=None, file_pattern=None, write_disposition="WRITE_TRUNCATE"):
    """
    GCSファイルを前処理してからBigQueryにロードします
    
    Args:
        gcs_path (str): GCSのパス（例: gs://bucket_name/folder または bucket_name/folder）
        table_prefix (str, optional): テーブル名のプレフィックス
        dataset_id (str, optional): BigQueryデータセットID
        file_pattern (str, optional): ファイル名パターン（例: '*.csv'）
        write_disposition (str, optional): 書き込み設定
        
    Returns:
        dict: 処理結果の辞書
    """
    # GCSパスを解析
    if gcs_path.startswith("gs://"):
        bucket_path = gcs_path[5:]  # "gs://" を削除
        parts = bucket_path.split("/", 1)
        bucket_name = parts[0]
        prefix = parts[1] if len(parts) > 1 else None
    else:
        parts = gcs_path.split("/", 1)
        bucket_name = parts[0]
        prefix = parts[1] if len(parts) > 1 else None
    
    # 環境変数がない場合はデフォルトを使用
    if not bucket_name:
        bucket_name = EnvironmentUtils.get_env_var("GCS_BUCKET_NAME")
    
    logger.info(f"GCSバケット: {bucket_name}, パス: {prefix or '(ルート)'}")
    
    # GCSファイル一覧を取得
    file_uris = get_gcs_files(bucket_name, prefix)
    
    # ファイルパターンでフィルタリング
    if file_pattern:
        import fnmatch
        filtered_uris = []
        for uri in file_uris:
            file_name = os.path.basename(uri)
            if fnmatch.fnmatch(file_name, file_pattern):
                filtered_uris.append(uri)
        file_uris = filtered_uris
    
    if not file_uris:
        logger.warning("指定されたパスにファイルが見つかりませんでした")
        return {}
    
    logger.info(f"処理対象ファイル数: {len(file_uris)}")
    for uri in file_uris:
        logger.info(f"  - {uri}")
    
    # 前処理とロードの結果を格納する辞書
    results = {}
    
    # GCSファイル前処理クラスを初期化
    preprocessor = GCSFilePreprocessor()
    
    try:
        # 各ファイルを処理
        for uri in file_uris:
            try:
                # ファイルの前処理
                logger.info(f"ファイルの前処理を開始: {uri}")
                processed_uri = preprocessor.preprocess_file(uri)
                
                # 前処理に成功したら、BigQueryにロード
                if processed_uri:
                    logger.info(f"前処理済みファイルをBigQueryにロード: {processed_uri}")
                    load_results = load_gcs_files_to_bigquery(
                        [processed_uri],
                        table_name_prefix=table_prefix,
                        dataset_id=dataset_id,
                        write_disposition=write_disposition
                    )
                    
                    # 結果を統合
                    for processed_uri, status in load_results.items():
                        # 元のURIをキーとして保存
                        results[uri] = status
                else:
                    logger.error(f"ファイルの前処理に失敗: {uri}")
                    results[uri] = "ERROR: Preprocessing failed"
                    
            except Exception as e:
                logger.error(f"ファイル {uri} の処理中にエラーが発生: {str(e)}")
                results[uri] = f"ERROR: {str(e)}"
    finally:
        # 前処理で使用した一時ファイルをクリーンアップ
        preprocessor.cleanup()
    
    # 結果サマリーをログに出力
    success_count = sum(1 for status in results.values() if "SUCCESS" in status)
    logger.info(f"処理完了: 成功={success_count}/{len(file_uris)}")
    
    # エラーがあれば詳細を出力
    errors = {uri: error for uri, error in results.items() if "SUCCESS" not in error}
    if errors:
        logger.error("エラーが発生したファイル:")
        for uri, error in errors.items():
            logger.error(f"  - {uri}: {error}")
    
    return results

def main():
    """メイン実行関数"""
    try:
        # 環境変数をロード
        EnvironmentUtils.load_env()
        
        # ロガーを設定
        setup_logger()
        
        logger.info("カラム名前処理付きGCSからBigQueryへのデータロード処理を開始します")
        
        # コマンドライン引数の解析
        parser = argparse.ArgumentParser(description="カラム名前処理付きGCSからBigQueryへのデータロード")
        parser.add_argument("--gcs-path", required=True, help="GCSのパス（例: gs://bucket_name/folder または bucket_name/folder）")
        parser.add_argument("--table-prefix", help="テーブル名のプレフィックス")
        parser.add_argument("--dataset", help="BigQueryデータセット名")
        parser.add_argument("--file-pattern", help="ファイル名のパターン（例: *.csv, *.parquet）")
        parser.add_argument("--write-disposition", default="WRITE_TRUNCATE", 
                          choices=["WRITE_TRUNCATE", "WRITE_APPEND", "WRITE_EMPTY"],
                          help="書き込み設定（デフォルト: WRITE_TRUNCATE）")
        
        args = parser.parse_args()
        
        # 前処理付きロード実行
        results = load_preprocessed_files_to_bigquery(
            gcs_path=args.gcs_path,
            table_prefix=args.table_prefix,
            dataset_id=args.dataset,
            file_pattern=args.file_pattern,
            write_disposition=args.write_disposition
        )
        
        # エラーがあれば終了コードで示す
        if any("ERROR" in status for status in results.values()):
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 