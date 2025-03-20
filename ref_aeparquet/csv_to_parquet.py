import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import logging
import csv
import re

def dedup_columns(columns):
    seen = set()
    result = []
    for item in columns:
        if item in seen:
            counter = 1
            while f"{item}_{counter}" in seen:
                counter += 1
            item = f"{item}_{counter}"
        seen.add(item)
        result.append(item)
    return result

def check_and_clean_csv(file_path, expected_fields):
    cleaned_rows = []
    with open(file_path, 'r', encoding='cp932') as f:
        reader = csv.reader(f)
        headers = next(reader)  # ヘッダー行を保存
        headers = [h.strip() for h in headers if h.strip()]  # 空のヘッダーを削除
        headers = dedup_columns(headers)
        sales_amount_index = headers.index('売上金額') if '売上金額' in headers else -1  # 売上金額の列インデックスを取得
        cleaned_rows.append(headers)
        for i, row in enumerate(reader, 2):  # 2から始めるのは、ヘッダー行を考慮するため
            if len(row) != expected_fields:
                logging.warning(f"行 {i}: 予期しないフィールド数 {len(row)}, 期待値 {expected_fields}")
                row = row[:expected_fields] + [''] * (expected_fields - len(row))  # 切り捨てまたは埋める
            cleaned_row = []
            for index, field in enumerate(row):
                if index == sales_amount_index:
                    cleaned_row.append(convert_currency(field))  # 売上金額の列だけ変換
                else:
                    cleaned_row.append(field)  # その他の列はそのまま
            cleaned_rows.append(cleaned_row)
    return cleaned_rows

def convert_currency(field):
    # 数値のみを抽出
    numeric_value = re.sub(r'[^\d.]', '', field)
    
    # 抽出した数値が空でない場合、それを返す
    if numeric_value:
        return numeric_value
    
    # 数値が抽出できなかった場合、元の値をそのまま返す
    return field

def get_csv_field_count(file_path):
    with open(file_path, 'r', encoding='cp932') as f:
        reader = csv.reader(f)
        headers = next(reader)
        return len([h for h in headers if h.strip()])

