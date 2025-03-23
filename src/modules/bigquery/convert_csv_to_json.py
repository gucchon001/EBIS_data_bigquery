#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CSVファイルをJSONファイルに変換するスクリプト。
cp932エンコーディングでCSVを読み込み、指定した形式のJSONファイルを出力します。
行数を指定して変換することも可能です。
"""

import os
import sys
import argparse
import logging
import pandas as pd
from pathlib import Path
from src.utils.environment import EnvironmentUtils as env

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def convert_csv_to_json(csv_file, json_file=None, encoding='cp932', nrows=None, orient='records', lines=True):
    """
    CSVファイルをJSONファイルに変換する
    
    Args:
        csv_file (str): 入力CSVファイルのパス
        json_file (str, optional): 出力JSONファイルのパス。Noneの場合は入力ファイル名に基づいて自動生成
        encoding (str, optional): CSVファイルのエンコーディング（デフォルト: cp932）
        nrows (int, optional): 変換する行数。Noneの場合は全行変換
        orient (str, optional): JSON形式の指定（デフォルト: records）
        lines (bool, optional): 行区切りJSONを出力するかどうか（デフォルト: True）
        
    Returns:
        str: 出力されたJSONファイルのパス
    """
    try:
        # CSVファイルの存在確認
        if not os.path.exists(csv_file):
            logger.error(f"CSVファイル '{csv_file}' が見つかりません")
            return None
            
        # 出力ファイルパスの設定
        if json_file is None:
            csv_path = Path(csv_file)
            if nrows:
                json_file = f"{csv_path.parent}/{csv_path.stem}_{nrows}records.json"
            else:
                json_file = f"{csv_path.parent}/{csv_path.stem}.json"
        
        # CSVファイルを読み込む
        logger.info(f"CSVファイル '{csv_file}' を読み込み中...")
        read_args = {'encoding': encoding, 'low_memory': False}
        if nrows:
            read_args['nrows'] = nrows
            logger.info(f"最初の {nrows} 行を読み込みます")
        
        df = pd.read_csv(csv_file, **read_args)
        logger.info(f"CSVファイルを読み込みました: {len(df)} 行")
        
        # データサンプルを表示
        logger.info(f"データサンプル:\n{df.head(3)}")
        
        # JSONファイルに保存
        df.to_json(json_file, orient=orient, lines=lines, force_ascii=False)
        logger.info(f"JSONファイル '{json_file}' を作成しました")
        
        return json_file
        
    except Exception as e:
        logger.error(f"変換中にエラーが発生しました: {e}")
        # スタックトレースを出力
        import traceback
        logger.error(f"エラー詳細: {traceback.format_exc()}")
        return None

def main():
    """メイン処理関数"""
    # 引数の解析
    parser = argparse.ArgumentParser(description='CSVファイルをJSONファイルに変換します')
    parser.add_argument('csv_file', help='入力CSVファイルのパス')
    parser.add_argument('--json-file', help='出力JSONファイルのパス（デフォルト: 入力ファイル名に基づいて自動生成）')
    parser.add_argument('--encoding', default='cp932', help='CSVファイルのエンコーディング（デフォルト: cp932）')
    parser.add_argument('--nrows', type=int, help='変換する行数（デフォルト: 全行）')
    parser.add_argument('--orient', default='records', choices=['records', 'columns', 'index', 'split', 'table'], 
                        help='JSON形式の指定（デフォルト: records）')
    parser.add_argument('--no-lines', action='store_false', dest='lines', 
                        help='行区切りJSONを使用しない（デフォルト: 行区切りJSON）')
    
    args = parser.parse_args()
    
    # 環境変数を読み込む
    env.load_env()
    
    # CSVをJSONに変換
    json_file = convert_csv_to_json(
        args.csv_file, 
        args.json_file, 
        args.encoding, 
        args.nrows, 
        args.orient, 
        args.lines
    )
    
    if json_file:
        logger.info(f"変換が完了しました: {json_file}")
        return 0
    else:
        logger.error("変換に失敗しました")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 