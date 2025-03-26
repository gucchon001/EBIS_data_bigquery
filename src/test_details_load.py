#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
詳細分析レポートのBigQueryへのインポートをテストするスクリプト
"""

import os
import logging
import sys
import pandas as pd
import re
from datetime import datetime
from src.utils.environment import EnvironmentUtils as env
from src.modules.bigquery.csv_to_bigquery import csv_to_bigquery

# ロギングの設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def extract_date_from_filename(filename):
    """
    ファイル名から日付を抽出する
    
    Args:
        filename: ファイル名（例: 20250325_ebis_SS_CV.csv）
    
    Returns:
        str: YYYY-MM-DD形式の日付
    """
    match = re.search(r'(\d{8})', os.path.basename(filename))
    if match:
        date_str = match.group(1)
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            logger.error(f"ファイル名から抽出した日付 '{date_str}' の解析に失敗しました")
    return None

def preprocess_csv(csv_file, output_file=None):
    """
    CSVファイルを前処理して、日付カラムを追加する
    
    Args:
        csv_file: 入力CSVファイルのパス
        output_file: 出力CSVファイルのパス（指定しない場合は一時ファイルを作成）
        
    Returns:
        str: 処理後のCSVファイルのパス
    """
    logger.info(f"CSVファイル '{csv_file}' の前処理を開始します")
    
    # 出力ファイルが指定されていない場合は一時ファイルを作成
    if output_file is None:
        output_file = os.path.join(os.path.dirname(csv_file), 'temp_preprocessed.csv')
        
    # ファイル名から日付を抽出
    date_value = extract_date_from_filename(csv_file)
    if not date_value:
        logger.error("ファイル名から日付を抽出できませんでした")
        return None
        
    # データ取得日（現在日付）
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # CSVファイルを読み込む
        df = pd.read_csv(csv_file, encoding='cp932')
        logger.info(f"CSVファイルを読み込みました: {len(df)} 行")
        
        # カラム名の変換マッピング
        column_mapping = {
            'チャネル種別': 'チャネル名',
            'カテゴリ': 'カテゴリ',
            '広告ID': '広告ID',
            '名称': '名称',
            '表示回数': '表示',
            'クリック／流入回数': 'クリック数',
            'CTR': 'CTR',
            'セッション数': 'セッション数',
            '総PV': '総PV',
            '平均PV': '平均PV',
            '直帰数': 'リピート数',
            '直帰率': 'リピート率',
            '総滞在時間': '滞在時間',
            '総滞在時間（秒）': '滞在時間_秒',
            '平均滞在時間': '平均滞在時間',
            '平均滞在時間（秒）': '平均滞在時間_秒',
            '総潜伏期間': '総閲覧時間',
            '総潜伏期間（秒）': '総閲覧時間_秒',
            '平均潜伏期間': '平均閲覧時間',
            '平均潜伏期間（秒）': '平均閲覧時間_秒',
            '応募完了（CV）': '直接動線_CV',
            '応募完了（CVR）': '直接動線_CVR',
            '会員登録完了（CV）': '会員登録動線_CV',
            '会員登録完了（CVR）': '会員登録動線_CVR',
            'CV（合計）': 'CV_合計',
            'CVR（合計）': 'CVR_合計',
            '間接効果2': '間接効果2',
            '間接効果3': '間接効果3',
            '間接効果4': '間接効果4',
            '間接効果5': '間接効果5',
            '間接効果6 - 10': '間接効果6_10',
            '間接効果（合計）': '間接効果_合計',
            '直間比率（直接）': '貢献割合_直接',
            '直間比率（間接）': '貢献割合_間接',
            '初回接触': '初回接触',
            '再配分CV': '再訪問CV',
            '売上総額': '売上送金額',
            '広告コスト': '広告コスト',
            'CPA': 'CPA',
            'TCPA': 'TCPA',
            'ROAS': 'ROAS'
        }
        
        # カラム名を変換
        df = df.rename(columns=column_mapping)
        logger.info(f"カラム名を変換しました: {list(df.columns)}")
        
        # 日付カラムを追加
        df['日付'] = date_value
        df['データ取得日'] = today
        logger.info(f"日付カラムを追加しました: 日付={date_value}, データ取得日={today}")
        
        # CSVファイルに保存
        df.to_csv(output_file, index=False, encoding='utf-8')
        logger.info(f"前処理済みCSVファイルを保存しました: {output_file}")
        
        return output_file
        
    except Exception as e:
        logger.error(f"CSVファイルの前処理中にエラーが発生しました: {e}", exc_info=True)
        return None

def main():
    try:
        # 環境変数ファイルのロード
        env_file = os.path.join(env.get_project_root(), "config", "secrets.env")
        logger.info(f"環境変数ファイル '{env_file}' をロードします")
        env.load_env()

        # 現在のディレクトリとPYTHONPATHを確認
        logger.debug(f"現在のディレクトリ: {os.getcwd()}")
        logger.debug(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
        logger.debug(f"GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")

        # CSVファイルパスの設定
        csv_file = os.path.join(env.get_project_root(), "data", "downloads", "20250325_ebis_SS_CV.csv")
        logger.debug(f"CSVファイルの絶対パス: {os.path.abspath(csv_file)}")
        
        # BigQueryのデータセットとテーブルの設定を表示
        dataset = env.get_env_var('BIGQUERY_DATASET')
        table = 'details_analysis_report'
        table_name = f"{dataset}.{table}"
        logger.info(f"BigQueryテーブル: {table_name} にデータをロードします")

        # CSVファイルの存在確認
        if not os.path.exists(csv_file):
            logger.error(f"CSVファイル '{csv_file}' が見つかりません")
            raise FileNotFoundError(f"CSVファイル '{csv_file}' が見つかりません")
        else:
            logger.debug(f"CSVファイルのサイズ: {os.path.getsize(csv_file)} bytes")

        logger.info(f"CSVファイル '{csv_file}' の処理を開始します")

        # CSVファイルの前処理
        processed_csv = preprocess_csv(csv_file)
        if not processed_csv:
            logger.error("CSVファイルの前処理に失敗しました")
            return

        # 日付カラムの指定
        date_columns = ['日付', 'データ取得日']
        
        # 整数型カラムの指定
        integer_columns = [
            '表示', 'クリック数', 'セッション数', '総PV', 'リピート数',
            '滞在時間_秒', '平均滞在時間_秒', '総閲覧時間_秒', '平均閲覧時間_秒',
            '直接動線_CV', '会員登録動線_CV', 'CV_合計',
            '間接効果2', '間接効果3', '間接効果4', '間接効果5',
            '間接効果6_10', '間接効果_合計', '初回接触'
        ]

        # データのロード処理
        success = csv_to_bigquery(
            csv_file=processed_csv,
            table_name=table_name,
            write_disposition='WRITE_APPEND',
            column_mapping=None,  # 前処理で既に変換済み
            date_columns=date_columns,
            integer_columns=integer_columns
        )

        # 一時ファイルの削除
        try:
            if os.path.exists(processed_csv):
                os.remove(processed_csv)
                logger.debug(f"一時ファイル '{processed_csv}' を削除しました")
        except Exception as e:
            logger.warning(f"一時ファイル '{processed_csv}' の削除中にエラーが発生しました: {e}")

        if success:
            logger.info("データのロードが正常に完了しました")
        else:
            logger.error("データのロード中にエラーが発生しました")

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main() 