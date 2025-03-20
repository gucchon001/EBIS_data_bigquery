import logging
import traceback
from logging.handlers import RotatingFileHandler
import configparser
import sys 
import os

def setup_global_exception_logging(logger):
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # 未処理例外の詳細情報を含むエラーメッセージを生成
        error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error("Uncaught exception: %s", error_message)

    sys.excepthook = handle_exception

def setup_department_logger(name):
    # 設定ファイルからログ設定を読み込む
    config = configparser.ConfigParser()
    config.read('settings.ini', encoding='utf-8')

    # ログレベル、ログファイルのパス、ファイル名を取得
    log_level = config['logging']['level']
    log_file = config['logging']['logfile']

    # ログファイルの完全なパスを生成
    log_file_full_path = os.path.join(log_file)

    # ログのフォーマットを設定
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # ファイルハンドラの設定（ログローテーション対応）
    file_handler = RotatingFileHandler(log_file_full_path, maxBytes=10000000, backupCount=10)
    file_handler.setLevel(logging.getLevelName(log_level))
    file_handler.setFormatter(formatter)

    # コンソールハンドラの設定
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.getLevelName(log_level))
    console_handler.setFormatter(formatter)

    # ロガーを作成し、ハンドラを追加
    logger = logging.getLogger(name)
    logger.setLevel(logging.getLevelName(log_level))
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    # グローバル例外ハンドラの設定
    setup_global_exception_logging(logger)

    return logger
