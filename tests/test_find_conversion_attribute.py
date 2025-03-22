# -*- coding: utf-8 -*-
"""
Seleniumで「コンバージョン属性」要素を見つけるテスト
HTMLファイルを読み込み、SeleniumでコンバージョンB属性要素を見つけられるかテストします。
"""

import os
import sys
import time
from pathlib import Path
import json

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.utils.environment import EnvironmentUtils as env
from src.utils.logging_config import get_logger
from src.modules.browser.browser import Browser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# openaiパッケージをインポート（要素の特定に使用）
import openai

logger = get_logger(__name__)

class ConversionAttributeFindTest:
    """コンバージョン属性要素を見つけるテストクラス"""
    
    def __init__(self, headless=False):
        """初期化"""
        # 環境変数を読み込む
        env.load_env()
        
        # APIキーを取得
        self.api_key = env.get_env_var("OPENAI_API_KEY", "")
        if not self.api_key:
            logger.error("OpenAI APIキーが設定されていません")
            raise ValueError("OpenAI APIキーが設定されていません")
            
        # AIモデルを設定ファイルから取得
        self.ai_model = env.get_config_value("API", "ai_model", "gpt-3.5-turbo")
        logger.info(f"使用するAIモデル: {self.ai_model}")
        
        # OpenAI クライアントの設定
        openai.api_key = self.api_key
        
        # Browserインスタンスの作成
        logger.info("ブラウザを初期化します")
        self.browser = Browser(headless=headless)
        if not self.browser.setup():
            logger.error("ブラウザのセットアップに失敗しました")
            raise RuntimeError("ブラウザのセットアップに失敗しました")
    
    def read_html_file(self, file_path):
        """HTMLファイルを読み込む"""
        try:
            # ファイルパスを絶対パスに変換
            absolute_path = env.resolve_path(file_path)
            logger.info(f"HTMLファイルを読み込みます: {absolute_path}")
            
            # ファイルの存在確認
            if not os.path.exists(absolute_path):
                logger.error(f"ファイルが存在しません: {absolute_path}")
                return None
                
            # ファイルを読み込む
            with open(absolute_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
                
            logger.info(f"HTMLファイルを読み込みました（{len(html_content)} 文字）")
            return html_content, absolute_path
            
        except Exception as e:
            logger.error(f"HTMLファイルの読み込み中にエラーが発生しました: {str(e)}")
            return None, None
    
    def get_element_xpath_with_openai(self, html_content, element_name="コンバージョン属性"):
        """OpenAI APIを使用して要素のXPathを取得する"""
        try:
            logger.info(f"OpenAI APIを使用して「{element_name}」要素のXPathを取得します")
            
            # OpenAI APIにリクエストを送信
            response = openai.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": "あなたはHTMLの解析とXPath生成のエキスパートです。指定された要素を見つけるための最適なXPathを提供してください。複数のXPathがある場合は、より確実に要素を見つけられる複数の候補を提供してください。"},
                    {"role": "user", "content": f"以下のHTMLから「{element_name}」という名前またはテキストを持つボタンや項目の要素を見つけるための最適なXPathを提供してください。XPathは複数提案してください。XPathのみを返し、説明は不要です。\n\n{html_content[:15000]}"}
                ],
                max_tokens=500
            )
            
            # レスポンスからXPathを抽出
            message = response.choices[0].message.content
            logger.info(f"APIレスポンス: {message}")
            
            # 複数のXPathをリストにする（単純な分割で取得）
            xpaths = [xpath.strip() for xpath in message.strip().split('\n') if xpath.strip().startswith('//')]
            
            if not xpaths:
                logger.warning(f"有効なXPathが見つかりませんでした。APIレスポンス: {message}")
                # バックアップXPathを提供
                return [
                    f"//*[contains(text(), '{element_name}')]",
                    f"//a[contains(text(), '{element_name}')]",
                    f"//button[contains(text(), '{element_name}')]",
                    f"//div[contains(text(), '{element_name}')]",
                    f"//span[contains(text(), '{element_name}')]"
                ]
            
            logger.info(f"取得したXPath候補: {xpaths}")
            return xpaths
            
        except Exception as e:
            logger.error(f"XPath取得中にエラーが発生しました: {str(e)}")
            # エラー時のバックアップXPath
            return [f"//*[contains(text(), '{element_name}')]"]
    
    def find_element_with_selenium(self, html_file_path, xpaths, timeout=10):
        """Seleniumで要素を見つける"""
        found_element = None
        found_xpath = None
        
        try:
            # HTMLファイルをブラウザで開く
            file_url = f"file:///{html_file_path}"
            logger.info(f"ブラウザでHTMLファイルを開きます: {file_url}")
            
            if not self.browser.navigate_to(file_url):
                logger.error("HTMLファイルへのナビゲーションに失敗しました")
                return None, None
            
            # スクリーンショットを保存
            screenshot_path = "screenshot_before_find.png"
            self.browser.save_screenshot(screenshot_path)
            logger.info(f"スクリーンショットを保存しました: {screenshot_path}")
            
            # 各XPathで要素を検索
            wait = WebDriverWait(self.browser.driver, timeout)
            
            for xpath in xpaths:
                try:
                    logger.info(f"XPathで要素を検索します: {xpath}")
                    element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                    
                    if element:
                        element_text = element.text
                        element_tag = element.tag_name
                        element_attrs = {
                            "class": element.get_attribute("class"),
                            "id": element.get_attribute("id"),
                            "href": element.get_attribute("href")
                        }
                        
                        logger.info(f"要素が見つかりました: {element_tag}, テキスト: {element_text}, 属性: {element_attrs}")
                        
                        # スクリーンショットで要素をハイライト
                        self.browser.execute_script(
                            "arguments[0].style.border='3px solid red'", element)
                        self.browser.save_screenshot("element_found.png")
                        
                        found_element = element
                        found_xpath = xpath
                        break
                        
                except Exception as e:
                    logger.warning(f"XPath '{xpath}' では要素が見つかりませんでした: {str(e)}")
            
            if not found_element:
                logger.error("指定されたすべてのXPathで要素が見つかりませんでした")
                
                # 追加のバックアップ検索: テキストの一部に一致するリンクを探す
                try:
                    partial_text_xpath = "//a[contains(text(), '属性')]"
                    logger.info(f"部分一致でリンクを検索します: {partial_text_xpath}")
                    elements = self.browser.driver.find_elements(By.XPATH, partial_text_xpath)
                    
                    if elements:
                        for el in elements:
                            logger.info(f"部分一致要素が見つかりました: {el.text}")
                            if "コンバージョン" in el.text:
                                logger.info(f"コンバージョン属性要素が見つかりました: {el.text}")
                                self.browser.execute_script(
                                    "arguments[0].style.border='3px solid blue'", el)
                                self.browser.save_screenshot("partial_match_found.png")
                                found_element = el
                                found_xpath = partial_text_xpath
                                break
                except Exception as e:
                    logger.error(f"部分一致での検索中にエラーが発生しました: {str(e)}")
            
            return found_element, found_xpath
            
        except Exception as e:
            logger.error(f"要素検索中にエラーが発生しました: {str(e)}")
            return None, None
        
    def cleanup(self):
        """リソースのクリーンアップ"""
        if self.browser:
            self.browser.quit()
            logger.info("ブラウザを終了しました")

