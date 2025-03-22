#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
要素検索機能の単体テスト
ボタンやフィールドなどの要素検索ロジックをテストします
"""

import os
import sys
from pathlib import Path
import traceback
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent)
sys.path.append(project_root)

# テスト用のHTMLを作成
TEST_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>要素検索テスト</title>
    <meta charset="UTF-8">
</head>
<body>
    <!-- ナビゲーションバー -->
    <nav class="navbar">
        <div class="nav-item">ホーム</div>
        <div class="nav-item">詳細分析</div>
        <div class="nav-item">全トラフィック</div>
        <div class="nav-item btn">コンバージョン属性</div>
    </nav>
    
    <!-- メインコンテンツ -->
    <div class="main-content">
        <h1>EBiS分析ツール</h1>
        
        <!-- ボタン類 -->
        <button id="analysis-btn" class="btn btn-primary">詳細分析 ボタン</button>
        <button id="traffic-btn" class="btn btn-secondary">全トラフィック ボタン</button>
        <button id="calendar-btn" class="btn btn-info">カレンダー ボタン</button>
        <button id="export-btn" class="btn btn-success">エクスポート ボタン</button>
        <button id="csv-btn" class="btn btn-export">表を出力（CSV） ボタン</button>
        
        <!-- フォーム要素 -->
        <div class="form-group">
            <label for="start-date">期間指定 開始日</label>
            <input type="date" id="start-date" class="form-control" placeholder="開始日を選択">
        </div>
        
        <div class="form-group">
            <label for="end-date">期間指定 終了日</label>
            <input type="date" id="end-date" class="form-control" placeholder="終了日を選択">
        </div>
        
        <!-- ドロップダウン -->
        <div class="dropdown">
            <button class="btn dropdown-toggle">ビュー ボタン</button>
            <div class="dropdown-menu">
                <div class="dropdown-item">プログラム用全項目ビュー</div>
                <div class="dropdown-item">標準ビュー</div>
            </div>
        </div>
        
        <!-- 適用ボタン -->
        <button id="apply-btn" class="btn btn-apply">適用 ボタン</button>
    </div>
</body>
</html>
"""

