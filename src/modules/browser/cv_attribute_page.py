#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
コンバージョン属性ページ操作モジュール
EBiSコンバージョン属性ページへのアクセスとCSVダウンロードを実行するクラスを提供します。
"""

import os
import time
import sys
from pathlib import Path
import traceback
from datetime import datetime, timedelta

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent.parent.parent)
sys.path.append(project_root)

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env
from src.modules.browser.browser import Browser
from src.modules.browser.login_page import LoginPage

logger = get_logger(__name__)

class CvAttributePage:
    """
    コンバージョン属性ページの操作を担当するクラス
    コンバージョン属性ページへのアクセス、日付範囲の選択、CSVダウンロードなどの操作を提供します
    """
    
    def __init__(self, browser=None, login_first=True):
        """
        初期化
        Browser クラスのインスタンスを使用してブラウザ操作を行います
        
        Args:
            browser (Browser): 既存のブラウザインスタンス（省略時は新規作成）
            login_first (bool): インスタンス化時に自動的にログインするかどうか
        """
        # 環境変数を確実に読み込む
        env.load_env()
        
        # ブラウザインスタンスの設定
        self.browser_created = False
        if browser is None:
            # ブラウザインスタンスの作成
            headless_value = env.get_config_value("BROWSER", "headless", "false")
            # 文字列またはブール値の両方に対応
            if isinstance(headless_value, str):
                headless = headless_value.lower() == "true"
            else:
                headless = bool(headless_value)
                
            self.browser = Browser(selectors_path="config/selectors.csv", headless=headless)
            if not self.browser.setup():
                logger.error("ブラウザのセットアップに失敗しました")
                raise RuntimeError("ブラウザのセットアップに失敗しました")
            self.browser_created = True
            
            # ログインが必要な場合は実行
            if login_first:
                login_page = LoginPage(browser=self.browser)
                if not login_page.execute_login_flow():
                    logger.error("ログインに失敗しました")
                    raise RuntimeError("ログインに失敗しました")
                logger.info("ログインに成功しました")
        else:
            # 既存のブラウザインスタンスを使用
            self.browser = browser
        
        # ダッシュボードURL
        self.dashboard_url = env.get_config_value("Login", "success_url", "https://bishamon.ebis.ne.jp/dashboard")
        
        # 要素待機のタイムアウト設定
        self.timeout = int(env.get_config_value("BROWSER", "element_timeout", "30"))
        
    def navigate_to_cv_attribute_page(self):
        """
        コンバージョン属性ページに移動
        
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("コンバージョン属性ページに移動します")
            
            # ダッシュボードページに移動
            if not self.browser.navigate_to(self.dashboard_url):
                logger.error("ダッシュボードページへのアクセスに失敗しました")
                return False
            
            # コンバージョン属性ボタンを探してクリック
            try:
                logger.info("コンバージョン属性ボタンを探します")
                WebDriverWait(self.browser.driver, self.timeout).until(
                    EC.presence_of_element_located((By.XPATH, 
                        "//a[contains(text(), 'コンバージョン属性') or .//span[contains(text(), 'コンバージョン属性')]]"))
                )
                
                # スクリーンショット取得
                self.browser.save_screenshot("dashboard_before_cv_click.png")
                
                # コンバージョン属性ボタンのクリック
                cv_btn = self.browser.driver.find_element(By.XPATH, 
                    "//a[contains(text(), 'コンバージョン属性') or .//span[contains(text(), 'コンバージョン属性')]]")
                self.browser.click_element(None, None, element=cv_btn)
                
                # ページ遷移待機（URL変化またはページロード完了）
                WebDriverWait(self.browser.driver, self.timeout).until(
                    lambda driver: "conversion" in driver.current_url.lower() or "cv" in driver.current_url.lower() or
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'コンバージョン属性')]"))(driver)
                )
                
                logger.info(f"コンバージョン属性ページに移動しました: {self.browser.driver.current_url}")
                return True
                
            except (TimeoutException, NoSuchElementException) as e:
                logger.error(f"コンバージョン属性ボタンが見つからないか、クリックできませんでした: {str(e)}")
                self.browser.save_screenshot("error_cv_button_not_found.png")
                return False
                
        except Exception as e:
            logger.error(f"コンバージョン属性ページへの移動中にエラーが発生しました: {str(e)}")
            self.browser.save_screenshot("error_navigate_to_cv.png")
            return False
    
    def click_all_traffic_if_needed(self):
        """
        全トラフィックボタンが表示されている場合にクリックする
        
        Returns:
            bool: 成功した場合または不要だった場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("全トラフィックボタンの有無を確認しています")
            
            # 全トラフィックボタンがあるか確認
            try:
                all_traffic_btn = WebDriverWait(self.browser.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, 
                        "//button[contains(text(), '全トラフィック') or .//span[contains(text(), '全トラフィック')]]"))
                )
                
                logger.info("全トラフィックボタンが見つかりました。クリックします。")
                self.browser.click_element(None, None, element=all_traffic_btn)
                
                # クリック後の要素表示を待機
                WebDriverWait(self.browser.driver, self.timeout).until(
                    EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'data-table')]"))
                )
                
                return True
                
            except TimeoutException:
                logger.info("全トラフィックボタンは表示されていません。スキップします。")
                return True
                
        except Exception as e:
            logger.error(f"全トラフィックボタンの処理中にエラーが発生しました: {str(e)}")
            self.browser.save_screenshot("error_all_traffic_button_cv.png")
            return False
    
    def select_date_range(self, start_date=None, end_date=None):
        """
        日付範囲を選択する
        
        Args:
            start_date (str or datetime): 開始日（YYYY-MM-DD形式の文字列または日付オブジェクト）
            end_date (str or datetime): 終了日（YYYY-MM-DD形式の文字列または日付オブジェクト）
            
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 日付が指定されていない場合は、デフォルトで先月1日から末日までを設定
            if start_date is None or end_date is None:
                today = datetime.now()
                last_month = today.replace(day=1) - timedelta(days=1)
                start_date = last_month.replace(day=1)
                end_date = last_month
            
            # 文字列の場合は日付オブジェクトに変換
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
                
            logger.info(f"日付範囲を設定します: {start_date.strftime('%Y-%m-%d')} から {end_date.strftime('%Y-%m-%d')}")
            
            # カレンダーボタンをクリック
            try:
                logger.info("カレンダーボタンを探します")
                calendar_btn = WebDriverWait(self.browser.driver, self.timeout).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        "//button[contains(@class, 'calendar') or contains(text(), 'カレンダー') or .//span[contains(text(), 'カレンダー')]]"))
                )
                
                # スクロールして要素を表示
                self.browser.scroll_to_element(calendar_btn)
                
                # カレンダーボタンのクリック
                self.browser.click_element(None, None, element=calendar_btn)
                
                # ダイアログの表示を待機
                WebDriverWait(self.browser.driver, self.timeout).until(
                    EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'datepicker') or contains(@class, 'calendar-dialog')]"))
                )
                
                logger.info("カレンダーダイアログが表示されました")
                
                # 開始日フィールドを探す
                start_date_field = WebDriverWait(self.browser.driver, self.timeout).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        "//input[contains(@placeholder, '開始') or @name='start' or contains(@class, 'start-date')]"))
                )
                
                # 開始日フィールドをクリア
                start_date_field.clear()
                
                # 開始日を入力
                start_date_str = start_date.strftime("%Y-%m-%d")
                start_date_field.send_keys(start_date_str)
                
                logger.info(f"開始日を入力しました: {start_date_str}")
                
                # 終了日フィールドを探す
                end_date_field = WebDriverWait(self.browser.driver, self.timeout).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        "//input[contains(@placeholder, '終了') or @name='end' or contains(@class, 'end-date')]"))
                )
                
                # 終了日フィールドをクリア
                end_date_field.clear()
                
                # 終了日を入力
                end_date_str = end_date.strftime("%Y-%m-%d")
                end_date_field.send_keys(end_date_str)
                
                logger.info(f"終了日を入力しました: {end_date_str}")
                
                # 適用ボタンをクリック
                apply_btn = WebDriverWait(self.browser.driver, self.timeout).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        "//button[contains(text(), '適用') or contains(@class, 'apply')]"))
                )
                
                self.browser.click_element(None, None, element=apply_btn)
                
                # ダイアログが閉じられ、データ読み込みが完了するのを待機
                WebDriverWait(self.browser.driver, self.timeout).until(
                    EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class, 'datepicker') or contains(@class, 'calendar-dialog')]"))
                )
                
                # データ読み込み完了を待機（ローディングインジケータが消えるのを待つ）
                try:
                    WebDriverWait(self.browser.driver, self.timeout).until(
                        EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class, 'loading')]"))
                    )
                except TimeoutException:
                    logger.warning("ローディングインジケータの消失を待機中にタイムアウトしました。処理を続行します。")
                
                logger.info("日付範囲の設定が完了しました")
                return True
                
            except (TimeoutException, NoSuchElementException) as e:
                logger.error(f"日付範囲の設定中にエラーが発生しました: {str(e)}")
                self.browser.save_screenshot("error_date_range_selection_cv.png")
                return False
                
        except Exception as e:
            logger.error(f"日付範囲の設定中に予期せぬエラーが発生しました: {str(e)}")
            self.browser.save_screenshot("error_date_range_unexpected_cv.png")
            traceback.print_exc()
            return False
    
    def download_csv(self):
        """
        CSV形式でデータをダウンロードする
        
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("エクスポートボタンをクリックします")
            
            # エクスポートボタンをクリック
            export_btn = WebDriverWait(self.browser.driver, self.timeout).until(
                EC.element_to_be_clickable((By.XPATH, 
                    "//button[contains(text(), 'エクスポート') or .//span[contains(text(), 'エクスポート')]]"))
            )
            
            self.browser.click_element(None, None, element=export_btn)
            
            # ドロップダウンメニューの表示を待機
            WebDriverWait(self.browser.driver, self.timeout).until(
                EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'dropdown') or contains(@class, 'menu')]"))
            )
            
            logger.info("表を出力（CSV）を選択します")
            
            # 表を出力（CSV）を選択
            csv_option = WebDriverWait(self.browser.driver, self.timeout).until(
                EC.element_to_be_clickable((By.XPATH, 
                    "//a[contains(text(), '表を出力（CSV）') or .//span[contains(text(), '表を出力（CSV）')]]"))
            )
            
            self.browser.click_element(None, None, element=csv_option)
            
            # ダウンロード開始を待機（直接確認は難しいので少し待機）
            logger.info("ダウンロードが開始されるのを待機しています...")
            time.sleep(5)
            
            logger.info("CSVのダウンロードが完了しました")
            return True
            
        except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as e:
            logger.error(f"CSVダウンロード中にエラーが発生しました: {str(e)}")
            self.browser.save_screenshot("error_csv_download_cv.png")
            return False
            
        except Exception as e:
            logger.error(f"CSVダウンロード中に予期せぬエラーが発生しました: {str(e)}")
            self.browser.save_screenshot("error_csv_download_unexpected_cv.png")
            traceback.print_exc()
            return False
    
    def execute_download_flow(self, start_date=None, end_date=None):
        """
        コンバージョン属性データのダウンロードフローを実行する
        
        Args:
            start_date (str or datetime): 開始日（YYYY-MM-DD形式の文字列または日付オブジェクト）
            end_date (str or datetime): 終了日（YYYY-MM-DD形式の文字列または日付オブジェクト）
            
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # コンバージョン属性ページに移動
            if not self.navigate_to_cv_attribute_page():
                logger.error("コンバージョン属性ページへの移動に失敗しました")
                return False
                
            # 全トラフィックボタンをクリック（必要に応じて）
            if not self.click_all_traffic_if_needed():
                logger.warning("全トラフィックボタンの処理に失敗しましたが、処理を続行します")
                
            # 日付範囲を選択
            if not self.select_date_range(start_date, end_date):
                logger.error("日付範囲の選択に失敗しました")
                return False
                
            # CSVをダウンロード
            if not self.download_csv():
                logger.error("CSVのダウンロードに失敗しました")
                return False
                
            logger.info("コンバージョン属性データのダウンロードフローが正常に完了しました")
            return True
            
        except Exception as e:
            logger.error(f"コンバージョン属性データのダウンロードフロー中に予期せぬエラーが発生しました: {str(e)}")
            self.browser.save_screenshot("error_download_flow_cv.png")
            traceback.print_exc()
            return False
            
    def quit(self):
        """
        ブラウザを終了する（このインスタンスで作成した場合のみ）
        """
        if self.browser_created and self.browser:
            logger.info("ブラウザを終了します")
            self.browser.quit()

def main():
    """メイン実行関数"""
    try:
        # 環境変数を読み込む
        env.load_env()
        
        # コンバージョン属性ページインスタンスを作成（ログインも実行）
        cv_attribute = CvAttributePage(login_first=True)
        
        # ダウンロードフローを実行
        start_date = datetime.now().replace(day=1) - timedelta(days=1)  # 先月1日
        end_date = datetime.now().replace(day=1) - timedelta(days=1)    # 先月末日
        
        success = cv_attribute.execute_download_flow(start_date, end_date)
        
        if success:
            print("コンバージョン属性データのダウンロードに成功しました")
        else:
            print("コンバージョン属性データのダウンロードに失敗しました")
            
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        traceback.print_exc()
        
    finally:
        # ブラウザを終了
        if 'cv_attribute' in locals() and cv_attribute:
            cv_attribute.quit()

if __name__ == "__main__":
    main() 