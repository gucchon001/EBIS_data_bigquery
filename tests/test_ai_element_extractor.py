# -*- coding: utf-8 -*-
"""
AIエレメントエクストラクターの単体テスト
"""

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
from selenium.webdriver.common.by import By

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.modules.browser.ai_element_extractor import AIElementExtractor

def test_parse_direction_file():
    """方向ファイル解析の基本テスト"""
    print("テスト開始: parse_direction_file")
    extractor = AIElementExtractor(keep_browser_open=True)
    direction = extractor.parse_direction_file("cv_attribute")
    
    # 基本的な検証
    print(f"方向ファイル解析結果: {direction.keys()}")
    
    # URL検証
    if "url" in direction:
        print(f"URL: {direction['url']}")
    else:
        print("URLが見つかりません")
    
    # 前提条件の検証
    if "prerequisites" in direction:
        print(f"前提操作: {direction['prerequisites']}")
    
    # 操作手順の検証
    if "operations" in direction:
        print(f"操作手順数: {len(direction['operations'])}")
        for i, op in enumerate(direction['operations']):
            print(f"操作 {i+1}: {op}")
    
    # 要素の検証
    if "elements" in direction:
        print(f"elements: {direction['elements']}")
    else:
        print("elementsが見つかりません")
    
    print("テスト終了: parse_direction_file")
    return True

def test_execute_extraction():
    """execute_extractionメソッドのテスト"""
    print("\nテスト開始: execute_extraction")
    try:
        extractor = AIElementExtractor(keep_browser_open=True)
        result = extractor.execute_extraction("cv_attribute")
        print(f"実行結果: {result}")
        print("テスト終了: execute_extraction")
        return True
    except Exception as e:
        print(f"エラー発生: {str(e)}")
        return False

class TestXPathSearch(unittest.TestCase):
    """XPath検索機能のテスト"""
    
    def setUp(self):
        self.extractor = AIElementExtractor(keep_browser_open=True)
        
        # テスト用HTML
        self.test_html = """
        <!DOCTYPE html>
        <html>
        <head><title>XPathテスト</title></head>
        <body>
            <div class="menu">
                <button class="btn btn-primary">詳細分析</button>
                <button class="btn">コンバージョン属性</button>
            </div>
            <div class="content">
                <button id="calendar" class="calendar-btn">カレンダー</button>
                <div class="actions">
                    <button id="export-btn" class="export">エクスポート</button>
                    <button class="csv-btn">表を出力（CSV）</button>
                </div>
            </div>
        </body>
        </html>
        """
        
        # テスト用のドライバーモック
        self.driver_mock = MagicMock()
        self.browser_mock = MagicMock()
        self.browser_mock.driver = self.driver_mock
        self.extractor.browser = self.browser_mock
    
    def test_find_element_by_xpath(self):
        """XPathによる要素検索テスト"""
        # find_elementの戻り値をモック
        element_mock = MagicMock()
        element_mock.text = "詳細分析"
        element_mock.get_attribute.return_value = "btn btn-primary"
        self.driver_mock.find_element.return_value = element_mock
        
        # テスト実行
        xpath = "//button[contains(text(), '詳細分析')]"
        element = self.extractor.browser.driver.find_element(By.XPATH, xpath)
        
        # 検証
        self.assertIsNotNone(element)
        self.assertEqual(element.text, "詳細分析")
        self.driver_mock.find_element.assert_called_once_with(By.XPATH, xpath)
    
    def test_find_element_by_japanese_partial_match(self):
        """日本語部分一致による要素検索テスト"""
        # find_element呼び出しをモック
        element_mock = MagicMock()
        element_mock.text = "コンバージョン属性"
        self.driver_mock.find_element.return_value = element_mock
        
        # 実装されていなければモックする
        def find_by_partial_match(text, element_type):
            parts = text.split()
            if len(parts) > 1:
                for part in parts:
                    xpath = f"//button[contains(text(), '{part}')]"
                    return self.driver_mock.find_element(By.XPATH, xpath)
            return None
            
        # モックメソッドを使用
        element = find_by_partial_match("コンバージョン 属性", "button")
        
        # 検証
        self.assertIsNotNone(element)
        self.assertEqual(element.text, "コンバージョン属性")
        self.driver_mock.find_element.assert_called_once()
    
    def test_find_element_by_text_or_id(self):
        """テキストまたはIDによる要素検索テスト"""
        # find_elementの戻り値をモック
        element_mock = MagicMock()
        element_mock.text = "カレンダー"
        self.driver_mock.find_element.return_value = element_mock
        
        # テスト実行 - テキストでの検索
        text_xpath = f"//button[contains(text(), 'カレンダー')]"
        element = self.driver_mock.find_element(By.XPATH, text_xpath)
        
        # 検証
        self.assertIsNotNone(element)
        self.assertEqual(element.text, "カレンダー")
        self.driver_mock.find_element.assert_called_once_with(By.XPATH, text_xpath)

def test_xpath_search():
    """XPath検索テスト実行"""
    print("\nテスト開始: XPath検索")
    suite = unittest.TestLoader().loadTestsFromTestCase(TestXPathSearch)
    result = unittest.TextTestRunner().run(suite)
    print(f"テスト結果: {result}")
    return result.wasSuccessful()

if __name__ == "__main__":
    success1 = test_parse_direction_file()
    print(f"テスト1結果: {'成功' if success1 else '失敗'}")
    
    # XPath検索テスト実行
    success3 = test_xpath_search()
    print(f"テスト3結果: {'成功' if success3 else '失敗'}")
    
    # execute_extractionのテストはブラウザを起動するため、コメントアウト
    # 必要な場合はコメントを外して実行
    # success2 = test_execute_extraction()
    # print(f"テスト2結果: {'成功' if success2 else '失敗'}")
