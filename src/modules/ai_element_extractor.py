import os
import sys
import re
import time
import json
import logging
import argparse
from bs4 import BeautifulSoup
import requests
import traceback
from datetime import datetime

# browser.pyのインポート
from src.modules.browser.browser import Browser
from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env

# ロガー設定
logger = get_logger(__name__)

class AIElementExtractor:
    """
    AIを使用したWebページ要素抽出ツール
    
    ディレクションファイルに基づいてWebページから要素を抽出するクラス。
    browser.pyのBrowserクラスを使用してブラウザ操作を行い、OpenAI APIを使用して
    要素の抽出を行います。
    """
    
    def __init__(self, direction_file=None, section=None, openai_api_key=None):
        """
        AIElementExtractorの初期化
        
        Args:
            direction_file (str): ディレクションファイルのパス
            section (str): ディレクションファイル内のセクション名
            openai_api_key (str): OpenAI APIキー
        """
        # 環境変数の設定
        self.openai_api_key = openai_api_key or env.get_env_var("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI APIキーが設定されていません")
        
        # ブラウザインスタンスの初期化
        self.browser = None
        
        # ディレクトリ設定
        self.output_dir = env.resolve_path("data/output")
        self.screenshot_dir = env.resolve_path("data/screenshots")
        self.pages_dir = env.resolve_path("data/pages")
        
        # ディレクトリ作成
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.screenshot_dir, exist_ok=True)
        os.makedirs(self.pages_dir, exist_ok=True)
        
        # ディレクションの初期化
        self.direction = {}
        if direction_file and section:
            self.direction = self.parse_direction_file(direction_file, section)
            
    def prepare_browser(self, headless=None):
        """
        ブラウザを準備する
        
        Args:
            headless (bool, optional): ヘッドレスモードで実行するかどうか。Noneの場合はsettings.iniから読み込む
            
        Returns:
            bool: ブラウザの準備が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("ブラウザを準備しています...")
            
            # セレクタファイルのパスを取得
            selectors_path = env.resolve_path("config/selectors.csv")
            if os.path.exists(selectors_path):
                logger.info(f"セレクタファイルを使用します: {selectors_path}")
            else:
                selectors_path = None
                logger.warning("セレクタファイルが見つかりません。直接XPathを使用します。")
            
            # Browser インスタンスを作成（headlessがNoneの場合はsettings.iniから自動判定）
            self.browser = Browser(selectors_path=selectors_path, headless=headless)
            
            # ブラウザのセットアップ
            setup_result = self.browser.setup()
            if not setup_result:
                logger.error("ブラウザのセットアップに失敗しました")
                return False
                
            logger.info("✅ ブラウザの準備が完了しました")
            return True
            
        except Exception as e:
            logger.error(f"ブラウザの準備中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
            
    def parse_direction_file(self, file_path, section):
        """
        ディレクションファイルを解析する
        
        Args:
            file_path (str): ディレクションファイルのパス
            section (str): ファイル内のセクション名
            
        Returns:
            dict: 解析結果の辞書
        """
        try:
            logger.info(f"ディレクションファイルを解析しています: {file_path}, セクション: {section}")
            
            # ファイルの存在確認
            if not os.path.exists(file_path):
                logger.error(f"ディレクションファイルが見つかりません: {file_path}")
                return {}
                
            # ファイル読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # セクションを検索（Markdown形式: ## 数字. セクション名）
            pattern = rf"## \d+\. {re.escape(section)}(.*?)(?:## \d+\.|$)"
            match = re.search(pattern, content, re.DOTALL)
            
            if not match:
                logger.error(f"セクション '{section}' が見つかりませんでした")
                return {}
                
            section_content = match.group(1).strip()
            
            # セクション内容を解析
            result = {
                'overview': '',
                'url': '',
                'prerequisites': '',
                'operations': [],
                'elements_to_extract': []
            }
            
            # 各項目を抽出
            overview_match = re.search(r'--概要\s*(.*?)(?:--|\Z)', section_content, re.DOTALL)
            if overview_match:
                result['overview'] = overview_match.group(1).strip()
                
            url_match = re.search(r'--url\s*(.*?)(?:--|\Z)', section_content, re.DOTALL)
            if url_match:
                result['url'] = url_match.group(1).strip()
                
            prerequisites_match = re.search(r'--前提操作\s*(.*?)(?:--|\Z)', section_content, re.DOTALL)
            if prerequisites_match:
                result['prerequisites'] = prerequisites_match.group(1).strip()
                
            # 操作手順の抽出
            operations_match = re.search(r'--操作手順\s*(.*?)(?:--|\Z)', section_content, re.DOTALL)
            if operations_match:
                operations_content = operations_match.group(1).strip()
                # 番号付きの操作リストを解析
                operation_lines = operations_content.split('\n')
                for line in operation_lines:
                    line = line.strip()
                    if re.match(r'^\d+\.', line):  # 数字で始まる行を操作として認識
                        operation = line.split('.', 1)[1].strip()
                        result['operations'].append(operation)
            
            # 取得要素の抽出
            elements_match = re.search(r'--取得要素\s*(.*?)(?:--|\Z)', section_content, re.DOTALL)
            if elements_match:
                elements_content = elements_match.group(1).strip()
                elements_lines = elements_content.split('\n')
                for line in elements_lines:
                    element = line.strip()
                    if element and not element.startswith('--'):
                        result['elements_to_extract'].append(element)
            
            logger.info(f"ディレクションファイルの解析が完了しました: URL={result['url']}, 操作数={len(result['operations'])}, 抽出要素数={len(result['elements_to_extract'])}")
            return result
            
        except Exception as e:
            logger.error(f"ディレクションファイルの解析中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return {}
            
    def get_page_content_with_selenium(self, url, filename=None):
        """
        Seleniumを使用してページのコンテンツを取得する
        
        Args:
            url (str): 取得するページのURL
            filename (str, optional): 保存するHTMLファイル名
            
        Returns:
            tuple: (ページのHTML, 保存されたHTMLファイルパス)
        """
        try:
            logger.info(f"Seleniumを使用してページコンテンツを取得します: {url}")
            
            # ブラウザが初期化されていない場合は初期化
            if not self.browser:
                logger.info("ブラウザが初期化されていないため、初期化します")
                if not self.prepare_browser():
                    raise Exception("ブラウザの準備に失敗しました")
            
            # URLに移動
            navigate_result = self.browser.navigate_to(url)
            if not navigate_result:
                logger.error(f"URLへの移動に失敗しました: {url}")
                return None, None
            
            # ページが完全に読み込まれるまで少し待機
            time.sleep(3)
            
            # スクリーンショットを取得
            screenshot_path = None
            if filename:
                screenshot_filename = f"{filename.replace('.html', '')}_screenshot.png"
                if self.browser.save_screenshot(screenshot_filename):
                    screenshot_path = os.path.join(self.browser.screenshot_dir, screenshot_filename)
                    logger.info(f"スクリーンショットを保存しました: {screenshot_path}")
            
            # ページソースを取得
            page_source = self.browser.get_page_source()
            
            # ページソースをファイルに保存
            html_path = None
            if filename:
                if not filename.endswith('.html'):
                    filename += '.html'
                
                html_path = os.path.join(self.pages_dir, filename)
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                logger.info(f"HTMLを保存しました: {html_path}")
            
            return page_source, html_path
            
        except Exception as e:
            error_message = f"ページコンテンツの取得中にエラーが発生しました: {str(e)}"
            logger.error(error_message)
            logger.error(traceback.format_exc())
            
            # エラー発生時にスクリーンショットを取得
            if self.browser:
                self.browser.save_screenshot(f"error_get_page_content_{int(time.time())}.png")
            
            return None, None
            
    def extract_elements_with_openai(self, html_content, elements_to_extract):
        """
        OpenAI APIを使用してHTMLから要素を抽出する
        
        Args:
            html_content (str): 抽出対象のHTML
            elements_to_extract (list): 抽出する要素のリスト
            
        Returns:
            list: 抽出された要素のリスト。各要素は {'name': 要素名, 'xpath': xpath} の形式
        """
        try:
            logger.info(f"OpenAI APIを使用して要素を抽出します: {elements_to_extract}")
            
            if not html_content:
                error_message = "HTMLコンテンツが空です"
                logger.error(error_message)
                return []
            
            # HTML内容の前処理
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 不要なスクリプトやスタイルを削除してHTMLを軽量化
            for script in soup(["script", "style"]):
                script.extract()
            
            # HTMLを整形してテキスト抽出
            text = soup.get_text()
            
            # 抽出するコンテンツの準備
            content_to_analyze = text[:10000]  # 最初の10000文字だけを使用（APIの制限を考慮）
            
            # OpenAI APIを使用して要素を抽出
            import openai
            
            openai.api_key = self.openai_api_key
            
            # プロンプトの準備
            prompt = f"""
            以下のHTMLコンテンツから次の要素を抽出してください:
            {', '.join(elements_to_extract)}
            
            各要素のXPathを特定し、以下の形式でJSON配列で返してください:
            [
                {{"name": "要素名1", "xpath": "要素のXPath1"}},
                {{"name": "要素名2", "xpath": "要素のXPath2"}},
                ...
            ]
            
            要素が見つからない場合はxpathを空文字にしてください。
            
            HTMLコンテンツ:
            {content_to_analyze}
            """
            
            # APIリクエスト
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたはHTMLコンテンツから特定の要素を抽出してXPathを特定するAIアシスタントです。抽出結果はJSON配列形式で返してください。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # レスポンスの解析
            result_text = response.choices[0].message.content
            
            # JSON部分を抽出
            json_match = re.search(r'```json(.*?)```', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                json_str = result_text
            
            # 余分な文字を削除してJSONパース
            json_str = re.sub(r'^```|```$', '', json_str)
            
            try:
                result_list = json.loads(json_str)
                # 結果が辞書の場合はリストに変換
                if isinstance(result_list, dict):
                    converted_list = []
                    for name, xpath in result_list.items():
                        converted_list.append({"name": name, "xpath": xpath})
                    result_list = converted_list
            except json.JSONDecodeError:
                # JSONパースに失敗した場合は独自に解析してリスト形式で返す
                result_list = []
                for element in elements_to_extract:
                    result_list.append({"name": element, "xpath": ""})
            
            logger.info(f"要素抽出が完了しました: {result_list}")
            return result_list
            
        except Exception as e:
            error_message = f"要素抽出中にエラーが発生しました: {str(e)}"
            logger.error(error_message)
            logger.error(traceback.format_exc())
            return []

    def perform_operations(self, operations):
        """
        ディレクションファイルに指定された操作を実行する
        
        Args:
            operations (list): 実行する操作のリスト
            
        Returns:
            bool: すべての操作が成功した場合はTrue
        """
        try:
            logger.info(f"ページ操作を実行します: {len(operations)}個の操作")
            
            # ブラウザが初期化されていない場合は初期化
            if not self.browser:
                logger.info("ブラウザが初期化されていないため、初期化します")
                if not self.prepare_browser():
                    raise Exception("ブラウザの準備に失敗しました")
            
            for i, operation in enumerate(operations):
                logger.info(f"操作 {i+1}/{len(operations)}: {operation}")
                
                # 操作タイプを解析
                if operation.startswith("click:"):
                    target = operation[len("click:"):].strip()
                    success = self._perform_click_operation(target)
                elif operation.startswith("input:"):
                    parts = operation[len("input:"):].strip().split("=", 1)
                    if len(parts) != 2:
                        logger.error(f"無効な入力操作: {operation}")
                        return False
                    target, value = parts
                    success = self._perform_input_operation(target.strip(), value.strip())
                elif operation.startswith("select:"):
                    parts = operation[len("select:"):].strip().split("=", 1)
                    if len(parts) != 2:
                        logger.error(f"無効な選択操作: {operation}")
                        return False
                    target, value = parts
                    success = self._perform_select_operation(target.strip(), value.strip())
                elif operation.startswith("wait:"):
                    timeout_str = operation[len("wait:"):].strip()
                    try:
                        timeout = int(timeout_str)
                        success = self._perform_wait_operation(timeout)
                    except ValueError:
                        logger.error(f"無効な待機時間: {timeout_str}")
                        return False
                elif operation == "take_screenshot":
                    success = self._perform_screenshot_operation()
                # 日本語形式の操作を解析
                elif "クリック" in operation:
                    # クリック操作（例：「詳細分析　ボタン　クリック」）
                    element_name = operation.split("　クリック")[0].strip()
                    logger.info(f"日本語形式のクリック操作を検出: 対象={element_name}")
                    success = self._perform_click_operation(element_name)
                elif "入力" in operation:
                    # 入力操作（例：「検索ボックス　に　キーワード　を入力」）
                    if "　に　" in operation and "　を入力" in operation:
                        parts = operation.split("　に　")
                        if len(parts) == 2:
                            target = parts[0].strip()
                            value = parts[1].split("　を入力")[0].strip()
                            logger.info(f"日本語形式の入力操作を検出: 対象={target}, 値={value}")
                            success = self._perform_input_operation(target, value)
                        else:
                            logger.error(f"無効な日本語入力操作: {operation}")
                            success = False
                    else:
                        logger.error(f"無効な日本語入力操作: {operation}")
                        success = False
                elif "選択" in operation:
                    # 選択操作（例：「プルダウン　から　オプション1　を選択」）
                    if "　から　" in operation and "　を選択" in operation:
                        parts = operation.split("　から　")
                        if len(parts) == 2:
                            target = parts[0].strip()
                            value = parts[1].split("　を選択")[0].strip()
                            logger.info(f"日本語形式の選択操作を検出: 対象={target}, 値={value}")
                            success = self._perform_select_operation(target, value)
                        else:
                            logger.error(f"無効な日本語選択操作: {operation}")
                            success = False
                    else:
                        logger.error(f"無効な日本語選択操作: {operation}")
                        success = False
                elif "待機" in operation:
                    # 待機操作（例：「5秒　待機」）
                    try:
                        timeout_str = operation.split("　待機")[0].strip()
                        if "秒" in timeout_str:
                            timeout_str = timeout_str.replace("秒", "").strip()
                        timeout = int(timeout_str)
                        logger.info(f"日本語形式の待機操作を検出: {timeout}秒")
                        success = self._perform_wait_operation(timeout)
                    except (ValueError, IndexError):
                        logger.error(f"無効な日本語待機操作: {operation}")
                        success = False
                else:
                    logger.warning(f"未対応の操作タイプ: {operation}")
                    success = False
                
                if not success:
                    logger.error(f"操作 '{operation}' の実行に失敗しました")
                    return False
                
                # 操作間の待機
                time.sleep(1)
            
            logger.info("すべての操作が正常に完了しました")
            return True
            
        except Exception as e:
            error_message = f"操作の実行中にエラーが発生しました: {str(e)}"
            logger.error(error_message)
            logger.error(traceback.format_exc())
            return False
    
    def _perform_click_operation(self, target):
        """
        要素をクリックする操作を実行する
        
        Args:
            target (str): クリックする要素のセレクタ
            
        Returns:
            bool: 操作が成功した場合はTrue
        """
        try:
            logger.info(f"クリック操作を実行します: {target}")
            
            # XPath形式かどうかをチェック
            if target.startswith("//"):
                # XPath形式のセレクタを直接使用
                from selenium.webdriver.common.by import By
                elements = self.browser.find_elements(By.XPATH, target)
                
                if not elements:
                    logger.error(f"クリック対象の要素が見つかりません: {target}")
                    return False
                
                # 最初の要素をクリック
                element = elements[0]
                
                # 要素が画面内に表示されるようにスクロール
                self.browser.scroll_to_element(element)
                time.sleep(1)  # スクロール完了を待機
                
                # クリック実行
                element.click()
                logger.info(f"✓ 要素のクリックに成功しました: {target}")
                
            else:
                # 予め定義されたセレクタグループ・名前から要素を取得
                group, name = target.split(".", 1) if "." in target else ("default", target)
                
                # Browser.click_elementメソッドを使用
                click_result = self.browser.click_element(group, name)
                if not click_result:
                    # JavaScriptによるクリックも試行
                    click_result = self.browser.click_element(group, name, use_javascript=True)
                    if not click_result:
                        logger.error(f"要素のクリックに失敗しました: {target}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"クリック操作中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            
            # エラー発生時にスクリーンショットを取得
            self.browser.save_screenshot(f"error_click_{target.replace('.', '_')}.png")
            
            return False
    
    def _perform_input_operation(self, target, value):
        """
        要素に値を入力する操作を実行する
        
        Args:
            target (str): 入力対象の要素のセレクタ
            value (str): 入力する値
            
        Returns:
            bool: 操作が成功した場合はTrue
        """
        try:
            logger.info(f"入力操作を実行します: {target} = {value}")
            
            # XPath形式かどうかをチェック
            if target.startswith("//"):
                # XPath形式のセレクタを直接使用
                from selenium.webdriver.common.by import By
                elements = self.browser.find_elements(By.XPATH, target)
                
                if not elements:
                    logger.error(f"入力対象の要素が見つかりません: {target}")
                    return False
                
                # 最初の要素に入力
                element = elements[0]
                
                # 要素が画面内に表示されるようにスクロール
                self.browser.scroll_to_element(element)
                time.sleep(1)  # スクロール完了を待機
                
                # 入力欄をクリア
                element.clear()
                
                # 値を入力
                element.send_keys(value)
                logger.info(f"✓ 要素への入力に成功しました: {target} = {value}")
                
            else:
                # 予め定義されたセレクタグループ・名前から要素を取得
                group, name = target.split(".", 1) if "." in target else ("default", target)
                
                # 要素を取得
                element = self.browser.get_element(group, name)
                if not element:
                    logger.error(f"入力対象の要素が見つかりません: {target}")
                    return False
                
                # 要素が画面内に表示されるようにスクロール
                self.browser.scroll_to_element(element)
                time.sleep(1)  # スクロール完了を待機
                
                # 入力欄をクリア
                element.clear()
                
                # 値を入力
                element.send_keys(value)
                logger.info(f"✓ 要素への入力に成功しました: {target} = {value}")
            
            return True
            
        except Exception as e:
            logger.error(f"入力操作中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            
            # エラー発生時にスクリーンショットを取得
            self.browser.save_screenshot(f"error_input_{target.replace('.', '_')}.png")
            
            return False
    
    def _perform_select_operation(self, target, value):
        """
        セレクトボックスから値を選択する操作を実行する
        
        Args:
            target (str): 選択対象のセレクトボックスのセレクタ
            value (str): 選択する値
            
        Returns:
            bool: 操作が成功した場合はTrue
        """
        try:
            from selenium.webdriver.support.ui import Select
            
            logger.info(f"選択操作を実行します: {target} = {value}")
            
            # XPath形式かどうかをチェック
            if target.startswith("//"):
                # XPath形式のセレクタを直接使用
                from selenium.webdriver.common.by import By
                elements = self.browser.find_elements(By.XPATH, target)
                
                if not elements:
                    logger.error(f"選択対象の要素が見つかりません: {target}")
                    return False
                
                # 最初の要素を選択
                element = elements[0]
                
            else:
                # 予め定義されたセレクタグループ・名前から要素を取得
                group, name = target.split(".", 1) if "." in target else ("default", target)
                
                # 要素を取得
                element = self.browser.get_element(group, name)
                if not element:
                    logger.error(f"選択対象の要素が見つかりません: {target}")
                    return False
            
            # 要素が画面内に表示されるようにスクロール
            self.browser.scroll_to_element(element)
            time.sleep(1)  # スクロール完了を待機
            
            # Selectオブジェクトを作成
            select = Select(element)
            
            # valueがインデックスかどうかをチェック
            if value.isdigit():
                # インデックスによる選択
                select.select_by_index(int(value))
            else:
                # テキストまたは値による選択を試行
                try:
                    select.select_by_visible_text(value)
                except:
                    try:
                        select.select_by_value(value)
                    except:
                        logger.error(f"値 '{value}' が選択肢に見つかりません")
                        return False
            
            logger.info(f"✓ 要素からの選択に成功しました: {target} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"選択操作中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            
            # エラー発生時にスクリーンショットを取得
            self.browser.save_screenshot(f"error_select_{target.replace('.', '_')}.png")
            
            return False
    
    def _perform_wait_operation(self, seconds):
        """
        指定された秒数だけ待機する操作を実行する
        
        Args:
            seconds (int): 待機する秒数
            
        Returns:
            bool: 常にTrue
        """
        logger.info(f"{seconds}秒間待機します")
        time.sleep(seconds)
        return True
    
    def _perform_screenshot_operation(self):
        """
        スクリーンショットを取得する操作を実行する
        
        Returns:
            bool: 操作が成功した場合はTrue
        """
        try:
            screenshot_filename = f"screenshot_{int(time.time())}.png"
            result = self.browser.save_screenshot(screenshot_filename)
            
            if result:
                logger.info(f"スクリーンショットを取得しました: {screenshot_filename}")
                return True
            else:
                logger.error("スクリーンショットの取得に失敗しました")
                return False
                
        except Exception as e:
            logger.error(f"スクリーンショット取得中にエラーが発生しました: {str(e)}")
            return False
    
    def run(self):
        """
        ディレクションに基づいて要素抽出処理を実行する
        
        Returns:
            dict: 抽出された要素の辞書
        """
        try:
            logger.info("AIElementExtractor の実行を開始します")
            
            # ディレクションが設定されているか確認
            if not self.direction:
                logger.error("ディレクションが設定されていません")
                return {}
            
            # URLの取得
            url = self.direction.get('url')
            if not url:
                logger.error("URLが指定されていません")
                return {}
            
            # 操作リストの取得
            operations = self.direction.get('operations', [])
            
            # 抽出要素リストの取得
            extract_elements = self.direction.get('elements_to_extract', [])
            if not extract_elements:
                logger.warning("抽出する要素が指定されていません")
            
            # タイムスタンプを含むファイル名を生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"page_{timestamp}.html"
            
            # ブラウザの準備
            if not self.browser:
                logger.info("ブラウザが初期化されていないため、初期化します")
                if not self.prepare_browser():
                    logger.error("ブラウザの準備に失敗しました")
                    return {}
            
            # 前提操作の実行
            prerequisites = self.direction.get('prerequisites')
            if prerequisites:
                logger.info(f"前提操作を実行します: {prerequisites}")
                
                # ログイン処理を実行
                if "login_page.py" in prerequisites.lower():
                    logger.info("ログイン処理を実行します")
                    try:
                        # LoginPageクラスをインポート
                        from src.modules.browser.login_page import LoginPage
                        
                        # ログインページインスタンスを作成し、ログイン実行
                        login_page = LoginPage(browser=self.browser)
                        login_result = login_page.execute_login_flow()
                        
                        if not login_result:
                            logger.error("ログイン処理に失敗しました")
                            return {}
                            
                        logger.info("✅ ログイン処理が完了しました")
                    except Exception as e:
                        logger.error(f"ログイン処理中にエラーが発生しました: {str(e)}")
                        logger.error(traceback.format_exc())
                        return {}
            
            try:
                # 操作を実行
                if operations:
                    logger.info(f"{len(operations)}個の操作を実行します")
                    
                    # URLに移動
                    html_result = self.get_page_content_with_selenium(url, filename)
                    if not html_result or not html_result[0]:  # タプルの最初の要素（HTML内容）を確認
                        logger.error("ページコンテンツの取得に失敗しました")
                        return {}
                    
                    html_content = html_result[0]  # HTMLコンテンツを取得
                    
                    # 操作を実行
                    operations_result = self.perform_operations(operations)
                    if not operations_result:
                        logger.error("操作の実行に失敗しました")
                        return {}
                    
                    # 操作実行後のページコンテンツを再取得
                    html_result = self.get_page_content_with_selenium(
                        self.browser.get_current_url(), 
                        f"page_after_operations_{timestamp}.html"
                    )
                    
                    if not html_result or not html_result[0]:
                        logger.error("操作後のページコンテンツの取得に失敗しました")
                        return {}
                        
                    html_content = html_result[0]  # 操作後のHTMLコンテンツを取得
                else:
                    # 操作がない場合は、直接URLからコンテンツを取得
                    html_result = self.get_page_content_with_selenium(url, filename)
                    if not html_result or not html_result[0]:
                        logger.error("ページコンテンツの取得に失敗しました")
                        return {}
                        
                    html_content = html_result[0]  # HTMLコンテンツを取得
                
                # 要素を抽出
                if extract_elements:
                    extracted_data = self.extract_elements_with_openai(html_content, extract_elements)
                    
                    # 抽出結果をJSONファイルに保存
                    json_path = os.path.join(self.output_dir, f"extracted_data_{timestamp}.json")
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(extracted_data, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"抽出データをJSONファイルに保存しました: {json_path}")
                    return extracted_data
                else:
                    logger.warning("抽出する要素が指定されていないため、抽出処理をスキップします")
                    return {}
            
            finally:
                # ブラウザを終了
                self.quit()
            
        except Exception as e:
            error_message = f"AIElementExtractor の実行中にエラーが発生しました: {str(e)}"
            logger.error(error_message)
            logger.error(traceback.format_exc())
            
            # ブラウザを終了
            self.quit(error_message, e)
            
            return {}
    
    def quit(self, error_message=None, exception=None, context=None):
        """
        リソースを解放する
        
        Args:
            error_message (str, optional): エラーメッセージ
            exception (Exception, optional): 例外オブジェクト
            context (dict, optional): エラーコンテキスト
        """
        if self.browser:
            self.browser.quit(error_message, exception, context)
            self.browser = None
            logger.info("ブラウザを終了しました")


def main():
    """
    コマンドライン引数を解析して AIElementExtractor を実行するメイン関数
    """
    parser = argparse.ArgumentParser(description='AIを使用したWebページ要素抽出ツール')
    parser.add_argument('--direction', '-d', required=True, help='ディレクションファイルのパス')
    parser.add_argument('--section', '-s', required=True, help='ディレクションファイル内のセクション名')
    parser.add_argument('--api-key', '-k', help='OpenAI APIキー（設定されていない場合は環境変数から読み込み）')
    parser.add_argument('--headless', action='store_true', help='ヘッドレスモードでブラウザを実行する')
    parser.add_argument('--no-headless', action='store_true', help='ブラウザを表示モードで実行する')
    parser.add_argument('--verbose', '-v', action='store_true', help='詳細ログを出力する')
    
    args = parser.parse_args()
    
    # ログレベルの設定
    if args.verbose:
        logging.getLogger('src').setLevel(logging.DEBUG)
    
    # ヘッドレスモードの設定（コマンドラインで明示的に指定された場合のみ使用）
    headless = None
    if args.headless and args.no_headless:
        logger.warning("--headlessと--no-headlessの両方が指定されました。--headlessを優先します。")
        headless = True
    elif args.headless:
        headless = True
    elif args.no_headless:
        headless = False
    
    try:
        # AIElementExtractor インスタンスの作成
        extractor = AIElementExtractor(
            direction_file=args.direction,
            section=args.section,
            openai_api_key=args.api_key
        )
        
        # ブラウザの準備（コマンドラインで指定された場合はその設定を使用）
        if not extractor.prepare_browser(headless=headless):
            logger.error("ブラウザの準備に失敗しました")
            return 1
        
        # 実行
        result = extractor.run()
        
        if result:
            logger.info(f"抽出結果: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return 0
        else:
            logger.error("要素の抽出に失敗しました")
            return 1
            
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {str(e)}")
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main()) 