class ElementSearchTest:
    """要素検索テストクラス"""
    
    def __init__(self):
        """初期化"""
        self.setup_browser()
        self.test_results = {
            "成功": 0,
            "失敗": 0,
            "テスト数": 0
        }
    
    def setup_browser(self):
        """ブラウザをセットアップ"""
        try:
            # Chrome オプション設定
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')  # ヘッドレスモード
            
            # ChromeDriverのセットアップ
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # テスト用HTMLを読み込み
            test_html_path = os.path.join(project_root, "test_page.html")
            
            # テスト用HTMLファイルを書き込み
            with open(test_html_path, "w", encoding="utf-8") as f:
                f.write(TEST_HTML)
            
            # ファイルをブラウザで開く
            self.driver.get(f"file://{test_html_path}")
            print("ブラウザのセットアップが完了しました")
            
            # HTMLをパースしてBeautifulSoupオブジェクトを作成
            self.soup = BeautifulSoup(self.driver.page_source, "html.parser")
            return True
            
        except Exception as e:
            print(f"ブラウザのセットアップ中にエラーが発生: {e}")
            print(traceback.format_exc())
            return False
    
    def test_xpath_search(self, xpath, name, expected_result=True):
        """XPath検索のテスト"""
        self.test_results["テスト数"] += 1
        try:
            print(f"\nテスト: {name}")
            print(f"XPath: {xpath}")
            
            # タイムアウト設定を短くして高速にテスト
            element = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            
            if element:
                print(f"✅ 成功: 要素が見つかりました: {element.text}")
                self.test_results["成功"] += 1
                return True
            else:
                print("❌ 失敗: 要素が見つかりませんでした")
                if expected_result:
                    self.test_results["失敗"] += 1
                return False
                
        except (NoSuchElementException, TimeoutException):
            print("❌ 失敗: 要素が見つかりませんでした")
            if expected_result:
                self.test_results["失敗"] += 1
            return False
        except Exception as e:
            print(f"❌ エラー: {e}")
            if expected_result:
                self.test_results["失敗"] += 1
            return False
    
    def test_text_search(self, text, element_type="button", expected_result=True):
        """テキスト検索のテスト"""
        # 1. 完全一致
        exact_xpath = f"//{element_type}[contains(text(), '{text}')]"
        exact_result = self.test_xpath_search(exact_xpath, f"'{text}'の完全一致検索 ({element_type})", expected_result)
        
        # 2. 空白を含む場合のテスト
        if " " in text:
            parts = text.split(" ")
            parts_xpath = f"//{element_type}[contains(text(), '{parts[0]}')]"
            parts_result = self.test_xpath_search(parts_xpath, f"'{parts[0]}'の部分一致検索 ({element_type})", expected_result)
            
            # 3. 複合検索（複数の部分を含む）
            complex_conditions = " and ".join([f"contains(text(), '{part}')" for part in parts])
            complex_xpath = f"//{element_type}[{complex_conditions}]"
            complex_result = self.test_xpath_search(complex_xpath, f"'{text}'の複合部分一致検索 ({element_type})", expected_result)
            
            return exact_result or parts_result or complex_result
        else:
            return exact_result
    
    def test_class_search(self, class_name, element_type="button", expected_result=True):
        """クラス検索のテスト"""
        # クラス属性の検索
        class_xpath = f"//{element_type}[contains(@class, '{class_name}')]"
        return self.test_xpath_search(class_xpath, f"'{class_name}'クラスの検索 ({element_type})", expected_result)
    
    def test_complex_search_patterns(self):
        """複雑な検索パターンのテスト"""
        # ボタンとテキストの組み合わせ
        complex_xpath = "//button[contains(@class, 'btn') and contains(text(), '詳細分析')]"
        self.test_xpath_search(complex_xpath, "クラスとテキストの複合検索", True)
        
        # 前後の要素を利用した検索
        complex_xpath = "//label[contains(text(), '期間指定')]/following-sibling::input"
        self.test_xpath_search(complex_xpath, "ラベルテキストから入力フィールドを検索", True)
        
        # 親要素を使った検索
        complex_xpath = "//div[contains(@class, 'form-group')]/input"
        self.test_xpath_search(complex_xpath, "親要素のクラスから入力フィールドを検索", True)
    
    def test_partial_japanese_text_search(self):
        """日本語テキストの部分一致検索テスト"""
        print("\n=== 日本語テキスト部分一致検索テスト ===")
        
        # テスト対象のテキスト
        test_cases = [
            "詳細分析 ボタン",
            "詳細分析",
            "全トラフィック ボタン",
            "カレンダー ボタン",
            "期間指定 開始日",
            "コンバージョン属性",
            "表を出力（CSV） ボタン"
        ]
        
        for text in test_cases:
            # 日本語テキストの分割処理
            parts = text.split(" ")
            first_part = parts[0]
            
            # 分割された最初の部分でのXPath検索
            xpath = f"//*[contains(text(), '{first_part}')]"
            
            result = self.test_xpath_search(xpath, f"'{text}'の部分一致検索 (最初の部分: '{first_part}')", True)
            
            # さらに複雑な検索（ボタンに限定するなど）
            if "ボタン" in text:
                button_xpath = f"//button[contains(text(), '{first_part}')]"
                button_result = self.test_xpath_search(button_xpath, f"'{text}'の部分一致検索（ボタン要素のみ）", True)
    
    def run_all_tests(self):
        """すべてのテストを実行"""
        print("=== 要素検索テスト開始 ===")
        
        # 基本的なボタン検索テスト
        self.test_text_search("詳細分析 ボタン")
        self.test_text_search("全トラフィック ボタン")
        self.test_text_search("カレンダー ボタン")
        
        # クラス検索テスト
        self.test_class_search("btn-primary")
        self.test_class_search("btn-secondary")
        self.test_class_search("btn-info")
        
        # 複雑な検索パターンのテスト
        self.test_complex_search_patterns()
        
        # 日本語テキストの部分一致検索テスト
        self.test_partial_japanese_text_search()
        
        # テスト結果の表示
        print("\n=== テスト結果 ===")
        print(f"総テスト数: {self.test_results['テスト数']}")
        print(f"成功: {self.test_results['成功']}")
        print(f"失敗: {self.test_results['失敗']}")
        
        success_rate = (self.test_results['成功'] / self.test_results['テスト数']) * 100 if self.test_results['テスト数'] > 0 else 0
        print(f"成功率: {success_rate:.1f}%")
    
    def cleanup(self):
        """クリーンアップ処理"""
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()
            print("ブラウザを終了しました")
        
        # テスト用HTMLファイルの削除
        test_html_path = os.path.join(project_root, "test_page.html")
        if os.path.exists(test_html_path):
            os.remove(test_html_path)
            print("テスト用HTMLファイルを削除しました")


def main():
    """メイン処理"""
    tester = ElementSearchTest()
    try:
        tester.run_all_tests()
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main() 