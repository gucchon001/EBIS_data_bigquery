import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os
from pathlib import Path

# 入力と出力のファイルパス
input_file = r'\\eps50\powerbi_sorce\data\掲載教室\count_classroom.csv'
output_folder = r'\\eps50\powerbi_sorce\data\掲載教室'
output_file = os.path.join(output_folder, 'count_classroom.parquet')

# 数値型に変換する列のリスト
numeric_columns = ['教室グループID', '企業ID', '都道府県', 'プラン', '掲載設定数', '急募求人数']

try:
    # 入力ファイルの存在確認
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"入力ファイルが見つかりません: {input_file}")

    # 出力フォルダの存在確認と作成
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    # CSVファイルを読み込む
    df = pd.read_csv(input_file, encoding='cp932')

    # 指定された列を数値型に変換し、それ以外をobject型に設定
    for column in df.columns:
        if column in numeric_columns:
            df[column] = pd.to_numeric(df[column], errors='coerce')
        else:
            df[column] = df[column].astype('object')

    # DataFrameをArrow Tableに変換
    table = pa.Table.from_pandas(df)

    # Parquetファイルとして保存
    pq.write_table(table, output_file)

    print(f"変換が完了しました。Parquetファイルが保存されました: {output_file}")

except FileNotFoundError as e:
    print(f"エラー: {e}")
except PermissionError:
    print(f"エラー: 出力ファイルへの書き込み権限がありません: {output_file}")
except Exception as e:
    print(f"予期せぬエラーが発生しました: {e}")