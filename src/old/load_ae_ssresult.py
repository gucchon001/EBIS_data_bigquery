#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AE_SSresultデータのBigQueryロード

data/AE_SSresultディレクトリに存在するファイルをGCSを介してBigQueryにロードします。
これは特定の処理に特化した簡易実行用スクリプトです。
"""

import os
import sys
from pathlib import Path

# プロジェクトのルートディレクトリをシステムパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import argparse
from loguru import logger

from src.utils.environment import EnvironmentUtils
from src.old.gcs_to_bigquery import load_gcs_files_to_bigquery, get_gcs_files, setup_logger

def main():
    """AE_SSresultデータのBigQueryロード処理"""
    try:
        # 環境変数をロード
        EnvironmentUtils.load_env()
        
        # ロガーを設定
        setup_logger()
        
        logger.info("AE_SSresultデータのBigQueryロード処理を開始します")
        
        # コマンドライン引数の解析
        parser = argparse.ArgumentParser(description="AE_SSresultデータのBigQueryロード")
        parser.add_argument("--table-prefix", default="ae_ssresult", help="テーブル名のプレフィックス（デフォルト: ae_ssresult）")
        parser.add_argument("--dataset", help="BigQueryデータセット名（指定しない場合は環境変数のデフォルト値を使用）")
        parser.add_argument("--file-type", choices=["csv", "parquet", "all"], default="all", 
                          help="ロードするファイルタイプ（デフォルト: all）")
        parser.add_argument("--write-disposition", default="WRITE_TRUNCATE", 
                          choices=["WRITE_TRUNCATE", "WRITE_APPEND", "WRITE_EMPTY"],
                          help="書き込み設定（デフォルト: WRITE_TRUNCATE）")
        parser.add_argument("--use-character-map-v2", action="store_true", default=True,
                          help="Character Map V2を使用して日本語フィールド名を適切に処理（デフォルト: 有効）")
        
        args = parser.parse_args()
        
        # GCSバケット名を取得
        bucket_name = EnvironmentUtils.get_env_var("GCS_BUCKET_NAME")
        if not bucket_name:
            raise ValueError("GCS_BUCKET_NAME環境変数が設定されていません")
        
        # GCS上のAE_SSresultディレクトリパス
        prefix = "AE_SSresult"
        
        # GCSファイル一覧を取得
        logger.info(f"GCSバケット '{bucket_name}' からファイル一覧を取得中...")
        file_uris = get_gcs_files(bucket_name, prefix)
        
        if not file_uris:
            logger.warning(f"GCS上のパス 'gs://{bucket_name}/{prefix}' にファイルが見つかりませんでした")
            return
        
        # ファイルタイプによるフィルタリング
        if args.file_type != "all":
            file_uris = [uri for uri in file_uris if uri.endswith(f".{args.file_type}")]
        
        if not file_uris:
            logger.warning(f"指定されたファイルタイプ '{args.file_type}' に一致するファイルが見つかりませんでした")
            return
        
        # ロード対象ファイルのリストを表示
        logger.info(f"BigQueryへのロード対象ファイル数: {len(file_uris)}")
        for uri in file_uris:
            logger.info(f"  - {uri}")
        
        # ファイルをBigQueryにロード
        results = load_gcs_files_to_bigquery(
            file_uris,
            table_name_prefix=args.table_prefix,
            dataset_id=args.dataset,
            write_disposition=args.write_disposition,
            use_character_map_v2=args.use_character_map_v2
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
            
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 