def run_test(html_file_path, element_name="コンバージョン属性", headless=False):
    """テストを実行する"""
    tester = None
    
    try:
        print(f"「{element_name}」要素を見つけるテストを開始します...")
        
        tester = ConversionAttributeFindTest(headless=headless)
        
        # HTMLファイルを読み込む
        html_content, absolute_path = tester.read_html_file(html_file_path)
        if not html_content:
            print("HTMLファイルの読み込みに失敗しました。")
            return False
        
        # OpenAI APIを使用してXPathを取得
        xpaths = tester.get_element_xpath_with_openai(html_content, element_name)
        
        # Seleniumで要素を検索
        element, found_xpath = tester.find_element_with_selenium(absolute_path, xpaths)
        
        if element:
            print(f"\n✅ テスト成功: 「{element_name}」要素が見つかりました！")
            print(f"- 使用したXPath: {found_xpath}")
            print(f"- 要素のテキスト: {element.text}")
            print(f"- 要素のタグ: {element.tag_name}")
            print(f"- 要素のクラス: {element.get_attribute('class')}")
            print(f"- 要素のID: {element.get_attribute('id')}")
            print(f"- 要素のhref: {element.get_attribute('href')}")
            print("\n要素のクリックもテストできますが、現在のテストではクリックは実行していません。")
            return True
        else:
            print(f"\n❌ テスト失敗: 「{element_name}」要素が見つかりませんでした。")
            print("試したXPathの候補:")
            for xpath in xpaths:
                print(f"- {xpath}")
            return False
            
    except Exception as e:
        print(f"テスト実行中にエラーが発生しました: {str(e)}")
        return False
        
    finally:
        if tester:
            tester.cleanup()

if __name__ == "__main__":
    # コマンドライン引数からHTMLファイルのパスと要素名を取得
    if len(sys.argv) > 2:
        html_file_path = sys.argv[1]
        element_name = sys.argv[2]
    elif len(sys.argv) > 1:
        html_file_path = sys.argv[1]
        element_name = "コンバージョン属性"
    else:
        html_file_path = "data/pages/bishamon_ebis_ne_jp_20250321_075218.html"
        element_name = "コンバージョン属性"
    
    # ヘッドレスモードを無効化（実際のブラウザを表示）
    headless = False
    
    success = run_test(html_file_path, element_name, headless)
    sys.exit(0 if success else 1) 