def csv_to_parquet(csv_file, parquet_file):
    try:
        expected_fields = get_csv_field_count(csv_file)
        cleaned_rows = check_and_clean_csv(csv_file, expected_fields)
        
        # クリーニングされたデータをDataFrameに変換
        df = pd.DataFrame(cleaned_rows[1:], columns=cleaned_rows[0])
        
        # すべての列をobject型に変換
        df = df.astype('object')
        
        # 重複するカラム名を一意にする
        df.columns = dedup_columns(df.columns)
        
        # DataFrameをParquetファイルとして保存
        table = pa.Table.from_pandas(df)
        pq.write_table(table, parquet_file)
        logging.info(f"{csv_file} を Parquet ファイルに変換しました: {parquet_file}")
    except Exception as e:
        logging.error(f"{csv_file} の変換中にエラーが発生しました: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())

def convert_csv_to_parquet(config):
    set_folder = config['Paths']['set_folder']
    
    csv_files = [
        'AE_CV属性result.csv',
        'AE_CVresult.csv',
        'AE_SSresult.csv'
    ]

    for csv_file in csv_files:
        csv_path = os.path.join(set_folder, csv_file)
        parquet_file = os.path.splitext(csv_path)[0] + '.parquet'
        
        if os.path.exists(csv_path):
            csv_to_parquet(csv_path, parquet_file)
        else:
            logging.warning(f"ファイルが見つかりません: {csv_path}")

if __name__ == "__main__":
    import configparser
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    config = configparser.ConfigParser()
    config.read('settings.ini', encoding='utf-8')
    convert_csv_to_parquet(config)

# import os
# import pandas as pd
# import pyarrow as pa
# import pyarrow.parquet as pq
# import logging
# import csv
# import re
# import configparser
# from datetime import datetime, timedelta

# def dedup_columns(columns):
#     seen = set()
#     result = []
#     for item in columns:
#         if item in seen:
#             counter = 1
#             while f"{item}_{counter}" in seen:
#                 counter += 1
#             item = f"{item}_{counter}"
#         seen.add(item)
#         result.append(item)
#     return result

# def check_and_clean_csv(file_path, expected_fields):
#     cleaned_rows = []
#     with open(file_path, 'r', encoding='cp932') as f:
#         reader = csv.reader(f)
#         headers = next(reader)  # ヘッダー行を保存
#         headers = [h.strip() for h in headers if h.strip()]  # 空のヘッダーを削除
#         headers = dedup_columns(headers)
#         sales_amount_index = headers.index('売上金額') if '売上金額' in headers else -1  # 売上金額の列インデックスを取得
#         cleaned_rows.append(headers)
#         for i, row in enumerate(reader, 2):  # 2から始めるのは、ヘッダー行を考慮するため
#             if len(row) != expected_fields:
#                 logging.warning(f"行 {i}: 予期しないフィールド数 {len(row)}, 期待値 {expected_fields}")
#                 row = row[:expected_fields] + [''] * (expected_fields - len(row))  # 切り捨てまたは埋める
#             cleaned_row = []
#             for index, field in enumerate(row):
#                 if index == sales_amount_index:
#                     cleaned_row.append(convert_currency(field))  # 売上金額の列だけ変換
#                 else:
#                     cleaned_row.append(field)  # その他の列はそのまま
#             cleaned_rows.append(cleaned_row)
#     return cleaned_rows

# def convert_currency(field):
#     # 数値のみを抽出
#     numeric_value = re.sub(r'[^\d.]', '', field)
#     return numeric_value if numeric_value else field

# def get_csv_field_count(file_path):
#     with open(file_path, 'r', encoding='cp932') as f:
#         reader = csv.reader(f)
#         headers = next(reader)
#         return len([h for h in headers if h.strip()])

# def csv_to_parquet(csv_file, parquet_file):
#     try:
#         expected_fields = get_csv_field_count(csv_file)
#         cleaned_rows = check_and_clean_csv(csv_file, expected_fields)
        
#         # クリーニングされたデータをDataFrameに変換
#         df = pd.DataFrame(cleaned_rows[1:], columns=cleaned_rows[0])
        
#         # すべての列をobject型に変換
#         df = df.astype('object')
        
#         # 重複するカラム名を一意にする
#         df.columns = dedup_columns(df.columns)
        
#         # DataFrameをParquetファイルとして保存
#         table = pa.Table.from_pandas(df)
#         pq.write_table(table, parquet_file)
#         logging.info(f"{csv_file} を Parquet ファイルに変換しました: {parquet_file}")
#     except Exception as e:
#         logging.error(f"{csv_file} の変換中にエラーが発生しました: {str(e)}")
#         import traceback
#         logging.error(traceback.format_exc())

# def convert_csv_to_parquet(config):
#     # 設定ファイルから必要な情報を取得
#     set_folder = config['Paths']['set_folder']
#     days_ago = int(config['DownloadSettings']['days_ago'])
#     target_date = datetime.now() - timedelta(days=days_ago)
#     date_str = target_date.strftime('%Y%m%d')  # YYYYMMDD形式

#     # ターゲット日付に基づくファイル名
#     csv_files = {
#         f"{date_str}_ebis_CVrepo.csv": 'AE_CV属性result.csv',
#         f"{date_str}_CV.csv": 'AE_CVresult.csv',
#         f"{date_str}_SS.csv": 'AE_SSresult.csv'
#     }

#     for source_file, parquet_name in csv_files.items():
#         csv_path = os.path.join(set_folder, source_file)
#         parquet_file = os.path.splitext(csv_path)[0] + '.parquet'
        
#         if os.path.exists(csv_path):
#             csv_to_parquet(csv_path, parquet_file)
#         else:
#             logging.warning(f"ファイルが見つかりません: {csv_path}")

# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#     config = configparser.ConfigParser()
#     config.read('settings.ini', encoding='utf-8')
#     convert_csv_to_parquet(config)
