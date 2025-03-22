import os
import sys
import time
from datetime import datetime, timedelta

# プロジェクトルートへのパスを追加
sys.path.append(os.path.abspath('.'))

from src.utils.environment import EnvironmentUtils as env
from src.utils.logging_config import get_logger
from src.modules.browser.detail_analytics_page import DetailAnalyticsPage

logger = get_logger(__name__)

def test_detail_analytics():
    """detail_analyticsページの操作をテストする"""
    try:
        # 環境変数の読み込み
        env.load_env()
        
        # DetailAnalyticsPageのインスタンス作成（ログイン実行）
        logger.info("DetailAnalyticsPageクラスのインスタンスを作成します")
        detail_analytics = DetailAnalyticsPage(login_first=True)
        
        # 先月の日付範囲を設定
        today = datetime.now()
        first_day_of_this_month = today.replace(day=1)
        last_month_last_day = first_day_of_this_month - timedelta(days=1)
        last_month_first_day = last_month_last_day.replace(day=1)
        
        # 詳細分析ページのダウンロードフロー実行
        logger.info(f"詳細分析データのダウンロードを実行します: {last_month_first_day.strftime('%Y-%m-%d')} から {last_month_last_day.strftime('%Y-%m-%d')}")
        success = detail_analytics.execute_download_flow(
            start_date=last_month_first_day,
            end_date=last_month_last_day
        )
        
        if success:
            logger.info("テスト成功: 詳細分析データのダウンロードが完了しました")
            print("テスト成功: 詳細分析データのダウンロードが完了しました")
        else:
            logger.error("テスト失敗: 詳細分析データのダウンロードに失敗しました")
            print("テスト失敗: 詳細分析データのダウンロードに失敗しました")
    
    except Exception as e:
        logger.error(f"テスト中にエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # ブラウザを終了
        if 'detail_analytics' in locals() and detail_analytics:
            detail_analytics.quit()

if __name__ == "__main__":
    test_detail_analytics() 