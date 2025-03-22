#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AE_SSresultデータの前処理付きBigQueryロード

AE_SSresultディレクトリのファイルをカラム名前処理してからBigQueryにロードします。
カッコや特殊文字を含むカラム名を修正し、BigQueryでのロードエラーを回避します。
"""

import os
import sys
import argparse
from loguru import logger

# プロジェクトのルートディレクトリをシステムパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.utils.environment import EnvironmentUtils
from src.modules.bigquery.load_preprocessed_files import load_preprocessed_files_to_bigquery
from src.old.gcs_to_bigquery import setup_logger

def main():
    """AE_SSresultデータの前処理付きBigQueryロード処理"""
    try:
        # 環境変数をロード
        EnvironmentUtils.load_env()
        
        # ロガーを設定
        setup_logger()
        
        logger.info("AE_SSresultデータの前処理付きBigQueryロード処理を開始します")
        
        # コマンドライン引数の解析
        parser = argparse.ArgumentParser(description="AE_SSresultデータの前処理付きBigQueryロード")
        parser.add_argument("--table-prefix", default="ae_ssresult", help="テーブル名のプレフィックス（デフォルト: ae_ssresult）")
        parser.add_argument("--dataset", help="BigQueryデータセット名（指定しない場合は環境変数のデフォルト値を使用）")
        parser.add_argument("--file-type", choices=["csv", "parquet", "all"], default="all", 
                          help="ロードするファイルタイプ（デフォルト: all）")
        parser.add_argument("--write-disposition", default="WRITE_TRUNCATE", 
                          choices=["WRITE_TRUNCATE", "WRITE_APPEND", "WRITE_EMPTY"],
                          help="書き込み設定（デフォルト: WRITE_TRUNCATE）")
        
        args = parser.parse_args()
        
        # GCSバケット名を取得
        bucket_name = EnvironmentUtils.get_env_var("GCS_BUCKET_NAME")
        if not bucket_name:
            raise ValueError("GCS_BUCKET_NAME環境変数が設定されていません")
        
        # GCS上のAE_SSresultディレクトリパス
        gcs_path = f"gs://{bucket_name}/AE_SSresult"
        
        # ファイルパターンの設定
        file_pattern = None
        if args.file_type != "all":
            file_pattern = f"*.{args.file_type}"
        
        # 前処理付きロード実行
        logger.info(f"GCS パス: {gcs_path}")
        logger.info(f"ファイルタイプ: {args.file_type}")
        
        results = load_preprocessed_files_to_bigquery(
            gcs_path=gcs_path,
            table_prefix=args.table_prefix,
            dataset_id=args.dataset,
            file_pattern=file_pattern,
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