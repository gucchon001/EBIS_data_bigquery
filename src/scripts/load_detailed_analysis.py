#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
詳細分析レポートデータをBigQueryにロードするスクリプト

このスクリプトは、CSVファイルから詳細分析レポートデータを読み込み、
BigQueryにロードする処理を実行します。
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# プロジェクトルートのパスを追加
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from src.utils.environment import EnvironmentUtils
from src.utils.logging_config import configure_logging
from src.modules.bigquery.data_loader import load_detailed_analysis_data

def parse_arguments():
    """
    コマンドライン引数の解析
    
    Returns:
        解析された引数
    """
    parser = argparse.ArgumentParser(description='詳細分析レポートデータをBigQueryにロードします')
    parser.add_argument('--csv', '-c', required=True, help='ロードするCSVファイルのパス')
    parser.add_argument('--log-level', '-l', default='INFO', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='ログレベル')
    
    return parser.parse_args()

def main():
    """
    メイン処理
    """
    # コマンドライン引数の解析
    args = parse_arguments()
    
    # 環境変数の読み込み
    EnvironmentUtils.load_env()
    
    # ログの設定
    log_dir = os.path.join(project_root, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'detailed_analysis_load_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    configure_logging(log_file, console_level=args.log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("詳細分析レポートデータのロード処理を開始します")
    
    try:
        # CSVファイルのパスを検証
        csv_file_path = args.csv
        resolved_path = EnvironmentUtils.resolve_path(csv_file_path)
        if not os.path.exists(resolved_path):
            logger.error(f"CSVファイルが見つかりません: {csv_file_path}")
            return 1
        
        logger.info(f"CSVファイル: {csv_file_path} を処理します")
        
        # データロード処理の実行
        loaded_rows = load_detailed_analysis_data(csv_file_path)
        
        if loaded_rows > 0:
            logger.info(f"正常に {loaded_rows} 行のデータをロードしました")
        else:
            logger.info("新しくロードされたデータはありません")
        
        return 0
    
    except Exception as e:
        logger.exception(f"データロード中にエラーが発生しました: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 