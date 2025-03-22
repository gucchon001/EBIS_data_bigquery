#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
汎用的なログインページ操作モジュール
様々なWebサイトのログイン処理を実行するための汎用的なクラスを提供します。
POMパターン（Page Object Model）で実装し、Browser クラスの機能を活用します。
"""

import os
import time
import sys
import csv
import functools
from pathlib import Path
import traceback
import urllib.parse
import re

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

# カスタム例外クラス
class LoginError(Exception):
    """
    ログイン処理中に発生するエラーを表す例外クラス
    """
    pass

# エラーハンドリング用のデコレータ
def handle_errors(screenshot_name=None, raise_exception=False):
    """
    共通のエラーハンドリングを行うデコレータ
    
    Args:
        screenshot_name (str, optional): エラー時に保存するスクリーンショットの名前
        raise_exception (bool, optional): Trueの場合は例外を再発生させる
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                method_name = func.__name__
                error_msg = f"{method_name}の実行中にエラーが発生しました: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                
                if hasattr(self, 'browser') and screenshot_name:
                    screenshot_file = f"{screenshot_name}_{int(time.time())}.png"
                    self.browser.save_screenshot(screenshot_file)
                
                if raise_exception:
                    raise
                return False
        return wrapper
    return decorator

class LoginPage:
    """
    汎用ログインページの操作を担当するクラス
    様々なWebサイトのログイン処理に対応できるよう設定ファイルから設定を読み込みます
    POMパターン（Page Object Model）で実装しつつ、Browser クラスの汎用機能を活用しています
    
    以下の特徴があります：
    1. セレクタをクラス変数として定義し、目的ごとにメソッドを分離（POMパターン）
    2. Browser クラスの汎用的なブラウザ操作機能を内部で使用
    3. Browserクラスのセレクタ管理機能と連携し、selectors.csvからロケーター情報を読み込み
    4. スクリーンショット、ログ記録、エラーハンドリングなどの共通機能をBrowserクラスから継承
    """
    
    # ロケーターは selectors.csv から動的に読み込まれます
    # POMパターンのロケーター定義（実際の値はCSVから動的に読み込まれる）
    account_key_input = None
    username_input = None
    password_input = None
    login_button = None
    popup_notice = None
    
    def __init__(self, selector_group='login', browser=None):
        """
        初期化
        settings.iniの[Login]セクションから設定を読み込みます
        Browser クラスのインスタンスを使用してブラウザ操作を行います
        
        Args:
            selector_group (str): セレクタのグループ名（デフォルト: 'login'）
            browser (Browser): 既存のブラウザインスタンス（省略時は新規作成）
        """
        # 環境変数を確実に読み込む
        env.load_env()
        
        # セレクタグループを設定
        self.selector_group = selector_group
        
        # ブラウザインスタンスの初期化
        self._init_browser(browser)
        
        # セレクタとフォールバックロケーターの設定
        self._load_selectors_from_browser()
        
        # ログイン設定の読み込み
        self._load_config()
    
    @handle_errors(screenshot_name="browser_init_error")
    def _init_browser(self, browser=None):
        """
        ブラウザインスタンスを初期化する
        
        Args:
            browser (Browser): 既存のブラウザインスタンス
        
        Returns:
            bool: 初期化が成功した場合はTrue
        """
        self.browser_created = False
        
        if browser is None:
            # ヘッドレスモード設定を取得
            headless_value = env.get_config_value("BROWSER", "headless", "false")
            headless = headless_value.lower() == "true" if isinstance(headless_value, str) else bool(headless_value)
            
            # セレクタファイルのパスを設定
            selectors_path = "config/selectors.csv"
            if not os.path.exists(selectors_path):
                logger.warning(f"セレクタファイルが見つかりません: {selectors_path}")
                selectors_path = None
            
            # ブラウザインスタンスを作成
            self.browser = Browser(selectors_path=selectors_path, headless=headless)
            if not self.browser.setup():
                logger.error("ブラウザのセットアップに失敗しました")
                raise RuntimeError("ブラウザのセットアップに失敗しました")
            
            self.browser_created = True
        else:
            # 既存のブラウザインスタンスを使用
            self.browser = browser
        
        # WebDriverを取得
        self.driver = self.browser.driver
        return True
    
    @handle_errors(screenshot_name="load_selectors_error")
    def _load_selectors_from_browser(self):
        """
        Browser クラスのセレクタ情報から POM のロケーターを設定する
        """
        # Browser クラスのセレクタ情報が存在しない場合は終了
        if not hasattr(self.browser, 'selectors') or not self.browser.selectors:
            logger.warning("Browser クラスでセレクタが読み込まれていません")
            return
        
        # POMで必要なロケーターのマッピング定義
        locator_map = {
            ('login', 'account_key'): 'account_key_input',
            ('login', 'username'): 'username_input',
            ('login', 'password'): 'password_input',
            ('login', 'login_button'): 'login_button',
            ('popup', 'login_notice'): 'popup_notice'
        }
        
        # 各ロケーターをマッピングに基づいて設定
        for (group, name), attr_name in locator_map.items():
            if group in self.browser.selectors and name in self.browser.selectors[group]:
                selector_info = self.browser.selectors[group][name]
                by_type = self.browser._get_by_type(selector_info['selector_type'])
                
                if by_type:
                    # クラス変数に設定
                    setattr(LoginPage, attr_name, (by_type, selector_info['selector_value']))
                    logger.debug(f"ロケーター '{attr_name}' を設定しました: {by_type}={selector_info['selector_value']}")
        
        # 必要なロケーターが設定されているか確認
        missing_locators = [attr for attr in ['account_key_input', 'username_input', 'password_input', 'login_button'] 
                           if getattr(LoginPage, attr) is None]
        if missing_locators:
            logger.warning(f"以下のロケーターが設定されていません: {', '.join(missing_locators)}")
            logger.warning("selectors.csvに必要なセレクタを追加してください")
            
        logger.info("Browser クラスからセレクタ情報を読み込みました")
    
    def _setup_fallback_locators(self):
        """
        セレクタが見つからない場合のエラーメッセージを表示
        """
        # フォールバックロケーターを使用しないように変更
        logger.warning("デフォルトのロケーターは使用されません。selectors.csvにセレクタを設定してください。")
    
    @handle_errors(screenshot_name="load_config_error")
    def _load_config(self):
        """
        設定ファイルからログイン設定を読み込む
        settings.iniの[Login]セクションから設定を読み込みます
        """
        # URL設定の読み込み
        self._load_url_config()
        
        # タイムアウト設定の読み込み
        self._load_timeout_config()
        
        # 認証設定の読み込み
        self._load_auth_config()
        
        # フォームフィールド設定の読み込み
        self._load_form_fields()
        
        # 成功/エラー判定要素の設定
        self._load_validation_elements()
        
        # 設定の検証
        self._validate_config()
        
        logger.info("設定ファイルからログイン設定を読み込みました")
    
    def _load_url_config(self):
        """URLに関する設定を読み込む"""
        # 基本URL設定
        self.login_url = env.get_config_value("Login", "url", "")
        if not self.login_url:
            raise ValueError("ログインURLが設定されていません")
        
        logger.info(f"ログインURL: {self.login_url}")
        
        # 成功判定用URL
        self.success_url = env.get_config_value("Login", "success_url", "")
    
    def _load_timeout_config(self):
        """タイムアウト関連設定を読み込む"""
        # 最大試行回数
        max_attempts_value = env.get_config_value("Login", "max_attempts", "3")
        self.max_attempts = int(max_attempts_value) if isinstance(max_attempts_value, str) else int(max_attempts_value or 3)
        
        # リダイレクトタイムアウト
        redirect_timeout_value = env.get_config_value("Login", "redirect_timeout", "30")
        self.redirect_timeout = int(redirect_timeout_value) if isinstance(redirect_timeout_value, str) else int(redirect_timeout_value or 30)
        
        # 要素待機タイムアウト
        element_timeout_value = env.get_config_value("Login", "element_timeout", "10")
        self.element_timeout = int(element_timeout_value) if isinstance(element_timeout_value, str) else int(element_timeout_value or 10)
    
    def _load_auth_config(self):
        """認証関連設定を読み込む"""
        # ベーシック認証設定
        basic_auth_value = env.get_config_value("Login", "basic_auth_enabled", "false")
        self.basic_auth_enabled = basic_auth_value.lower() == "true" if isinstance(basic_auth_value, str) else bool(basic_auth_value)
        
        if self.basic_auth_enabled:
            self.basic_auth_username = env.get_config_value("Login", "basic_auth_username", "")
            self.basic_auth_password = env.get_config_value("Login", "basic_auth_password", "")
            
            if not self.basic_auth_username or not self.basic_auth_password:
                logger.warning("ベーシック認証が有効ですが、ユーザー名またはパスワードが設定されていません")
                self.basic_auth_enabled = False
            else:
                logger.info("ベーシック認証が有効です")
                # URLにベーシック認証情報を埋め込む
                self.login_url_with_auth = self._embed_basic_auth_to_url(
                    self.login_url, self.basic_auth_username, self.basic_auth_password
                )
    
    def _load_form_fields(self):
        """フォームフィールド設定を読み込む"""
        # フォームフィールド初期化
        self.form_fields = []
        
        # アカウント番号の取得（複数アカウント対応）
        account_number = env.get_config_value("Login", "account_number", "1")
        
        # ユーザー名フィールド
        username_env_key = f"username{account_number}"
        username = env.get_env_var(username_env_key, "")
        if username:
            self.form_fields.append({'name': 'username', 'value': username})
        
        # パスワードフィールド
        password_env_key = f"password{account_number}"
        password = env.get_env_var(password_env_key, "")
        if password:
            self.form_fields.append({'name': 'password', 'value': password})
        
        # 3つ目のフィールド（アカウントキーなど）
        third_field_name = env.get_config_value("Login", "third_field_name", "account_key")
        third_field_env_key = f"{third_field_name}{account_number}"
        third_field_value = env.get_env_var(third_field_env_key, "")
        if third_field_value:
            self.form_fields.append({'name': third_field_name, 'value': third_field_value})
    
    def _load_validation_elements(self):
        """ログイン成功/失敗判定用の要素設定を読み込む"""
        # 成功要素
        success_element_selector = env.get_config_value("Login", "success_element_selector", "")
        success_element_type_str = env.get_config_value("Login", "success_element_type", "css")
        
        self.success_element = {
            'type': success_element_type_str,
            'selector': success_element_selector
        } if success_element_selector else None
        
        # エラー要素
        error_selector = env.get_config_value("Login", "error_selector", "")
        error_type_str = env.get_config_value("Login", "error_type", "css")
        
        self.error_selector = {
            'type': error_type_str,
            'selector': error_selector
        } if error_selector else None
    
    def _validate_config(self):
        """設定の妥当性を検証する"""
        if not self.login_url:
            raise ValueError("ログインURLが設定されていません")
        
        if not self.form_fields:
            logger.warning("ログインフォームのフィールドが設定されていません")
    
    def _embed_basic_auth_to_url(self, url, username, password):
        """
        URLにベーシック認証情報を埋め込む
        
        Args:
            url (str): 元のURL
            username (str): ベーシック認証のユーザー名
            password (str): ベーシック認証のパスワード
            
        Returns:
            str: ベーシック認証情報が埋め込まれたURL
        """
        try:
            # URLをパース
            parsed_url = urllib.parse.urlparse(url)
            
            # ベーシック認証情報を追加
            netloc = f"{username}:{password}@{parsed_url.netloc}"
            
            # URLを再構築
            auth_url = parsed_url._replace(netloc=netloc).geturl()
            
            logger.debug(f"ベーシック認証情報を埋め込んだURL: {auth_url}")
            return auth_url
            
        except Exception as e:
            logger.error(f"URLへのベーシック認証情報埋め込み中にエラーが発生しました: {str(e)}")
            return url
    
    # POMパターンに基づく要素操作メソッド
    @handle_errors(screenshot_name="input_error")
    def enter_account_key(self, account_key):
        """
        アカウントキーを入力します
        
        Args:
            account_key (str): アカウントキー
            
        Returns:
            bool: 成功した場合はTrue
        """
        result = self.browser.input_text(self.account_key_input, account_key)
        if result:
            logger.debug(f"アカウントキーを入力しました: {account_key}")
        return result
    
    @handle_errors(screenshot_name="input_error")
    def enter_username(self, username):
        """
        ユーザー名を入力します
        
        Args:
            username (str): ユーザー名
            
        Returns:
            bool: 成功した場合はTrue
        """
        result = self.browser.input_text(self.username_input, username)
        if result:
            logger.debug(f"ユーザー名を入力しました: {username}")
        return result
    
    @handle_errors(screenshot_name="input_error")
    def enter_password(self, password):
        """
        パスワードを入力します
        
        Args:
            password (str): パスワード
            
        Returns:
            bool: 成功した場合はTrue
        """
        result = self.browser.input_text(self.password_input, password)
        if result:
            logger.debug("パスワードを入力しました")
        return result
    
    @handle_errors(screenshot_name="click_error")
    def click_login_button(self):
        """
        ログインボタンをクリックします
        
        Returns:
            bool: 成功した場合はTrue
        """
        # Browser クラスのロケーターを優先して使用
        if 'login' in self.browser.selectors and 'login_button' in self.browser.selectors['login']:
            result = self.browser.click_element('login', 'login_button', ensure_visible=True)
            if result:
                logger.info("ログインボタンをクリックしました")
            return result
        
        # なければ POM のロケーターを使用
        try:
            # リトライ機能を持つクリックメソッドを使用
            result = self.browser.click_element_by_locator(
                self.login_button[0], 
                self.login_button[1], 
                ensure_visible=True, 
                retry_count=2
            )
            if result:
                logger.info("ログインボタンをクリックしました")
            return result
        except AttributeError:
            # Browser クラスに click_element_by_locator メソッドがない場合の対応
            element = self.driver.find_element(*self.login_button)
            self.browser.scroll_to_element(element)
            element.click()
            logger.info("ログインボタンをクリックしました")
            return True
    
    @handle_errors(screenshot_name="popup_error")
    def close_popup(self):
        """
        ログイン後のポップアップを閉じます
        
        Returns:
            bool: 成功した場合はTrue、ポップアップがない場合はFalse
        """
        # ポップアップの存在を短時間で確認（タイムアウトを短くして高速に判定）
        try:
            element = self.browser.wait_for_element(
                self.popup_notice[0], 
                self.popup_notice[1], 
                timeout=3
            )
            
            if not element:
                logger.info("ログイン後のポップアップは表示されていません")
                return False
            
            # ポップアップが存在する場合はクリック
            if 'popup' in self.browser.selectors and 'login_notice' in self.browser.selectors.get('popup', {}):
                # Browser のセレクタを使用
                result = self.browser.click_element('popup', 'login_notice', ensure_visible=True)
            else:
                # POM のロケーターを使用
                try:
                    result = self.browser.click_element_by_locator(
                        self.popup_notice[0], 
                        self.popup_notice[1], 
                        ensure_visible=True
                    )
                except AttributeError:
                    # Browser に click_element_by_locator がない場合
                    element = self.browser.wait_for_element(
                        self.popup_notice[0], 
                        self.popup_notice[1], 
                        condition=EC.element_to_be_clickable,
                        timeout=5
                    )
                    if element:
                        self.browser.scroll_to_element(element)
                        element.click()
                        result = True
                    else:
                        result = False
            
            if result:
                logger.info("ログイン後のポップアップを閉じました")
            return result
            
        except TimeoutException:
            logger.info("ログイン後のポップアップは表示されていません")
            return False
    
    # 主要なアクションメソッド
    @handle_errors(screenshot_name="navigation")
    def navigate_to_login_page(self):
        """
        ログインページに移動します
        
        Returns:
            bool: 移動が成功した場合はTrue
        """
        if not self.login_url:
            logger.error("ログインURLが設定されていません")
            return False
            
        try:
            logger.info(f"ログインページへ移動します: {self.login_url}")
            
            # Browserクラスを使用してナビゲーション
            if hasattr(self.browser, 'navigate_to'):
                self.browser.navigate_to(self.login_url)
            else:
                self.driver.get(self.login_url)
                
            # ページの読み込みを待機
            self.browser.wait_for_page_load()
            
            # フォーム要素の存在を確認
            form_elements = [
                self.account_key_input,
                self.username_input,
                self.password_input,
                self.login_button
            ]
            
            # 少なくとも1つのフォーム要素が必要
            for element in form_elements:
                if element:
                    try:
                        self.browser.wait_for_element(
                            element[0],
                            element[1],
                            timeout=self.element_timeout
                        )
                        logger.info("ログインページのフォーム要素を確認しました")
                        return True
                    except Exception:
                        continue
                        
            # 何もない場合はタイトルとURLで確認
            if "login" in self.driver.title.lower() or "login" in self.driver.current_url.lower():
                logger.info("ログインページの表示を確認しました（タイトルまたはURLで判定）")
                return True
                
            logger.warning("ログインページの表示を確認できませんでした")
            return False
            
        except Exception as e:
            logger.error(f"ログインページへの移動中にエラーが発生しました: {str(e)}")
            return False
    
    @handle_errors(screenshot_name="login_flow", raise_exception=True)
    def execute_login_flow(self, account_key=None, username=None, password=None, handle_popup=True, max_attempts=3):
        """
        ログインフローを実行します
        
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
        logger.info("ログインフローを開始します")
        
        # 試行回数を設定（設定値と引数の小さい方を採用）
        max_attempts = min(max_attempts, self.max_attempts) if self.max_attempts else max_attempts
        
        for attempt in range(1, max_attempts + 1):
            try:
                if attempt > 1:
                    logger.info(f"ログイン再試行: {attempt}/{max_attempts}")
                
                # 1. ログインページへの移動
                if not self.navigate_to_login_page():
                    logger.error("ログインページへの移動に失敗しました")
                    continue
                
                # 2. ログインフォームへの入力
                if not self.fill_login_form(account_key, username, password):
                    logger.error("ログインフォームの入力に失敗しました")
                    continue
                
                # 3. ログインフォームの送信
                if not self.submit_login_form():
                    logger.error("ログインフォームの送信に失敗しました")
                    continue
                
                # 4. ログイン成功の確認
                if not self.check_login_success():
                    logger.error("ログイン成功の確認に失敗しました")
                    continue
                
                # 5. ポップアップの処理
                if handle_popup:
                    self.handle_post_login_popup()
                
                logger.info("ログインフローが成功しました")
                return True
                
            except Exception as e:
                logger.error(f"ログインフロー実行中にエラーが発生しました: {str(e)}")
                # スクリーンショットはデコレーターが対応
        
        # 全試行が失敗した場合
        error_msg = f"ログインに失敗しました: {max_attempts}回の試行後も成功しませんでした"
        logger.error(error_msg)
        raise LoginError(error_msg)
    
    @handle_errors(screenshot_name="popup_handle")
    def handle_post_login_popup(self):
        """
        ログイン後のポップアップを処理します
        
        Returns:
            bool: ポップアップが処理された場合はTrue
        """
        if self.popup_notice is None:
            logger.info("ポップアップ処理は設定されていません")
            return False
            
        logger.info("ログイン後のポップアップを確認しています")
        
        # ポップアップを閉じる
        return self.close_popup()
    
    @handle_errors(screenshot_name="fill_form_error")
    def fill_login_form(self, account_key=None, username=None, password=None):
        """
        ログインフォームに情報を入力します
        
        Args:
            account_key (str, optional): アカウントキー。指定がなければ設定値を使用
            username (str, optional): ユーザー名。指定がなければ設定値を使用
            password (str, optional): パスワード。指定がなければ設定値を使用
            
        Returns:
            bool: 入力が成功した場合はTrue
        """
        # 入力値の設定（引数が指定されていなければフォームフィールドから取得）
        account_key_value = account_key
        username_value = username
        password_value = password
        
        # フォームフィールドから取得
        if not account_key_value or not username_value or not password_value:
            for field in self.form_fields:
                if field['name'] == 'account_key' and not account_key_value:
                    account_key_value = field['value']
                elif field['name'] == 'username' and not username_value:
                    username_value = field['value']
                elif field['name'] == 'password' and not password_value:
                    password_value = field['value']
        
        success = True
        
        # アカウントキーの入力（ある場合のみ）
        if self.account_key_input and account_key_value:
            if not self.enter_account_key(account_key_value):
                logger.error("アカウントキーの入力に失敗しました")
                success = False
        
        # ユーザー名の入力
        if self.username_input and username_value:
            if not self.enter_username(username_value):
                logger.error("ユーザー名の入力に失敗しました")
                success = False
        
        # パスワードの入力
        if self.password_input and password_value:
            if not self.enter_password(password_value):
                logger.error("パスワードの入力に失敗しました")
                success = False
        
        if success:
            logger.info("ログインフォームへの入力が完了しました")
        
        return success
    
    @handle_errors(screenshot_name="submit_form_error")
    def submit_login_form(self):
        """
        ログインフォームを送信します
        
        Returns:
            bool: 送信が成功した場合はTrue
        """
        # ログインボタンクリック
        if not self.click_login_button():
            logger.error("ログインボタンのクリックに失敗しました")
            return False
        
        # ページの読み込みを待機
        try:
            # URLの変更を確認
            current_url = self.driver.current_url
            
            # ブラウザのページ読み込み待機メソッドを使用
            self.browser.wait_for_page_load()
            
            # URLの変更またはログイン成功要素の出現を待機
            if self.success_url:
                # 成功URLが設定されている場合は、URLのリダイレクトを待機
                retry_count = 0
                max_retry = 10
                
                while retry_count < max_retry:
                    if (self.success_url in self.driver.current_url) or \
                       (current_url != self.driver.current_url):
                        break
                    time.sleep(0.5)
                    retry_count += 1
            
            logger.info("ログインフォームの送信が完了しました")
            return True
            
        except Exception as e:
            logger.error(f"ログインフォーム送信後の処理中にエラーが発生しました: {str(e)}")
            return False
    
    @handle_errors(screenshot_name="login_check_error")
    def check_login_success(self):
        """
        ログイン成功を確認します
        
        Returns:
            bool: ログインが成功した場合はTrue
        """
        # 成功判定方法
        # 1. 成功URLの確認
        if self.success_url and self.success_url in self.driver.current_url:
            logger.info(f"成功URLを確認しました: {self.driver.current_url}")
            return True
        
        # 2. 成功要素の確認
        if self.success_element and self.success_element['selector']:
            by_type = self.browser._get_by_type(self.success_element['type'])
            try:
                element = self.browser.wait_for_element(
                    by_type,
                    self.success_element['selector'],
                    timeout=self.element_timeout
                )
                if element:
                    logger.info("ログイン成功要素を確認しました")
                    return True
            except Exception as e:
                logger.debug(f"ログイン成功要素の確認中にエラーが発生しました: {str(e)}")
        
        # 3. エラー要素の確認（存在しない場合は成功と見なす）
        if self.error_selector and self.error_selector['selector']:
            by_type = self.browser._get_by_type(self.error_selector['type'])
            try:
                element = self.browser.wait_for_element(
                    by_type,
                    self.error_selector['selector'],
                    timeout=3  # エラー要素は短い時間で判定
                )
                if element:
                    error_text = element.text
                    logger.error(f"ログインエラーを検出しました: {error_text}")
                    return False
            except TimeoutException:
                # エラー要素がない場合は成功と見なす
                logger.info("ログインエラー要素は検出されませんでした")
                return True
            except Exception as e:
                logger.debug(f"ログインエラー要素の確認中にエラーが発生しました: {str(e)}")
        
        # 4. URLが変更されているかを確認
        if self.login_url and self.login_url not in self.driver.current_url:
            logger.info(f"URLの変更を確認しました: {self.driver.current_url}")
            return True
        
        logger.warning("ログイン成功の確認ができませんでした")
        return False
    
    def quit(self):
        """
        ブラウザを終了する
        自分で作成したブラウザインスタンスのみ終了する
        """
        if self.browser and self.browser_created:
            self.browser.quit()
            logger.info("ブラウザを終了しました")

def main():
    """
    テスト用のメイン関数
    """
    try:
        # コマンドライン引数の処理
        import argparse
        parser = argparse.ArgumentParser(description='ログインモジュールのテスト実行')
        parser.add_argument('--selector-group', type=str, default='login',
                            help='使用するセレクタグループ名（デフォルト: login）')
        parser.add_argument('--headless', action='store_true',
                            help='ヘッドレスモードでブラウザを実行する')
        parser.add_argument('--account', type=str, default='1',
                            help='使用するアカウント番号（デフォルト: 1）')
        parser.add_argument('--verify', action='store_true',
                            help='ログインせずに要素の検証のみを行う')
        args = parser.parse_args()
        
        # 環境変数の設定
        if args.account != '1':
            env.update_config_value("Login", "account_number", args.account)
        
        # ヘッドレスモードの設定
        if args.headless:
            headless_value = "true"
            env.update_config_value("BROWSER", "headless", headless_value)
        
        # ログインページのインスタンスを作成
        login_page = LoginPage(selector_group=args.selector_group)
        
        # 検証モードの場合
        if args.verify:
            logger.info("検証モードでログインページにアクセスします")
            result = login_page.navigate_to_login_page()
            if result:
                logger.info("ログインページへのアクセスに成功しました")
                time.sleep(5)  # 画面確認用
            else:
                logger.error("ログインページへのアクセスに失敗しました")
            login_page.quit()
            return 0 if result else 1
        
        # ログイン処理を実行
        result = login_page.execute_login_flow()
        
        if result:
            logger.info("ログインテストに成功しました")
            
            # ブラウザを少し開いたままにする（画面を確認するため）
            time.sleep(5)
        else:
            logger.error("ログインテストに失敗しました")
        
        # ブラウザを終了
        login_page.quit()
        return 0 if result else 1
            
    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生しました: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 