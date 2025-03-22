#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AIElementExtractor - Seleniumを使用してWebページから要素を動的に抽出するツール

このモジュールは指示ファイル(ai_selenium_direction.md)から操作シナリオを読み取り、
Seleniumを使用してWebページの要素を抽出し、操作するための機能を提供します。
"""

import os
import sys
import re
import time
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
import traceback
import urllib.parse
from bs4 import BeautifulSoup
import requests

# Selenium関連のインポート
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementNotInteractableException,
    StaleElementReferenceException
)

# OpenAI API
import openai

# プロジェクトルートへのパスを追加
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
sys.path.append(PROJECT_ROOT)

from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env

logger = get_logger(__name__)

class AIElementExtractor:
    """
    Webページから要素を抽出し、操作を行うためのクラス
    
    このクラスは指示ファイルからセクションを解析し、指定されたURLにアクセスして
    要素情報を抽出します。必要に応じて操作（クリック、入力など）を実行できます。
    
    Attributes:
        browser: Seleniumのwebdriverインスタンス
        wait: WebDriverWaitインスタンス
        keep_browser_open: ブラウザを開いたままにするかどうか
        use_cookies: Cookieを使用するかどうか
        headless: ヘッドレスモードで実行するかどうか
        timeout: 要素を待機する最大時間（秒）
        screenshot_dir: スクリーンショットの保存先ディレクトリ
    """
    
    def __init__(self, keep_browser_open=False, use_cookies=True, headless=False):
        """
        AIElementExtractorの初期化
        
        Args:
            keep_browser_open (bool): 処理完了後もブラウザを開いたままにするかどうか
            use_cookies (bool): Cookieを使用するかどうか
            headless (bool): ヘッドレスモードで実行するかどうか
        """
        # 環境変数を読み込む
        env.load_env()
        
        # メンバ変数の初期化
        self.browser = None
        self.wait = None
        self.keep_browser_open = keep_browser_open
        self.use_cookies = use_cookies
        self.headless = headless
        self.timeout = 30  # デフォルトのタイムアウト時間
        
        # OpenAI APIキーを設定
        openai.api_key = env.get_openai_api_key()
        
        # スクリーンショットの保存先設定
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.screenshot_dir = os.path.join(PROJECT_ROOT, "logs", "screenshots", timestamp)
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # データディレクトリの設定
        self.data_dir = os.path.join(PROJECT_ROOT, "data", "pages")
        os.makedirs(self.data_dir, exist_ok=True)
    
        # セクション情報を保存するディレクトリ
        self.elements_dir = os.path.join(PROJECT_ROOT, "data", "elements")
        os.makedirs(self.elements_dir, exist_ok=True)
        
        # 指示ファイルのパス
        self.direction_file = os.path.join(PROJECT_ROOT, "docs", "ai_selenium_direction.md")
        
        # ブラウザの準備
        logger.info("AIElementExtractorの初期化を開始します")
    
    def prepare_browser(self):
        """
        Seleniumブラウザを準備する
            
        Returns:
            bool: 準備が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("ブラウザを準備します")
            
            # Chrome オプションの設定
            chrome_options = Options()
            
            if self.headless:
                logger.info("ヘッドレスモードで実行します")
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--window-size=1920,1080')
            
            # UAの設定
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
            chrome_options.add_argument(f'--user-agent={user_agent}')
            
            # その他のオプション
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--lang=ja')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # ダウンロード設定
            download_dir = os.path.join(PROJECT_ROOT, "data", "downloads")
            os.makedirs(download_dir, exist_ok=True)
            
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # ChromeDriverの設定
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service as ChromeService
                
                logger.info("WebDriverManagerを使用してChromeDriverをセットアップします")
                service = ChromeService(ChromeDriverManager().install())
                
                # ブラウザの起動
                self.browser = webdriver.Chrome(service=service, options=chrome_options)
                self.browser.set_page_load_timeout(self.timeout)
                
                # WebDriverWaitの設定
                self.wait = WebDriverWait(self.browser, self.timeout)
                
                logger.info("ブラウザの準備が完了しました")
                return True
                
            except Exception as e:
                logger.error(f"ChromeDriverのセットアップに失敗しました: {str(e)}")
                logger.error(traceback.format_exc())
                return False
            
        except Exception as e:
            logger.error(f"ブラウザの準備中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def parse_direction_file(self, section_name):
        """
        指示ファイルから特定のセクションを解析する
        
        Args:
            section_name (str): 解析するセクション名
            
        Returns:
            dict: 解析されたセクション情報（失敗した場合はNone）
                {
                    'name': セクション名,
                    'overview': 概要,
                    'url': URL,
                    'operations': 操作手順のリスト,
                    'elements': 取得する要素のリスト
                }
        """
        try:
            logger.info(f"指示ファイル {self.direction_file} からセクション '{section_name}' を解析します")
            
            if not os.path.exists(self.direction_file):
                logger.error(f"指示ファイルが存在しません: {self.direction_file}")
                return None
            
            # ファイルの内容を読み込む
            with open(self.direction_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # セクション名のパターンを構築（数字も含む可能性があるため）
            # 例: "## 1. login" や "## 2. detail_analytics" など
            section_pattern = re.compile(rf"## [\d\.]+ {re.escape(section_name)}\s*\n(.*?)(?:##|\Z)", re.DOTALL)
            
            # セクションを検索
            section_match = section_pattern.search(content)
            if not section_match:
                logger.error(f"セクション '{section_name}' が見つかりませんでした")
                return None
            
            section_content = section_match.group(1).strip()
            
            # セクションの各部分を解析
            section_info = {
                'name': section_name,
                'overview': '',
                'url': '',
                'operations': [],
                'elements': []
            }
            
            # 概要
            overview_match = re.search(r"--概要\s*\n(.*?)(?:--|\Z)", section_content, re.DOTALL)
            if overview_match:
                section_info['overview'] = overview_match.group(1).strip()
            
            # URL
            url_match = re.search(r"--url\s*\n(.*?)(?:--|\Z)", section_content, re.DOTALL)
            if url_match:
                section_info['url'] = url_match.group(1).strip()
            
            # 操作手順
            operations_match = re.search(r"--操作手順\s*\n(.*?)(?:--|\Z)", section_content, re.DOTALL)
            if operations_match:
                operations_text = operations_match.group(1).strip()
                operations = []
                
                for line in operations_text.split('\n'):
                    # 番号付きの操作を抽出
                    operation_match = re.match(r"(\d+)\.\s*(.*)", line.strip())
                    if operation_match:
                        step_num = int(operation_match.group(1))
                        operation_text = operation_match.group(2).strip()
                        operations.append({
                            'step': step_num,
                            'text': operation_text
                        })
                
                section_info['operations'] = operations
            
            # 取得要素
            elements_match = re.search(r"--取得要素\s*\n(.*?)(?:--|\Z)", section_content, re.DOTALL)
            if elements_match:
                elements_text = elements_match.group(1).strip()
                elements = [element.strip() for element in elements_text.split('\n') if element.strip()]
                section_info['elements'] = elements
            
            logger.info(f"セクション '{section_name}' の解析結果:")
            logger.info(f"  URL: {section_info['url']}")
            logger.info(f"  操作手順: {len(section_info['operations'])} ステップ")
            logger.info(f"  取得要素: {len(section_info['elements'])} 要素")
            
            return section_info
            
        except Exception as e:
            logger.error(f"指示ファイルの解析中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def get_page_content_with_selenium(self, url):
        """
        Seleniumを使用してページのHTMLコンテンツを取得する
        
        Args:
            url (str): アクセスするURL
        
        Returns:
            tuple: (成功したかどうか, HTMLコンテンツ)
        """
        try:
            logger.info(f"URLにアクセスします: {url}")
            
            # ブラウザがなければ準備
            if self.browser is None:
                if not self.prepare_browser():
                    return False, None
            
            # URLにアクセス
            self.browser.get(url)
            
            # ページの読み込みを待機
            self._wait_for_page_load()
            
            # スクリーンショットを撮影
            self._save_screenshot("page_loaded")
            
            # HTMLコンテンツを取得
            html_content = self.browser.page_source
            
            # ファイルに保存
            filepath = self._save_html_to_file(url, html_content)
            
            logger.info(f"ページのHTMLコンテンツを取得しました: {len(html_content)} バイト")
            logger.info(f"HTMLファイルに保存しました: {filepath}")
            
            return True, html_content
        
        except Exception as e:
            logger.error(f"ページコンテンツの取得中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            
            # エラー時にもスクリーンショットを撮影
            if self.browser:
                self._save_screenshot("error_page_content")
            
            return False, None

    def _wait_for_page_load(self, timeout=30):
        """
        ページの読み込みが完了するのを待機する
        
        Args:
            timeout (int): タイムアウト時間（秒）
        """
        try:
            # document.readyStateが'complete'になるのを待機
            WebDriverWait(self.browser, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # 少し待機して、JavaScriptの実行完了を待つ
            time.sleep(1)
            
        except TimeoutException:
            logger.warning(f"ページの読み込み待機中にタイムアウトしました（{timeout}秒）")
        except Exception as e:
            logger.warning(f"ページの読み込み待機中にエラーが発生しました: {str(e)}")

    def _save_html_to_file(self, url, html_content, suffix=""):
        """
        HTMLコンテンツをファイルに保存する
        
        Args:
            url (str): 対象のURL
            html_content (str): HTMLコンテンツ
            suffix (str): ファイル名の接尾辞
            
        Returns:
            str: 保存したファイルのパス
        """
        # ファイル名を生成
        filename = self._generate_filename(url, suffix)
        filepath = os.path.join(self.data_dir, filename)
            
        # ファイルに保存
        with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
        return filepath

    def _generate_filename(self, url, suffix=""):
        """
        URLからファイル名を生成する
        
        Args:
            url (str): 対象のURL
            suffix (str): ファイル名の接尾辞
            
        Returns:
            str: 生成されたファイル名
        """
        # URLをパース
        parsed_url = urllib.parse.urlparse(url)
        
        # ドメイン名と経路を取得
        domain = parsed_url.netloc
        path = parsed_url.path.strip('/')
        
        # パス部分を加工（不要な記号を除去）
        path = re.sub(r'[^a-zA-Z0-9_]', '_', path)
        if len(path) > 30:
            path = path[:30]  # 長すぎるパスは切り詰める
        
        # タイムスタンプ
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # ファイル名を生成
        if suffix:
            filename = f"{domain}_{path}_{suffix}_{timestamp}.html"
        else:
            filename = f"{domain}_{path}_{timestamp}.html"
            
            return filename

    def _save_screenshot(self, filename_base):
        """
        スクリーンショットを保存する
        
        Args:
            filename_base (str): ファイル名のベース部分
            
        Returns:
            str: 保存したファイルのパス
        """
        if not self.browser:
            logger.warning("ブラウザが初期化されていないため、スクリーンショットを撮影できません")
            return None
        
        try:
            # タイムスタンプ
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # ファイル名を生成
            filename = f"{filename_base}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            # スクリーンショットを撮影
            self.browser.save_screenshot(filepath)
            
            logger.info(f"スクリーンショットを保存しました: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"スクリーンショットの保存中にエラーが発生しました: {str(e)}")
            return None
    
    def extract_elements_with_openai(self, direction, html_content, filepath):
        """
        OpenAI APIを使用してHTMLから要素情報を抽出する
        
        Args:
            direction (dict): セクション情報
            html_content (str): HTMLコンテンツ
            filepath (str): HTMLファイルのパス
            
        Returns:
            list: 抽出された要素情報のリスト
        """
        try:
            logger.info("OpenAI APIを使用して要素情報を抽出します")
            
            # HTMLを適切なサイズに切り詰める
            # OpenAIのAPIにはトークン制限があるため、HTMLを適切なサイズに切り詰める
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 不要なタグを削除
            for tag in soup(['script', 'style', 'svg', 'path', 'meta', 'link']):
                tag.decompose()
            
            # HTMLを文字列に変換
            simplified_html = str(soup)
            
            # 文字数制限（トークン数はこれより少なくなる）
            # OpenAI APIの制限に応じて調整する必要がある
            max_length = 50000
            if len(simplified_html) > max_length:
                logger.warning(f"HTMLが長すぎるため、{max_length}文字に切り詰めます")
                simplified_html = simplified_html[:max_length] + "..."
            
            # 要素の取得対象
            element_names = direction['elements']
            elements_text = "\n".join(element_names)
            
            # OpenAI APIへのプロンプト作成
            prompt = f"""
            あなたはHTML要素抽出の専門家です。以下のHTMLから、指定された要素を抽出し、それらのセレクター情報を返してください。

            【抽出する要素】
            {elements_text}

            【抽出する情報】
            各要素について、以下の情報を抽出してください。
            1. 要素の種類（ボタン、リンク、入力フィールド、テキスト、画像、コンテナ、その他）
            2. セレクター情報（複数の方法を提供）:
               - ID
               - Name
               - CSS セレクター（最も具体的なもの）
               - XPath（最も信頼性の高いもの）
            3. 重要な属性（クラス、role、aria-*など）
            4. 表示テキスト（ある場合）
            5. 推奨される操作方法（クリック、入力、ホバー、スクロールなど）

            【HTML】
            {simplified_html}

            【出力形式】
            JSON形式で出力してください。以下はフォーマットです：
```json
            [
              {{
                "name": "要素名",
                "type": "要素の種類",
      "selectors": {{
                  "id": "id値（存在する場合）",
                  "name": "name属性（存在する場合）",
                  "css": "CSSセレクター",
                  "xpath": "XPath"
      }},
      "attributes": {{
                  "キー1": "値1",
                  "キー2": "値2"
                }},
                "text": "表示テキスト",
                "operation": "推奨される操作方法"
              }}
            ]
            ```

            見つからない要素についても、最も近いと思われる要素を推測して出力してください。
            """.strip()
            
            # OpenAI APIへのリクエスト
            response = openai.ChatCompletion.create(
                model=env.get_openai_model(),  # 例: "gpt-4o"
                messages=[
                    {"role": "system", "content": "あなたはHTMLからセレクタを抽出する専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 低い温度で決定論的な応答を得る
                max_tokens=2000,   # 必要に応じて調整
            )
            
            # レスポンスから要素情報を抽出
            result = response.choices[0].message.content.strip()
            
            # JSONパートを抽出
            json_match = re.search(r'```json\s*(.*?)\s*```', result, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # ```json ブロックがない場合は、全体を試す
                json_str = result
            
            # JSON解析
            try:
                elements = json.loads(json_str)
                logger.info(f"OpenAI APIから {len(elements)} 個の要素情報を取得しました")
                return elements
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析エラー: {str(e)}")
                logger.error(f"JSON文字列: {json_str}")
                return []
            
        except Exception as e:
            logger.error(f"OpenAI APIを使用した要素抽出中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def perform_operations(self, operations):
        """
        指定された操作を実行する
        
        Args:
            operations (list): 実行する操作のリスト
            
        Returns:
            bool: すべての操作が成功した場合はTrue、いずれかが失敗した場合はFalse
        """
        if not operations:
            logger.info("実行する操作がありません")
            return True
        
        logger.info(f"{len(operations)} 個の操作を実行します")
        
        for op in operations:
            step = op.get('step', 0)
            text = op.get('text', '')
            
            logger.info(f"ステップ {step}: {text}")
            
            # スクリーンショットを撮影（操作前）
            self._save_screenshot(f"operation_{step}_before")
            
            # 操作種別を判定して実行
            success = self._perform_operation(text)
            
            # スクリーンショットを撮影（操作後）
            self._save_screenshot(f"operation_{step}_after")
            
            if not success:
                logger.error(f"ステップ {step} の実行に失敗しました: {text}")
                return False
            
            # 少し待機して、次の操作の準備をする
            time.sleep(1)
        
        logger.info("すべての操作が成功しました")
        return True
    
    def _perform_operation(self, operation_text):
        """
        操作を実行する
        
        Args:
            operation_text (str): 操作の説明テキスト
            
        Returns:
            bool: 操作が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # クリック操作
            if "クリック" in operation_text:
                return self._perform_click_operation(operation_text)
            
            # 入力操作
            elif "入力" in operation_text:
                return self._perform_input_operation(operation_text)
            
            # 選択操作
            elif "選択" in operation_text:
                return self._perform_select_operation(operation_text)
            
            # 待機操作
            elif "待機" in operation_text:
                return self._perform_wait_operation(operation_text)
            
            # 不明な操作
            else:
                logger.warning(f"不明な操作: {operation_text}")
                return True  # とりあえず成功にしておく
            
        except Exception as e:
            logger.error(f"操作の実行中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _perform_click_operation(self, operation_text):
        """
        クリック操作を実行する
        
        Args:
            operation_text (str): クリック操作の説明テキスト
            
        Returns:
            bool: 操作が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 要素名を抽出
            element_name = operation_text.replace("クリック", "").strip()
            if "をクリック" in element_name:
                element_name = element_name.replace("をクリック", "").strip()
            
            logger.info(f"要素 '{element_name}' をクリックします")
            
            # XPathを試行
            xpath_patterns = [
                f"//*[contains(text(), '{element_name}')]",
                f"//*[contains(@title, '{element_name}')]",
                f"//*[contains(@aria-label, '{element_name}')]",
                f"//*[contains(@placeholder, '{element_name}')]",
                f"//*[contains(@value, '{element_name}')]",
                f"//*[contains(@alt, '{element_name}')]",
                f"//button[contains(., '{element_name}')]",
                f"//a[contains(., '{element_name}')]",
                f"//input[@type='button' and contains(@value, '{element_name}')]",
                f"//*[contains(@class, 'btn') and contains(., '{element_name}')]"
            ]
            
            element = None
            
            # 各XPathを試す
            for xpath in xpath_patterns:
                try:
                    elements = self.browser.find_elements(By.XPATH, xpath)
                    if elements:
                        # 表示されている要素を優先
                        for el in elements:
                            if el.is_displayed():
                                element = el
                                break
                        
                        # 表示されている要素がなければ最初の要素
                        if element is None:
                            element = elements[0]
                        
                        logger.info(f"要素が見つかりました: {xpath}")
                        break
                except Exception:
                    pass
            
            if element is None:
                logger.error(f"クリックする要素 '{element_name}' が見つかりませんでした")
                return False
            
            # 要素が表示されているか確認
            if not element.is_displayed():
                logger.warning(f"要素 '{element_name}' は表示されていません。JavaScript経由でクリックを試みます。")
                self.browser.execute_script("arguments[0].scrollIntoView(true);", element)
                self.browser.execute_script("arguments[0].click();", element)
            else:
                # 要素に移動してクリック
                self.browser.execute_script("arguments[0].scrollIntoView(true);", element)
                try:
                    element.click()
                except ElementNotInteractableException:
                    logger.warning("直接クリックできないため、JavaScript経由でクリックします")
                    self.browser.execute_script("arguments[0].click();", element)
            
            # 少し待機
            time.sleep(1)
            
            logger.info(f"要素 '{element_name}' のクリックに成功しました")
            return True
            
        except Exception as e:
            logger.error(f"クリック操作の実行中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _perform_input_operation(self, operation_text):
        """
        入力操作を実行する
        
        Args:
            operation_text (str): 入力操作の説明テキスト
            
        Returns:
            bool: 操作が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 要素名と入力値を抽出
            match = re.search(r"(.*?)に「(.*)」を入力", operation_text)
            if not match:
                logger.error(f"入力操作の形式が不正です: {operation_text}")
                return False
            
            element_name = match.group(1).strip()
            input_value = match.group(2).strip()
            
            logger.info(f"要素 '{element_name}' に '{input_value}' を入力します")
            
            # XPathを試行
            xpath_patterns = [
                f"//input[contains(@placeholder, '{element_name}')]",
                f"//input[contains(@name, '{element_name}')]",
                f"//input[contains(@id, '{element_name}')]",
                f"//input[contains(@aria-label, '{element_name}')]",
                f"//textarea[contains(@placeholder, '{element_name}')]",
                f"//textarea[contains(@name, '{element_name}')]",
                f"//textarea[contains(@id, '{element_name}')]",
                f"//textarea[contains(@aria-label, '{element_name}')]",
                f"//*[contains(text(), '{element_name}')]/following::input[1]",
                f"//*[contains(text(), '{element_name}')]/following::textarea[1]"
            ]
            
            element = None
            
            # 各XPathを試す
            for xpath in xpath_patterns:
                try:
                    elements = self.browser.find_elements(By.XPATH, xpath)
                    if elements:
                        # 表示されている要素を優先
                        for el in elements:
                            if el.is_displayed():
                                element = el
                                break
                        
                        # 表示されている要素がなければ最初の要素
                        if element is None:
                            element = elements[0]
                        
                        logger.info(f"要素が見つかりました: {xpath}")
                        break
                except Exception:
                    pass
            
            if element is None:
                logger.error(f"入力する要素 '{element_name}' が見つかりませんでした")
                return False
            
            # 要素をクリア
            element.clear()
            
            # 値を入力
            element.send_keys(input_value)
            
            logger.info(f"要素 '{element_name}' への入力に成功しました")
            return True
            
        except Exception as e:
            logger.error(f"入力操作の実行中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _perform_select_operation(self, operation_text):
        """
        選択操作を実行する
        
        Args:
            operation_text (str): 選択操作の説明テキスト
            
        Returns:
            bool: 操作が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 要素名と選択値を抽出
            match = re.search(r"(.*?)から「(.*)」を選択", operation_text)
            if not match:
                logger.error(f"選択操作の形式が不正です: {operation_text}")
                return False
                
            element_name = match.group(1).strip()
            select_value = match.group(2).strip()
            
            logger.info(f"要素 '{element_name}' から '{select_value}' を選択します")
            
            # selectタグの場合はSeleniumのSelectクラスを使用
            # まずドロップダウンを探す
            xpath_patterns = [
                f"//select[contains(@name, '{element_name}')]",
                f"//select[contains(@id, '{element_name}')]",
                f"//select[contains(@aria-label, '{element_name}')]",
                f"//*[contains(text(), '{element_name}')]/following::select[1]"
            ]
            
            select_element = None
            
            # 各XPathを試す
            for xpath in xpath_patterns:
                try:
                    elements = self.browser.find_elements(By.XPATH, xpath)
                    if elements:
                        select_element = elements[0]
                        logger.info(f"セレクト要素が見つかりました: {xpath}")
                        break
                except Exception:
                    pass
            
            if select_element:
                # Selectクラスを使用
                from selenium.webdriver.support.ui import Select
                select = Select(select_element)
                select.select_by_visible_text(select_value)
                logger.info(f"セレクト要素 '{element_name}' から '{select_value}' を選択しました")
                return True
            else:
                logger.error(f"セレクト要素 '{element_name}' が見つかりませんでした")
                return False
        except Exception as e:
            logger.error(f"選択操作の実行中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
            
    def _perform_wait_operation(self, operation_text):
        """
        待機操作を実行する
        
        Args:
            operation_text (str): 待機操作の説明テキスト
            
        Returns:
            bool: 操作が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 待機時間を抽出
            wait_match = re.search(r'(\d+)\s*秒', operation_text)
            if not wait_match:
                logger.warning(f"待機時間が指定されていません。デフォルトの3秒を使用します: {operation_text}")
                wait_seconds = 3
            else:
                wait_seconds = int(wait_match.group(1))
            
            logger.info(f"{wait_seconds}秒間待機します")
            time.sleep(wait_seconds)
            logger.info(f"{wait_seconds}秒間の待機が完了しました")
            return True
        except Exception as e:
            logger.error(f"待機操作の実行中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
        
    def extract_elements_from_soup(self, section_name, soup, filepath):
        """
        BeautifulSoupオブジェクトから要素を抽出する
        
        Args:
            section_name (str): セクション名
            soup (BeautifulSoup): 解析済みのBeautifulSoupオブジェクト
            filepath (str): HTMLファイルのパス
            
        Returns:
            dict: 抽出された要素情報
            
        Note:
            このクラスには複数の要素抽出関連メソッドがあり、重複した機能を持っています：
            - extract_elements_from_soup: BeautifulSoupから要素を抽出
            - extract_elements_with_openai: OpenAI APIを使用して要素を抽出
            - extract_elements_from_page: HTMLコンテンツから要素を抽出
            - extract_elements_for_step: ステップごとの要素を抽出
            リファクタリング時には、これらのメソッド間の共通処理を抽出し、
            階層構造を整理することでコードの重複を減らせる可能性があります。
        """
        logger.info("BeautifulSoupオブジェクトから要素を抽出します")
        
        try:
            # 指示ファイルからセクション情報を取得
            direction = self.parse_direction_file(section_name)
            if not direction:
                logger.error(f"セクション '{section_name}' の情報取得に失敗しました")
                return None
                
            # HTML内容を取得
            html_content = str(soup)
            
            # OpenAI APIを使用して要素を抽出
            return self.extract_elements_with_openai(direction, html_content, filepath)
            
        except Exception as e:
            logger.error(f"要素の抽出中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def get_page_content(self, url):
        """
        URLのページ内容を取得する（requestsとBeautifulSoupで解析）
        
        Args:
            url (str): 解析するURL
            
        Returns:
            str: ページのHTML
            BeautifulSoup: 解析結果
            str: 保存したファイルパス
            
        Note:
            このメソッドとget_page_content_with_seleniumメソッドは類似した機能を持ちます。
            このメソッドはrequestsを使用し、get_page_content_with_seleniumはSeleniumを使用します。
            リファクタリング時には、共通部分を抽出して再利用性を高めることを検討してください。
        """
        logger.info(f"URLからページ内容を取得します: {url}")
        
        try:
            # リクエストを送信
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # BeautifulSoupで解析
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # ファイルに保存
            filepath = self._save_html_to_file(url, html_content)
            
            logger.info(f"ページ内容の取得に成功しました: {len(html_content)} バイト")
            logger.info(f"HTMLファイルを保存しました: {filepath}")
            
            return html_content, soup, filepath
            
        except Exception as e:
            logger.error(f"ページ内容の取得中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return "", None, ""
    
    def extract_elements_from_page(self, html_content, element_names):
        """
        HTMLコンテンツから指定された要素名に一致する要素を抽出する
        
        Args:
            html_content (str): ページのHTML
            element_names (list): 抽出する要素名のリスト
            
        Returns:
            dict: 要素名をキー、要素情報をバリューとする辞書
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        elements = {}
        
        for element_name in element_names:
            # 日本語の要素名を半角スペースで分割して、部分一致検索を行う
            name_parts = element_name.split()
            
            # ログイン関連の要素はスキップ
            if any(login_keyword in element_name for login_keyword in ["アカウントID", "ログインID", "パスワード", "ログイン　クリック"]):
                logger.info(f"ログイン関連の要素のため、スキップします: {element_name}")
                continue
            
            logger.info(f"要素を検索しています: {element_name}")
            element_found = False
            
            # 1. テキストが完全一致するボタンまたはリンク要素を検索
            button_elements = soup.find_all(['button', 'a', 'input'], string=lambda s: s and element_name in s)
            button_elements.extend(soup.find_all(['button', 'a', 'input'], text=lambda s: s and element_name in s))
            
            # role="button"属性を持つ要素も検索
            button_elements.extend(soup.find_all(attrs={"role": "button"}, string=lambda s: s and element_name in s))
            button_elements.extend(soup.find_all(attrs={"role": "button"}, text=lambda s: s and element_name in s))
            
            # class属性にbtnを含む要素も検索
            button_elements.extend(soup.find_all(lambda tag: tag.name in ['button', 'a', 'input', 'div', 'span'] and 
                                             tag.has_attr('class') and 
                                             any('btn' in cls for cls in tag['class']) and
                                             (tag.string and element_name in tag.string or 
                                              tag.text and element_name in tag.text)))
            
            if button_elements:
                element_found = True
                elements[element_name] = {
                    "type": "button",
                    "selector": f"xpath=//*[contains(text(), '{element_name}') and (contains(@class, 'btn') or @role='button' or self::button or self::a or self::input[@type='button' or @type='submit'])]",
                    "found_by": "button_search",
                    "text": button_elements[0].text.strip() if button_elements[0].text else ""
                }
                logger.info(f"ボタン要素を見つけました: {element_name}")
            
            # 2. 要素名の部分一致でボタンやリンクを検索（日本語テキストの一部が一致する場合）
            if not element_found and len(name_parts) > 1:
                logger.info(f"部分一致で検索しています: {name_parts}")
                
                # 各部分で検索
                for part in name_parts:
                    if len(part) < 2:  # 短すぎる部分はスキップ
                        continue
                        
                    button_elements = soup.find_all(['button', 'a', 'input'], 
                                                 string=lambda s: s and part in s)
                    button_elements.extend(soup.find_all(['button', 'a', 'input'], 
                                                     text=lambda s: s and part in s))
                    button_elements.extend(soup.find_all(attrs={"role": "button"}, 
                                                     string=lambda s: s and part in s))
                    
                    if button_elements:
                        element_found = True
                        elements[element_name] = {
                            "type": "button",
                            "selector": f"xpath=//*[contains(text(), '{part}') and (contains(@class, 'btn') or @role='button' or self::button or self::a or self::input[@type='button' or @type='submit'])]",
                            "found_by": "partial_button_search",
                            "text": button_elements[0].text.strip() if button_elements[0].text else ""
                        }
                        logger.info(f"部分一致 '{part}' で要素を見つけました: {element_name}")
                        break
            
            # 3. 入力フィールドの検索
            if not element_found and ("入力" in element_name or "フィールド" in element_name):
                # プレースホルダーまたはラベルテキストで検索
                input_elements = soup.find_all(['input', 'textarea'], 
                                            attrs={"placeholder": lambda v: v and any(part in v for part in name_parts)})
                
                # name属性で検索
                if not input_elements:
                    input_elements = soup.find_all(['input', 'textarea'], 
                                                attrs={"name": lambda v: v and any(part in v for part in name_parts)})
                
                # ラベルに関連付けられた入力要素を検索
                if not input_elements:
                    for part in name_parts:
                        if len(part) < 2:
                            continue
                        labels = soup.find_all('label', string=lambda s: s and part in s)
                        labels.extend(soup.find_all('label', text=lambda s: s and part in s))
                        
                        for label in labels:
                            if label.has_attr('for'):
                                input_elem = soup.find(['input', 'textarea'], id=label['for'])
                                if input_elem:
                                    input_elements.append(input_elem)
                
                if input_elements:
                    element_found = True
                    input_type = input_elements[0].get('type', 'text')
                    elements[element_name] = {
                        "type": "input",
                        "input_type": input_type,
                        "selector": f"xpath=//*[@placeholder='{input_elements[0].get('placeholder', '')}' or @name='{input_elements[0].get('name', '')}' or @id='{input_elements[0].get('id', '')}']",
                        "found_by": "input_search",
                        "value": input_elements[0].get('value', '')
                    }
                    logger.info(f"入力フィールドを見つけました: {element_name}")
            
            # 4. セレクト（ドロップダウン）要素の検索
            if not element_found and ("選択" in element_name or "ドロップダウン" in element_name or "リスト" in element_name):
                select_elements = soup.find_all('select')
                
                # 近くのラベルを探す
                if select_elements:
                    for select in select_elements:
                        # IDがある場合はラベルを探す
                        if select.has_attr('id'):
                            label = soup.find('label', attrs={"for": select['id']})
                            if label and any(part in label.text for part in name_parts):
                                element_found = True
                                elements[element_name] = {
                                    "type": "select",
                                    "selector": f"xpath=//select[@id='{select['id']}']",
                                    "found_by": "select_search",
                                    "options": [option.text.strip() for option in select.find_all('option')]
                                }
                                logger.info(f"セレクト要素を見つけました: {element_name}")
                                break
                    
                    # まだ見つからない場合は、近くのテキストを探す
                    if not element_found and select_elements:
                        for select in select_elements:
                            # 前後の要素をチェック
                            prev_elem = select.find_previous()
                            next_elem = select.find_next()
                            
                            if (prev_elem and any(part in prev_elem.text for part in name_parts)) or \
                               (next_elem and any(part in next_elem.text for part in name_parts)):
                                element_found = True
                                elements[element_name] = {
                                    "type": "select",
                                    "selector": "xpath=//select[" + (f"preceding-sibling::*[contains(text(), '{name_parts[0]}')]" if prev_elem else "") + (f"following-sibling::*[contains(text(), '{name_parts[0]}')]" if next_elem else "") + "]",
                                    "found_by": "select_context_search",
                                    "options": [option.text.strip() for option in select.find_all('option')]
                                }
                                logger.info(f"コンテキストからセレクト要素を見つけました: {element_name}")
                                break
            
            # 要素が見つからなかった場合のログ
            if not element_found:
                logger.warning(f"要素が見つかりませんでした: {element_name}")
        
        return elements

    def _extract_and_save_elements(self, html, section_name, html_filepath):
        """
        HTMLから要素を抽出して保存する
        
        Args:
            html (str): HTML内容
            section_name (str): セクション名
            html_filepath (str): HTML保存先パス
            
        Returns:
            bool: 要素抽出が成功したかどうか
        """
        try:
            logger.info(f"{section_name} セクションの要素抽出を開始します")
            
            # HTMLをBeautifulSoupで解析
            soup = BeautifulSoup(html, 'html.parser')
            
            # 要素を抽出
            extracted_elements = self.extract_elements_from_soup(section_name, soup, html_filepath)
            
            if not extracted_elements:
                logger.warning(f"{section_name} セクションからの要素抽出結果が空です")
                return False
            
            # 結果をJSONファイルとして保存
            result_file = self.save_elements_to_file(section_name, extracted_elements)
            if not result_file:
                logger.error(f"{section_name} セクションの要素情報の保存に失敗しました")
                return False
            
            logger.info(f"{section_name} セクションの要素を保存しました: {result_file}")
            return True
            
        except Exception as e:
            logger.error(f"{section_name} セクションの要素抽出中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
                
    def _save_screenshot(self, filename_base):
        """
        スクリーンショットを保存する
        
        Args:
            filename_base (str): ファイル名のベース部分
            
        Returns:
            str: 保存したファイルのパス
        """
        try:
            # 保存ディレクトリの作成
            screenshot_dir = os.path.join(self.output_dir, "screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            
            # 拡張子を除去（もし含まれていれば）
            base_name = os.path.splitext(filename_base)[0]
            
            # スクリーンショットのパス
            screenshot_path = os.path.join(screenshot_dir, f"{base_name}.png")
            
            # スクリーンショット撮影
            self.browser.driver.save_screenshot(screenshot_path)
            
            logger.info(f"スクリーンショットを保存しました: {screenshot_path}")
            return screenshot_path
            
        except Exception as e:
            logger.error(f"スクリーンショットの保存中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return ""

    def _check_login_status(self):
        """
        現在のブラウザセッションがログイン済みかどうかを確認する
        
        Returns:
            bool: ログイン済みの場合はTrue、未ログインの場合はFalse
            
        Note:
            このクラスにはログイン関連の機能が複数あり、一部重複しています：
            - _check_login_status: シンプルなログイン状態チェック
            - check_login_status: 詳細なログイン状態チェック（引数あり）
            - _perform_login: 低レベルのログイン処理実行
            - execute_login_if_needed: 条件付きログイン処理
            
            また、LoginPageクラスとの責任分担も不明確です。
            リファクタリング時には、ログイン関連の機能をLoginPageクラスに集約し、
            このクラスからは委譲するパターンに変更することで、責任の分離と重複の削減ができます。
        """
        try:
            # ユーザー情報セクションやアカウント情報が表示されているかどうかを確認
            if not self.browser or not self.browser.driver:
                logger.warning("ブラウザが初期化されていません")
                return False
                
            try:
                # まず、ログアウトリンクがあるかを確認
                selectors = [
                    "//a[contains(text(), 'ログアウト')]",
                    "//a[contains(text(), 'Logout')]",
                    "//button[contains(text(), 'ログアウト')]",
                    "//button[contains(text(), 'Logout')]",
                    "//div[contains(@class, 'logged-in')]",
                    "//div[contains(@class, 'user-info')]",
                    "//div[contains(@class, 'account-info')]"
                ]
                
                for selector in selectors:
                    try:
                        element = self.browser.driver.find_element(By.XPATH, selector)
                        if element.is_displayed():
                            logger.info(f"ログイン済み状態と判断しました（要素が見つかりました: {selector}）")
                            return True
                    except NoSuchElementException:
                        pass
            except Exception as inner_e:
                logger.debug(f"ログイン状態確認中のエラー（無視）: {str(inner_e)}")
            
            logger.info("未ログイン状態と判断しました")
            return False
            
        except Exception as e:
            logger.error(f"ログイン状態確認中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def _perform_login(self):
        """
        ログイン処理を実行する
        
        Returns:
            bool: ログイン成功時はTrue、失敗時はFalse
        """
        try:
            from src.modules.browser.login_page import LoginPage
            
            # ブラウザが初期化されていない場合は初期化
            if not self.browser:
                self.prepare_browser()
                
            # ログインページのインスタンスを作成
            self.login_page = LoginPage(browser=self.browser)
            
            # ログイン処理を実行
            login_success = self.login_page.execute_login_flow()
            
            if login_success:
                logger.info("ログインに成功しました")
                return True
            else:
                logger.error("ログインに失敗しました")
                return False
            
        except Exception as e:
            logger.error(f"ログイン処理中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _parse_step_elements(self, step_elements_text):
        """
        ステップ別取得要素セクションを解析する
        
        Args:
            step_elements_text (str): ステップ別取得要素セクションのテキスト
            
        Returns:
            dict: ステップ番号をキー、要素リストを値とする辞書
        """
        step_elements = {}
        current_step = None
        
        for line in step_elements_text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('ステップ'):
                # ステップ行の解析（例: "ステップ0:" -> 0）
                step_match = re.match(r'ステップ(\d+)[:：]', line)
                if step_match:
                    current_step = int(step_match.group(1))
                    step_elements[current_step] = []
            elif current_step is not None and line.startswith('-'):
                # 要素行の解析（例: "- コンバージョン属性　ボタン" -> "コンバージョン属性　ボタン"）
                element_name = line[1:].strip()
                step_elements[current_step].append(element_name)
                
        return step_elements

    def extract_elements_for_step(self, step_number, element_names, html_content):
        """
        指定されたステップの要素を抽出する
        
        Args:
            step_number (int): ステップ番号
            element_names (list): 要素名のリスト
            html_content (str): HTMLコンテンツ
            
        Returns:
            dict: 抽出された要素情報
        """
        logger.info(f"ステップ{step_number}の要素を抽出中: {', '.join(element_names)}")
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # スクリーンショット撮影
        self._save_screenshot(f"step{step_number}")
        
        # HTMLを保存
        url = self.browser.get_current_url()
        self._save_html_to_file(url, html_content, f"_step{step_number}")
        
        # 抽出処理（既存のextract_elements_from_pageを利用）
        return self.extract_elements_from_page(html_content, element_names)

    def _perform_operation(self, operation):
        """
        操作を実行する
        
        Args:
            operation (dict): 操作情報
            
        Note:
            このメソッドはperform_operationsメソッドと類似した機能を持っています。
            このメソッドはより単純な操作を実行し、perform_operationsはより詳細な処理と
            複数操作の順次実行を行います。リファクタリング時には両メソッドの統合を検討すべきです。
        """
        operation_text = operation.get('text', '')
        if not operation_text:
            return
            
        # 操作の種類を判断
        if 'クリック' in operation_text:
            element_name = operation_text.split('クリック')[0].strip()
            logger.info(f"「{element_name}」をクリックします")
            self._perform_click_operation({'element': element_name})
        elif '入力' in operation_text:
            parts = operation_text.split('入力')
            element_name = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ""
            logger.info(f"「{element_name}」に「{value}」を入力します")
            self._perform_input_operation({'element': element_name, 'value': value})

    def _wait_for_condition(self, condition):
        """
        待機条件に応じて待機する
        
        Args:
            condition (str): 待機条件
        """
        if not condition:
            # デフォルトの待機時間
            time.sleep(2)
            return
            
        logger.info(f"待機条件「{condition}」に基づいて待機します")
        
        if 'URL変化' in condition:
            # URL変化を待機
            current_url = self.browser.get_current_url()
            timeout = 30
            start_time = time.time()
            while time.time() - start_time < timeout:
                time.sleep(1)
                new_url = self.browser.get_current_url()
                if new_url != current_url:
                    logger.info(f"URLが変化しました: {new_url}")
                    self._wait_for_page_load()
                    return
                    
        elif 'ダイアログ表示' in condition:
            # ダイアログの表示を待機
            time.sleep(3)  # 単純な待機
            
        elif 'カレンダー表示' in condition:
            # カレンダーの表示を待機
            time.sleep(2)
            
        elif 'データ読み込み完了' in condition:
            # データの読み込み完了を待機
            self._wait_for_page_load()
            time.sleep(2)
        
        else:
            # その他の条件は一定時間待機
            time.sleep(3)

def parse_arguments():
    """
    コマンドライン引数を解析する
    
    Returns:
        argparse.Namespace: 解析された引数
    """
    parser = argparse.ArgumentParser(description='AIを使ったEBiS要素抽出ツール')
    parser.add_argument('--keep-browser', action='store_true', help='ブラウザを終了せずに保持する')
    parser.add_argument('--section', type=str, default='login', help='操作セクション名（例: login）')
    parser.add_argument('--save-cookies', action='store_true', help='実行後にCookieを保存する')
    parser.add_argument('--headless', action='store_true', help='ヘッドレスモードで実行する')
    parser.add_argument('--auto-login', action='store_true', help='自動的にログイン処理を行う')
    parser.add_argument('--use-cookies', action='store_true', help='保存済みのCookieを使用する')
    parser.add_argument('--clear-cookies', action='store_true', help='既存のCookieをクリアする')
    parser.add_argument('--force-login', action='store_true', help='強制的にログイン処理を行う')
    parser.add_argument('--dashboard-url', type=str, help='ダッシュボードURL（ログイン確認用）')
    
    return parser.parse_args()

def main():
    """
    メイン処理
    """
    # 引数解析
    args = parse_arguments()
    
    # インスタンス作成
    extractor = AIElementExtractor(
        keep_browser_open=args.keep_browser,
        use_cookies=args.use_cookies,
        headless=args.headless
    )
    
    try:
        # 自動ログインオプションが指定されている場合
        if args.auto_login:
            logger.info("自動ログインが指定されています")
            
            # ログイン処理
            success = extractor.execute_login_if_needed(
                login_section="login", 
                dashboard_url=args.dashboard_url,
                force_login=args.force_login,
                clear_cookies=args.clear_cookies
            )
            
            if not success:
                logger.error("自動ログイン処理に失敗しました")
                return 1
            
            logger.info("自動ログイン処理が完了しました")
            
            # セクションが指定されていないか、ログインセクションだけの場合は終了
            if not args.section or args.section.lower() == "login":
                logger.info("ログイン処理のみが要求されたため、追加の要素抽出は行わずに処理を終了します")
                return 0
        
        # 指定されたセクションを実行
        logger.info(f"セクション '{args.section}' の処理を開始します")
        success = extractor.execute_extraction(
            section_name=args.section
        )
        
        if not success:
            logger.error(f"セクション '{args.section}' の処理に失敗しました")
            return 1
            
        logger.info(f"セクション '{args.section}' の処理が完了しました")
        return 0
        
    except KeyboardInterrupt:
        logger.info("ユーザーによる中断が検出されました")
        return 1
        
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
        
    finally:
        # ブラウザを終了
        if not args.keep_browser and extractor.browser:
            extractor.browser.quit()

if __name__ == "__main__":
    sys.exit(main()) 