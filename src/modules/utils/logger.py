import logging
import sys

def get_logger(name):
    """
    指定された名前でロガーを取得する
    
    Args:
        name: ロガー名
    
    Returns:
        logging.Logger: 設定済みのロガーインスタンス
    """
    logger = logging.getLogger(name)
    
    # ロガーのレベルをDEBUGに設定
    logger.setLevel(logging.DEBUG)
    
    # 既存のハンドラをクリア
    logger.handlers.clear()
    
    # 標準出力へのハンドラを追加
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    
    # フォーマッタを設定
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # ハンドラをロガーに追加
    logger.addHandler(handler)
    
    return logger 