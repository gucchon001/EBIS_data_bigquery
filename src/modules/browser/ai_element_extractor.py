#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
指示ファイル（ai_selenium_direction.md）から操作を読み込み、
URLのページを解析して、HTMLをファイルに保存し、OpenAIを使って要素を抽出するツール
"""

import sys
import time
import argparse
import re
import json
import os
import pickle
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent.parent.parent)
sys.path.append(project_root)

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.modules.browser.browser import Browser
from src.modules.browser.login_page import EbisLoginPage
from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env

logger = get_logger(__name__)

class AIElementExtractor:
    """
    指示ファイルとURLから要素を抽出するクラス
    """
    
    def __init__(self, keep_browser_open=False, use_cookies=True, headless=False):
        """
        初期化
        
        Args:
            keep_browser_open (bool): ブラウザを継続して使用するかどうか
            use_cookies (bool): Cookieを使用してログイン状態を維持するかどうか
            headless (bool): ヘッドレスモードで実行するかどうか
        """
        # 環境変数を確実に読み込む
        env.load_env()
        logger.info("環境変数を読み込みました")
        
        # OpenAI APIキーが設定されているか確認
        self.openai_api_key = env.get_env_var("OPENAI_API_KEY", "")
        if self.openai_api_key:
            logger.info("OpenAI APIキーが設定されています")
        else:
            logger.error("OpenAI APIキーが設定されていません")
            raise ValueError("OpenAI APIキーが必要です")
        
        # 指示ファイルのパス
        self.direction_file = env.resolve_path("docs/ai_selenium_direction.md")
        if not os.path.exists(self.direction_file):
            logger.error(f"指示ファイルが見つかりません: {self.direction_file}")
            raise FileNotFoundError(f"指示ファイルが見つかりません: {self.direction_file}")
        
        # ページ保存ディレクトリの作成
        try:
            self.pages_dir = env.resolve_path("data/pages")
        except FileNotFoundError:
            # パスが存在しない場合は、プロジェクトルートから相対パスを作成
            project_root = env.get_project_root()
            self.pages_dir = os.path.join(project_root, "data", "pages")
            os.makedirs(self.pages_dir, exist_ok=True)
            logger.info(f"ページ保存ディレクトリを作成しました: {self.pages_dir}")
            
        # Cookie保存ディレクトリの作成
        try:
            self.cookies_dir = env.resolve_path("data/cookies")
        except FileNotFoundError:
            # パスが存在しない場合は、プロジェクトルートから相対パスを作成
            project_root = env.get_project_root()
            self.cookies_dir = os.path.join(project_root, "data", "cookies")
            os.makedirs(self.cookies_dir, exist_ok=True)
            logger.info(f"Cookie保存ディレクトリを作成しました: {self.cookies_dir}")
        
        # 設定
        self.keep_browser_open = keep_browser_open
        self.use_cookies = use_cookies
        self.headless = headless
        
        # ブラウザインスタンス
        self.browser = None
        
        # ログインモジュール
        self.login_page = None
        
        # 最後にログインしたドメイン
        self.last_login_domain = None
    
    def parse_direction_file(self, section_name):
        """
        指示ファイルから特定のセクションを解析する
        
        Args:
            section_name (str): セクション名（例: "## 1. login"）
            
        Returns:
            dict: セクションの内容
        """
        logger.info(f"指示ファイルから '{section_name}' セクションを解析します")
        
        try:
            with open(self.direction_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # セクション名が完全一致または部分一致する場合に対応
            if not section_name.startswith("##"):
                section_pattern = f"## .*{section_name}"
            else:
                section_pattern = section_name
            
            # セクションを正規表現で検索
            pattern = f"({section_pattern}.*?)(?=^## |\Z)"
            matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
            
            if not matches:
                logger.error(f"セクション '{section_name}' が見つかりません")
                return {}
            
            section_content = matches[0].strip()
            logger.info(f"セクション '{section_name}' の内容を取得しました")
            
            # セクションの内容を解析
            section_dict = self._parse_section_content(section_content)
            return section_dict
            
        except Exception as e:
            logger.error(f"指示ファイルの解析中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
    
    def _parse_section_content(self, content):
        """
        セクションの内容を解析する
        
        Args:
            content (str): セクションの内容
            
        Returns:
            dict: 解析結果
        """
        lines = content.split('\n')
        result = {
            'title': lines[0].strip(),
            'url': '',
            'elements': [],
            'operations': [],  # 操作手順を格納する配列を追加
            'login_code': '',  # ログインコードのパス
            'prerequisites': []  # 前提条件
        }
        
        current_section = ''
        
        for line in lines:
            line = line.strip()
            
            # 空行はスキップ
            if not line:
                continue
                
            # URLの解析
            if '--url' in line:
                # --urlの後の行を取得
                url_index = lines.index(line)
                if url_index + 1 < len(lines) and lines[url_index + 1].strip():
                    result['url'] = lines[url_index + 1].strip()
                continue
            
            # @付きのURLの解析
            if line.startswith('@'):
                result['url'] = line[1:].strip()
                continue
            
            # ログインコードの解析
            if '--ログインコード' in line:
                login_code_index = lines.index(line)
                if login_code_index + 1 < len(lines) and lines[login_code_index + 1].strip():
                    result['login_code'] = lines[login_code_index + 1].strip()
                continue
            
            # 前提操作の解析
            if '--前提操作' in line:
                prereq_index = lines.index(line)
                current_section = '前提操作'
                continue
            
            # セクション見出しの解析（--で始まる行）
            if line.startswith('--'):
                current_section = line[2:].strip()
                continue
            
            # 取得要素の解析
            if current_section == '取得要素' and not line.startswith('##') and not line.startswith('--'):
                result['elements'].append(line.strip())
            
            # 操作手順の解析（数字. で始まる行）
            if current_section == '操作手順' and not line.startswith('##') and not line.startswith('--'):
                # 番号付きリストの形式（例: 1. クリック）を解析
                operation_match = re.match(r'^\d+\.\s+(.+)$', line)
                if operation_match:
                    operation = operation_match.group(1).strip()
                    result['operations'].append(operation)
            
            # 前提操作の解析
            if current_section == '前提操作' and not line.startswith('##') and not line.startswith('--'):
                parts = line.split(' ')
                if len(parts) >= 2:
                    prereq_type = parts[0]
                    prereq_value = ' '.join(parts[1:])
                    result['prerequisites'].append({
                        'type': prereq_type,
                        'value': prereq_value
                    })
        
        # デバッグ
        logger.debug(f"解析結果: {result}")
        
        return result
    
    def get_page_content(self, url):
        """
        URLのページ内容を取得する（requestsとBeautifulSoupで解析）
        
        Args:
            url (str): 解析するURL
            
        Returns:
            str: ページのHTML
            BeautifulSoup: 解析結果
            str: 保存したファイルパス
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
    
    def get_page_content_with_selenium(self, url):
        """
        URLのページ内容をSeleniumで取得する（JavaScriptレンダリング後）
        
        Args:
            url (str): 解析するURL
            
        Returns:
            str: ページのHTML
            BeautifulSoup: 解析結果
            str: 保存したファイルパス
        """
        logger.info(f"Seleniumを使用してページ内容を取得します: {url}")
        
        try:
            # ブラウザを準備
            if not self.prepare_browser():
                return "", None, ""
            
            # 現在のURLを取得
            current_url = self.browser.driver.current_url
            
            # 同じURLの場合はページ遷移をスキップ（リロードする）
            if current_url == url:
                logger.info(f"すでに同じURL ({url}) にいるため、ページをリロードします")
                self.browser.driver.refresh()
            else:
                # 新しいURLに移動
                logger.info(f"URLに移動します: {url}")
                self.browser.navigate_to(url)
            
            # ページ読み込み完了を待機
            try:
                WebDriverWait(self.browser.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                logger.info("ページ読み込みが完了しました")
            except Exception as e:
                logger.warning(f"ページ読み込み待機中にタイムアウトしました: {str(e)}")
            
            # 追加の待機時間（JavaScriptの実行完了など）
            time.sleep(2)
            
            # ページのHTMLを取得
            html_content = self.browser.driver.page_source
            
            # BeautifulSoupで解析
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # ファイルに保存
            filepath = self._save_html_to_file(url, html_content)
            
            logger.info(f"Seleniumでページ内容の取得に成功しました: {len(html_content)} バイト")
            logger.info(f"HTMLファイルを保存しました: {filepath}")
            
            return html_content, soup, filepath
            
        except Exception as e:
            logger.error(f"Seleniumでのページ内容取得中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return "", None, ""
    
    def _save_html_to_file(self, url, html_content):
        """
        HTMLコンテンツをファイルに保存する
        
        Args:
            url (str): 解析したURL
            html_content (str): HTMLコンテンツ
            
        Returns:
            str: 保存したファイルパス
        """
        try:
            # URLからファイル名を生成
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace('.', '_')
            path = parsed_url.path.replace('/', '_').replace('.', '_')
            if not path:
                path = 'index'
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{domain}{path}_{timestamp}.html"
            filepath = os.path.join(self.pages_dir, filename)
            
            # ファイルに保存
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return filepath
            
        except Exception as e:
            logger.error(f"HTMLファイルの保存中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return ""
    
    def extract_elements_with_openai(self, direction, html_content, filepath):
        """
        OpenAI APIを使用して要素を抽出する
        
        Args:
            direction (dict): 指示内容
            html_content (str): ページのHTML
            filepath (str): 保存されたHTMLファイルのパス
            
        Returns:
            dict: 抽出された要素情報
        """
        logger.info("OpenAI APIを使用して要素を抽出します")
        
        # システムプロンプト
        system_prompt = """
あなたはウェブページ解析の専門家です。ユーザーから提供されたHTML要素を分析して、
要素情報を抽出してください。

以下の情報を各要素に対して特定してください：
1. 要素のタイプ（入力フィールド、ボタン、リンクなど）
2. 最適なセレクタ（ID、name、CSS、XPathの順で優先度が高い）
3. 要素の属性情報（name, placeholder, valueなど）
4. 表示テキスト（該当する場合）
5. Seleniumで要素を操作するための最適な方法

応答は必ずJSON形式で返してください。各要素の情報を含む配列として構造化してください。
"""

        # ユーザープロンプト
        user_prompt = f"""
# 指示内容
タイトル: {direction.get('title', '')}
URL: {direction.get('url', '')}

# 探したい要素
{json.dumps(direction.get('elements', []), ensure_ascii=False, indent=2)}

# HTMLファイル
HTMLファイルは {filepath} に保存されています。

# HTMLコンテンツ（一部）
```html
{html_content[:50000]}  # HTML内容が長い場合に備えて制限
```

# 必要な出力
上記の指示内容とHTMLコンテンツに基づいて、各要素の情報を抽出してJSON形式で返してください。
各要素について以下の情報を含めてください：
1. element_name: 要素の名前（指示内容の要素リストに対応）
2. element_type: 要素の種類（input, button, link, select など）
3. selectors: 要素を特定するためのセレクタ（複数の方法）
   - id: ID属性によるセレクタ（存在する場合）
   - name: name属性によるセレクタ（存在する場合）
   - css: CSSセレクタ（最も具体的で一意なもの）
   - xpath: XPath（最も具体的で一意なもの）
4. attributes: 要素の主要な属性（type, placeholder, valueなど）
5. visible_text: 表示テキスト（ボタンやリンクの場合）
6. recommendations: Seleniumでの操作方法の推奨事項

レスポンスは必ず以下のようなJSON形式にしてください:
```json
{{
  "elements": [
    {{
      "element_name": "アカウントID入力フィールド",
      "element_type": "input",
      "selectors": {{
        "id": "account_key",
        "name": "account_key",
        "css": "#account_key",
        "xpath": "//input[@id='account_key']"
      }},
      "attributes": {{
        "type": "text",
        "placeholder": "アカウントID"
      }},
      "visible_text": "",
      "recommendations": "WebDriverWait と presence_of_element_located を使用し、テキストを送信する"
    }},
    ...
  ]
}}
```
"""

        try:
            # OpenAI APIを呼び出す
            import openai
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=2500,
                response_format={"type": "json_object"}
            )
            
            # 生成された応答
            response_content = response.choices[0].message.content
            
            # JSONとして解析
            try:
                extracted_elements = json.loads(response_content)
                logger.info(f"要素の抽出に成功しました: {len(extracted_elements.get('elements', []))} 個の要素が見つかりました")
                return extracted_elements
            except json.JSONDecodeError as e:
                logger.error(f"OpenAI応答のJSON解析に失敗しました: {str(e)}")
                logger.debug(f"応答内容: {response_content}")
                return {"elements": []}
            
        except Exception as e:
            logger.error(f"OpenAI APIによる要素抽出中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"elements": []}
    
    def log_extracted_elements(self, extracted_elements):
        """
        抽出された要素情報をログに出力する
        
        Args:
            extracted_elements (dict): 抽出された要素情報
        """
        elements = extracted_elements.get('elements', [])
        
        if not elements:
            logger.warning("抽出された要素がありません")
            return
        
        logger.info(f"===== 抽出された要素 ({len(elements)}個) =====")
        
        for i, element in enumerate(elements, 1):
            logger.info(f"要素 {i}: {element.get('element_name', 'Unknown')}")
            logger.info(f"  - タイプ: {element.get('element_type', 'Unknown')}")
            
            selectors = element.get('selectors', {})
            logger.info(f"  - セレクタ:")
            for selector_type, selector_value in selectors.items():
                if selector_value:
                    logger.info(f"    - {selector_type}: {selector_value}")
            
            attributes = element.get('attributes', {})
            if attributes:
                logger.info(f"  - 属性:")
                for attr_name, attr_value in attributes.items():
                    logger.info(f"    - {attr_name}: {attr_value}")
            
            visible_text = element.get('visible_text', '')
            if visible_text:
                logger.info(f"  - 表示テキスト: {visible_text}")
            
            recommendations = element.get('recommendations', '')
            if recommendations:
                logger.info(f"  - 推奨操作: {recommendations}")
            
            logger.info("-----")
    
    def perform_operations(self, operations):
        """
        指示された操作を順番に実行する
        
        Args:
            operations (list): 実行する操作のリスト
            
        Returns:
            bool: 全ての操作が成功した場合はTrue、失敗した場合はFalse
        """
        if not operations:
            logger.info("実行する操作はありません")
            return True
        
        logger.info(f"操作手順を実行します（{len(operations)}ステップ）")
        
        try:
            # ブラウザが準備されているか確認
            if not self.browser or not self.browser.driver:
                logger.error("ブラウザが初期化されていません")
                return False
            
            # 各操作を順番に実行
            for i, operation in enumerate(operations, 1):
                logger.info(f"操作 {i}/{len(operations)}: {operation}")
                
                # スクリーンショットを撮影（操作前）
                screenshot_path = f"operation_{i}_before.png"
                self.browser.save_screenshot(screenshot_path)
                
                # 操作タイプを判定
                if "クリック" in operation.lower():
                    self._perform_click_operation(operation)
                elif "入力" in operation.lower():
                    self._perform_input_operation(operation)
                elif "選択" in operation.lower():
                    self._perform_select_operation(operation)
                elif "待機" in operation.lower():
                    self._perform_wait_operation(operation)
                else:
                    logger.warning(f"未対応の操作です: {operation}")
                
                # 操作後に少し待機
                time.sleep(2)
                
                # スクリーンショットを撮影（操作後）
                screenshot_path = f"operation_{i}_after.png"
                self.browser.save_screenshot(screenshot_path)
            
            logger.info("全ての操作が完了しました")
            return True
            
        except Exception as e:
            logger.error(f"操作の実行中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # エラー時のスクリーンショット
            self.browser.save_screenshot("operation_error.png")
            
            return False
    
    def _perform_click_operation(self, operation):
        """
        クリック操作を実行する
        
        Args:
            operation (str): 操作内容（例: "設定メニューをクリック"）
        """
        # 操作内容からクリックする要素を特定
        element_name = operation.replace("クリック", "").strip()
        if "を" in element_name:
            element_name = element_name.split("を")[0].strip()
            
        logger.info(f"'{element_name}' 要素をクリックします")
        
        try:
            # テキストで要素を検索
            wait = WebDriverWait(self.browser.driver, 10)
            
            # 様々な方法で要素を検索
            try:
                # リンクテキスト
                element = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, element_name)))
            except:
                try:
                    # 部分一致リンクテキスト
                    element = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, element_name)))
                except:
                    try:
                        # XPathで要素を検索
                        element = wait.until(EC.element_to_be_clickable((
                            By.XPATH, 
                            f"//button[contains(text(), '{element_name}')] | "
                            f"//a[contains(text(), '{element_name}')] | "
                            f"//*[contains(@title, '{element_name}')] | "
                            f"//*[contains(@aria-label, '{element_name}')] | "
                            f"//*[contains(@alt, '{element_name}')]"
                        )))
                    except:
                        # CSSセレクタで要素を検索
                        element = wait.until(EC.element_to_be_clickable((
                            By.CSS_SELECTOR, 
                            f"[title*='{element_name}'], [aria-label*='{element_name}'], [alt*='{element_name}']"
                        )))
            
            # 要素が見つかったらクリック
            element.click()
            logger.info(f"'{element_name}' 要素のクリックに成功しました")
            
        except Exception as e:
            logger.error(f"'{element_name}' 要素のクリックに失敗しました: {str(e)}")
            # JavaScriptでのクリックを試みる
            try:
                logger.info(f"JavaScriptを使用して '{element_name}' 要素のクリックを試みます")
                elements = self.browser.driver.find_elements(By.XPATH, 
                    f"//button[contains(text(), '{element_name}')] | "
                    f"//a[contains(text(), '{element_name}')] | "
                    f"//*[contains(@title, '{element_name}')] | "
                    f"//*[contains(@aria-label, '{element_name}')] | "
                    f"//*[contains(@alt, '{element_name}')]"
                )
                
                if elements:
                    self.browser.driver.execute_script("arguments[0].click();", elements[0])
                    logger.info(f"JavaScriptによる '{element_name}' 要素のクリックに成功しました")
                else:
                    logger.error(f"'{element_name}' 要素が見つかりませんでした")
            except Exception as js_e:
                logger.error(f"JavaScriptによる '{element_name}' 要素のクリックにも失敗しました: {str(js_e)}")
    
    def _perform_input_operation(self, operation):
        """
        入力操作を実行する
        
        Args:
            operation (str): 操作内容（例: "ユーザー名に「test」を入力"）
        """
        # 入力する要素名と入力値を抽出
        parts = operation.split("に")
        if len(parts) < 2:
            logger.error(f"入力操作の形式が不正です: {operation}")
            return
            
        element_name = parts[0].strip()
        input_value_part = parts[1].strip()
        
        # 入力値を「」または""から抽出
        input_value_match = re.search(r'[「""](.*?)[」""]', input_value_part)
        if not input_value_match:
            logger.error(f"入力値が見つかりません: {operation}")
            return
            
        input_value = input_value_match.group(1)
        logger.info(f"'{element_name}' 要素に '{input_value}' を入力します")
        
        try:
            # 様々な方法で要素を検索
            wait = WebDriverWait(self.browser.driver, 10)
            try:
                # name属性
                element = wait.until(EC.presence_of_element_located((By.NAME, element_name)))
            except:
                try:
                    # id属性
                    element = wait.until(EC.presence_of_element_located((By.ID, element_name)))
                except:
                    try:
                        # placeholder属性
                        element = wait.until(EC.presence_of_element_located((
                            By.XPATH, 
                            f"//input[@placeholder='{element_name}' or contains(@placeholder, '{element_name}')] | "
                            f"//textarea[@placeholder='{element_name}' or contains(@placeholder, '{element_name}')]"
                        )))
                    except:
                        # ラベルテキスト
                        element = wait.until(EC.presence_of_element_located((
                            By.XPATH, 
                            f"//label[text()='{element_name}' or contains(text(), '{element_name}')]"
                                f"/following::input[1] | "
                            f"//label[text()='{element_name}' or contains(text(), '{element_name}')]"
                                f"/following::textarea[1]"
                        )))
            
            # 要素が見つかったら入力
            element.clear()
            element.send_keys(input_value)
            logger.info(f"'{element_name}' 要素への入力に成功しました")
            
        except Exception as e:
            logger.error(f"'{element_name}' 要素への入力に失敗しました: {str(e)}")
    
    def _perform_select_operation(self, operation):
        """
        選択操作を実行する
        
        Args:
            operation (str): 操作内容（例: "ドロップダウンから「オプション1」を選択"）
        """
        # 選択する要素名と選択値を抽出
        parts = operation.split("から")
        if len(parts) < 2:
            logger.error(f"選択操作の形式が不正です: {operation}")
            return
            
        element_name = parts[0].strip()
        select_value_part = parts[1].strip()
        
        # 選択値を「」または""から抽出
        select_value_match = re.search(r'[「""](.*?)[」""]', select_value_part)
        if not select_value_match:
            logger.error(f"選択値が見つかりません: {operation}")
            return
            
        select_value = select_value_match.group(1)
        logger.info(f"'{element_name}' 要素から '{select_value}' を選択します")
        
        try:
            from selenium.webdriver.support.ui import Select
            
            # 様々な方法で要素を検索
            wait = WebDriverWait(self.browser.driver, 10)
            try:
                # name属性
                element = wait.until(EC.presence_of_element_located((By.NAME, element_name)))
                select = Select(element)
            except:
                try:
                    # id属性
                    element = wait.until(EC.presence_of_element_located((By.ID, element_name)))
                    select = Select(element)
                except:
                    try:
                        # ラベルテキスト
                        element = wait.until(EC.presence_of_element_located((
                            By.XPATH, 
                            f"//label[text()='{element_name}' or contains(text(), '{element_name}')]"
                                f"/following::select[1]"
                        )))
                        select = Select(element)
                    except:
                        logger.error(f"'{element_name}' の選択要素が見つかりません")
                        return
            
            # 可視テキストで選択を試みる
            try:
                select.select_by_visible_text(select_value)
                logger.info(f"'{element_name}' から '{select_value}' の選択に成功しました（可視テキスト）")
                return
            except:
                pass
                
            # 値で選択を試みる
            try:
                select.select_by_value(select_value)
                logger.info(f"'{element_name}' から '{select_value}' の選択に成功しました（値）")
                return
            except:
                pass
                
            # インデックスで選択を試みる（数値の場合）
            if select_value.isdigit():
                try:
                    select.select_by_index(int(select_value) - 1)  # 0ベースのインデックス
                    logger.info(f"'{element_name}' から '{select_value}' の選択に成功しました（インデックス）")
                    return
                except:
                    pass
            
            logger.error(f"'{element_name}' から '{select_value}' の選択に失敗しました")
            
        except Exception as e:
            logger.error(f"'{element_name}' からの選択操作に失敗しました: {str(e)}")
    
    def _perform_wait_operation(self, operation):
        """
        待機操作を実行する
        
        Args:
            operation (str): 操作内容（例: "5秒待機"）
        """
        # 待機時間を抽出
        wait_match = re.search(r'(\d+)\s*秒', operation)
        if not wait_match:
            logger.warning(f"待機時間が指定されていません。デフォルトの3秒を使用します: {operation}")
            wait_seconds = 3
        else:
            wait_seconds = int(wait_match.group(1))
        
        logger.info(f"{wait_seconds}秒間待機します")
        time.sleep(wait_seconds)
        logger.info(f"{wait_seconds}秒間の待機が完了しました")

    def _get_cookie_file_path(self, domain):
        """
        ドメイン用のCookieファイルパスを取得する
        
        Args:
            domain (str): ドメイン名
            
        Returns:
            str: Cookieファイルパス
        """
        # ドメイン名を正規化
        domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
        filename = f"cookies_{domain}.pkl"
        return os.path.join(self.cookies_dir, filename)
    
    def save_cookies(self, domain=None):
        """
        現在のブラウザのCookieを保存する
        
        Args:
            domain (str, optional): ドメイン名（指定しない場合は現在のURL）
            
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        if not self.browser or not self.browser.driver:
            logger.error("ブラウザが初期化されていません")
            return False
            
        try:
            # ドメインが指定されていない場合は現在のURLからドメインを取得
            if not domain:
                current_url = self.browser.get_current_url()
                from urllib.parse import urlparse
                domain = urlparse(current_url).netloc
                
            # Cookieを取得
            cookies = self.browser.driver.get_cookies()
            if not cookies:
                logger.warning(f"保存するCookieがありません: {domain}")
                return False
                
            # Cookieをファイルに保存
            cookie_path = self._get_cookie_file_path(domain)
            with open(cookie_path, 'wb') as f:
                pickle.dump(cookies, f)
                
            logger.info(f"{len(cookies)}個のCookieを保存しました: {cookie_path}")
            self.last_login_domain = domain
            return True
            
        except Exception as e:
            logger.error(f"Cookieの保存中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def load_cookies(self, domain):
        """
        保存されたCookieをブラウザにロードする
        
        Args:
            domain (str): ドメイン名
            
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        if not self.browser or not self.browser.driver:
            logger.error("ブラウザが初期化されていません")
            return False
            
        try:
            # ドメイン名の正規化
            normalized_domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
            logger.info(f"Cookieロード対象ドメイン: {normalized_domain}")
            
            # 関連するドメインのCookieも検索（サブドメインや関連ドメイン）
            related_domains = self._find_related_cookie_domains(normalized_domain)
            if not related_domains:
                logger.warning(f"関連するCookieが見つかりません: {normalized_domain}")
                return False
                
            # ドメインにアクセスしてからCookieをロード
            base_url = f"https://{normalized_domain}"
            logger.info(f"Cookieをロードするためにドメインにアクセスします: {base_url}")
            self.browser.navigate_to(base_url)
            time.sleep(2)  # ページロード待機時間を増加
            
            # 関連するすべてのドメインのCookieをロード
            loaded_cookies_count = 0
            success = False
            
            for cookie_domain, cookie_path in related_domains.items():
                try:
                    with open(cookie_path, 'rb') as f:
                        cookies = pickle.load(f)
                    
                    logger.info(f"Cookieファイルを読み込みました: {cookie_path} ({len(cookies)}個)")
                    
                    # 各Cookieを追加
                    for cookie in cookies:
                        try:
                            # セキュリティ対策を強化したCookieを作成
                            cookie_to_add = self._prepare_cookie_for_domain(cookie, normalized_domain)
                            
                            # Cookieをデバッグ出力
                            logger.debug(f"追加するCookie: {json.dumps(cookie_to_add)}")
                            
                            # 特定の問題のあるCookieは無視
                            if self._should_skip_cookie(cookie_to_add):
                                logger.debug(f"問題のあるCookieをスキップします: {cookie_to_add.get('name')}")
                                continue
                                
                            # Cookieを追加
                            self.browser.driver.add_cookie(cookie_to_add)
                            loaded_cookies_count += 1
                            success = True
                            
                        except Exception as cookie_e:
                            logger.warning(f"Cookieの追加に失敗しました: {str(cookie_e)} - {cookie.get('name')}")
                            logger.debug(f"問題のあるCookie: {json.dumps(cookie)}")
                            # 単一のCookieの失敗を無視して続行
                            continue
                            
                except Exception as file_e:
                    logger.warning(f"Cookieファイルの読み込みに失敗しました: {str(file_e)} - {cookie_path}")
                    # 単一のファイルの失敗を無視して続行
                    continue
            
            # ロード結果の確認
            if success:
                logger.info(f"合計{loaded_cookies_count}個のCookieをロードしました")
                
                # リロードして変更を適用
                self.browser.driver.refresh()
                time.sleep(1)
                
                return True
            else:
                logger.warning("有効なCookieをロードできませんでした")
                return False
                
        except Exception as e:
            logger.error(f"Cookieのロード中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    def _prepare_cookie_for_domain(self, cookie, target_domain):
        """
        Cookieをターゲットドメイン用に準備する
        
        Args:
            cookie (dict): 元のCookie
            target_domain (str): ターゲットドメイン
            
        Returns:
            dict: 準備されたCookie
        """
        # Cookieのディープコピーを作成
        prepared_cookie = cookie.copy()
        
        # ドメインの互換性を確保
        if 'domain' in prepared_cookie:
            original_domain = prepared_cookie['domain']
            if original_domain.startswith('.'):
                # ドメインが.で始まる場合は対応
                stripped_domain = original_domain[1:]
                if stripped_domain in target_domain or target_domain in stripped_domain:
                    # 主要なドメイン部分が一致する場合
                    prepared_cookie['domain'] = target_domain
            elif target_domain not in original_domain and original_domain not in target_domain:
                # 全く関係ないドメインの場合は修正
                prepared_cookie['domain'] = target_domain
            
            logger.debug(f"Cookie '{prepared_cookie.get('name')}' のドメインを調整: {original_domain} -> {prepared_cookie['domain']}")
            
        # 不要なフィールドを削除（エラーの原因になる可能性あり）
        fields_to_remove = ['expiry', 'expires', 'httpOnly', 'sameSite', 'secure']
        for field in fields_to_remove:
            if field in prepared_cookie:
                del prepared_cookie[field]
                
        return prepared_cookie
        
    def _should_skip_cookie(self, cookie):
        """
        問題のあるCookieをスキップするかどうかを判断
        
        Args:
            cookie (dict): 確認するCookie
            
        Returns:
            bool: スキップする場合はTrue
        """
        # 特定の問題のあるCookieをスキップ
        if not cookie.get('name') or not cookie.get('value'):
            return True
            
        if len(str(cookie.get('value', ''))) > 4000:  # 値が非常に長いCookie
            return True
            
        return False
        
    def _find_related_cookie_domains(self, domain):
        """
        関連するドメインのCookieファイルを検索
        
        Args:
            domain (str): 検索対象のドメイン
            
        Returns:
            dict: 関連ドメインとCookieファイルパスのマッピング
        """
        related_domains = {}
        
        # 指定されたドメインのCookieファイル
        domain_cookie_path = self._get_cookie_file_path(domain)
        if os.path.exists(domain_cookie_path):
            related_domains[domain] = domain_cookie_path
            
        # ドメインを分割して親ドメインを取得
        domain_parts = domain.split('.')
        
        # メインドメインを特定（例: example.comなど）
        if len(domain_parts) >= 2:
            main_domain = f"{domain_parts[-2]}.{domain_parts[-1]}"
            main_cookie_path = self._get_cookie_file_path(main_domain)
            if os.path.exists(main_cookie_path):
                related_domains[main_domain] = main_cookie_path
                
        # サブドメインのCookieも検索
        if len(domain_parts) > 2:
            for i in range(1, len(domain_parts) - 1):
                subdomain = '.'.join(domain_parts[i:])
                subdomain_cookie_path = self._get_cookie_file_path(subdomain)
                if os.path.exists(subdomain_cookie_path):
                    related_domains[subdomain] = subdomain_cookie_path
                    
        # 特定のドメインペアを追加（ebis.ne.jpとbishamon.ebis.ne.jp）
        if 'ebis.ne.jp' in domain:
            other_domains = ['id.ebis.ne.jp', 'bishamon.ebis.ne.jp']
            for other_domain in other_domains:
                if other_domain != domain:
                    other_cookie_path = self._get_cookie_file_path(other_domain)
                    if os.path.exists(other_cookie_path):
                        related_domains[other_domain] = other_cookie_path
                        
        logger.info(f"関連するCookieドメイン: {', '.join(related_domains.keys())}")
        return related_domains
    
    def check_login_status(self, login_url, dashboard_url):
        """
        ログイン状態をチェックする
        
        Args:
            login_url (str): ログインページのURL
            dashboard_url (str): ダッシュボードページのURL
            
        Returns:
            bool: ログイン済みの場合はTrue、未ログインの場合はFalse
        """
        if not self.browser or not self.browser.driver:
            logger.error("ブラウザが初期化されていません")
            return False
            
        try:
            # ダッシュボードページにアクセス
            logger.info(f"ログイン状態をチェックします: {dashboard_url}")
            self.browser.navigate_to(dashboard_url)
            
            # ページの読み込みを待機（十分な時間）
            time.sleep(5)
            
            # 現在のURLを取得
            current_url = self.browser.get_current_url()
            logger.info(f"現在のURL: {current_url}")
            
            # HTMLソースを取得して特定の要素や特徴をチェック
            page_source = self.browser.driver.page_source
            
            # ログイン判定方法1: URLベースのチェック
            if login_url in current_url:
                logger.info("URLベースのチェック: ログインページにリダイレクトされました（未ログイン状態）")
                return False
                
            # ログイン判定方法2: ダッシュボードURLが含まれているかチェック
            dashboard_domain = dashboard_url.replace("https://", "").replace("http://", "").split("/")[0]
            if dashboard_domain in current_url:
                logger.info("URLベースのチェック: ダッシュボードドメインが現在のURLに含まれています（ログイン済み状態）")
                
                # ログイン判定方法3: 特定のダッシュボード要素が存在するかチェック
                dashboard_elements = [
                    'ダッシュボード',
                    'ログアウト',
                    'マイアカウント',
                    'bishamon-header',
                    'account-menu'
                ]
                
                for element in dashboard_elements:
                    if element in page_source:
                        logger.info(f"要素ベースのチェック: ダッシュボード要素 '{element}' が見つかりました（ログイン済み状態）")
                        return True
            
            # ログイン判定方法4: ログイン特有の要素をチェック
            login_elements = [
                'loginForm',
                'ログインする',
                'ログインページ',
                'ユーザー名',
                'パスワード',
                'アカウントキー'
            ]
            
            for element in login_elements:
                if element in page_source:
                    logger.info(f"要素ベースのチェック: ログイン要素 '{element}' が見つかりました（未ログイン状態）")
                    return False
            
            # 判定できない場合は、URLに基づいて判断
            if 'id.ebis.ne.jp' in current_url:
                logger.info("URLベースのチェック（最終判断）: id.ebis.ne.jpドメインが現在のURLに含まれています（未ログイン状態）")
                return False
            elif 'bishamon.ebis.ne.jp' in current_url:
                logger.info("URLベースのチェック（最終判断）: bishamon.ebis.ne.jpドメインが現在のURLに含まれています（ログイン済み状態）")
                return True
            
            # 最後の保険として、ログインURLにリダイレクトされていなければログイン済みと判断
            logger.info("最終判断: 明確な判断材料がないため、URLに基づいて判断します")
            return login_url not in current_url
            
        except Exception as e:
            logger.error(f"ログイン状態のチェック中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def prepare_browser(self):
        """
        ブラウザを準備する（存在しない場合は作成）
        
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            if not self.browser:
                logger.info(f"ブラウザをセットアップします（ヘッドレスモード: {self.headless}）")
                self.browser = Browser(headless=self.headless)
                
            if not self.browser.driver:
                if not self.browser.setup():
                    logger.error("ブラウザのセットアップに失敗しました")
                    return False
            
            # ログインページのインスタンスを初期化
            if not self.login_page and self.browser:
                self.login_page = EbisLoginPage(self.browser)
            
            return True
            
        except Exception as e:
            logger.error(f"ブラウザの準備中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def execute_login_if_needed(self, login_section="login", dashboard_url=None, force_login=False, clear_cookies=False):
        """
        必要に応じてログイン処理を実行する
        
        Args:
            login_section (str): ログイン処理を含む指示ファイルのセクション名
            dashboard_url (str, optional): ダッシュボードページのURL
            force_login (bool): 強制的に再ログインするかどうか
            clear_cookies (bool): 既存のCookieをクリアするかどうか
            
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # ブラウザを準備
            if not self.prepare_browser():
                logger.error("ブラウザの準備に失敗しました")
                return False
            
            # 指示ファイルからログイン情報を取得
            login_info = self.parse_direction_file(login_section)
            if not login_info:
                logger.error(f"セクション '{login_section}' の解析に失敗しました")
                return False
            
            # ダッシュボードURLを取得（引数 > 設定ファイル > デフォルト値）
            if not dashboard_url:
                dashboard_url = env.get_config_value("Credentials", "url_dashboard", "https://bishamon.ebis.ne.jp/dashboard")
                logger.info(f"設定ファイルからダッシュボードURLを取得: {dashboard_url}")
                
            # 強制ログインが指定されているか、Cookieを使用しない場合は直接ログイン
            if force_login or not self.use_cookies:
                logger.info("専用ログインモジュールを使用してログインします")
                
                # ログイン処理を実行
                if not self.login_page:
                    self.login_page = EbisLoginPage(self.browser)
                
                login_success = self.login_page.execute_login_flow()
                if not login_success:
                    logger.error("ログイン処理に失敗しました")
                    return False
                
                logger.info("ログイン処理が完了しました")
                return True
            
        except Exception as e:
            logger.error(f"ログイン処理中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def save_elements_to_file(self, section_name, elements):
        """
        抽出された要素情報をJSONファイルとして保存する
        
        Args:
            section_name (str): セクション名
            elements (list): 抽出された要素のリスト
            
        Returns:
            str: 保存されたファイルパス、失敗した場合は空文字
        """
        try:
            import json
            import os
            
            # elements_dirの作成
            try:
                elements_dir = env.resolve_path("data/elements")
            except FileNotFoundError:
                # パスが存在しない場合は、プロジェクトルートから相対パスを作成
                project_root = env.get_project_root()
                elements_dir = os.path.join(project_root, "data", "elements")
            
            # ディレクトリが存在しない場合は作成
            os.makedirs(elements_dir, exist_ok=True)
            
            # セクション名だけのファイル名を使用（タイムスタンプなし）
            filename = f"{section_name}.json"
            filepath = os.path.join(elements_dir, filename)
            
            # detail_analytics セクションの場合、ログイン関連要素をフィルタリング
            if section_name == 'detail_analytics' and 'elements' in elements:
                # ログイン関連の要素名のリスト
                login_element_names = [
                    "アカウントID　入力フィールド",
                    "ログインID　入力フィールド",
                    "パスワード　入力フィールド",
                    "ログイン　クリックボタン"
                ]
                
                # ログイン関連要素を除外して新しいリストを作成
                filtered_elements = [
                    element for element in elements['elements'] 
                    if element.get('element_name') not in login_element_names
                ]
                
                # 元のデータ構造を維持しつつ、フィルタリングした要素を設定
                elements_copy = elements.copy()
                elements_copy['elements'] = filtered_elements
                elements = elements_copy
                
                logger.info(f"detail_analyticsセクションからログイン関連要素を除外しました")
            
            # 保存用のデータ構造を作成
            data = {
                "section": section_name,
                "elements": elements
            }
            
            # JSONファイルに保存
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"要素情報をJSONファイルに保存しました: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"要素情報の保存中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return ""
    
    def execute_extraction(self, section_name, save_cookies=False, keep_browser_open=None):
        """
        指示ファイルの解析から要素抽出までを行う
        
        Args:
            section_name (str): セクション名
            save_cookies (bool, optional): 実行後にCookieを保存するかどうか
            keep_browser_open (bool, optional): ブラウザを開いたままにするかどうか（指定しない場合はインスタンス変数を使用）
            
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # keep_browser_openの設定
            if keep_browser_open is None:
                keep_browser_open = self.keep_browser_open
                
            # 指示ファイルからセクションを解析
            direction = self.parse_direction_file(section_name)
            if not direction:
                logger.error(f"セクション '{section_name}' の解析に失敗しました")
                return False
            
            # 自動ログイン済みかどうかの確認
            is_already_logged_in = hasattr(self, 'login_page') and self.login_page is not None and self.browser and self.browser.driver
            
            # URLが指定されているか確認
            url = direction.get('url', '')
            if not url:
                logger.error("URLが指定されていません")
                return False
                
            # ログイン済み状態で分析系セクションの場合は、現在のURLが優先
            # セクション名が'detail_analytics'で始まり、ログイン済みの場合
            if section_name == 'detail_analytics' and is_already_logged_in:
                dashboard_url = env.get_config_value("Credentials", "url_dashboard", "https://bishamon.ebis.ne.jp/dashboard")
                current_url = self.browser.driver.current_url
                
                if dashboard_url and dashboard_url in current_url:
                    logger.info(f"ログイン済み状態のため、現在のURL（{current_url}）を使用します")
                    url = current_url
                else:
                    logger.info(f"ダッシュボードURLをセクションURLに設定します: {dashboard_url}")
                    url = dashboard_url
            
            # 前提条件の確認と実行
            prerequisites = direction.get('prerequisites', [])
            for prereq in prerequisites:
                prereq_type = prereq.get('type', '')
                prereq_value = prereq.get('value', '')
                
                if prereq_type == 'ログイン' and not is_already_logged_in:
                    logger.info(f"前提条件: ログイン処理が必要です - {prereq_value}")
                    # ログインモジュールを使用
                    if not self.login_page:
                        self.prepare_browser()
                    
                    login_success = self.login_page.execute_login_flow()
                    if not login_success:
                        logger.error("ログイン処理に失敗しました")
                        return False
                elif prereq_type == 'ログイン' and is_already_logged_in:
                    logger.info("すでにログイン済みのため、前提条件のログイン処理をスキップします")
            
            # ログインコードの確認と実行
            login_code = direction.get('login_code', '')
            if login_code and not is_already_logged_in:
                logger.info(f"ログインコードが指定されています: {login_code}")
                # ログインモジュールを使用
                if not self.login_page:
                    self.prepare_browser()
                
                login_success = self.login_page.execute_login_flow()
                if not login_success:
                    logger.error("ログイン処理に失敗しました")
                    return False
            elif login_code and is_already_logged_in:
                logger.info(f"ログインコードが指定されていますが、すでにログイン済みのためスキップします: {login_code}")
            
            # ページ内容を取得（Seleniumを使用）
            logger.info(f"ページ内容を取得します: {url}")
            html_content, soup, filepath = self.get_page_content_with_selenium(url)
            if not html_content:
                logger.error("ページ内容の取得に失敗しました")
                return False
            
            # 操作手順がある場合は実行
            operations = direction.get('operations', [])
            if operations:
                logger.info(f"{len(operations)}個の操作手順が見つかりました")
                if not self.perform_operations(operations):
                    logger.error("操作手順の実行に失敗しました")
                    return False
                
                # 操作後のページ内容を再取得
                logger.info("操作後のページ内容を取得します")
                html_content = self.browser.driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 更新されたHTMLを保存
                filepath = self._save_html_to_file(url, html_content)
                logger.info(f"操作後のHTMLファイルを保存しました: {filepath}")
            
            # OpenAI APIを使用して要素を抽出
            extracted_elements = self.extract_elements_with_openai(direction, html_content, filepath)
            if not extracted_elements:
                logger.error("要素の抽出に失敗しました")
                return False
            
            # 抽出された要素情報をログに出力
            self.log_extracted_elements(extracted_elements)
            
            # 抽出された要素をJSONファイルとして保存
            json_filepath = self.save_elements_to_file(section_name, extracted_elements)
            if json_filepath:
                logger.info(f"要素情報をファイルに保存しました: {json_filepath}")
            
            # Cookieを保存（オプション - 非推奨）
            if save_cookies:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                self.save_cookies(domain)
            
            logger.info(f"要素抽出が完了しました: {section_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"要素抽出中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        
        finally:
            # ブラウザを終了（オプション）
            if not keep_browser_open and self.browser:
                logger.info("ブラウザを終了します")
                self.browser.quit()
                self.browser = None
                self.login_page = None

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
            section_name=args.section,
            save_cookies=args.save_cookies,
            keep_browser_open=args.keep_browser
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