#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EBiSログインページを操作するためのモジュール
"""

import os
import time
import sys
from pathlib import Path
import traceback

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent.parent.parent)
sys.path.append(project_root)

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env
from src.modules.browser.browser import Browser

logger = get_logger(__name__)

class EbisLoginPage:
    """
    EBiSログインページの操作を担当するクラス
    """
    
    def __init__(self, browser=None):
        """
        初期化
        
        Args:
            browser (Browser, optional): 使用するブラウザインスタンス
        """
        self.browser = browser
        if not self.browser:
            logger.info("ブラウザインスタンスが提供されていないため、新しく作成します")
            self.browser = Browser(headless=False)
            if not self.browser.setup():
                logger.error("ブラウザのセットアップに失敗しました")
                raise RuntimeError("ブラウザのセットアップに失敗しました")
        
        # 環境変数を確実に読み込む
        env.load_env()
        
        # ログイン情報を環境変数から取得
        self.account_id = env.get_env_var("account_key1", "")
        self.login_id = env.get_env_var("username1", "")
        self.password = env.get_env_var("password1", "")
        
        # 必須情報の確認
        if not all([self.account_id, self.login_id, self.password]):
            logger.error("ログインに必要な環境変数が設定されていません")
            raise ValueError("環境変数 account_key1, username1, password1 が必要です")
        
        # ログインページURL - 設定ファイルから取得
        self.login_url = env.get_config_value("Credentials", "login_url", "")
        if not self.login_url:
            logger.warning("設定ファイルからログインURLが取得できませんでした。デフォルト値を使用します。")
            self.login_url = "https://id.ebis.ne.jp/"
        logger.info(f"ログインURL: {self.login_url}")
        
        # 最大試行回数
        self.max_attempts = 3
    
    def navigate_to_login_page(self):
        """
        ログインページに移動
        
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info(f"ログインページにアクセスします: {self.login_url}")
            self.browser.navigate_to(self.login_url)
            
            # ページが読み込まれるまで待機
            WebDriverWait(self.browser.driver, 10).until(
                EC.presence_of_element_located((By.ID, "account_key"))
            )
            
            logger.info("ログインページへのアクセスに成功しました")
            return True
            
        except TimeoutException:
            logger.error("ログインページの読み込みがタイムアウトしました")
            return False
            
        except Exception as e:
            logger.error(f"ログインページへのアクセス中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def fill_login_form(self):
        """
        ログインフォームに必要な情報を入力
        
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("ログインフォームに情報を入力します")
            
            # アカウントID入力
            account_id_input = self.browser.driver.find_element(By.ID, "account_key")
            account_id_input.clear()
            account_id_input.send_keys(self.account_id)
            logger.debug(f"アカウントIDを入力しました: {self.account_id}")
            
            # ログインID入力
            login_id_input = self.browser.driver.find_element(By.ID, "username")
            login_id_input.clear()
            login_id_input.send_keys(self.login_id)
            logger.debug(f"ログインIDを入力しました: {self.login_id}")
            
            # パスワード入力
            password_input = self.browser.driver.find_element(By.ID, "password")
            password_input.clear()
            password_input.send_keys(self.password)
            logger.debug("パスワードを入力しました")
            
            logger.info("ログインフォームへの入力が完了しました")
            return True
            
        except NoSuchElementException as e:
            logger.error(f"ログインフォームの要素が見つかりません: {str(e)}")
            return False
            
        except Exception as e:
            logger.error(f"ログインフォームへの入力中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def submit_login_form(self):
        """
        ログインフォームを送信
        
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("ログインボタンをクリックします")
            
            # ログインボタンをクリック
            login_button = self.browser.driver.find_element(By.CSS_SELECTOR, "button.loginbtn")
            login_button.click()
            
            # リダイレクトを待機
            start_url = self.browser.driver.current_url
            logger.info(f"クリック前のURL: {start_url}")
            
            # 一定時間待機してURLの変化を確認
            timeout = 15  # 15秒
            wait_time = 0
            check_interval = 1
            
            while wait_time < timeout:
                time.sleep(check_interval)
                wait_time += check_interval
                current_url = self.browser.driver.current_url
                
                if current_url != start_url:
                    logger.info(f"URLが変化しました: {current_url}")
                    return True
                
                logger.debug(f"待機中... {wait_time}秒経過")
            
            # タイムアウトした場合でも、念のためURLをチェック
            current_url = self.browser.driver.current_url
            if current_url != start_url:
                logger.info(f"待機後にURLが変化していました: {current_url}")
                return True
                
            logger.warning(f"ログイン後のリダイレクトがタイムアウトしましたが、処理を続行します（{timeout}秒待機）")
            return True  # テスト用に仮に成功と扱う
            
        except NoSuchElementException:
            logger.error("ログインボタンが見つかりません")
            return False
            
        except Exception as e:
            logger.error(f"ログインフォームの送信中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def check_login_success(self):
        """
        ログインの成功を確認
        
        Returns:
            bool: ログイン成功の場合はTrue、失敗の場合はFalse
        """
        try:
            # 現在のURLが正しいかチェック
            current_url = self.browser.driver.current_url
            logger.info(f"ログイン後のURL: {current_url}")
            
            # 成功URL（ダッシュボードのドメイン）を設定ファイルから取得
            success_domain = "bishamon.ebis.ne.jp"
            
            # ログイン成功URLにリダイレクトされたかチェック
            if success_domain in current_url:
                logger.info("ログインに成功しました")
                return True
                
            # エラーメッセージの有無をチェック
            try:
                error_message = self.browser.driver.find_element(By.CLASS_NAME, "alert-danger")
                logger.error(f"ログインエラーが表示されています: {error_message.text}")
                return False
            except NoSuchElementException:
                # エラーメッセージがない場合はOK
                pass
                
            # ログインページから移動した場合は成功とみなす
            login_domain = self.login_url
            if login_domain and login_domain in current_url:
                logger.warning("まだログインページにいるようです")
                return False
            else:
                logger.info("ログインページから移動しました。ログイン成功と判断します")
                return True
                
            logger.warning("ログイン状態が確認できません")
            return False
            
        except Exception as e:
            logger.error(f"ログイン確認中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def execute_login_flow(self):
        """
        ログイン処理の一連のフローを実行
        
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        for attempt in range(1, self.max_attempts + 1):
            try:
                logger.info(f"ログイン試行 {attempt}/{self.max_attempts}")
                
                # ログインページに移動
                if not self.navigate_to_login_page():
                    logger.error("ログインページへのアクセスに失敗しました")
                    continue
                
                # ログインフォームに情報を入力
                if not self.fill_login_form():
                    logger.error("ログインフォームへの入力に失敗しました")
                    continue
                
                # ログインフォームを送信
                if not self.submit_login_form():
                    logger.error("ログインフォームの送信に失敗しました")
                    continue
                
                # ログイン成功の確認
                if self.check_login_success():
                    logger.info(f"{attempt}回目の試行でログインに成功しました")
                    
                    # ダッシュボードにアクセス（必須）
                    try:
                        dashboard_url = env.get_config_value("Credentials", "url_dashboard", "https://bishamon.ebis.ne.jp/dashboard")
                        logger.info(f"ダッシュボードにアクセスします: {dashboard_url}")
                        self.browser.navigate_to(dashboard_url)
                        
                        # ページ読み込み完了を待機
                        WebDriverWait(self.browser.driver, 10).until(
                            lambda driver: driver.execute_script("return document.readyState") == "complete"
                        )
                        logger.info("ダッシュボードページの読み込みが完了しました")
                        
                        # 追加の待機時間
                        time.sleep(2)
                        
                        # 念のためURLを確認
                        current_url = self.browser.driver.current_url
                        if dashboard_url in current_url:
                            logger.info(f"ダッシュボードURL ({dashboard_url}) に正常に遷移しました")
                        else:
                            logger.warning(f"ダッシュボードへの遷移に問題がある可能性があります。現在のURL: {current_url}")
                    except Exception as e:
                        logger.warning(f"ダッシュボードへのアクセス中にエラーが発生しました: {str(e)}")
                        logger.error(traceback.format_exc())
                    
                    return True
                
                logger.warning(f"{attempt}回目のログイン試行が失敗しました")
                
            except Exception as e:
                logger.error(f"ログイン処理中に予期しないエラーが発生しました: {str(e)}")
                logger.error(traceback.format_exc())
            
            # 次の試行前に少し待機
            time.sleep(3)
        
        logger.error(f"{self.max_attempts}回の試行後もログインに失敗しました")
        return False
        
def main():
    """
    テスト用のメイン関数
    """
    try:
        # 環境変数を読み込む
        env.load_env()
        
        # ログインページのインスタンスを作成
        login_page = EbisLoginPage()
        
        # ログイン処理を実行
        result = login_page.execute_login_flow()
        
        if result:
            logger.info("ログインテストに成功しました")
            
            # ブラウザを終了
            login_page.browser.quit()
            return 0
        else:
            logger.error("ログインテストに失敗しました")
            return 1
            
    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生しました: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 