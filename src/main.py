from src.utils.environment import EnvironmentUtils as env
from src.utils.logging_config import get_logger

# 名前付きロガーを取得
logger = get_logger(__name__)

def setup_configurations():
    """
    設定ファイルと機密情報をロードしてデータを取得します。
    """
    # 環境変数のロード
    env.load_env()

    # settings.ini の値を取得
    temp_value = env.get_config_value("demo", "temp", default="N/A")
    logger.info(f"取得した設定値: demo.temp = {temp_value}")

    # secrets.env の値を取得
    secrets_demo = env.get_env_var("secrets_demo", default="N/A")
    logger.info(f"取得した秘密情報: secrets_demo = {secrets_demo}")

    # 現在の環境
    environment = env.get_environment()
    logger.info(f"現在の環境: {environment}")

    return temp_value, secrets_demo, environment

def main() -> None:
    """メイン処理"""
    # 実行時のメッセージ
    print("Hello, newProject!!")
    logger.info("Hello, newProject!!")

    # 設定値と秘密情報のロード
    temp, secrets_demo, environment = setup_configurations()

    # 設定完了メッセージの表示
    print(f'設定ファイルの設定完了{{"demo": "{temp}"}}')
    print(f'機密情報ファイルの設定完了{{"demo": "{secrets_demo}"}}')
    print('ログ設定完了')

if __name__ == "__main__":
    main()
