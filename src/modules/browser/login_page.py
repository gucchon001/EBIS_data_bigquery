#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ログインページ操作モジュール
このモジュールは、特定のWebサイトのログイン処理を実行するための
LoginPageクラスを提供します。

login_page_template.py の汎用的なクラスを継承し、
特定のWebサイト用にカスタマイズしています。
"""

import os
import sys
import time
import traceback
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent.parent.parent)
sys.path.append(project_root)

from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env
from src.modules.browser.login_page_template import LoginPage as LoginPageTemplate
from src.modules.browser.login_page_template import handle_errors, LoginError

logger = get_logger(__name__)

class LoginPage(LoginPageTemplate):
    """
    特定のWebサイト用にカスタマイズされたログインページクラス
    
    汎用的なLoginPageTemplateクラスを継承し、
    特定のWebサイト専用の処理を追加しています。
    
    特徴:
    1. 特定のWebサイト向けのセレクタと設定を利用
    2. 親クラスのPOMパターン実装と共通機能を継承
    3. 組織選択・2要素認証など、サイト特有の機能に対応
    4. 親クラスのエラーハンドリングと連携し、堅牢な操作を実現
    5. サイト固有のログインフォーム処理とバリデーションを実装
    """
    
    def __init__(self, browser=None):
        """
        LoginPageクラスの初期化
        
        Args:
            browser (Browser): 既存のブラウザインスタンス（省略時は新規作成）
        """
        # 親クラスの初期化を呼び出す
        super().__init__(selector_group='login', browser=browser)
        
        # 追加の設定を読み込む
        self._load_additional_settings()
    
    @handle_errors(screenshot_name="load_settings_error")
    def _load_additional_settings(self):
        """
        特定のWebサイト用の追加設定を読み込む
        
        設定ファイルから組織選択関連の設定や2要素認証関連の設定を読み込みます。
        
        Returns:
            bool: 設定の読み込みが成功した場合はTrue
        """
        # 組織選択関連の設定
        org_value = env.get_config_value("Login", "auto_select_org", "false")
        self.auto_select_org = org_value.lower() == "true" if isinstance(org_value, str) else bool(org_value)
        self.org_name = env.get_config_value("Login", "org_name", "")
        
        # 2要素認証関連の設定
        tfa_value = env.get_config_value("Login", "handle_2fa", "false")
        self.handle_2fa = tfa_value.lower() == "true" if isinstance(tfa_value, str) else bool(tfa_value)
        backup_value = env.get_config_value("Login", "use_backup_code", "false")
        self.use_backup_code = backup_value.lower() == "true" if isinstance(backup_value, str) else bool(backup_value)
        self.backup_code = env.get_config_value("Login", "backup_code", "")
        
        # ポップアップ関連の設定
        popup_value = env.get_config_value("Login", "auto_handle_post_login_popup", "false")
        self.auto_handle_popup = popup_value.lower() == "true" if isinstance(popup_value, str) else bool(popup_value)
        self.popup_timeout = int(env.get_config_value("Login", "popup_timeout", "10"))
        
        # サイト固有のログインフォーム設定
        remember_value = env.get_config_value("Login", "remember_me", "false")
        self.remember_me = remember_value.lower() == "true" if isinstance(remember_value, str) else bool(remember_value)
        recaptcha_value = env.get_config_value("Login", "require_recaptcha", "false")
        self.require_recaptcha = recaptcha_value.lower() == "true" if isinstance(recaptcha_value, str) else bool(recaptcha_value)
        
        logger.info("サイト固有の設定を読み込みました")
        return True
    
    @handle_errors(screenshot_name="fill_form_error")
    def fill_login_form(self, account_key=None, username=None, password=None):
        """
        ログインフォームに情報を入力します
        親クラスのメソッドをオーバーライドして、サイト固有の処理を追加します
        
        Args:
            account_key (str, optional): アカウントキー。指定がなければ設定値を使用
            username (str, optional): ユーザー名。指定がなければ設定値を使用
            password (str, optional): パスワード。指定がなければ設定値を使用
            
        Returns:
            bool: 入力が成功した場合はTrue
        """
        # 親クラスのメソッドを呼び出して基本情報を入力
        if not super().fill_login_form(account_key, username, password):
            logger.error("基本ログイン情報の入力に失敗しました")
            return False
        
        # サイト固有のフォーム要素処理（必要に応じて実装）
        try:
            # 「ログイン状態を保持する」チェックボックスの処理
            if self.remember_me:
                remember_me_selector = ('login', 'remember_me')
                if 'login' in self.browser.selectors and 'remember_me' in self.browser.selectors['login']:
                    # チェックボックスの現在の状態を取得
                    checkbox = self.browser.get_element(*remember_me_selector)
                    if checkbox and not checkbox.is_selected():
                        # チェックされていない場合はクリック
                        self.browser.click_element(*remember_me_selector)
                        logger.info("「ログイン状態を保持する」をチェックしました")
            
            # reCAPTCHAの処理（必要に応じて実装）
            if self.require_recaptcha:
                logger.info("reCAPTCHAの処理が必要ですが、自動対応は実装されていません")
                # 手動での対応が必要な場合は待機
                time.sleep(5)
            
            logger.info("サイト固有のフォーム要素の処理が完了しました")
            return True
            
        except Exception as e:
            logger.error(f"サイト固有のフォーム処理中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    @handle_errors(screenshot_name="submit_form_error")
    def submit_login_form(self):
        """
        ログインフォームを送信します
        親クラスのメソッドをオーバーライドして、サイト固有の処理を追加します
        
        Returns:
            bool: 送信が成功した場合はTrue
        """
        # 送信前の追加処理（必要に応じて実装）
        # ...
        
        # 親クラスのメソッドを呼び出してフォーム送信
        result = super().submit_login_form()
        if not result:
            return False
        
        # 送信後の追加処理（必要に応じて実装）
        # 例: 特定のサイトでは送信後に追加の確認ダイアログが表示される場合など
        try:
            # サイト固有の送信後処理が必要な場合はここに実装
            confirm_dialog_selector = ('login', 'confirm_dialog_ok')
            if 'login' in self.browser.selectors and 'confirm_dialog_ok' in self.browser.selectors['login']:
                # 確認ダイアログの有無を確認（短いタイムアウトで待機）
                try:
                    dialog = self.browser.get_element(*confirm_dialog_selector, wait_time=3)
                    if dialog:
                        self.browser.click_element(*confirm_dialog_selector)
                        logger.info("送信後の確認ダイアログを処理しました")
                except TimeoutException:
                    # ダイアログがない場合は何もしない
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"フォーム送信後の処理中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    @handle_errors(screenshot_name="login_check_error")
    def check_login_success(self):
        """
        ログイン成功を確認します
        親クラスのメソッドをオーバーライドして、サイト固有の成功判定を追加します
        
        Returns:
            bool: ログインが成功した場合はTrue
        """
        # 親クラスの成功確認メソッドを呼び出し
        if super().check_login_success():
            logger.info("親クラスの判定基準によりログイン成功を確認しました")
            return True
        
        # サイト固有の成功判定（必要に応じて実装）
        try:
            # 例: 特定のサイトでは特定の要素が表示されるかどうかで判定
            dashboard_element = ('css', '.dashboard-header')
            try:
                element = self.browser.wait_for_element(
                    dashboard_element[0],
                    dashboard_element[1],
                    timeout=5
                )
                if element:
                    logger.info("ダッシュボード要素を確認しました - ログイン成功")
                    return True
            except TimeoutException:
                pass
                
            # 例: URLに特定の文字列が含まれるかで判定
            if "dashboard" in self.driver.current_url or "home" in self.driver.current_url:
                logger.info(f"ダッシュボードURLを確認しました: {self.driver.current_url}")
                return True
                
            # その他のサイト固有の判定方法を追加
            
            logger.warning("すべての判定方法でログイン成功を確認できませんでした")
            return False
            
        except Exception as e:
            logger.error(f"ログイン成功確認中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    @handle_errors(screenshot_name="popup_handle_error")
    def handle_post_login_popup(self):
        """
        ログイン後のお知らせポップアップを処理するためのメソッド
        
        設定ファイルの[Login]セクションからauto_handle_post_login_popupを取得し、
        popupセレクタグループのlogin_noticeセレクタを使用してポップアップを閉じます。
        
        Returns:
            bool: ポップアップを処理できた場合はTrue、処理しなかった場合はFalse
        """
        # ポップアップ処理が無効な場合は何もしない
        if not self.auto_handle_popup:
            logger.info("ログイン後のポップアップ自動処理は無効です")
            return False
        
        logger.info(f"ポップアップの表示を {self.popup_timeout} 秒間待機します")
        
        # ポップアップのセレクタ設定を確認
        if self.popup_notice is None:
            logger.warning("popup_notice ロケーターが設定されていません")
            return False
        
        # ポップアップの存在を確認
        try:
            popup_element = self.browser.wait_for_element(
                self.popup_notice[0], 
                self.popup_notice[1], 
                timeout=self.popup_timeout
            )
            
            if not popup_element:
                logger.info("ログイン後のポップアップは表示されませんでした")
                return False
            
            # 親クラスのclose_popupメソッドを呼び出し
            result = self.close_popup()
            
            if result:
                logger.info("ログイン後のポップアップを閉じました")
            else:
                logger.warning("ポップアップは表示されましたが、クリックできませんでした")
            
            return result
            
        except TimeoutException:
            logger.info("ログイン後のポップアップは表示されませんでした（タイムアウト）")
            return False
        
        except WebDriverException as e:
            logger.warning(f"ポップアップ処理中にWebDriver例外が発生しました: {str(e)}")
            self.browser.save_screenshot(f"popup_error_{int(time.time())}.png")
            return False
    
    @handle_errors(screenshot_name="org_selection_error")
    def select_organization(self):
        """
        組織選択画面での組織選択処理
        
        ログイン後に組織選択画面が表示された場合に、
        settings.iniで指定された組織を選択します。
        
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        if not self.auto_select_org or not self.org_name:
            logger.info("組織選択機能は無効または組織名が設定されていません")
            return False
        
        # 必要に応じて実装してください
        logger.info("組織選択機能は実装されていません")
        return True
    
    @handle_errors(screenshot_name="2fa_error")
    def handle_two_factor_auth(self):
        """
        2要素認証処理
        
        ログイン後に2要素認証が必要な場合に、
        バックアップコードの入力などの処理を行います。
        
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        if not self.handle_2fa:
            logger.info("2要素認証処理は無効です")
            return False
        
        # 必要に応じて実装してください
        logger.info("2要素認証処理は実装されていません")
        return True
    
    @handle_errors(screenshot_name="login_flow", raise_exception=True)
    def execute_login_flow(self, account_key=None, username=None, password=None, handle_popup=True, max_attempts=3):
        """
        ログインフローを実行します
        
        親クラスのログインフローに加えて、必要に応じて組織選択や2要素認証の処理も行います。
        
        Args:
            account_key (str, optional): アカウントキー。指定がなければ設定値を使用
            username (str, optional): ユーザー名。指定がなければ設定値を使用
            password (str, optional): パスワード。指定がなければ設定値を使用
            handle_popup (bool): ログイン後のポップアップを自動処理するかどうか
            max_attempts (int): 最大試行回数
            
        Returns:
            bool: ログインが成功した場合はTrue
            
        Raises:
            LoginError: ログインに失敗した場合
        """
        # 親クラスのログインフローを実行
        result = super().execute_login_flow(
            account_key=account_key,
            username=username,
            password=password,
            handle_popup=False,  # 親クラスでのポップアップ処理をスキップ
            max_attempts=max_attempts
        )
        
        if not result:
            return False
        
        # 組織選択処理
        if self.auto_select_org:
            self.select_organization()
        
        # 2要素認証処理
        if self.handle_2fa:
            self.handle_two_factor_auth()
        
        # ポップアップ処理
        if handle_popup and self.auto_handle_popup:
            self.handle_post_login_popup()
        
        logger.info("サイト固有のログインフローが完了しました")
        return True

def main():
    """
    テスト用のメイン関数
    """
    try:
        # ログインページのインスタンスを作成
        login_page = LoginPage()
        
        # ログイン処理を実行
        result = login_page.execute_login_flow()
        
        if result:
            logger.info("ログインに成功しました")
            
            # ブラウザを少し開いたままにする（画面を確認するため）
            time.sleep(5)
        else:
            logger.error("ログインに失敗しました")
        
        # ブラウザを終了
        login_page.quit()
        return 0 if result else 1
            
    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生しました: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 