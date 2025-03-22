#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CSVファイルまたはJSONファイルからデータを読み込み、BigQueryテーブルにロードするスクリプト。
既存のBigQueryテーブルスキーマに合わせてデータを調整します。
日付形式の自動変換機能を備えており、BigQueryの要求形式（YYYY-MM-DD HH:MM:SS）に正しく変換します。
"""

import os
import sys
import argparse
import logging
import pandas as pd
import json
from datetime import datetime
import uuid
import time
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from dotenv import load_dotenv
from src.utils.environment import EnvironmentUtils as env

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_env_vars(env_file='config/secrets.env'):
    """環境変数ファイルを読み込む"""
    env.load_env(env_file)

def convert_date_format(date_str):
    """
    日付文字列をBigQueryのタイムスタンプ形式に変換
    例: '2023/3/26 0:05' -> '2023-03-26 00:05:00'
    
    Args:
        date_str: 変換対象の日付文字列またはdatetimeオブジェクト
        
    Returns:
        str: BigQuery互換形式の日付文字列、または変換できない場合はNone
    """
    if pd.isna(date_str) or not date_str:
        return None
    
    try:
        # datetimeオブジェクトの場合は直接フォーマット
        if isinstance(date_str, (datetime, pd.Timestamp)):
            return date_str.strftime('%Y-%m-%d %H:%M:%S')
            
        # 数値のように見える場合はNoneを返す
        if str(date_str).isdigit():
            return None
            
        # 複数の書式をパースしてみる
        for format_str in ['%Y/%m/%d %H:%M', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
            try:
                dt = datetime.strptime(str(date_str), format_str)
                # BigQuery互換形式に変換
                return dt.strftime('%Y-%m-%d %H:%M:%S') if 'H' in format_str else dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        logger.warning(f"日付の変換に失敗しました: {date_str}")
        return None
    except Exception as e:
        logger.warning(f"日付の変換中に例外が発生しました: {e}, 値: {date_str}")
        return None

def normalize_column_name(column_name):
    """
    カラム名をBigQuery互換の形式に正規化
    
    Args:
        column_name: 正規化対象のカラム名
        
    Returns:
        str: 正規化されたカラム名
    """
    # 括弧や特殊文字をアンダースコアに置き換える
    if isinstance(column_name, str):
        normalized = column_name.replace('(', '_').replace(')', '').replace(':', '_').replace(' ', '_')
        return normalized
    return column_name

def get_table_schema(client, table_ref):
    """
    BigQueryテーブルのスキーマを取得する
    
    Args:
        client: BigQuery クライアント
        table_ref: テーブル参照オブジェクト
    
    Returns:
        list: スキーマのフィールドリスト、テーブルが存在しない場合はNone
    """
    try:
        table = client.get_table(table_ref)
        logger.info(f"テーブル '{table.table_id}' のスキーマを取得しました")
        return table.schema
    except NotFound:
        logger.info(f"テーブル '{table_ref.table_id}' が存在しないため、スキーマを自動検出します。")
        return None

def adjust_data_to_schema(df, schema):
    """
    データフレームを既存のBigQueryスキーマに合わせて調整する
    
    Args:
        df: 調整対象のデータフレーム
        schema: BigQueryスキーマフィールドのリスト
    
    Returns:
        pandas.DataFrame: スキーマに合わせて調整されたデータフレーム
    """
    if schema is None:
        return df
    
    # スキーマのカラム名リストを作成
    schema_columns = [field.name for field in schema]
    logger.info(f"スキーマのカラム: {len(schema_columns)}個")
    logger.info(f"データフレームのカラム: {len(df.columns)}個")
    
    # 不足カラムを追加
    for column in schema_columns:
        if column not in df.columns:
            logger.info(f"カラム '{column}' をデータフレームに追加します")
            df[column] = None
    
    # データ型の変換
    for field in schema:
        if field.name in df.columns:
            if field.field_type == 'TIMESTAMP' and df[field.name].dtype != 'datetime64[ns]':
                logger.info(f"カラム '{field.name}' をTIMESTAMP型に変換します")
                # 日付/時間文字列をTIMESTAMP型に変換
                df[field.name] = df[field.name].apply(convert_date_format)
            elif field.field_type == 'DATE' and df[field.name].dtype != 'datetime64[ns]':
                logger.info(f"カラム '{field.name}' をDATE型に変換します")
                # 日付文字列をDATE型に変換
                df[field.name] = df[field.name].apply(lambda x: convert_date_format(x) if pd.notna(x) else None)
    
    # スキーマにないカラムを削除
    excess_columns = [col for col in df.columns if col not in schema_columns]
    if excess_columns:
        logger.info(f"余分なカラム {len(excess_columns)}個 を削除します: {excess_columns[:5]}...")
        df = df.drop(columns=excess_columns)
    
    # カラムの順序をスキーマと一致させる
    df = df[schema_columns]
    
    return df

def process_date_columns(df):
    """
    データフレーム内の日付カラムを明示的に処理する
    
    Args:
        df: 処理対象のデータフレーム
    
    Returns:
        pandas.DataFrame: 日付カラムが処理されたデータフレーム
    """
    # 処理対象のタイムスタンプカラム
    timestamp_columns = [
        'CV時間', '直接効果_発生日時', '間接効果2_発生日時', '間接効果3_発生日時',
        '間接効果4_発生日時', '間接効果5_発生日時', '間接効果6_発生日時',
        '間接効果7_発生日時', '間接効果8_発生日時', '間接効果9_発生日時',
        '間接効果10_発生日時', '初回接触_発生日時'
    ]
    
    # 各タイムスタンプカラムを処理
    for col in timestamp_columns:
        if col in df.columns:
            try:
                logger.info(f"カラム '{col}' を明示的に変換します")
                # pd.to_datetimeを使用して日付を変換し、その後文字列に戻す
                df[col] = pd.to_datetime(df[col], errors='coerce')
                df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                logger.warning(f"カラム '{col}' の変換中にエラーが発生しました: {e}")
    
    return df

def load_data_to_bigquery(file_path, table_name, write_disposition='WRITE_TRUNCATE'):
    """
    CSVまたはJSONファイルからデータを読み込み、BigQueryにロードする
    
    Args:
        file_path: CSVまたはJSONファイルのパス
        table_name: ロード先のテーブル名（形式: データセット.テーブル）
        write_disposition: 書き込み方法（デフォルト: WRITE_TRUNCATE）
        
    Returns:
        bool: 処理が成功した場合はTrue、失敗した場合はFalse
    """
    # 一時ファイルのパスを生成（ユニークなID + タイムスタンプ）
    temp_file = f"temp_data_{int(time.time())}_{uuid.uuid4().hex[:8]}.json"
    
    try:
        # 環境変数とBigQuery設定の読み込み
        env.load_env()
        bigquery_settings = env.get_bigquery_settings()
        
        # ファイル拡張子を確認
        _, file_extension = os.path.splitext(file_path)
        
        # ファイルの種類に応じてデータを読み込む
        if file_extension.lower() == '.csv':
            logger.info(f"CSVファイル '{file_path}' を読み込んでいます...")
            df = pd.read_csv(file_path, encoding='cp932')
            logger.info(f"CSVファイルを正常に読み込みました。行数: {len(df)}")
        elif file_extension.lower() == '.json':
            logger.info(f"JSONファイル '{file_path}' を読み込んでいます...")
            df = pd.read_json(file_path, lines=True)
            logger.info(f"JSONファイルを正常に読み込みました。行数: {len(df)}")
        else:
            logger.error(f"サポートされていないファイル形式です: {file_extension}")
            return False
        
        # データサンプルを表示
        logger.info(f"データサンプル:\n{df.head()}")
        
        # カラム名を正規化
        df.columns = [normalize_column_name(col) for col in df.columns]
        
        # BigQueryクライアントを初期化
        client = bigquery.Client.from_service_account_json(bigquery_settings["key_path"])
        
        # プロジェクトIDとデータセットIDを取得
        project_id = bigquery_settings["project_id"]
        
        # データセット.テーブル名を分割
        if '.' in table_name:
            dataset_id, table_id = table_name.split('.')
        else:
            dataset_id = bigquery_settings["dataset_id"]  # デフォルトのデータセット
            table_id = table_name
        
        # テーブル参照を作成
        table_ref = f"{project_id}.{dataset_id}.{table_id}"
        
        # 既存のテーブルのスキーマを取得
        try:
            table = client.get_table(table_ref)
            schema = table.schema
            logger.info(f"テーブル '{table_id}' のスキーマを取得しました")
        except NotFound:
            schema = None
            logger.info(f"テーブル '{table_id}' が存在しないため、スキーマを自動検出します。")
        
        # データをスキーマに合わせて調整（この時点で基本的な日付型の変換も行う）
        if schema:
            df = adjust_data_to_schema(df, schema)
        
        # 日付カラムを明示的に処理
        df = process_date_columns(df)
        
        # 一時ファイルにデータを保存
        df.to_json(temp_file, orient='records', lines=True, force_ascii=False)
        logger.info(f"一時ファイル {temp_file} にデータを保存しました。")
        
        # ロードジョブの設定
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=getattr(bigquery.WriteDisposition, write_disposition)
        )
        
        # スキーマが存在する場合、それを使用
        if schema:
            logger.info(f"既存のテーブル '{table_name}' のスキーマを使用します。")
            job_config.schema = schema
        else:
            logger.info(f"テーブル '{table_name}' のスキーマを自動検出します。")
            job_config.autodetect = True
        
        # ファイルをロード
        with open(temp_file, "rb") as source_file:
            job = client.load_table_from_file(
                source_file,
                table_ref,
                job_config=job_config
            )
        
        # ジョブの完了を待機
        job.result()
        
        # 一時ファイルを削除
        os.remove(temp_file)
        logger.info(f"一時ファイル '{temp_file}' を削除しました。")
        
        logger.info(f"BigQueryテーブル '{table_name}' に {len(df)} 行のデータをロードしました。")
        return True
    
    except Exception as e:
        logger.error(f"データロード中に例外が発生しました: {e}")
        # エラー発生時も一時ファイルを削除
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                logger.info(f"一時ファイル '{temp_file}' を削除しました。")
            except Exception as e2:
                logger.warning(f"一時ファイル '{temp_file}' の削除に失敗しました: {e2}")
        return False

def main():
    """メイン処理関数"""
    # 引数の解析
    parser = argparse.ArgumentParser(description='CSVまたはJSONファイルからデータを読み込み、BigQueryにロードします')
    parser.add_argument('file_path', help='入力CSVまたはJSONファイルのパス')
    parser.add_argument('table_name', help='ロード先のテーブル名（形式: データセット.テーブル）')
    parser.add_argument('--write-disposition', choices=['WRITE_TRUNCATE', 'WRITE_APPEND', 'WRITE_EMPTY'], 
                        default='WRITE_TRUNCATE', help='書き込み方法（デフォルト: WRITE_TRUNCATE）')
    parser.add_argument('--env-file', default='config/secrets.env', 
                        help='環境変数ファイルのパス（デフォルト: config/secrets.env）')
    
    args = parser.parse_args()
    
    # 環境変数を読み込む
    load_env_vars(args.env_file)
    
    # 入力ファイルの存在確認
    if not os.path.exists(args.file_path):
        logger.error(f"入力ファイル '{args.file_path}' が見つかりません")
        sys.exit(1)
    
    # データのロード
    if load_data_to_bigquery(args.file_path, args.table_name, args.write_disposition):
        logger.info("データのロードが成功しました")
    else:
        logger.error("データのロードに失敗しました")
        sys.exit(1)

if __name__ == '__main__':
    main() 