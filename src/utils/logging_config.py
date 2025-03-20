# logging_config.py
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional

class LoggingConfig:
    _initialized = False

    def __init__(self):
        """
        ログ設定を初期化します。
        """
        if LoggingConfig._initialized:
            return  # 再初期化を防止

        self.log_dir = Path("logs")
        self.log_level = logging.INFO
        self.log_format = "%(asctime)s - %(name)s - [%(levelname)s] - %(message)s"

        self.setup_logging()

        LoggingConfig._initialized = True  # 初期化済みフラグを設定

    def setup_logging(self) -> None:
        """
        ロギング設定をセットアップします。
        """
        if not self.log_dir.exists():
            self.log_dir.mkdir(parents=True, exist_ok=True)

        log_file = self.log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"

        handlers = [
            logging.handlers.TimedRotatingFileHandler(
                log_file, when="midnight", interval=1, backupCount=30, encoding="utf-8"
            ),
            logging.StreamHandler(),
        ]

        logging.basicConfig(
            level=self.log_level,
            format=self.log_format,
            handlers=handlers,
        )

        logging.getLogger().info("Logging setup complete.")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    名前付きロガーを取得します。

    Args:
        name (Optional[str]): ロガー名

    Returns:
        logging.Logger: 名前付きロガー
    """
    LoggingConfig()
    return logging.getLogger(name)