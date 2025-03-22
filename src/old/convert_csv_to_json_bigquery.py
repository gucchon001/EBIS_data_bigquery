#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CSVファイルを読み込み、BigQueryに適したフォーマットでJSONファイルに変換するスクリプト。
日付/時間フィールドをBigQueryのタイムスタンプ形式に変換します。
"""

import os
import sys
import argparse
import logging
import pandas as pd
import json
from datetime import datetime

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def convert_date_format(date_str):
    """
    日付文字列をBigQueryのタイムスタンプ形式に変換
    例: '2023/3/26 0:05' -> '2023-03-26 00:05:00'
    """
    if pd.isna(date_str) or not date_str:
        return None
    
    try:
        # 元の日付形式を解析 (時間あり)
        dt = datetime.strptime(date_str, '%Y/%m/%d %H:%M')
        # BigQuery互換形式に変換
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        # 時間なしの日付形式を試す
        try:
            dt = datetime.strptime(date_str, '%Y/%m/%d')
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            # さらに別の形式を試す
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    logger.warning(f"日付の変換に失敗しました: {date_str}")
                    return None

def convert_simple_date_format(date_str):
    """
    単純な日付文字列をBigQueryの日付形式に変換
    例: '2003/4/8' -> '2003-04-08'
    """
    if pd.isna(date_str) or not date_str:
        return None
    
    try:
        # 様々な日付形式を試す
        formats = ['%Y/%m/%d', '%Y-%m-%d', '%Y/%m', '%Y-%m', '%Y年%m月%d日']
        for fmt in formats:
            try:
                dt = datetime.strptime(str(date_str), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # 数字のみの場合にスラッシュを挿入して再試行
        if isinstance(date_str, str) and '/' not in date_str and '-' not in date_str:
            if len(date_str) == 8:  # YYYYMMDD
                try:
                    dt = datetime.strptime(date_str, '%Y%m%d')
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    pass
        
        logger.warning(f"日付の変換に失敗しました: {date_str}")
        return None
    except Exception as e:
        logger.warning(f"日付の変換中にエラーが発生しました: {date_str}, エラー: {str(e)}")
        return None

def normalize_column_name(column_name):
    """
    カラム名をBigQuery互換の形式に正規化
    """
    # 括弧や特殊文字をアンダースコアに置き換える
    if isinstance(column_name, str):
        normalized = column_name.replace('(', '_').replace(')', '').replace(':', '_').replace(' ', '_')
        return normalized
    return column_name

def convert_csv_to_json(csv_file, json_file, encoding='cp932', limit=None):
    """
    CSVファイルをBigQuery互換のJSONファイルに変換
    """
    try:
        # CSVファイルを読み込み
        logger.info(f"CSVファイル '{csv_file}' を読み込みます（エンコーディング: {encoding}）")
        
        # ヘッダーを含む最初のn行を読み込む
        if limit:
            df = pd.read_csv(csv_file, encoding=encoding, nrows=limit)
            logger.info(f"最初の {limit} 行を読み込みました")
        else:
            df = pd.read_csv(csv_file, encoding=encoding)
            logger.info(f"全 {len(df)} 行を読み込みました")
        
        # データサンプルを表示
        logger.info(f"データサンプル:\n{df.head(2)}")
        
        # カラム名を正規化
        df.columns = [normalize_column_name(col) for col in df.columns]
        
        # タイムスタンプフィールドの変換
        timestamp_columns = ['CV時間', '直接効果_発生日時', '間接効果2_発生日時', '間接効果3_発生日時', 
                         '間接効果4_発生日時', '間接効果5_発生日時', '間接効果6_発生日時',
                         '間接効果7_発生日時', '間接効果8_発生日時', '間接効果9_発生日時',
                         '間接効果10_発生日時', '初回接触_発生日時']
        
        # 日付のみのフィールドの変換
        date_columns = ['項目4']
        
        for col in timestamp_columns:
            if col in df.columns:
                logger.info(f"タイムスタンプカラム '{col}' の日付形式を変換します")
                df[col] = df[col].apply(convert_date_format)
        
        for col in date_columns:
            if col in df.columns:
                logger.info(f"日付カラム '{col}' の日付形式を変換します")
                df[col] = df[col].apply(convert_simple_date_format)
        
        # JSONに変換して保存
        # orient='records'でレコードごとにJSONオブジェクトを作成
        # lines=Trueで各レコードを改行区切りで出力（BigQuery newline-delimited JSON形式）
        df.to_json(json_file, orient='records', lines=True, force_ascii=False)
        logger.info(f"JSONファイル '{json_file}' に保存しました")
        
        return True
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return False

def main():
    # 引数の解析
    parser = argparse.ArgumentParser(description='CSVファイルをBigQuery互換のJSONファイルに変換します')
    parser.add_argument('csv_file', help='入力CSVファイルのパス')
    parser.add_argument('json_file', help='出力JSONファイルのパス')
    parser.add_argument('--encoding', default='cp932', help='CSVファイルのエンコーディング（デフォルト: cp932）')
    parser.add_argument('--limit', type=int, help='読み込む最大行数')
    
    args = parser.parse_args()
    
    # 入力ファイルの存在確認
    if not os.path.exists(args.csv_file):
        logger.error(f"入力ファイル '{args.csv_file}' が見つかりません")
        sys.exit(1)
    
    # 変換の実行
    if convert_csv_to_json(args.csv_file, args.json_file, args.encoding, args.limit):
        logger.info("変換が正常に完了しました")
    else:
        logger.error("変換に失敗しました")
        sys.exit(1)

if __name__ == '__main__':
    main() 