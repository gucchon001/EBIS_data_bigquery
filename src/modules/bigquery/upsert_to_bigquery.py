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
import numpy as np
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from src.utils.environment import EnvironmentUtils as env
from src.modules.bigquery.load_to_bigquery_fixed import convert_date_format, normalize_column_name, process_data_columns
import re

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clean_integer_value(value):
    """
    数値として扱われるべき文字列をクリーニングして整数に変換する
    すべての小数点以下は切り捨てられる
    
    Args:
        value: 変換対象の値
        
    Returns:
        int or None: クリーニングされた整数値。変換できない場合はNone
    """
    if pd.isna(value):
        return None
    
    # 整数型の場合はそのまま返す
    if isinstance(value, int):
        return value
    
    # 浮動小数点型の場合は小数点以下を切り捨て
    if isinstance(value, float):
        # 無限大や NaN は None に変換
        if not np.isfinite(value):
            return None
        # 小数点以下を切り捨てて整数に変換
        return int(value)
    
    try:
        if isinstance(value, str):
            # 空文字列や空白のみの場合はNone
            if not value.strip() or value.lower() in ['undefined', 'null', 'none', '']:
                return None
            
            # カラム名やヘッダー行の場合はNoneを返す
            if any(keyword in value.lower() for keyword in ['名', 'id', 'カラム', 'ユーザー']):
                return None
            
            # JSONの特殊フォーマット（'number_value: "1.0"'）を処理
            if 'number_value:' in value:
                # より柔軟な正規表現パターンを使用して数値部分を抽出
                logger.debug(f"number_value形式の処理: '{value}'")
                match = re.search(r'number_value:\s*"?([^"]+)"?', value)
                if match:
                    clean_value = match.group(1).strip()
                    logger.debug(f"抽出された数値文字列: '{clean_value}'")
                    try:
                        # カンマを削除し、浮動小数点数に変換
                        clean_value = clean_value.replace(',', '')
                        float_val = float(clean_value)
                        logger.debug(f"浮動小数点数に変換: {float_val}")
                        
                        # 浮動小数点数を整数に変換（小数点以下を切り捨て）
                        if np.isfinite(float_val):
                            int_val = int(float_val)
                            logger.debug(f"整数に変換: {int_val}")
                            return int_val
                        return None
                    except ValueError as ve:
                        logger.warning(f"数値として解析できない値です: '{clean_value}'（元の値: '{value}'）、エラー: {ve}")
                        return None
                else:
                    # フォーマットが期待通りでない場合、より詳細なデバッグ情報
                    logger.warning(f"number_value形式が不正: '{value}'、パターンマッチに失敗")
                    
                    # 代替パターンで再試行
                    alt_match = re.search(r'number_value:(.+)', value)
                    if alt_match:
                        alt_value = alt_match.group(1).strip().replace('"', '').replace("'", "")
                        logger.debug(f"代替パターンで抽出された値: '{alt_value}'")
                        try:
                            # 代替方法で数値変換を試みる
                            alt_value = alt_value.replace(',', '')
                            float_val = float(alt_value)
                            if np.isfinite(float_val):
                                int_val = int(float_val)
                                logger.debug(f"代替処理で整数に変換: {int_val}")
                                return int_val
                        except ValueError:
                            pass
                    
                    return None
                
            # バックスラッシュ、カンマ、ダブルクォーテーションを削除
            clean_value = value.replace('\\', '').replace(',', '').replace('"', '').strip()
            
            # 数値に変換できるかチェック
            if clean_value:
                # 小数点を含む場合も含めて浮動小数点数として処理し、整数に変換
                try:
                    # デバッグ情報
                    logger.debug(f"整数変換を試みる値: '{clean_value}'")
                    float_val = float(clean_value)
                    if np.isfinite(float_val):
                        int_val = int(float_val)
                        logger.debug(f"浮動小数点 {float_val} から整数 {int_val} に変換")
                        return int_val
                    return None
                except ValueError as ve:
                    logger.warning(f"数値として解析できない値です: '{clean_value}'（元の値: '{value}'）、エラー: {ve}")
                    return None
    except Exception as e:
        logger.warning(f"整数への変換に失敗しました: {e}, 値: '{value}'")
    
    return None

