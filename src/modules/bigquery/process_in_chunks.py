#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CSVデータをチャンクに分割してBigQueryにロードするスクリプト

大きなCSVファイルをチャンク単位で処理し、BigQueryにロードします。
エラーが発生した場合でも処理を継続し、成功したチャンクと失敗したチャンクを記録します。
"""

import os
import sys
import argparse
import logging
import pandas as pd
import numpy as np
import time
import tempfile
from pathlib import Path
from datetime import datetime
from src.utils.environment import EnvironmentUtils as env
from src.modules.bigquery.csv_to_bigquery import process_csv_to_bigquery

# ロガーの設定
logging.basicConfig(
    level=logging.DEBUG,  # DEBUGレベルに変更してより詳細なログを出力
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_total_rows(file_path):
    """
    CSVファイルの総行数を取得します（ヘッダーを含む）
    
    Args:
        file_path: CSVファイルのパス
        
    Returns:
        int: CSVファイルの総行数
    """
    try:
        logger.debug(f"ファイル {file_path} の行数を取得中...")
        # まずcp932（Shift-JIS）で試す - 日本語ファイルなのでcp932を最初に試す
        try:
            with open(file_path, 'r', encoding='cp932') as f:
                total_rows = sum(1 for _ in f)
            logger.debug(f"cp932エンコーディングでファイルの行数を取得: {total_rows}行")
            return total_rows
        except UnicodeDecodeError:
            # cp932で失敗した場合はUTF-8で試す
            with open(file_path, 'r', encoding='utf-8') as f:
                total_rows = sum(1 for _ in f)
            logger.debug(f"UTF-8エンコーディングでファイルの行数を取得: {total_rows}行")
            return total_rows
    except Exception as e:
        logger.error(f"CSVファイルの行数確認中にエラーが発生しました: {e}")
        raise

def read_csv_chunk(file_path, start_row, chunk_size, encoding='cp932', start_row_with_header=None):
    """
    CSVファイルの特定の範囲の行を読み込む
    
    Args:
        file_path: CSVファイルのパス
        start_row: 開始行（0-indexed）
        chunk_size: 読み込む行数
        encoding: ファイルのエンコーディング（デフォルト: cp932）
        start_row_with_header: ヘッダー行を含む開始行（指定された場合はスキップ行を調整）
        
    Returns:
        pandas.DataFrame: 読み込んだCSVデータ
    """
    try:
        # 開始行を調整（ヘッダー行をスキップするため）
        header_row = 0
        skiprows = start_row
        
        if start_row_with_header is not None:
            # ヘッダー行と開始行を調整
            header_row = start_row_with_header
            skiprows = list(range(1, start_row_with_header))  # ヘッダー行の前の行をスキップ
            skiprows.extend(range(start_row_with_header + 1, start_row + 1))  # ヘッダー行から開始行までスキップ
        
        logger.debug(f"CSV読み込み: 開始行={start_row}, チャンクサイズ={chunk_size}, エンコーディング={encoding}")
        logger.debug(f"ヘッダー行: {header_row}, スキップ行: {skiprows}")
        
        try:
            # 指定されたエンコーディングでCSVファイルを読み込む（デフォルトはcp932）
            logger.info(f"エンコーディング {encoding} でCSVファイルの読み込みを試みます")
            df = pd.read_csv(
                file_path,
                nrows=chunk_size,
                skiprows=skiprows,
                header=header_row,
                encoding=encoding
            )
            logger.info(f"エンコーディング {encoding} でCSVファイルを正常に読み込みました")
            logger.debug(f"読み込んだデータ形状: {df.shape}、カラム: {df.columns.tolist()}")
            return df
        except Exception as e:
            # エラーが発生した場合はフォールバック処理
            logger.warning(f"{encoding}エンコーディングでの読み込みに失敗しました: {e}")
            
            # 他のエンコーディングを試す
            encodings = ['utf-8', 'shift_jis', 'euc_jp', 'latin1']
            for enc in encodings:
                if enc == encoding:  # 既に試したエンコーディングはスキップ
                    continue
                try:
                    logger.info(f"エンコーディング {enc} でCSVファイルの読み込みを試みます")
                    df = pd.read_csv(
                        file_path,
                        nrows=chunk_size,
                        skiprows=skiprows,
                        header=header_row,
                        encoding=enc
                    )
                    logger.info(f"エンコーディング {enc} でCSVファイルを正常に読み込みました")
                    logger.debug(f"読み込んだデータ形状: {df.shape}、カラム: {df.columns.tolist()}")
                    return df
                except Exception as inner_e:
                    logger.warning(f"エンコーディング {enc} での読み込みに失敗しました: {inner_e}")
                    continue
            
            # すべてのエンコーディングが失敗した場合
            raise Exception("すべてのエンコーディングでCSVファイルの読み込みに失敗しました")
            
    except Exception as e:
        logger.error(f"CSVファイルの読み込み中にエラーが発生しました: {e}")
        raise

def process_in_chunks(
    csv_file, 
    table_name, 
    chunk_size=1000,
    max_chunks=None,
    start_row=0,
    column_mapping=None,
    date_columns=None,
    integer_columns=None,
    write_disposition=None
):
    """
    CSVファイルをチャンク単位で処理し、BigQueryにロードする
    
    Args:
        csv_file: 入力CSVファイルのパス
        table_name: BigQueryテーブル名（形式: データセット.テーブル）
        chunk_size: 一度に処理する行数
        max_chunks: 処理する最大チャンク数（None=全て処理）
        start_row: 処理を開始する行番号（0から始まる）
        column_mapping: カラム名のマッピング辞書
        date_columns: 日付型として処理するカラムのリスト
        integer_columns: 整数型として処理するカラムのリスト
        write_disposition: テーブルへの書き込み方法（WRITE_TRUNCATE, WRITE_APPEND, WRITE_EMPTY）
    
    Returns:
        tuple: (成功したチャンク数, 失敗したチャンク数)
    """
    # スタート時間
    start_time = time.time()
    
    # 結果格納用の変数
    success_count = 0
    failed_count = 0
    failed_ranges = []
    
    # CSVファイルの存在確認
    if not os.path.exists(csv_file):
        logger.error(f"CSVファイル '{csv_file}' が見つかりません")
        return (0, 0)

    # CSVファイルの行数を確認（ヘッダー行を含む）
    try:
        total_rows = get_total_rows(csv_file)
        logger.info(f"CSVファイル '{csv_file}' の総行数: {total_rows}行（ヘッダー行を含む）")
    except Exception as e:
        logger.error(f"CSVファイルの行数確認中にエラーが発生しました: {e}")
        return (0, 0)
    
    # 処理対象の行数とチャンク数を計算
    rows_to_process = total_rows - 1  # ヘッダー行を除く
    chunk_count = (rows_to_process + chunk_size - 1) // chunk_size  # 切り上げ

    # CSVファイルの最初の行を読んでカラム名を取得
    try:
        # cp932（Shift-JIS）で読み込む
        try:
            csv_columns = pd.read_csv(csv_file, nrows=0, encoding='cp932').columns.tolist()
            logger.info(f"CSVファイルのカラム (cp932): {csv_columns}")
        except Exception as e:
            logger.warning(f"cp932でのカラム名取得に失敗しました: {e}")
            # 他のエンコーディングを試す
            try:
                csv_columns = pd.read_csv(csv_file, nrows=0, encoding='utf-8').columns.tolist()
                logger.info(f"CSVファイルのカラム (utf-8): {csv_columns}")
            except:
                # 最終手段: エラーが出ても固定のカラム名リストを使用
                logger.warning("カラム名の取得に失敗したため、デフォルトのカラム名を使用します")
                csv_columns = ["CV名", "CV時間", "ユーザーID", "ユーザー名", "売上金額", "属性1", "属性2", "属性3", "属性4", "属性5"]
    except Exception as e:
        logger.error(f"CSVファイルのカラム名取得中にエラーが発生しました: {e}")
        return (0, 0)
    
    # カラム名のマッピングを適用
    if column_mapping:
        # 変換前のカラム名をログに出力
        logger.info(f"変換前のカラム名: {csv_columns}")
        logger.info(f"適用するマッピング: {column_mapping}")
        
        columns = []
        for col in csv_columns:
            # マッピングが存在する場合は変換、それ以外はそのまま
            if col in column_mapping:
                columns.append(column_mapping[col])
                logger.debug(f"カラム '{col}' を '{column_mapping[col]}' に変換しました")
            else:
                columns.append(col)
        logger.info(f"カラム名を変換しました: {column_mapping}")
    else:
        columns = csv_columns
    
    logger.info(f"変換後のカラム: {columns}")

    # チャンク処理を開始
    logger.info(f"チャンク処理を開始します: サイズ={chunk_size}, 開始行={start_row}, 最大チャンク数={max_chunks or '無制限'}")
    
    # 各チャンクを処理
    for chunk_idx in range(chunk_count):
        if max_chunks is not None and chunk_idx >= max_chunks:
            break
            
        # チャンクの範囲を計算
        chunk_start = start_row + (chunk_idx * chunk_size)
        chunk_end = chunk_start + chunk_size
        chunk_progress = (chunk_idx + 1) / (max_chunks or chunk_count) * 100.0
        
        logger.info(f"チャンク処理中 ({chunk_start+1}-{chunk_end}): 進捗 {chunk_progress:.1f}%")
        
        # チャンクを処理
        try:
            # CSVファイルからチャンクを読み込む
            # デフォルトエンコーディングはcp932
            chunk_df = read_csv_chunk(csv_file, chunk_start, chunk_size, encoding='cp932', start_row_with_header=0)
            
            # カラム名のマッピングを適用
            if column_mapping:
                # 元のカラム名を表示
                logger.info(f"変換前のカラム: {chunk_df.columns.tolist()}")
                
                # 実際のファイルにある列名のリストを作成
                existing_columns = chunk_df.columns.tolist()
                
                # マッピングキーで存在するカラム名のみ変換
                mapping_to_apply = {}
                for src_col, dest_col in column_mapping.items():
                    if src_col in existing_columns:
                        mapping_to_apply[src_col] = dest_col
                
                if mapping_to_apply:
                    # カラム名を変換（列名を置き換え）
                    chunk_df = chunk_df.rename(columns=mapping_to_apply)
                    logger.info(f"カラム名を変換しました: {mapping_to_apply}")
                else:
                    logger.warning(f"マッピング対象のカラム {list(column_mapping.keys())} がデータ内に見つかりませんでした")
                    logger.debug(f"実際のカラム: {existing_columns}")
                
                # 変換後のカラム名を表示
                logger.info(f"変換後のカラム: {chunk_df.columns.tolist()}")
                
                # キーカラム '応募ID' が存在するか確認
                if '応募ID' not in chunk_df.columns:
                    # 最初の列を応募IDとして使用
                    logger.warning("'応募ID'カラムが見つかりません。最初の列を応募IDとして使用します。")
                    first_col = chunk_df.columns[0]
                    chunk_df['応募ID'] = chunk_df[first_col]
                    logger.info(f"'{first_col}'カラムの値を'応募ID'にコピーしました")
            
            logger.debug(f"チャンク {chunk_idx+1} の行数: {len(chunk_df)}")
            logger.debug(f"チャンク {chunk_idx+1} のカラム: {chunk_df.columns.tolist()}")
            
            # 一時ファイルを作成してチャンクを保存
            temp_chunk_file = os.path.join(os.path.dirname(csv_file), f"temp_chunk_{chunk_idx}.csv")
            chunk_df.to_csv(temp_chunk_file, index=False, encoding='utf-8')
            logger.debug(f"一時ファイル '{temp_chunk_file}' にデータを保存しました")
            
            # 日付型カラムとデータ型の処理
            if date_columns:
                for col in date_columns:
                    try:
                        if col in chunk_df.columns:
                            # 日付データサンプルを表示
                            non_dates = chunk_df[pd.to_datetime(chunk_df[col], errors='coerce').isna() & chunk_df[col].notna()]
                            if not non_dates.empty:
                                logger.debug(f"カラム '{col}' の日付として解析できない値: {non_dates[col].unique()[:5]}")
                        else:
                            logger.warning(f"指定された日付カラム '{col}' がデータ内に見つかりません")
                    except Exception as e:
                        logger.warning(f"カラム '{col}' の日付変換中にエラーが発生しました: {e}")
            
            # 整数型カラムの処理
            if integer_columns:
                for col in integer_columns:
                    try:
                        if col in chunk_df.columns:
                            # 整数サンプルを表示
                            non_ints = chunk_df[~chunk_df[col].astype(str).str.replace('.', '', regex=False).str.isdigit() & chunk_df[col].notna()]
                            if not non_ints.empty:
                                logger.debug(f"カラム '{col}' の整数として解析できない値: {non_ints[col].unique()[:5]}")
                        else:
                            logger.warning(f"指定された整数カラム '{col}' がデータ内に見つかりません")
                    except Exception as e:
                        logger.warning(f"カラム '{col}' の型変換中にエラーが発生しました: {e}")
            
            # BigQueryへのロード
            try:
                # アップロード処理（write_dispositionを適切に設定）
                if write_disposition:
                    # 最初のチャンクのみwrite_dispositionを適用
                    if chunk_idx == 0:
                        logger.info(f"最初のチャンク: write_disposition={write_disposition} を使用")
                        if process_csv_to_bigquery(temp_chunk_file, table_name, key_column='応募ID', write_disposition=write_disposition):
                            success_count += 1
                            logger.info(f"チャンク {chunk_idx+1}: 処理成功")
                        else:
                            logger.error(f"チャンク {chunk_idx+1}: 処理失敗")
                            failed_count += 1
                            failed_ranges.append((chunk_start+1, chunk_end))
                    else:
                        # 2つ目以降のチャンクはAPPEND
                        logger.info(f"後続チャンク: write_disposition=WRITE_APPEND を使用")
                        if process_csv_to_bigquery(temp_chunk_file, table_name, key_column='応募ID', write_disposition='WRITE_APPEND'):
                            success_count += 1
                            logger.info(f"チャンク {chunk_idx+1}: 処理成功")
                        else:
                            logger.error(f"チャンク {chunk_idx+1}: 処理失敗")
                            failed_count += 1
                            failed_ranges.append((chunk_start+1, chunk_end))
                else:
                    # write_dispositionが指定されていない場合はデフォルト動作
                    logger.info(f"デフォルトのwrite_dispositionを使用")
                    if process_csv_to_bigquery(temp_chunk_file, table_name, key_column='応募ID'):
                        success_count += 1
                        logger.info(f"チャンク {chunk_idx+1}: 処理成功")
                    else:
                        logger.error(f"チャンク {chunk_idx+1}: 処理失敗")
                        failed_count += 1
                        failed_ranges.append((chunk_start+1, chunk_end))
            except Exception as e:
                logger.error(f"チャンク {chunk_idx+1} のBigQueryロード中にエラーが発生しました: {e}")
                failed_count += 1
                failed_ranges.append((chunk_start+1, chunk_end))
            
            # 一時ファイルを削除
            try:
                if os.path.exists(temp_chunk_file):
                    os.remove(temp_chunk_file)
                    logger.debug(f"一時ファイル '{temp_chunk_file}' を削除しました")
            except Exception as e:
                logger.warning(f"一時ファイル '{temp_chunk_file}' の削除中にエラーが発生しました: {e}")
            
        except Exception as e:
            logger.error(f"チャンク {chunk_idx+1} の処理中にエラーが発生しました: {e}")
            failed_count += 1
            failed_ranges.append((chunk_start+1, chunk_end))

    # 処理の完了情報
    elapsed_time = time.time() - start_time
    logger.info(f"チャンク処理完了: 合計 {success_count + failed_count} チャンク処理, 成功: {success_count}, 失敗: {failed_count}, 所要時間: {elapsed_time:.1f}秒")
    
    if failed_count > 0:
        logger.warning(f"失敗した行範囲: {failed_ranges}")
    
    return (success_count, failed_count)

def main():
    """メイン関数"""
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='CSVファイルを分割して処理し、BigQueryにロードするスクリプト')
    parser.add_argument('csv_file', help='入力CSVファイルのパス')
    parser.add_argument('table_name', help='ロード先のテーブル名（形式: データセット.テーブル）')
    parser.add_argument('--chunk-size', type=int, default=1000, help='1回の処理で読み込む行数（デフォルト: 1000）')
    parser.add_argument('--max-chunks', type=int, help='処理する最大チャンク数（デフォルト: すべて処理）')
    parser.add_argument('--start-row', type=int, default=0, help='処理を開始する行番号（0始まり、デフォルト: 0）')
    parser.add_argument('--write-disposition', default='WRITE_TRUNCATE', 
                      choices=['WRITE_TRUNCATE', 'WRITE_APPEND', 'WRITE_EMPTY'], 
                      help='初回チャンクの書き込み方法（デフォルト: WRITE_TRUNCATE）')
    
    args = parser.parse_args()
    
    # 環境変数を読み込む
    env.load_env()
    
    # 売上金額→応募IDの変換マッピング
    column_mapping = {
        '売上金額': '応募ID',
        # 必要に応じて他のカラム変換も追加可能
    }
    
    # 日付カラムの指定
    date_columns = ['CV時間']
    
    # 整数カラムの指定
    integer_columns = ['応募ID', '接触回数', '潜伏期間（秒）']
    
    # チャンク処理の実行
    success, failed = process_in_chunks(
        args.csv_file,
        args.table_name,
        args.chunk_size,
        args.max_chunks,
        args.start_row,
        column_mapping,
        date_columns,
        integer_columns,
        args.write_disposition
    )
    
    # 終了コードを設定（失敗があれば1、成功のみなら0）
    sys.exit(1 if failed > 0 else 0)

if __name__ == '__main__':
    main() 