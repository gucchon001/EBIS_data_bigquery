#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
実際のHTMLファイルを対象にした要素検索テスト
EBiSページのHTMLから特定の要素を検索する処理を検証します
"""

import os
import sys
import glob
import time
from pathlib import Path
import traceback
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
import re

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent)
sys.path.append(project_root)

class RealHTMLTest:
    """実際のHTMLファイルを使用した要素検索テスト"""
    
    def __init__(self):
        """初期化"""
        self.html_files = []
        self.current_file = None
        self.results = {
            "成功": 0,
            "失敗": 0,
            "テスト数": 0
        }
        
        # HTMLファイルを検索
        self.find_html_files()
        
        # ブラウザをセットアップ
        self.setup_browser()
    
    def find_html_files(self):
        """data/pagesディレクトリからHTMLファイルを検索"""
        html_dir = os.path.join(project_root, "data", "pages")
        
        if not os.path.exists(html_dir):
            print(f"HTMLディレクトリが見つかりません: {html_dir}")
            return
        
        # HTMLファイルを検索
        pattern = os.path.join(html_dir, "*.html")
        self.html_files = glob.glob(pattern)
        
        # dashboard_htmlファイルとid_ebis_ne_jpファイルを分類
        self.dashboard_htmls = [f for f in self.html_files if "dashboard" in f]
        self.login_htmls = [f for f in self.html_files if "id_ebis_ne_jp" in f]
        
        print(f"HTMLファイルが見つかりました: {len(self.html_files)}個")
        print(f"ダッシュボードHTML: {len(self.dashboard_htmls)}個")
        print(f"ログインページHTML: {len(self.login_htmls)}個")
    
    def setup_browser(self):
        """ブラウザをセットアップ"""
        try:
            # Chrome オプション設定
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')  # ヘッドレスモード
            
            # ChromeDriverのセットアップ
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            print("ブラウザのセットアップが完了しました")
            return True
            
        except Exception as e:
            print(f"ブラウザのセットアップ中にエラーが発生: {e}")
            print(traceback.format_exc())
            return False
    
    def load_html_file(self, html_path):
        """HTMLファイルを読み込み、ブラウザに表示"""
        try:
            self.current_file = html_path
            file_name = os.path.basename(html_path)
            
            print(f"\n=== HTMLファイル読み込み: {file_name} ===")
            
            # HTMLファイルの内容を読み込み
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # ファイルパスをURLに変換
            absolute_path = os.path.abspath(html_path)
            file_url = f"file:///{absolute_path}"
            
            # ブラウザで開く
            self.driver.get(file_url)
            
            # ページが読み込まれるのを待機
            time.sleep(1)
            
            # BeautifulSoupで解析
            self.soup = BeautifulSoup(html_content, 'html.parser')
            
            print(f"HTMLファイルを読み込みました: {file_name}")
            print(f"タイトル: {self.driver.title}")
            return True
            
        except Exception as e:
            print(f"HTMLファイル読み込み中にエラーが発生: {e}")
            print(traceback.format_exc())
            return False
    
    def test_xpath_search(self, xpath, name, expected_result=True):
        """XPath検索のテスト"""
        self.results["テスト数"] += 1
        try:
            print(f"\nテスト: {name}")
            print(f"XPath: {xpath}")
            
            # タイムアウト設定を短くして高速にテスト
            element = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            
            if element:
                element_text = element.text.strip() if element.text else "[テキストなし]"
                print(f"✅ 成功: 要素が見つかりました: {element_text}")
                
                # 要素が見つかった場所をハイライト
                self.driver.execute_script(
                    "arguments[0].setAttribute('style', 'background-color: yellow; border: 2px solid red;');", 
                    element
                )
                self.results["成功"] += 1
                return element
                
        except (NoSuchElementException, TimeoutException, StaleElementReferenceException):
            print("❌ 失敗: 要素が見つかりませんでした")
            if expected_result:
                self.results["失敗"] += 1
            return None
        except Exception as e:
            print(f"❌ エラー: {e}")
            if expected_result:
                self.results["失敗"] += 1
            return None
    
    def test_find_element_with_fallback(self, text, element_types=["button", "*"], expected_result=True):
        """フォールバック機能を使った要素検索テスト"""
        print(f"\n=== フォールバック検索テスト: '{text}' ===")
        self.results["テスト数"] += 1
        
        # 1. 完全一致を試す
        for element_type in element_types:
            xpath = f"//{element_type}[contains(text(), '{text}')]"
            element = self.test_xpath_search(xpath, f"'{text}'の完全一致検索 ({element_type})", False)
            if element:
                if expected_result:
                    self.results["成功"] += 1
                return element
        
        # 2. スペースで分割して最初の部分で検索
        if " " in text:
            parts = text.split(" ")
            first_part = parts[0]
            for element_type in element_types:
                xpath = f"//{element_type}[contains(text(), '{first_part}')]"
                element = self.test_xpath_search(xpath, f"'{first_part}'の部分一致検索 ({element_type})", False)
                if element:
                    if expected_result:
                        self.results["成功"] += 1
                    return element
        
        # 3. より緩い検索（テキストの一部が含まれる要素を探す）
        for part in text.split(" "):
            if len(part) > 2:  # 短すぎる部分は除外
                for element_type in element_types:
                    xpath = f"//{element_type}[contains(text(), '{part}')]"
                    element = self.test_xpath_search(xpath, f"'{part}'の部分一致検索 ({element_type})", False)
                    if element:
                        if expected_result:
                            self.results["成功"] += 1
                        return element
        
        # 4. classやidで検索
        keywords = ["btn", "button", "nav"]
        for keyword in keywords + text.split(" "):
            if len(keyword) > 2:
                for element_type in element_types:
                    # class属性で検索
                    xpath = f"//{element_type}[contains(@class, '{keyword}')]"
                    element = self.test_xpath_search(xpath, f"'{keyword}'のクラス検索 ({element_type})", False)
                    if element:
                        if expected_result:
                            self.results["成功"] += 1
                        return element
                    
                    # id属性で検索
                    xpath = f"//{element_type}[contains(@id, '{keyword}')]"
                    element = self.test_xpath_search(xpath, f"'{keyword}'のID検索 ({element_type})", False)
                    if element:
                        if expected_result:
                            self.results["成功"] += 1
                        return element
        
        # 要素が見つからなかった
        if expected_result:
            self.results["失敗"] += 1
            print(f"❌ すべての検索方法で要素が見つかりませんでした: {text}")
        return None

    def find_japanese_text_elements(self):
        """HTML内の日本語テキストを含む要素を探索"""
        print("\n=== 日本語テキスト要素探索 ===")
        
        # HTMLソースを取得
        html_source = self.driver.page_source
        
        # 日本語テキストを抽出するための正規表現パターン
        japanese_pattern = re.compile(r'[一-龠]+|[ぁ-ん]+|[ァ-ヴー]+')
        
        # BeautifulSoupで解析
        soup = BeautifulSoup(html_source, 'html.parser')
        
        # すべてのテキストノードを走査
        japanese_texts = []
        for text in soup.stripped_strings:
            if japanese_pattern.search(text):
                japanese_texts.append(text)
        
        # 最初の20個の日本語テキストを表示
        print(f"日本語テキストが見つかりました: {len(japanese_texts)}個")
        for i, text in enumerate(japanese_texts[:20]):
            print(f"{i+1}. {text[:50]}...")
        
        return japanese_texts
    
    def search_conversion_attribute_elements(self):
        """コンバージョン属性関連の要素を検索"""
        print("\n=== コンバージョン属性要素検索 ===")
        
        # 検索対象のキーワード
        keywords = [
            "コンバージョン属性",
            "詳細分析",
            "全トラフィック",
            "カレンダー",
            "期間指定",
            "適用",
            "ビュー",
            "エクスポート",
            "表を出力",
            "CSV"
        ]
        
        # 各キーワードで検索
        found_elements = {}
        for keyword in keywords:
            element = self.test_find_element_with_fallback(keyword, ["*"], False)
            if element:
                found_elements[keyword] = element
        
        # 結果を表示
        print(f"\n見つかったキーワード: {len(found_elements)}/{len(keywords)}")
        for keyword in keywords:
            status = "✅ 見つかりました" if keyword in found_elements else "❌ 見つかりませんでした"
            print(f"{keyword}: {status}")
        
        return found_elements
    
    def analyze_html_structure(self):
        """HTML構造を分析"""
        print("\n=== HTML構造分析 ===")
        
        # ボタン要素を探す
        buttons = self.driver.find_elements(By.XPATH, "//button")
        print(f"ボタン要素: {len(buttons)}個")
        
        # リンク要素を探す
        links = self.driver.find_elements(By.XPATH, "//a")
        print(f"リンク要素: {len(links)}個")
        
        # クラス属性を持つ要素を探す
        elements_with_class = self.driver.find_elements(By.XPATH, "//*[@class]")
        print(f"クラス属性を持つ要素: {len(elements_with_class)}個")
        
        # id属性を持つ要素を探す
        elements_with_id = self.driver.find_elements(By.XPATH, "//*[@id]")
        print(f"ID属性を持つ要素: {len(elements_with_id)}個")
        
        # iframeを探す
        iframes = self.driver.find_elements(By.XPATH, "//iframe")
        print(f"iframe要素: {len(iframes)}個")
        
        for i, iframe in enumerate(iframes):
            try:
                src = iframe.get_attribute("src")
                print(f"iframe {i+1}: src={src}")
            except:
                print(f"iframe {i+1}: 属性取得エラー")
        
        return {
            "buttons": len(buttons),
            "links": len(links),
            "elements_with_class": len(elements_with_class),
            "elements_with_id": len(elements_with_id),
            "iframes": len(iframes)
        }
    
    def test_dashboard_file(self):
        """ダッシュボードHTMLファイルをテスト"""
        if not self.dashboard_htmls:
            print("ダッシュボードHTMLファイルが見つかりません")
            return
        
        # 最新のダッシュボードHTMLを使用
        latest_file = max(self.dashboard_htmls, key=os.path.getctime)
        self.load_html_file(latest_file)
        
        # 日本語テキスト要素を探索
        japanese_texts = self.find_japanese_text_elements()
        
        # HTML構造を分析
        structure = self.analyze_html_structure()
        
        # コンバージョン属性関連の要素を検索
        conversion_elements = self.search_conversion_attribute_elements()
        
        return {
            "japanese_texts": japanese_texts,
            "structure": structure,
            "conversion_elements": conversion_elements
        }
    
    def run_tests(self):
        """テストを実行"""
        print("=== 実際のHTMLファイルを使用したテスト開始 ===")
        
        # ダッシュボードファイルをテスト
        self.test_dashboard_file()
        
        # テスト結果を表示
        print("\n=== テスト結果 ===")
        print(f"総テスト数: {self.results['テスト数']}")
        print(f"成功: {self.results['成功']}")
        print(f"失敗: {self.results['失敗']}")
        
        success_rate = (self.results['成功'] / self.results['テスト数']) * 100 if self.results['テスト数'] > 0 else 0
        print(f"成功率: {success_rate:.1f}%")
    
    def cleanup(self):
        """クリーンアップ処理"""
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()
            print("ブラウザを終了しました")


def main():
    """メイン処理"""
    tester = RealHTMLTest()
    try:
        tester.run_tests()
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main() 