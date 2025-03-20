import configparser
from adebis_operations import perform_adebis_operations
from csv_integration import integrate_csv_files
from csv_to_parquet import convert_csv_to_parquet
from my_logging import setup_department_logger
import logging
import traceback
import slack_notify  

# ロガーを設定
LOGGER = setup_department_logger('main')

def main():
    try:
        # 設定ファイルを読み込む
        config = configparser.ConfigParser()
        config.read('settings.ini', encoding='utf-8')

        # アドエビス操作を実行
        LOGGER.info("アドエビスからデータを取得中...")
        perform_adebis_operations(config)

        # CSVファイルを統合
        LOGGER.info("CSVファイルを統合中...")
        integrate_csv_files(config)

        # CSVファイルをParquetに変換
        LOGGER.info("CSVファイルをParquetに変換中...")
        convert_csv_to_parquet(config)

        LOGGER.info("すべての処理が完了しました。")
    except Exception as e:
        # エラーログを記録
        error_message = traceback.format_exc()
        LOGGER.error(f"エラーが発生しました: {error_message}")

        # Slackにエラー通知を送信
        config = configparser.ConfigParser()
        config.read('settings.ini', encoding='utf-8')
        slack_notify.send_slack_error_message(e, config=config)

if __name__ == "__main__":
    main()


# import configparser
# from adebis_operations import perform_adebis_operations
# from csv_integration import integrate_csv_files
# from csv_to_parquet import convert_csv_to_parquet
# import logging

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# def main():
#     try:
#         # 設定ファイルを読み込む
#         config = configparser.ConfigParser()
#         config.read('settings.ini', encoding='utf-8')

#         # アドエビス操作を実行
#         logging.info("アドエビスからデータを取得中...")
#         perform_adebis_operations(config)

#         # CSVファイルを統合
#         logging.info("CSVファイルを統合中...")
#         integrate_csv_files(config)

#         # CSVファイルをParquetに変換
#         logging.info("CSVファイルをParquetに変換中...")
#         convert_csv_to_parquet(config)

#         logging.info("すべての処理が完了しました。")
#     except Exception as e:
#         logging.error(f"エラーが発生しました: {str(e)}", exc_info=True)

# if __name__ == "__main__":
#     main()