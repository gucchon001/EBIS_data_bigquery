import os
import csv
import time
import traceback
import configparser
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import subprocess
import re

from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env
from src.utils.slack_notifier import SlackNotifier

logger = get_logger(__name__)

class Browser:
    """
    ブラウザ操作を管理するクラス
    
    このクラスは、Seleniumを使用したブラウザ操作の基本機能を提供します。
    WebDriverの初期化、セレクタの読み込み、要素の取得、スクリーンショットの保存などの
    汎用的なブラウザ操作機能を担当します。また、設定ファイル（settings.ini）から
    ブラウザ関連の設定を読み込む機能も提供します。
    """
    
    def __init__(self, selectors_path=None, headless=None, timeout=10):
        """
        ブラウザ操作クラスの初期化
        
        Args:
            selectors_path (str): セレクタ情報を含むCSVファイルのパス
            headless (bool): ヘッドレスモードで実行するかどうか（Noneの場合はsettings.iniから読み込む）
            timeout (int): 要素を待機する最大時間（秒）
        """
        self.driver = None
        self.wait = None
        self.timeout = timeout
        
        # Slack通知用のインスタンスを初期化
        self.slack = SlackNotifier()
        
        # settings.iniからheadlessモードの設定を読み込む（引数で指定がなければ）
        if headless is None:
            self.headless = self._get_headless_setting()
        else:
            self.headless = headless
            
        self.selectors_path = selectors_path
        self.selectors = {}
        
        # スクリーンショット設定を読み込む
        self.auto_screenshot = self._get_screenshot_setting("auto_screenshot", default=True)
        self.screenshot_format = self._get_screenshot_setting("screenshot_format", default="png")
        self.screenshot_quality = int(self._get_screenshot_setting("screenshot_quality", default="100"))
        self.screenshot_on_error = self._get_screenshot_setting("screenshot_on_error", default=True)
        
        # スクリーンショット保存ディレクトリ
        screenshot_dir_setting = self._get_screenshot_setting("screenshot_dir", default="logs/screenshots")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.screenshot_dir = os.path.join(screenshot_dir_setting, timestamp)
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # セレクタファイルが指定されている場合は読み込む
        if selectors_path and os.path.exists(selectors_path):
            self._load_selectors()
            
        # セレクタのフォールバック設定
        self._setup_fallback_selectors()
    
    def _setup_fallback_selectors(self):
        """
        セレクタが見つからない場合のフォールバックセレクタを設定する
        
        主要なセレクタについて、代替のセレクタを設定し、要素が見つからない場合に使用する
        """
        # フォールバックセレクタの定義がない場合は空の辞書を作成
        self.fallback_selectors = {}
        
        # 基本的なフォールバックセレクタの例
        # 例: ログインフォームのフォールバックセレクタ
        if 'login' not in self.selectors:
            self.selectors['login'] = {}
            
        if 'username' not in self.selectors.get('login', {}):
            self.selectors.setdefault('login', {})['username'] = {
                'selector_type': 'xpath',
                'selector_value': '//input[@name="username" or @id="username" or contains(@class, "username")]'
            }
            
        if 'password' not in self.selectors.get('login', {}):
            self.selectors.setdefault('login', {})['password'] = {
                'selector_type': 'xpath',
                'selector_value': '//input[@name="password" or @id="password" or @type="password"]'
            }
            
        if 'submit' not in self.selectors.get('login', {}):
            self.selectors.setdefault('login', {})['submit'] = {
                'selector_type': 'xpath',
                'selector_value': '//button[@type="submit" or contains(@class, "submit") or contains(@class, "login")]'
            }
            
        logger.debug(f"フォールバックセレクタを設定しました")
    
    def _get_headless_setting(self):
        """
        settings.iniファイルからheadlessモードの設定を読み込む
        
        Returns:
            bool: headlessモードが有効な場合はTrue、無効な場合はFalse
        """
        try:
            # 環境変数からAPP_ENVを取得
            app_env = env.get_environment()
            
            # BROWSER セクションからheadless設定を読み込む
            headless = env.get_config_value("BROWSER", "headless", default="false")
            
            # 文字列をブール値に変換
            if isinstance(headless, str):
                return headless.lower() == "true"
            return bool(headless)
            
        except Exception as e:
            logger.warning(f"settings.iniからheadless設定を読み込めませんでした: {str(e)}")
            return False
            
    def _update_headless_setting(self, headless_value):
        """
        settings.iniファイルのheadless設定を更新する
        
        Args:
            headless_value (bool): 新しいheadless設定値
            
        Returns:
            bool: 更新が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            config_path = env.get_config_file()
            config = configparser.ConfigParser()
            
            # 設定ファイルを読み込む
            config.read(config_path, encoding='utf-8')
            
            # BROWSERセクションがなければ作成
            if not config.has_section("BROWSER"):
                config.add_section("BROWSER")
            
            # headless設定を更新
            config.set("BROWSER", "headless", str(headless_value).lower())
            
            # 設定を保存
            with open(config_path, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
                
            logger.info(f"headless設定を更新しました: {headless_value}")
            return True
            
        except Exception as e:
            logger.error(f"headless設定の更新に失敗しました: {str(e)}")
            return False
    
    def setup(self):
        """
        WebDriverをセットアップする
        
        Returns:
            bool: セットアップが成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("WebDriverのセットアップを開始します")
            
            # ヘッドレスモードの設定
            chrome_options = webdriver.ChromeOptions()
            
            if self.headless:
                logger.info("ヘッドレスモードで実行します")
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--window-size=1920,1080')
            else:
                logger.info("ブラウザ表示モードで実行します")
            
            # UAの設定
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
            chrome_options.add_argument(f'--user-agent={user_agent}')
            
            # その他のオプション
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--lang=ja')
            
            # ブラウザウィンドウのクラッシュを防止
            chrome_options.add_argument('--disable-features=RendererCodeIntegrity')
            
            # 通知を無効化
            chrome_options.add_argument('--disable-notifications')
            
            # Chromeのバージョンチェックを回避するオプション
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # バージョンチェックを無視
            chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
            # ChromeDriverのセッション作成時にバージョンチェックをスキップする
            chrome_options.set_capability("goog:chromeOptions", {"wdpOptions": {"acceptInsecureCerts": True}})
            
            # ChromeDriverのセットアップ
            # WebDriverManagerを使用して最新のChromeDriverをダウンロード
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service as ChromeService
            
            try:
                # ChromeDriverManagerを使用して適切なバージョンをダウンロード
                logger.info("WebDriverManagerを使用して最新のChromeDriverをダウンロードします")
                driver_path = ChromeDriverManager().install()
                
                # ファイルパスが実際にchromedriver.exeを指しているか確認
                driver_dir = os.path.dirname(driver_path)
                if not driver_path.endswith("chromedriver.exe"):
                    # ダウンロードディレクトリを検索
                    for root, dirs, files in os.walk(driver_dir):
                        for file in files:
                            if file.endswith("chromedriver.exe"):
                                driver_path = os.path.join(root, file)
                                logger.info(f"chromedriver.exeを検出しました: {driver_path}")
                                break
                
                chromedriver_path = driver_path
                logger.info(f"ChromeDriverManagerによりダウンロードされたドライバーを使用: {chromedriver_path}")
            except Exception as e:
                logger.error(f"ChromeDriverManagerの使用中にエラーが発生しました: {str(e)}")
                raise Exception(f"ChromeDriverのダウンロードに失敗しました: {str(e)}")
            
            # ダウンロード設定
            download_dir = env.resolve_path(env.get_config_value("Download", "directory", "data/downloads"))
            download_dir_str = str(download_dir)  # Path オブジェクトを文字列に変換
            os.makedirs(download_dir, exist_ok=True)
            logger.info(f"ダウンロードディレクトリを設定: {download_dir}")

            prefs = {
                "download.default_directory": download_dir_str,  # 文字列を使用
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # ChromeServiceを初期化
            service = webdriver.chrome.service.Service(executable_path=chromedriver_path)
            
            # WebDriverの初期化
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.maximize_window()
            self.wait = WebDriverWait(self.driver, self.timeout)
            
            logger.info("✅ WebDriverのセットアップが完了しました")
            return True
            
        except Exception as e:
            error_message = "WebDriverのセットアップ中にエラーが発生しました"
            logger.error(f"{error_message}: {str(e)}")
            logger.error(traceback.format_exc())
            self._notify_error(error_message, e, {"設定": f"headless={self.headless}, timeout={self.timeout}"})
            return False
    
    def _load_selectors(self):
        """
        CSVファイルからセレクタ情報を読み込む
        
        Returns:
            bool: 読み込みが成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info(f"セレクタファイルを読み込みます: {self.selectors_path}")
            
            with open(self.selectors_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'group' in row and 'name' in row and 'selector_type' in row and 'selector_value' in row:
                        group = row['group']
                        name = row['name']
                        
                        if group not in self.selectors:
                            self.selectors[group] = {}
                        
                        self.selectors[group][name] = {
                            'selector_type': row['selector_type'],
                            'selector_value': row['selector_value']
                        }
            
            logger.info(f"セレクタ情報を読み込みました: {len(self.selectors)} グループ")
            for group, selectors in self.selectors.items():
                logger.info(f"  - {group}: {len(selectors)} セレクタ")
            
            return True
            
        except Exception as e:
            logger.error(f"セレクタファイルの読み込み中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def navigate_to(self, url):
        """
        指定されたURLに移動する
        
        Args:
            url (str): 移動先のURL
            
        Returns:
            bool: 移動が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # URLが有効かチェック
            if not url or not isinstance(url, str):
                logger.error(f"無効なURLが指定されました: {url}")
                return False
                
            # URLの形式をチェック
            if not url.startswith(('http://', 'https://')):
                logger.warning(f"URLがhttpまたはhttpsで始まっていません: {url}")
                url = 'https://' + url
                logger.info(f"URLを修正しました: {url}")
            
            # 現在のURLを取得
            current_url = self.driver.current_url
            
            # 同じURLの場合はリロードする
            if current_url == url:
                logger.info(f"すでに同じURL ({url}) にいるため、ページをリロードします")
                self.driver.refresh()
            else:
                logger.info(f"URLに移動します: {url}")
                self.driver.get(url)
            
            # ページが完全に読み込まれるまで待機
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                logger.info("ページ読み込みが完了しました")
            except TimeoutException:
                logger.warning("ページ読み込みの完了を待機中にタイムアウトしました")
            
            return True
            
        except Exception as e:
            logger.error(f"URL移動中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _get_by_type(self, selector_type):
        """
        セレクタタイプの文字列を Selenium の By クラスの定数に変換する
        
        Args:
            selector_type (str): セレクタタイプの文字列 ('css', 'xpath', 'id', 'name', 'class')
            
        Returns:
            By: Selenium の By クラスの定数。未対応のタイプの場合は None
        """
        selector_type = selector_type.lower()
        if selector_type == 'id':
            return By.ID
        elif selector_type == 'css':
            return By.CSS_SELECTOR
        elif selector_type == 'xpath':
            return By.XPATH
        elif selector_type == 'name':
            return By.NAME
        elif selector_type == 'class':
            return By.CLASS_NAME
        else:
            logger.warning(f"未対応のセレクタタイプです: {selector_type}")
            return None

    def get_element(self, group, name, wait_time=None):
        """
        指定されたセレクタに一致する要素を取得する
        
        Args:
            group (str): セレクタのグループ名
            name (str): セレクタの名前
            wait_time (int, optional): 要素を待機する時間（秒）。指定がない場合はデフォルトのタイムアウトを使用
            
        Returns:
            WebElement: 見つかった要素。見つからない場合はNone
        """
        if not self.driver:
            logger.error("WebDriverが初期化されていません")
            return None
        
        if group not in self.selectors or name not in self.selectors[group]:
            logger.error(f"セレクタが見つかりません: {group}.{name}")
            return None
        
        selector_info = self.selectors[group][name]
        selector_type = selector_info['selector_type']
        selector_value = selector_info['selector_value']
        
        try:
            wait = WebDriverWait(self.driver, wait_time or self.timeout)
            
            # _get_by_type メソッドを使用
            by = self._get_by_type(selector_type)
            if by is None:
                return None
                
            element = wait.until(EC.presence_of_element_located((by, selector_value)))
            return element
            
        except TimeoutException:
            logger.warning(f"要素が見つかりませんでした: {group}.{name} ({selector_type}: {selector_value})")
            return None
        except Exception as e:
            logger.error(f"要素の取得中にエラーが発生しました: {str(e)}")
            return None
    
    def save_screenshot(self, filename, append_timestamp=False, append_url=False, custom_dir=None):
        """
        スクリーンショットを保存する
        
        Args:
            filename (str): 保存するファイル名
            append_timestamp (bool): ファイル名にタイムスタンプを追加するかどうか
            append_url (bool): ファイル名にURLのハッシュを追加するかどうか
            custom_dir (str): カスタムディレクトリ（指定しない場合は self.screenshot_dir を使用）
            
        Returns:
            str: 保存されたファイルのパス。失敗した場合はNone
        """
        if not self.driver:
            logger.error("WebDriverが初期化されていません")
            return None
        
        # 自動スクリーンショットが無効化されている場合はスキップ
        if not self.auto_screenshot and not filename.startswith("error_"):
            logger.debug(f"自動スクリーンショットが無効化されているため、{filename} のキャプチャをスキップします")
            return None
        
        # エラー時のスクリーンショットが無効化されている場合、エラー関連のスクリーンショットをスキップ
        if not self.screenshot_on_error and filename.startswith("error_"):
            logger.debug(f"エラー時のスクリーンショットが無効化されているため、{filename} のキャプチャをスキップします")
            return None
        
        try:
            # タイムスタンプ
            timestamp = ""
            if append_timestamp:
                timestamp = f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # URLハッシュ（オプション）
            url_hash = ""
            if append_url and self.driver:
                try:
                    current_url = self.driver.current_url
                    # URLから不要な部分を取り除いてハッシュ化
                    url_clean = re.sub(r'https?://', '', current_url)
                    url_clean = re.sub(r'[^\w]', '_', url_clean)
                    url_hash = f"_{url_clean[:20]}"  # 最初の20文字だけ使用
                except:
                    pass
            
            # 拡張子の処理
            base_name, ext = os.path.splitext(filename)
            if not ext:
                ext = f".{self.screenshot_format}"
            
            # 最終的なファイル名を構築
            final_filename = f"{base_name}{timestamp}{url_hash}{ext}"
            
            # 保存先ディレクトリを決定
            save_dir = custom_dir if custom_dir else self.screenshot_dir
            os.makedirs(save_dir, exist_ok=True)
            
            # フルパスを構築
            filepath = os.path.join(save_dir, final_filename)
            
            # スクリーンショットを撮影
            self.driver.save_screenshot(filepath)
            
            logger.debug(f"スクリーンショットを保存しました: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"スクリーンショットの保存中にエラーが発生しました: {str(e)}")
            return None
    
    def analyze_page_content(self, html_content):
        """
        ページのHTML内容を解析する
        
        Args:
            html_content (str): 解析するHTML内容
            
        Returns:
            dict: 解析結果を含む辞書
        """
        result = {
            'page_title': '',
            'main_heading': '',
            'error_messages': [],
            'menu_items': []
        }
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # タイトルを取得
            title_tag = soup.find('title')
            if title_tag:
                result['page_title'] = title_tag.text.strip()
            
            # 主な見出しを取得
            h1_tags = soup.find_all('h1')
            if h1_tags:
                result['main_heading'] = h1_tags[0].text.strip()
            
            # エラーメッセージを探す
            error_elements = soup.find_all(class_=lambda c: c and ('error' in c.lower() or 'alert' in c.lower()))
            for error in error_elements:
                error_text = error.text.strip()
                if error_text:
                    result['error_messages'].append(error_text)
            
            # メニュー項目を探す
            menu_elements = soup.find_all(['a', 'button'], class_=lambda c: c and ('menu' in c.lower() or 'nav' in c.lower()))
            for menu in menu_elements:
                menu_text = menu.text.strip()
                if menu_text:
                    result['menu_items'].append(menu_text)
            
            # 一般的なナビゲーション要素も探す
            nav_elements = soup.find_all('nav')
            for nav in nav_elements:
                links = nav.find_all('a')
                for link in links:
                    link_text = link.text.strip()
                    if link_text and link_text not in result['menu_items']:
                        result['menu_items'].append(link_text)
            
            return result
            
        except Exception as e:
            logger.error(f"ページ内容の解析中にエラーが発生しました: {str(e)}")
            return result
    
    def scroll_to_element(self, element, position="center", smooth=True):
        """
        要素が画面内に表示されるようにスクロールする
        
        Args:
            element (WebElement): スクロール対象の要素
            position (str): スクロール位置（"start", "center", "end", "nearest"）
            smooth (bool): スムーズスクロールを使用するかどうか
            
        Returns:
            bool: スクロールが成功した場合はTrue、失敗した場合はFalse
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return False
                
            # スムーズスクロールのオプション
            behavior = "smooth" if smooth else "auto"
            
            self.driver.execute_script(
                f"arguments[0].scrollIntoView({{behavior: '{behavior}', block: '{position}'}});", 
                element
            )
            
            # スクロール完了を待機（スムーズスクロールの場合は少し長めに）
            time.sleep(1 if smooth else 0.5)
            
            # デバッグ用の情報を記録
            logger.debug(f"要素にスクロールしました: position={position}, smooth={smooth}")
            return True
            
        except Exception as e:
            error_message = "要素へのスクロール中にエラーが発生しました"
            self._notify_error(error_message, e)
            return False

    def click_element(self, group, name, use_javascript=False, wait_time=None, ensure_visible=True, retry_count=1):
        """
        指定された要素をクリックする
        
        Args:
            group (str): セレクタのグループ名
            name (str): セレクタの名前
            use_javascript (bool): JavaScriptを使用してクリックするかどうか
            wait_time (int, optional): 要素を待機する時間（秒）
            ensure_visible (bool): 要素が表示されていることを確認するかどうか
            retry_count (int): 失敗時のリトライ回数
            
        Returns:
            bool: クリックが成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 要素を取得
            element = self.get_element(group, name, wait_time)
            if not element:
                logger.error(f"クリック対象の要素が見つかりません: {group}.{name}")
                return False
            
            # 要素が表示されていることを確認
            if ensure_visible and not element.is_displayed():
                logger.warning(f"要素は存在しますが表示されていません: {group}.{name}")
                # 強制的に表示するか、JavaScriptでクリックするオプションを設定
                use_javascript = True
            
            # 要素が画面内に表示されるようにスクロール
            self.scroll_to_element(element)
            
            # クリック実行
            success = False
            attempts = 0
            
            while not success and attempts <= retry_count:
                try:
                    if use_javascript:
                        logger.info(f"JavaScriptを使用して要素をクリックします: {group}.{name}")
                        self.driver.execute_script("arguments[0].click();", element)
                    else:
                        logger.info(f"要素をクリックします: {group}.{name}")
                        element.click()
                    
                    success = True
                except Exception as click_e:
                    attempts += 1
                    logger.warning(f"クリック試行 {attempts}/{retry_count + 1} が失敗しました: {str(click_e)}")
                    
                    # 最後の試行では通常と反対の方法を試す
                    if attempts <= retry_count:
                        if not use_javascript and attempts == retry_count:
                            logger.info("JavaScriptを使用したクリックを試みます")
                            use_javascript = True
                            time.sleep(0.5)  # 少し待機してから再試行
                        elif use_javascript and attempts == retry_count:
                            logger.info("通常のクリックを試みます")
                            use_javascript = False
                            time.sleep(0.5)  # 少し待機してから再試行
            
            if success:
                logger.info(f"✓ 要素のクリックに成功しました: {group}.{name}")
                return True
            else:
                logger.error(f"すべてのクリック試行が失敗しました: {group}.{name}")
                return False
            
        except Exception as e:
            logger.error(f"要素のクリック中にエラーが発生しました: {group}.{name}, エラー: {str(e)}")
            self.save_screenshot(f"click_error_{group}_{name}.png")
            return False

    def click_element_by_xpath(self, xpath, use_javascript=False, wait_time=None, ensure_visible=True, retry_count=1):
        """
        XPathで指定された要素をクリックする
        
        Args:
            xpath (str): 要素のXPath
            use_javascript (bool): JavaScriptを使用してクリックするかどうか
            wait_time (int, optional): 要素を待機する時間（秒）
            ensure_visible (bool): 要素が表示されていることを確認するかどうか
            retry_count (int): 失敗時のリトライ回数
            
        Returns:
            bool: クリックが成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 要素を待機して取得
            wait_timeout = wait_time or self.timeout
            element = self.wait_for_element(By.XPATH, xpath, timeout=wait_timeout)
            
            if not element:
                logger.error(f"クリック対象の要素が見つかりません: XPath={xpath}")
                return False
            
            # 要素が表示されていることを確認
            if ensure_visible and not element.is_displayed():
                logger.warning(f"要素は存在しますが表示されていません: XPath={xpath}")
                # 強制的に表示するか、JavaScriptでクリックするオプションを設定
                use_javascript = True
            
            # 要素が画面内に表示されるようにスクロール
            self.scroll_to_element(element)
            
            # クリック実行
            success = False
            attempts = 0
            
            while not success and attempts <= retry_count:
                try:
                    if use_javascript:
                        logger.info(f"JavaScriptを使用して要素をクリックします: XPath={xpath}")
                        self.driver.execute_script("arguments[0].click();", element)
                    else:
                        logger.info(f"要素をクリックします: XPath={xpath}")
                        element.click()
                    
                    success = True
                except Exception as click_e:
                    attempts += 1
                    logger.warning(f"クリック試行 {attempts}/{retry_count + 1} が失敗しました: {str(click_e)}")
                    
                    # 最後の試行では通常と反対の方法を試す
                    if attempts <= retry_count:
                        if not use_javascript and attempts == retry_count:
                            logger.info("JavaScriptを使用したクリックを試みます")
                            use_javascript = True
                            time.sleep(0.5)  # 少し待機してから再試行
                        elif use_javascript and attempts == retry_count:
                            logger.info("通常のクリックを試みます")
                            use_javascript = False
                            time.sleep(0.5)  # 少し待機してから再試行
            
            if success:
                logger.info(f"✓ 要素のクリックに成功しました: XPath={xpath}")
                return True
            else:
                logger.error(f"すべてのクリック試行が失敗しました: XPath={xpath}")
                return False
            
        except Exception as e:
            logger.error(f"要素のクリック中にエラーが発生しました: XPath={xpath}, エラー: {str(e)}")
            self.save_screenshot(f"click_error_xpath.png")
            return False
    
    def switch_to_new_window(self, current_handles=None, timeout=10, retries=3):
        """
        新しく開いたウィンドウに切り替える
        
        Args:
            current_handles (list, optional): 切り替え前のウィンドウハンドルリスト
            timeout (int, optional): 新しいウィンドウが開くまで待機する時間(秒)
            retries (int, optional): 失敗時のリトライ回数
            
        Returns:
            bool: 切り替えが成功した場合はTrue、失敗した場合はFalse
        """
        if not self.driver:
            logger.error("WebDriverが初期化されていません")
            return False
            
        # 現在のウィンドウハンドルが指定されていない場合は取得
        if current_handles is None:
            try:
                current_handles = self.driver.window_handles
                logger.info(f"現在のウィンドウハンドル: {current_handles}")
            except Exception as e:
                logger.error(f"現在のウィンドウハンドルの取得に失敗しました: {str(e)}")
                return False
        
        retry_count = 0
        while retry_count < retries:
            try:
                # 新しいウィンドウが開くまで待機
                start_time = time.time()
                new_handle = None
                
                while time.time() - start_time < timeout:
                    try:
                        # 現在のハンドルを再取得（セッションが無効になっていないか確認）
                        handles = self.driver.window_handles
                        
                        # 新しいウィンドウを探す
                        for handle in handles:
                            if handle not in current_handles:
                                new_handle = handle
                                break
                        
                        if new_handle:
                            break
                            
                        time.sleep(0.5)  # 短い間隔で再試行
                    except Exception as inner_e:
                        logger.warning(f"ウィンドウハンドルの取得中にエラーが発生しました（リトライ中）: {str(inner_e)}")
                        time.sleep(1)
                        continue
                
                if not new_handle:
                    logger.warning(f"新しいウィンドウが見つかりませんでした（{timeout}秒待機後）")
                    # スクリーンショットを撮影してエラーを記録
                    self.save_screenshot(f"window_switch_timeout_{retry_count}.png")
                    retry_count += 1
                    time.sleep(1)  # リトライ前に待機
                    continue
                
                # 新しいウィンドウに切り替え
                self.driver.switch_to.window(new_handle)
                
                # 切り替え後のURLを表示
                logger.info(f"新しいウィンドウに切り替えました: {self.driver.current_url}")
                
                # 切り替え後のスクリーンショット
                self.save_screenshot("after_window_switch.png")
                
                return True
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"新しいウィンドウへの切り替え中にエラーが発生しました (リトライ {retry_count}/{retries}): {str(e)}")
                
                if retry_count >= retries:
                    logger.error(f"新しいウィンドウへの切り替えに失敗しました（{retries}回リトライ後）")
                    self.save_screenshot("window_switch_error.png")
                    return False
                
                # リトライ前に待機
                time.sleep(2)
        
        return False
    
    def quit(self, error_message=None, exception=None, context=None):
        """
        WebDriverを終了する
        
        Args:
            error_message (str, optional): 通知するエラーメッセージ
            exception (Exception, optional): 例外オブジェクト
            context (dict, optional): エラーコンテキスト情報
        """
        if error_message:
            self._notify_error(error_message, exception, context)
            
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriverを正常に終了しました")
            except Exception as e:
                logger.warning(f"WebDriver終了時にエラーが発生しました: {str(e)}")
            finally:
                self.driver = None

    def set_headless_mode(self, headless_mode):
        """
        ヘッドレスモード設定を変更し、settings.iniファイルも更新する
        
        Args:
            headless_mode (bool): 新しいヘッドレスモード設定
            
        Returns:
            bool: 設定変更が成功した場合はTrue、失敗した場合はFalse
            
        Note:
            既に初期化済みのWebDriverには影響しません。
            次回のWebDriver初期化時から有効になります。
        """
        try:
            # 内部の設定を更新
            self.headless = bool(headless_mode)
            
            # settings.iniファイルも更新
            result = self._update_headless_setting(headless_mode)
            
            logger.info(f"ヘッドレスモード設定を {headless_mode} に変更しました")
            return result
        except Exception as e:
            logger.error(f"ヘッドレスモード設定の変更中にエラーが発生しました: {str(e)}")
            return False
    
    def _notify_error(self, error_message, exception=None, context=None):
        """
        エラーが発生した際にログに記録し、Slackに通知する
        
        Args:
            error_message (str): エラーメッセージ
            exception (Exception, optional): 発生した例外
            context (dict, optional): エラーのコンテキスト情報
        
        Returns:
            bool: 通知が成功した場合はTrue、失敗した場合はFalse
        """
        # エラーをログに記録
        if exception:
            logger.error(f"{error_message}: {str(exception)}")
            import traceback
            logger.error(traceback.format_exc())
        else:
            logger.error(error_message)
        
        # スクリーンショットを撮影
        screenshot_path = None
        if self.driver:
            error_screenshot = f"error_{datetime.now().strftime('%H%M%S')}.png"
            if self.save_screenshot(error_screenshot):
                screenshot_path = os.path.join(self.screenshot_dir, error_screenshot)
        
        # コンテキスト情報を準備
        ctx = context or {}
        if screenshot_path:
            ctx["スクリーンショット"] = f"保存済み: {screenshot_path}"
        
        # 現在のURLを追加
        if self.driver:
            try:
                ctx["現在のURL"] = self.driver.current_url
            except:
                ctx["現在のURL"] = "取得できません"
        
        try:
            # Slackに通知（失敗してもエラーにしない）
            slack_result = self.slack.send_error(
                error_message=error_message,
                exception=exception,
                title="ブラウザ操作エラー",
                context=ctx
            )
            
            if not slack_result:
                logger.warning("Slack通知の送信に失敗しましたが、処理は続行します")
            
            return slack_result
        except Exception as e:
            logger.warning(f"Slack通知処理中に例外が発生しましたが、処理は続行します: {str(e)}")
            return False

    def get_window_handles(self):
        """
        現在のウィンドウハンドルのリストを取得する
        
        Returns:
            list: ウィンドウハンドルのリスト。エラーが発生した場合は空リスト
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return []
            return self.driver.window_handles
        except Exception as e:
            error_message = "ウィンドウハンドル取得中にエラーが発生しました"
            self._notify_error(error_message, e)
            return []

    def get_page_source(self):
        """
        現在のページのHTMLソースを取得する
        
        Returns:
            str: HTMLソース。エラーが発生した場合は空文字列
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return ""
            return self.driver.page_source
        except Exception as e:
            error_message = "ページソース取得中にエラーが発生しました"
            self._notify_error(error_message, e)
            return ""

    def get_current_url(self):
        """
        現在のURLを取得する

        Returns:
            str: 現在のURL
        """
        try:
            return self.driver.current_url
        except Exception as e:
            logger.error(f"現在のURLの取得に失敗しました: {str(e)}")
            return None
    
    def wait_for_page_load(self, timeout=None):
        """
        ページの読み込みが完了するのを待機する
        
        Args:
            timeout (int, optional): タイムアウト秒数。デフォルトはインスタンス初期化時の値
            
        Returns:
            bool: 成功した場合はTrue
        """
        if timeout is None:
            timeout = self.timeout
            
        try:
            # document.readyStateがcompleteになるまで待機
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # JavaScriptによる非同期処理の完了を確認（オプション）
            self.driver.execute_script("return (typeof jQuery === 'undefined' || jQuery.active === 0)")
            
            logger.info("ページ読み込みが完了しました")
            return True
        except Exception as e:
            logger.warning(f"ページ読み込み待機中にエラーが発生しました: {str(e)}")
            return False
    
    def get_page_title(self):
        """
        現在のページのタイトルを取得する
        
        Returns:
            str: ページタイトル。エラーが発生した場合は空文字列
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return ""
            return self.driver.title
        except Exception as e:
            error_message = "ページタイトル取得中にエラーが発生しました"
            self._notify_error(error_message, e)
            return ""

    def execute_script(self, script, *args):
        """
        JavaScriptを実行する
        
        Args:
            script (str): 実行するJavaScriptコード
            *args: JavaScriptに渡す引数
            
        Returns:
            any: JavaScriptの実行結果。エラーが発生した場合はNone
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return None
            return self.driver.execute_script(script, *args)
        except Exception as e:
            error_message = "JavaScriptの実行中にエラーが発生しました"
            self._notify_error(error_message, e)
            return None

    def find_elements(self, by, value):
        """
        指定されたセレクタに一致する複数の要素を取得する
        
        Args:
            by (By): 検索方法（By.CSS_SELECTOR, By.XPATHなど）
            value (str): セレクタの値
            
        Returns:
            list: 見つかった要素のリスト。見つからない場合は空リスト
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return []
            return self.driver.find_elements(by, value)
        except Exception as e:
            error_message = f"要素の検索中にエラーが発生しました: {by}={value}"
            self._notify_error(error_message, e)
            return []

    def find_elements_by_tag(self, tag, text_filter=None):
        """
        指定されたタグ名の要素を検索し、オプションでテキスト内容でフィルタリングする
        
        Args:
            tag (str): 検索するHTML要素のタグ名
            text_filter (str, optional): 要素のテキストに含まれるべき文字列
            
        Returns:
            list: 見つかった要素のリスト。見つからない場合は空リスト
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return []
            
            elements = self.driver.find_elements(By.TAG_NAME, tag)
            
            if text_filter:
                filtered_elements = []
                for element in elements:
                    try:
                        if text_filter in element.text:
                            filtered_elements.append(element)
                    except:
                        continue
                return filtered_elements
            
            return elements
        except Exception as e:
            error_message = f"{tag}タグの要素検索中にエラーが発生しました"
            self._notify_error(error_message, e)
            return []

    def wait_for_element(self, by, value, condition=EC.presence_of_element_located, timeout=None):
        """
        指定された条件で要素を待機する
        
        Args:
            by (By): 検索方法（By.CSS_SELECTOR, By.XPATHなど）
            value (str): セレクタの値
            condition (function, optional): 待機条件。デフォルトはEC.presence_of_element_located
            timeout (int, optional): タイムアウト時間（秒）。未指定時はデフォルトのタイムアウトを使用
            
        Returns:
            WebElement: 見つかった要素。見つからない場合はNone
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return None
            
            wait_timeout = timeout or self.timeout
            return WebDriverWait(self.driver, wait_timeout).until(
                condition((by, value))
            )
        except TimeoutException:
            logger.warning(f"要素の待機中にタイムアウトが発生しました: {by}={value}")
            return None
        except Exception as e:
            error_message = f"要素の待機中にエラーが発生しました: {by}={value}"
            self._notify_error(error_message, e)
            return None

    def input_text(self, locator, text, clear_first=True):
        """
        指定されたロケーターで要素を見つけ、テキストを入力する
        
        Args:
            locator (tuple): (By.XX, "value") 形式のロケーター
            text (str): 入力するテキスト
            clear_first (bool): 入力前にフィールドをクリアするかどうか
            
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return False
            
            by, value = locator
            element = self.wait_for_element(by, value)
            
            if not element:
                logger.error(f"入力対象の要素が見つかりません: {by}={value}")
                self.save_screenshot(f"input_error_{value.replace('/', '_')}.png")
                return False
            
            # 要素が表示されるようにスクロール
            self.scroll_to_element(element)
            
            # フィールドをクリア
            if clear_first:
                element.clear()
            
            # テキストを入力
            element.send_keys(text)
            logger.debug(f"テキストを入力しました: {text[:2]}{'*' * (len(text) - 4) if len(text) > 4 else '*' * len(text)}{text[-2:] if len(text) > 4 else ''}")
            return True
            
        except Exception as e:
            error_message = f"テキスト入力中にエラーが発生しました: {by}={value}"
            logger.error(f"{error_message}: {str(e)}")
            self.save_screenshot(f"input_error_{value.replace('/', '_')}.png")
            return False
    
    def input_text_by_selector(self, group, name, text, clear_first=True):
        """
        セレクタ情報を使用して要素を見つけ、テキストを入力する
        
        Args:
            group (str): セレクタのグループ名
            name (str): セレクタの名前
            text (str): 入力するテキスト
            clear_first (bool): 入力前にフィールドをクリアするかどうか
            
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return False
            
            if group not in self.selectors or name not in self.selectors[group]:
                logger.error(f"セレクタが見つかりません: {group}.{name}")
                return False
            
            selector_info = self.selectors[group][name]
            selector_type = selector_info['selector_type']
            selector_value = selector_info['selector_value']
            
            # _get_by_type メソッドを使用
            by = self._get_by_type(selector_type)
            if by is None:
                return False
            
            return self.input_text((by, selector_value), text, clear_first)
            
        except Exception as e:
            error_message = f"テキスト入力中にエラーが発生しました: {group}.{name}"
            logger.error(f"{error_message}: {str(e)}")
            self.save_screenshot(f"input_error_{group}_{name}.png")
            return False

    def get_chrome_version(self):
        """
        システムのChromeバージョンを取得する
        
        Returns:
            str: システムのChromeバージョン
        """
        try:
            # Windowsの場合
            process = subprocess.Popen(
                ['reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
            output, error = process.communicate()
            version = re.search(r'version\s+REG_SZ\s+([\d\.]+)', output.decode('utf-8')).group(1)
            return version
        except:
            # 検出できない場合はデフォルトバージョンを返す
            return "134.0.6998.89"

    def _get_screenshot_setting(self, setting_name, default=None):
        """
        settings.iniファイルからスクリーンショット関連の設定を読み込む
        
        Args:
            setting_name (str): 設定名（auto_screenshot, screenshot_dir など）
            default: デフォルト値
            
        Returns:
            設定値。設定が見つからない場合はデフォルト値
        """
        try:
            # BROWSERセクションから設定を読み込む
            value = env.get_config_value("BROWSER", setting_name, default=default)
            
            # 文字列の "true" または "false" をブール値に変換
            if isinstance(value, str) and value.lower() in ["true", "false"]:
                return value.lower() == "true"
            
            return value
            
        except Exception as e:
            logger.warning(f"スクリーンショット設定 {setting_name} の読み込みに失敗しました: {str(e)}")
            return default 