def convert_japanese_date(date_str):
    """
    日本語形式の日付（yyyy年mm月dd日）をISO形式（yyyy-mm-dd）に変換する
    
    Args:
        date_str: 変換対象の日付文字列
        
    Returns:
        str: 変換後の日付文字列（yyyy-mm-dd形式）、変換できない場合は元の文字列
    """
    if not isinstance(date_str, str):
        return date_str
        
    # 日本語形式の日付を検出する正規表現パターン
    pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日'
    match = re.match(pattern, date_str.strip())
    
    if match:
        year, month, day = match.groups()
        # 桁数が足りない場合はゼロ埋め
        month = month.zfill(2)
        day = day.zfill(2)
        return f"{year}-{month}-{day}"
    
    return date_str

def process_all_date_columns(df, schema):
    """
    データフレームの日付カラムとタイムスタンプカラムをBigQuery互換の形式に変換
    
    Args:
        df: 処理対象のデータフレーム
        schema: BigQueryテーブルのスキーマ
        
    Returns:
        pandas.DataFrame: 日付が変換されたデータフレーム
    """
    for field in schema:
        if field.name in df.columns:
            if field.field_type == 'DATE':
                logger.info(f"DATE型カラム '{field.name}' を変換します")
                try:
                    # ヘッダー行を除外
                    mask = ~df[field.name].astype(str).str.contains('項目|日時|時間|date', case=False, na=False)
                    # 文字列として処理して変換エラーを回避
                    values = df.loc[mask, field.name]
                    
                    # 日本語形式の日付を前処理
                    logger.info(f"日本語形式の日付を前処理します（yyyy年mm月dd日 → yyyy-mm-dd）")
                    df.loc[mask, field.name] = values.apply(convert_japanese_date)
                    
                    # 前処理後の値を取得
                    preprocessed_values = df.loc[mask, field.name]
                    
                    try:
                        # 明示的にフォーマットを指定して変換
                        dates = pd.to_datetime(preprocessed_values, errors='coerce', format='%Y-%m-%d')
                        # フォーマット指定で変換できない場合は日付形式を推測
                        mask_failed = pd.isna(dates)
                        if mask_failed.any():
                            logger.warning(f"日付形式 '%Y-%m-%d' での変換に失敗した行があります。汎用的な日付変換を試みます。")
                            dates.loc[mask_failed] = pd.to_datetime(preprocessed_values.loc[mask_failed], errors='coerce')
                        
                        df.loc[mask, field.name] = dates.apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else None)
                        
                        # 変換結果のサンプルを表示
                        converted_sample = df.loc[mask, field.name].head(5).tolist()
                        logger.info(f"日付変換サンプル: {converted_sample}")
                        
                    except Exception as e:
                        logger.warning(f"DATE型カラム '{field.name}' の変換に失敗: {e}")
                except Exception as e:
                    logger.warning(f"DATE型カラム '{field.name}' の変換中にエラーが発生しました: {e}")
                    
            elif field.field_type == 'TIMESTAMP':
                logger.info(f"TIMESTAMP型カラム '{field.name}' を変換します")
                try:
                    # ヘッダー行を除外
                    mask = ~df[field.name].astype(str).str.contains('項目|日時|時間|timestamp', case=False, na=False)
                    # 文字列として処理して変換エラーを回避
                    values = df.loc[mask, field.name]
                    
                    # 日本語形式の日付を前処理
                    logger.info(f"TIMESTAMP型カラム '{field.name}' の日本語形式の日付を前処理します")
                    df.loc[mask, field.name] = values.apply(convert_japanese_date)
                    
                    # 前処理後の値を取得
                    preprocessed_values = df.loc[mask, field.name]
                    
                    try:
                        # まず明示的なフォーマットで変換を試みる
                        timestamps = pd.to_datetime(preprocessed_values, errors='coerce')
                        df.loc[mask, field.name] = timestamps.apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(x) else None)
                        
                        # 変換結果のサンプルを表示
                        converted_sample = df.loc[mask, field.name].head(5).tolist()
                        logger.info(f"タイムスタンプ変換サンプル: {converted_sample}")
                    except Exception as e:
                        logger.warning(f"TIMESTAMP型カラム '{field.name}' の変換に失敗: {e}")
                except Exception as e:
                    logger.warning(f"TIMESTAMP型カラム '{field.name}' の変換中にエラーが発生しました: {e}")
            
            elif field.field_type == 'INTEGER':
                logger.info(f"INTEGER型カラム '{field.name}' を変換します")
                try:
                    # 文字列変換前のサンプルデータを表示（デバッグ用）
                    sample_data = df[field.name].head(3).tolist()
                    logger.debug(f"サンプルデータ（変換前）: {sample_data}")
                    
                    # 数値を文字列として処理する場合のために、先に文字列に変換
                    df[field.name] = df[field.name].astype(str)
                    
                    # ヘッダー行を除外してから変換
                    mask = ~df[field.name].astype(str).str.contains('項目|ID|名|カラム|integer', case=False, na=False)
                    
                    # 特殊な数値フォーマットをチェック
                    special_format_mask = df[field.name].astype(str).str.contains('number_value:', case=False, na=False)
                    if special_format_mask.any():
                        logger.warning(f"カラム '{field.name}' に特殊な数値フォーマットが含まれています。サンプル: {df.loc[special_format_mask, field.name].head(3).tolist()}")
                    
                    # 各行に対して数値変換を適用
                    df.loc[mask, field.name] = df.loc[mask, field.name].apply(clean_integer_value)
                    
                    # 変換後のサンプルデータを表示（デバッグ用）
                    converted_sample = df[field.name].head(3).tolist()
                    logger.debug(f"サンプルデータ（変換後）: {converted_sample}")
                    
                except Exception as e:
                    logger.warning(f"INTEGER型カラム '{field.name}' の変換中にエラーが発生しました: {e}")
                    logger.warning(f"エラー詳細:", exc_info=True)
    
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
            try:
                # まずUTF-8で試す
                df = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                # UTF-8で失敗した場合はcp932（Shift-JIS）で試す
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
            # データの最初の列をキーカラムとして代用
            if len(df.columns) > 0:
                logger.warning(f"最初のカラム '{df.columns[0]}' をキーカラムとして代用します")
                df[key_column] = df[df.columns[0]]
            else:
                logger.error("データにカラムが存在しないため処理を中止します")
                return False
            
        # キーカラムのNullチェック
        null_keys = df[df[key_column].isnull()].shape[0]
        if null_keys > 0:
            logger.warning(f"キーカラム '{key_column}' に {null_keys} 個のNULL値が存在します。これらは正しく更新されない可能性があります。")
        
        # キーカラムの重複チェック
        duplicate_keys = df[df.duplicated(subset=[key_column], keep=False)]
        if not duplicate_keys.empty:
            duplicate_count = len(duplicate_keys)
            logger.warning(f"キーカラム '{key_column}' に {duplicate_count} 個の重複があります。最新の行のみを保持します。")
            
            # 重複キーの値をログに出力
            duplicate_key_values = duplicate_keys[key_column].unique()
            logger.info(f"重複キーのサンプル: {duplicate_key_values[:5] if len(duplicate_key_values) > 5 else duplicate_key_values}")
            
            # 重複を排除（最後の行を保持）
            df = df.drop_duplicates(subset=[key_column], keep='last')
            logger.info(f"重複排除後の行数: {len(df)}")
        
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