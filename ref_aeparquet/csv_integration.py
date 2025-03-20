# import pandas as pd
# import os
# from datetime import datetime, timedelta
# import logging
# import configparser

# def append_csv_data(source_file, destination_file):
#     try:
#         source_df = pd.read_csv(source_file, encoding='cp932')
#         source_df.to_csv(destination_file, mode='a', header=False, index=False, encoding='cp932')
#         logging.info(f"{source_file} のデータを {destination_file} に追加しました。")
#     except Exception as e:
#         logging.error(f"{source_file} の処理中にエラーが発生しました: {str(e)}")

# def integrate_csv_files(config):
#     moveto_folder = config['Paths']['moveto']
#     set_folder = config['Paths']['set_folder']

#     yesterday = datetime.now() - timedelta(days=1)
#     date_str = yesterday.strftime('%Y%m%d')

#     files = {
#         f"{date_str}_ebis_CVrepo.csv": 'AE_CV属性result.csv',
#         f"{date_str}_CV.csv": 'AE_CVresult.csv',
#         f"{date_str}_SS.csv": 'AE_SSresult.csv'
#     }

#     for source_file, dest_file in files.items():
#         source_path = os.path.join(moveto_folder, source_file)
#         dest_path = os.path.join(set_folder, dest_file)

#         if os.path.exists(source_path):
#             append_csv_data(source_path, dest_path)
#         else:
#             logging.warning(f"ファイルが見つかりません: {source_path}")

# if __name__ == "__main__":
#     import configparser
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#     config = configparser.ConfigParser()
#     config.read('settings.ini', encoding='utf-8')
#     integrate_csv_files(config)

import pandas as pd
import os
from datetime import datetime, timedelta
import logging
import configparser  # 必要なインポートを追加

def append_csv_data(source_file, destination_file):
    try:
        source_df = pd.read_csv(source_file, encoding='cp932')
        source_df.to_csv(destination_file, mode='a', header=False, index=False, encoding='cp932')
        logging.info(f"{source_file} のデータを {destination_file} に追加しました。")
    except Exception as e:
        logging.error(f"{source_file} の処理中にエラーが発生しました: {str(e)}")

def integrate_csv_files(config):
    # 設定ファイルからパス情報を取得
    moveto_folder = config['Paths']['moveto']
    set_folder = config['Paths']['set_folder']

    # settings.iniからdays_agoを取得して日付を計算
    days_ago = int(config['DownloadSettings']['days_ago'])
    target_date = datetime.now() - timedelta(days=days_ago)
    date_str = target_date.strftime('%Y%m%d')  # YYYYMMDD形式に変換

    # 操作対象のファイルを定義
    files = {
        f"{date_str}_ebis_CVrepo.csv": 'AE_CV属性result.csv',
        f"{date_str}_CV.csv": 'AE_CVresult.csv',
        f"{date_str}_SS.csv": 'AE_SSresult.csv'
    }

    for source_file, dest_file in files.items():
        source_path = os.path.join(moveto_folder, source_file)
        dest_path = os.path.join(set_folder, dest_file)

        if os.path.exists(source_path):
            append_csv_data(source_path, dest_path)
        else:
            logging.warning(f"ファイルが見つかりません: {source_path}")

if __name__ == "__main__":
    # 設定ファイルを読み込み
    import configparser
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    config = configparser.ConfigParser()
    config.read('settings.ini', encoding='utf-8')
    integrate_csv_files(config)
