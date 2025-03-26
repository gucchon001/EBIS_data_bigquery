#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BigQueryへのテストロード用スクリプト
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.utils.environment import EnvironmentUtils as env
from src.modules.bigquery.process_cv_data import process_cv_data

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """メイン処理"""
    try:
        # 環境変数の読み込み
        env.load_env()
        
        # CSVファイルのパス
        csv_file = os.path.join(project_root, "data", "downloads", "20250325_ebis_CVrepo.csv")
        
        # BigQueryのテーブル設定
        config = env.get_config_file()
        dataset = config.get('bigquery', 'dataset')
        table = config.get('bigquery', 'table')
        table_name = f"{dataset}.{table}"
        
        logger.info(f"テストロードを開始します: {csv_file} → {table_name}")
        
        # CSVファイルを処理してBigQueryにロード
        if process_cv_data(csv_file):
            logger.info("テストロードが正常に完了しました")
            return 0
        else:
            logger.error("テストロードに失敗しました")
            return 1
            
    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生しました: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())