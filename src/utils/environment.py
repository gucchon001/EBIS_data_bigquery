import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Any
import configparser

class EnvironmentUtils:
    """プロジェクト全体で使用する環境関連のユーティリティクラス"""

    # プロジェクトルートのデフォルト値
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    @staticmethod
    def set_project_root(path: Path) -> None:
        """
        プロジェクトのルートディレクトリを設定します。

        Args:
            path (Path): 新しいプロジェクトルート
        """
        EnvironmentUtils.BASE_DIR = path

    @staticmethod
    def get_project_root() -> Path:
        """
        プロジェクトのルートディレクトリを取得します。

        Returns:
            Path: プロジェクトのルートディレクトリ
        """
        return EnvironmentUtils.BASE_DIR

    @staticmethod
    def load_env(env_file: Optional[Path] = None) -> None:
        """
        環境変数を .env ファイルからロードします。

        Args:
            env_file (Optional[Path]): .env ファイルのパス
        """
        env_file = env_file or (EnvironmentUtils.BASE_DIR / "config" / "secrets.env")

        if not env_file.exists():
            raise FileNotFoundError(f"{env_file} が見つかりません。正しいパスを指定してください。")

        load_dotenv(env_file)

    @staticmethod
    def get_env_var(key: str, default: Optional[Any] = None) -> Any:
        """
        環境変数を取得します。

        Args:
            key (str): 環境変数のキー
            default (Optional[Any]): デフォルト値

        Returns:
            Any: 環境変数の値またはデフォルト値
        """
        return os.getenv(key, default)

    @staticmethod
    def get_config_file(file_name: str = "settings.ini") -> Path:
        """
        設定ファイルのパスを取得します。

        Args:
            file_name (str): 設定ファイル名

        Returns:
            Path: 設定ファイルのパス

        Raises:
            FileNotFoundError: 指定された設定ファイルが見つからない場合
        """
        config_path = EnvironmentUtils.BASE_DIR / "config" / file_name
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        return config_path

    @staticmethod
    def get_config_value(section: str, key: str, default: Optional[Any] = None) -> Any:
        """
        設定ファイルから指定のセクションとキーの値を取得します。

        Args:
            section (str): セクション名
            key (str): キー名
            default (Optional[Any]): デフォルト値

        Returns:
            Any: 設定値
        """
        config_path = EnvironmentUtils.get_config_file()
        config = configparser.ConfigParser()

        # utf-8 エンコーディングで読み込む
        config.read(config_path, encoding='utf-8')

        if not config.has_section(section):
            return default
        if not config.has_option(section, key):
            return default

        value = config.get(section, key, fallback=default)

        # 型変換
        if value.isdigit():
            return int(value)
        if value.replace('.', '', 1).isdigit():
            return float(value)
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        return value

    @staticmethod
    def resolve_path(path: str) -> Path:
        """
        指定されたパスをプロジェクトルートに基づいて絶対パスに変換します。

        Args:
            path (str): 相対パスまたは絶対パス

        Returns:
            Path: 解決された絶対パス
        """
        resolved_path = Path(path)
        if not resolved_path.is_absolute():
            resolved_path = EnvironmentUtils.get_project_root() / resolved_path

        if not resolved_path.exists():
            raise FileNotFoundError(f"Resolved path does not exist: {resolved_path}")

        return resolved_path

    @staticmethod
    def get_service_account_file() -> Path:
        """
        サービスアカウントファイルのパスを取得します。

        Returns:
            Path: サービスアカウントファイルの絶対パス

        Raises:
            FileNotFoundError: ファイルが存在しない場合
        """
        service_account_file = EnvironmentUtils.get_env_var(
            "SERVICE_ACCOUNT_FILE",
            default=EnvironmentUtils.get_config_value("GOOGLE", "service_account_file", default="config/service_account.json")
        )

        return EnvironmentUtils.resolve_path(service_account_file)

    @staticmethod
    def get_environment() -> str:
        """
        環境変数 APP_ENV を取得します。
        デフォルト値は 'development' です。

        Returns:
            str: 現在の環境（例: 'development', 'production'）
        """
        return EnvironmentUtils.get_env_var("APP_ENV", "development")

    @staticmethod
    def get_openai_api_key():
        """
        Get the OpenAI API key from the environment variables.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY が設定されていません。環境変数を確認してください。")
        return api_key

    @staticmethod
    def get_openai_model():
        """
        OpenAI モデル名を settings.ini ファイルから取得します。
        設定がない場合はデフォルト値 'gpt-4o' を返します。
        """
        return EnvironmentUtils.get_config_value("OPENAI", "model", default="gpt-4o")
