#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CSVファイルをBigQueryにロードするスクリプト

このスクリプトは、指定されたCSVファイルをGoogle BigQueryにロードします。
特にAE_CV属性result.csvファイルのデータを処理し、Tokyo時間のタイムスタンプ形式を
BigQueryのTIMESTAMP型に変換してロードします。

注意事項:
- CSVファイルは文字化けしている可能性があるため、適切なエンコーディングを使用します
- 1行目はヘッダー行であるため、スキップしてデータを読み込みます
- タイムスタンプは '%Y/%m/%d %H:%M' 形式から適切なBigQuery形式に変換されます
- データ型の混在エラーを防ぐため、すべての列を初期段階では文字列として読み込みます
"""

import pandas as pd
import sys
import logging
import re
from datetime import datetime, timedelta
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
from src.utils.environment import EnvironmentUtils as env
from pathlib import Path
import os

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

def loadCsvToBigquery(csvFilePath: str, tableName: str = None) -> None:
    """
    CSVファイルをBigQueryにロードする関数
    
    Args:
        csvFilePath: ロードするCSVファイルのパス
        tableName: BigQueryのテーブル名（指定がない場合はファイル名を使用）
    
    Returns:
        None
    
    Raises:
        FileNotFoundError: CSVファイルが見つからない場合
        GoogleCloudError: BigQueryへのロード中にエラーが発生した場合
        Exception: その他の例外が発生した場合
    """
    try:
        # 環境設定の読み込み
        env.load_env()
        
        # BigQuery設定の取得
        bigquerySettings = env.get_bigquery_settings()
        projectId = bigquerySettings["project_id"]
        datasetId = bigquerySettings["dataset_id"]
        keyPath = bigquerySettings["key_path"]
        
        # ファイル存在チェック
        csvPath = Path(csvFilePath)
        if not csvPath.exists():
            raise FileNotFoundError(f"CSVファイル '{csvFilePath}' が見つかりません。")
        
        # テーブル名が指定されていない場合はデフォルトで「AE_CVresult」を使用
        if tableName is None:
            tableName = "AE_CVresult"
            logger.info(f"テーブル名を '{tableName}' に設定しました")
        
        logger.info(f"'{csvFilePath}' を BigQuery テーブル '{tableName}' にロードします...")
        
        # BigQueryクライアントの初期化
        client = bigquery.Client.from_service_account_json(keyPath)
        
        # エンコーディングを強制的にcp932に設定
        encoding = 'cp932'
        logger.info(f"ファイルのエンコーディングを '{encoding}' として設定しました")
        
        # CSVファイルの読み込み - すべての列を文字列として読み込む
        try:
            # ヘッダー行をスキップし、2行目からデータとして読み込む
            # 最初の5行だけ読み込むようにnrowsパラメータを追加
            df = pd.read_csv(csvFilePath, encoding=encoding, dtype=str, low_memory=False, 
                            header=None, skiprows=1, nrows=5)
            
            logger.info(f"ヘッダー行をスキップし、2行目から5行だけデータを読み込みました")
        except Exception as e:
            logger.error(f"CSVファイル読み込み中にエラーが発生しました: {str(e)}")
            raise
        
        logger.info(f"CSVファイルを読み込みました。行数: {len(df)}、列数: {len(df.columns)}")
        
        # BigQueryのテーブルスキーマを取得（テーブルが存在する場合）
        tableId = f"{projectId}.{datasetId}.{tableName}"
        
        # 既存テーブルのスキーマを取得
        try:
            table = client.get_table(tableId)
            schema = table.schema
            logger.info(f"BigQueryのスキーマを取得しました: {len(schema)} 列")
            
            # スキーマから列名のリストを取得
            schema_field_names = [field.name for field in schema]
            
            # データフレームの列数とスキーマの列数を比較し、少ない方に合わせる
            min_cols = min(len(df.columns), len(schema_field_names))
            
            # データフレームの列名をスキーマの列名に変更（順序は列の位置順）
            new_columns = {}
            for i in range(min_cols):
                old_col = df.columns[i]
                new_col = schema_field_names[i]
                new_columns[old_col] = new_col
            
            # 列名を変更
            df = df.rename(columns=new_columns)
            
            logger.info(f"データフレームの列名をBigQueryスキーマに合わせて変更しました")
            
            # スキーマに基づいて列の型を変換
            for i, field in enumerate(schema):
                if i >= min_cols:
                    logger.warning(f"CSVの列数がBigQueryスキーマより少ないため、一部の列が処理されません")
                    break
                
                field_name = field.name
                field_type = field.field_type
                
                if field_name not in df.columns:
                    logger.warning(f"フィールド '{field_name}' はデータフレームに存在しません")
                    continue
                
                logger.info(f"列 '{field_name}' のBigQuery型: {field_type}")
                
                # サンプルデータの取得（最初の5行）
                sample_data = df[field_name].head(10).dropna().tolist()
                logger.info(f"列 '{field_name}' のサンプルデータ: {sample_data}")
                
                # データ型のチェック
                if field_type in ['TIMESTAMP', 'DATE', 'DATETIME']:
                    # タイムスタンプや日付と思われる列名のパターン
                    timestamp_patterns = ['time', 'date', '時間', '日時', '日付']
                    is_likely_timestamp = any(pattern in field_name.lower() for pattern in timestamp_patterns)
                    
                    # 単純な判定: Excelシリアル形式（数値のみ）のデータ数をカウント
                    excel_date_count = sum(1 for x in sample_data if str(x).strip() and bool(re.match(r'^[0-9]+(\.[0-9]+)?$', str(x))))
                    
                    # 標準日付形式のデータ数をカウント
                    std_date_count = sum(1 for x in sample_data if str(x).strip() and bool(re.match(r'^\d{4}[/\-]\d{1,2}[/\-]\d{1,2}(\s\d{1,2}:\d{1,2}(:\d{1,2})?)?$', str(x))))
                    
                    logger.info(f"列 '{field_name}' のExcel日付形式データ数: {excel_date_count}, 標準日付形式データ数: {std_date_count}")
                    
                    # 日付・時刻の変換関数
                    def convert_datetime_value(value):
                        """個別の値を日付・時刻に変換する関数"""
                        if pd.isna(value) or str(value).strip() == '':
                            return None
                        
                        value_str = str(value).strip()
                        
                        # 標準日付形式かチェック
                        if re.match(r'^\d{4}[/\-]\d{1,2}[/\-]\d{1,2}(\s\d{1,2}:\d{1,2}(:\d{1,2})?)?$', value_str):
                            try:
                                # 標準的な日付形式として処理
                                return pd.to_datetime(value_str)
                            except Exception:
                                pass
                        
                        # Excel日付形式かチェック
                        if re.match(r'^[0-9]+(\.[0-9]+)?$', value_str):
                            try:
                                excel_date = float(value_str)
                                # Excelでの日付の起点は1900年1月1日、値1は1900年1月1日を表す
                                if excel_date < 60:
                                    # 1900年1月と2月の日付
                                    dt = datetime(1900, 1, 1) + timedelta(days=excel_date - 1)
                                else:
                                    # 1900年3月1日以降の日付（Excelの閏年バグを考慮）
                                    dt = datetime(1900, 1, 1) + timedelta(days=excel_date - 2)
                                
                                # タイムスタンプの場合は時間も計算
                                if excel_date % 1 != 0:
                                    # 小数部分から時間を計算
                                    frac_of_day = excel_date % 1
                                    seconds = int(frac_of_day * 86400)  # 1日=86400秒
                                    hour = seconds // 3600
                                    minute = (seconds % 3600) // 60
                                    second = seconds % 60
                                    dt = dt.replace(hour=hour, minute=minute, second=second)
                                
                                return dt
                            except Exception:
                                pass
                        
                        # それ以外の場合はpandasの標準変換を試みる
                        try:
                            return pd.to_datetime(value_str, errors='coerce')
                        except Exception:
                            return None
                    
                    # 項目4の特別処理
                    if field_name == '項目4' and field_type == 'DATE':
                        try:
                            # さまざまな日付形式を試して変換
                            date_formats = ['%Y/%m/%d', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S']
                            for fmt in date_formats:
                                try:
                                    temp_dates = pd.to_datetime(df[field_name], errors='coerce', format=fmt)
                                    if not temp_dates.isna().all():  # 少なくとも1つの日付が変換できた場合
                                        df[field_name] = temp_dates.dt.strftime('%Y-%m-%d')  # BigQuery DATE型形式
                                        logger.info(f"列 '{field_name}' を日付型（{fmt}形式）に変換しました")
                                        break
                                except Exception:
                                    continue
                        except Exception as e:
                            logger.warning(f"列 '{field_name}' の日付変換に失敗しました: {str(e)}")
                    
                    # Excel日付形式または標準日付形式の両方を試みる一般的なアプローチ
                    elif excel_date_count > 0 or std_date_count > 0 or is_likely_timestamp:
                        logger.info(f"列 '{field_name}' は日付/時刻フィールドとして処理します")
                        try:
                            # 各値に対して個別に変換関数を適用
                            temp_series = df[field_name].apply(convert_datetime_value)
                            
                            # 変換結果が全てNaNでなければBigQuery形式に変換
                            if not temp_series.isna().all():
                                df[field_name] = temp_series
                                
                                # BigQueryに適した形式に変換
                                if field_type == 'DATE':
                                    # DATE型の場合は日付部分のみ
                                    # NaT (Not a Time) の値を処理 - 空文字列に変換
                                    df[field_name] = df[field_name].fillna('')
                                    # datetimeオブジェクトのみに.dtアクセサを使用
                                    valid_dates = pd.notna(df[field_name]) & (df[field_name] != '')
                                    if valid_dates.any():
                                        df.loc[valid_dates, field_name] = df.loc[valid_dates, field_name].dt.strftime('%Y-%m-%d')
                                    # すべての値を確実に文字列にする
                                    df[field_name] = df[field_name].astype(str)
                                    # 空文字列をNULLに戻す
                                    df[field_name] = df[field_name].replace('', None)
                                    logger.info(f"列 '{field_name}' をDATE型に変換しました")
                                elif field_type in ['TIMESTAMP', 'DATETIME']:
                                    # TIMESTAMP型の場合は日時を含む
                                    # NaT (Not a Time) の値を処理 - 空文字列に変換
                                    df[field_name] = df[field_name].fillna('')
                                    # datetimeオブジェクトのみに.dtアクセサを使用
                                    valid_dates = pd.notna(df[field_name]) & (df[field_name] != '')
                                    if valid_dates.any():
                                        df.loc[valid_dates, field_name] = df.loc[valid_dates, field_name].dt.strftime('%Y-%m-%d %H:%M:%S')
                                    # すべての値を確実に文字列にする
                                    df[field_name] = df[field_name].astype(str)
                                    # 空文字列をNULLに戻す
                                    df[field_name] = df[field_name].replace('', None)
                                    logger.info(f"列 '{field_name}' をTIMESTAMP型に変換しました")
                            else:
                                logger.warning(f"列 '{field_name}' の日付変換に失敗しました（全てNaN）")
                                # 文字列として維持
                                df[field_name] = df[field_name].astype(str)
                        except Exception as e:
                            logger.warning(f"列 '{field_name}' の日付/時刻変換に失敗しました: {str(e)}")
                            # 失敗した場合は文字列として維持
                            df[field_name] = df[field_name].astype(str)
                    else:
                        # 日付と判断できない場合は警告
                        logger.warning(f"列 '{field_name}' は日付型と一致していません。文字列として扱います。")
                        # 文字列として維持
                        df[field_name] = df[field_name].astype(str)
                
                elif field_type in ['INTEGER', 'FLOAT', 'NUMERIC']:
                    # 数値型のチェック
                    is_numeric_format = all(
                        bool(re.match(r'^-?\d+(\.\d+)?$', str(x)))
                        for x in sample_data if str(x).strip()
                    )
                    
                    if is_numeric_format:
                        logger.info(f"列 '{field_name}' は数値型と一致しています")
                    else:
                        logger.warning(f"列 '{field_name}' は数値型と一致していません。サンプル: {sample_data[:2]}")
                        
                    try:
                        df[field_name] = df[field_name].replace('', pd.NA)
                        df[field_name] = pd.to_numeric(df[field_name], errors='coerce')
                        logger.info(f"列 '{field_name}' を数値型に変換しました")
                    except Exception as e:
                        logger.warning(f"列 '{field_name}' の数値変換に失敗しました: {str(e)}")
                        
                elif field_type == 'BOOL':
                    # 論理型のチェック
                    is_bool_format = all(
                        str(x).lower() in ['true', 'false', '1', '0', 'yes', 'no', 'y', 'n']
                        for x in sample_data if str(x).strip()
                    )
                    
                    if is_bool_format:
                        logger.info(f"列 '{field_name}' は論理型と一致しています")
                    else:
                        logger.warning(f"列 '{field_name}' は論理型と一致していません。サンプル: {sample_data[:2]}")
                    
                    # 論理型の変換（pandas.DataFrameには明示的な論理型変換が必要ないため、処理なし）
                
                # その他の型（STRING等）は文字列のまま保持
                else:
                    logger.info(f"列 '{field_name}' は文字列型として維持します")
                
        except Exception as e:
            logger.error(f"既存のテーブルスキーマを取得できませんでした: {str(e)}")
            raise GoogleCloudError(f"テーブル '{tableId}' が存在しないか、アクセスできません: {str(e)}")
        
        # BigQueryにデータをロードする直前に、全ての列のデータ型を確認し処理
        logger.info("BigQueryデータ型の最終処理を行います...")
        
        # スキーマの列名リストを取得
        schema_field_names = [field.name for field in schema]
        logger.info(f"BigQueryスキーマの列数: {len(schema_field_names)}")
        logger.info(f"データフレームの列数: {len(df.columns)}")
        
        # データフレームの列がBigQueryスキーマより多い場合、余分な列を削除
        extra_columns = [col for col in df.columns if col not in schema_field_names]
        if extra_columns:
            logger.warning(f"BigQueryスキーマに存在しない余分な列を削除します: {extra_columns}")
            df = df.drop(columns=extra_columns)
        
        # データフレームの列をスキーマの列順に並べ替え
        logger.info(f"データフレームの列をスキーマの列順に調整します")
        new_df = pd.DataFrame()
        for col_name in schema_field_names:
            if col_name in df.columns:
                new_df[col_name] = df[col_name]
            else:
                new_df[col_name] = None
        
        # 新しいデータフレームに置き換え
        df = new_df
        logger.info(f"列の順序を調整しました。最終的なデータフレームの列数: {len(df.columns)}")
        
        # データフレームの全ての列を確認
        for col in df.columns:
            # データ型を確認
            col_dtype = df[col].dtype
            
            # 整数型の値を文字列に変換
            if pd.api.types.is_integer_dtype(col_dtype):
                logger.info(f"列 '{col}' は整数型のため、文字列型に変換します")
                df[col] = df[col].astype(str)
                # NULL値を処理
                df[col] = df[col].replace('nan', None)
            
            # 浮動小数点型の値を文字列に変換
            elif pd.api.types.is_float_dtype(col_dtype):
                logger.info(f"列 '{col}' は浮動小数点型のため、文字列型に変換します")
                df[col] = df[col].astype(str)
                # NULL値を処理
                df[col] = df[col].replace('nan', None)
            
            # 日付型の値を文字列に変換
            elif pd.api.types.is_datetime64_dtype(col_dtype):
                logger.info(f"列 '{col}' は日付型のため、文字列型に変換します")
                # NULL値を一時的に別の値に置き換えて処理
                df[col] = df[col].fillna(pd.NaT)
                # 有効な日付のみ変換
                mask = ~pd.isna(df[col])
                if mask.any():
                    df.loc[mask, col] = df.loc[mask, col].dt.strftime('%Y-%m-%d')
                # すべてを一度文字列に変換
                df[col] = df[col].astype(str)
                # 'NaT'をNoneに戻す
                df[col] = df[col].replace('NaT', None)
            
            # オブジェクト型（既に文字列など）の場合も確認
            elif pd.api.types.is_object_dtype(col_dtype):
                logger.info(f"列 '{col}' はオブジェクト型です。中身を検査して型変換します")
                # 明示的に各要素を文字列に変換（Noneを除く）
                # 列全体をリストに変換して確認
                try:
                    values = df[col].tolist()
                    for i, val in enumerate(values):
                        if val is not None and not isinstance(val, str):
                            logger.warning(f"列 '{col}' の行 {i} に非文字列値があります: {type(val)}")
                            df.at[i, col] = str(val)
                except Exception as e:
                    logger.error(f"列 '{col}' の検査中にエラーが発生: {str(e)}")
                    # 安全のため、すべての値を明示的に文字列変換
                    df[col] = df[col].apply(lambda x: str(x) if x is not None else None)
        
        # テーブルIDの設定
        tableId = f"{projectId}.{datasetId}.{tableName}"
        
        # BigQuery読み込み設定 - 既存スキーマを使用し、上書きモードで設定
        jobConfig = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            schema=schema,  # 既存のスキーマを使用
            # 自動検出は無効化
            autodetect=False
        )
        
        logger.info(f"BigQueryにデータをロードしています...")
        
        # PyArrowに問題がある可能性があるため、CSVに一時的に保存してから読み込み直す
        try:
            logger.info("一時的なCSVファイルに保存して読み込み直します")
            temp_csv_path = "temp_bigquery_data.csv"
            df.to_csv(temp_csv_path, index=False)
            df = pd.read_csv(temp_csv_path, dtype=str)
            
            # CV時間列が文字列型として正しく読み込まれたか確認
            if 'CV時間' in df.columns:
                logger.info(f"一時ファイル読み込み後のCV時間列のデータ型: {df['CV時間'].dtype}")
                cv_time_samples = df['CV時間'].dropna().head(5).tolist()
                logger.info(f"一時ファイル読み込み後のCV時間列のサンプル: {cv_time_samples}")
            
            import os
            os.remove(temp_csv_path)
            logger.info("一時ファイルを経由した読み込みが完了しました")
        except Exception as csv_error:
            logger.warning(f"一時CSVファイル処理中にエラー: {str(csv_error)}")
            
            # BigQueryジョブ設定を変更 - SQLで列挿入を利用
            try:
                logger.info("PyArrow変換エラーを回避するため、代替ロード方法を使用します")
                # JSONに変換してからBigQueryにロード
                json_data = df.to_json(orient="records")
                
                # JSONデータをテンポラリテーブルにロード
                temp_table_id = f"{projectId}.{datasetId}.temp_load_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                logger.info(f"一時テーブル {temp_table_id} を作成します")
                
                # JSON文字列をファイルに保存
                temp_json_path = "temp_bigquery_data.json"
                with open(temp_json_path, "w", encoding="utf-8") as f:
                    f.write(json_data)
                
                # JSONファイルから一時テーブルを作成
                job_config = bigquery.LoadJobConfig(
                    source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                    autodetect=True,
                )
                
                with open(temp_json_path, "rb") as source_file:
                    load_job = client.load_table_from_file(
                        source_file, temp_table_id, job_config=job_config
                    )
                    load_job.result()  # ジョブの完了を待機
                
                # 一時ファイルを削除
                os.remove(temp_json_path)
                
                # 一時テーブルから本来のテーブルにデータをコピー
                logger.info(f"一時テーブルからターゲットテーブル {tableId} にデータをコピーします")
                
                # テーブル間コピーのためのクエリを構築
                schema_columns_str = ", ".join([f"`{col}`" for col in schema_field_names])
                
                query = f"""
                INSERT INTO `{tableId}` ({schema_columns_str})
                SELECT {schema_columns_str}
                FROM `{temp_table_id}`
                """
                
                # クエリを実行
                query_job = client.query(query)
                query_job.result()
                
                # 一時テーブルを削除
                logger.info(f"一時テーブル {temp_table_id} を削除します")
                client.delete_table(temp_table_id)
                
                logger.info(f"データを BigQuery テーブル '{tableId}' に正常にロードしました。")
                logger.info(f"処理した行数: {len(df)}")
                return
            except Exception as e:
                logger.error(f"代替ロード方法でエラーが発生しました: {str(e)}")
                logger.warning("通常のロード方法に戻ります")
            
            # 通常のロード方法を試行（上記方法が失敗した場合）
            job = client.load_table_from_dataframe(df, tableId, job_config=jobConfig)
            job.result()  # ジョブの完了を待機
            logger.info(f"データを BigQuery テーブル '{tableId}' にロードしました。")
            logger.info(f"処理した行数: {len(df)}")
        
    except FileNotFoundError as e:
        logger.error(f"ファイルエラー: {str(e)}")
        raise
    except GoogleCloudError as e:
        logger.error(f"BigQuery エラー: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {str(e)}")
        raise

def main():
    """
    メイン実行関数
    コマンドライン引数でCSVファイルパスとテーブル名を受け取ることもできます
    """
    try:
        # デフォルトのCSVファイルパス
        defaultCsvPath = "data/AE_SSresult/AE_CV属性result.csv"
        csvFilePath = env.resolve_path(defaultCsvPath)
        
        # コマンドライン引数の処理
        tableName = None
        if len(sys.argv) > 1:
            csvFilePath = sys.argv[1]
        if len(sys.argv) > 2:
            tableName = sys.argv[2]
        
        # BigQueryへのロード処理実行
        loadCsvToBigquery(csvFilePath, tableName)
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()