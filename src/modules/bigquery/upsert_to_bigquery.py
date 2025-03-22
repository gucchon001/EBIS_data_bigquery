#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CSVファイルまたはJSONファイルからデータを読み込み、応募IDをキーとしてBigQueryテーブルにアップサート（更新または挿入）するスクリプト。
同じ応募IDが存在する場合は既存レコードを上書きし、存在しない場合は新規レコードを挿入します。
一時テーブルとマージ操作を使用して実装しています。
"""

import os
import sys
import argparse
import logging
import pandas as pd
import uuid
import time
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from src.utils.environment import EnvironmentUtils as env
from src.modules.bigquery.load_to_bigquery_fixed import convert_date_format, normalize_column_name, process_date_columns

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_all_date_columns(df, schema):
    """
    データフレームの全ての日付カラムをBigQueryスキーマに合わせて適切に変換する
    
    Args:
        df: 処理対象のデータフレーム
        schema: BigQueryテーブルのスキーマ
    
    Returns:
        pandas.DataFrame: 日付カラムが適切に変換されたデータフレーム
    """
    for field in schema:
        if field.name in df.columns:
            if field.field_type == 'DATE':
                logger.info(f"DATE型カラム '{field.name}' を変換します")
                try:
                    # まずpd.to_datetimeで変換
                    df[field.name] = pd.to_datetime(df[field.name], errors='coerce')
                    # DATEフォーマットに変換
                    df[field.name] = df[field.name].dt.strftime('%Y-%m-%d')
                except Exception as e:
                    logger.warning(f"DATE型カラム '{field.name}' の変換中にエラーが発生しました: {e}")
                    
            elif field.field_type == 'TIMESTAMP':
                logger.info(f"TIMESTAMP型カラム '{field.name}' を変換します")
                try:
                    # まずpd.to_datetimeで変換
                    df[field.name] = pd.to_datetime(df[field.name], errors='coerce')
                    # TIMESTAMPフォーマットに変換
                    df[field.name] = df[field.name].dt.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    logger.warning(f"TIMESTAMP型カラム '{field.name}' の変換中にエラーが発生しました: {e}")
    
    return df

def adjust_data_to_schema_columns(df, schema):
    """
    データフレームのカラムをスキーマと一致させる
    
    Args:
        df: 処理対象のデータフレーム
        schema: BigQueryテーブルのスキーマ
    
    Returns:
        pandas.DataFrame: カラムがスキーマと一致したデータフレーム
    """
    # スキーマのカラム名リストを作成
    schema_columns = [field.name for field in schema]
    logger.info(f"スキーマのカラム: {len(schema_columns)}個")
    logger.info(f"データフレームのカラム: {len(df.columns)}個")
    
    # 不足カラムを追加
    for column in schema_columns:
        if column not in df.columns:
            logger.info(f"カラム '{column}' をデータフレームに追加します")
            df[column] = None
    
    # スキーマにないカラムを削除
    excess_columns = [col for col in df.columns if col not in schema_columns]
    if excess_columns:
        logger.info(f"余分なカラム {len(excess_columns)}個 を削除します: {excess_columns[:5]}...")
        df = df.drop(columns=excess_columns)
    
    # カラムの順序をスキーマと一致させる
    df = df[schema_columns]
    
    return df

def upsert_data_to_bigquery(file_path, table_name, key_column='応募ID'):
    """
    CSVまたはJSONファイルからデータを読み込み、キーカラム（応募ID）に基づいて
    BigQueryテーブルにアップサート（更新または挿入）する
    
    Args:
        file_path: CSVまたはJSONファイルのパス
        table_name: ロード先のテーブル名（形式: データセット.テーブル）
        key_column: 更新キーとなるカラム名（デフォルト: 応募ID）
        
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
        
        # キーカラムの存在を確認
        if key_column not in df.columns:
            logger.error(f"キーカラム '{key_column}' がデータに存在しません")
            return False
            
        # キーカラムのNullチェック
        null_keys = df[df[key_column].isnull()].shape[0]
        if null_keys > 0:
            logger.warning(f"キーカラム '{key_column}' に {null_keys} 個のNULL値が存在します。これらは正しく更新されない可能性があります。")
        
        # カラム名を正規化
        df.columns = [normalize_column_name(col) for col in df.columns]
        normalized_key_column = normalize_column_name(key_column)
        
        # BigQueryクライアントを初期化
        client = bigquery.Client.from_service_account_json(bigquery_settings["key_path"])
        
        # データセット.テーブル名を分割
        if '.' in table_name:
            dataset_id, table_id = table_name.split('.')
        else:
            dataset_id = bigquery_settings["dataset_id"]  # デフォルトのデータセット
            table_id = table_name
        
        # 対象テーブルとデータセットの参照を作成
        dataset_ref = client.dataset(dataset_id)
        table_ref = dataset_ref.table(table_id)
        destination_table = f"{bigquery_settings['project_id']}.{dataset_id}.{table_id}"
        
        try:
            # テーブルの存在確認とスキーマ取得
            target_table = client.get_table(table_ref)
            schema = target_table.schema
            logger.info(f"テーブル '{table_id}' のスキーマを取得しました（{len(schema)}カラム）")
            
            # スキーマに合わせて日付カラムを明示的に処理
            df = process_all_date_columns(df, schema)
            
            # カラムをスキーマと一致させる
            df = adjust_data_to_schema_columns(df, schema)
            
            # 一時テーブル名を生成（テーブル名 + ランダムな文字列）
            temp_table_id = f"{table_id}_temp_{uuid.uuid4().hex[:8]}"
            temp_table_ref = dataset_ref.table(temp_table_id)
            temp_table_full = f"{bigquery_settings['project_id']}.{dataset_id}.{temp_table_id}"
            
            # 一時ファイルにデータを保存
            df.to_json(temp_file, orient='records', lines=True, force_ascii=False)
            logger.info(f"一時ファイル {temp_file} にデータを保存しました。")
            
            # 一時テーブルにデータをロード
            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                schema=schema
            )
            
            # 一時テーブルにロード
            with open(temp_file, "rb") as source_file:
                job = client.load_table_from_file(
                    source_file,
                    temp_table_ref,
                    job_config=job_config
                )
            job.result()  # ロード完了を待機
            
            # 一時ファイルを削除
            os.remove(temp_file)
            logger.info(f"一時ファイル '{temp_file}' を削除しました。")
            
            # MERGE文を作成（存在するレコードは更新、存在しないレコードは挿入）
            # カラムのリストを取得
            columns = [field.name for field in schema]
            
            # 更新用のSETステートメントを作成（各カラムをバッククォートで囲む）
            set_clause = ", ".join([f"T.`{col}` = S.`{col}`" for col in columns if col != normalized_key_column])
            
            # 挿入用のカラムリストとバリューリストを作成（各カラムをバッククォートで囲む）
            columns_clause = ", ".join([f"`{col}`" for col in columns])
            values_clause = ", ".join([f"S.`{col}`" for col in columns])
            
            # MERGE文を構築
            merge_query = f"""
            MERGE `{destination_table}` T
            USING `{temp_table_full}` S
            ON T.`{normalized_key_column}` = S.`{normalized_key_column}`
            WHEN MATCHED THEN
              UPDATE SET {set_clause}
            WHEN NOT MATCHED THEN
              INSERT({columns_clause})
              VALUES({values_clause})
            """
            
            # マージクエリを実行
            logger.info(f"マージクエリを実行します。キーカラム: {normalized_key_column}")
            query_job = client.query(merge_query)
            query_job.result()  # クエリ完了を待機
            
            # 一時テーブルを削除
            client.delete_table(temp_table_ref)
            logger.info(f"一時テーブル '{temp_table_id}' を削除しました。")
            
            # 変更行数を取得
            destination_rows = client.get_table(table_ref).num_rows
            logger.info(f"マージ操作が完了しました。テーブル '{table_id}' の現在の行数: {destination_rows}")
            
            return True
            
        except NotFound:
            logger.error(f"テーブル '{table_id}' が存在しません。先に通常のロード処理で作成してください。")
            return False
            
    except Exception as e:
        logger.error(f"アップサート処理中に例外が発生しました: {e}")
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
    parser = argparse.ArgumentParser(description='CSVまたはJSONファイルからデータを読み込み、キー指定でBigQueryにアップサートします')
    parser.add_argument('file_path', help='入力CSVまたはJSONファイルのパス')
    parser.add_argument('table_name', help='ロード先のテーブル名（形式: データセット.テーブル）')
    parser.add_argument('--key-column', default='応募ID', help='更新キーとなるカラム名（デフォルト: 応募ID）')
    parser.add_argument('--env-file', default='config/secrets.env', help='環境変数ファイルのパス（デフォルト: config/secrets.env）')
    
    args = parser.parse_args()
    
    # 環境変数を読み込む
    env.load_env(args.env_file)
    
    # 入力ファイルの存在確認
    if not os.path.exists(args.file_path):
        logger.error(f"入力ファイル '{args.file_path}' が見つかりません")
        sys.exit(1)
    
    # データのアップサート
    if upsert_data_to_bigquery(args.file_path, args.table_name, args.key_column):
        logger.info("データのアップサートが成功しました")
    else:
        logger.error("データのアップサートに失敗しました")
        sys.exit(1)

if __name__ == '__main__':
    main() 