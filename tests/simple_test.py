# -*- coding: utf-8 -*-
"""
非常にシンプルなSeleniumテスト
特定のHTMLファイルを開いて要素を検索する簡易テスト
"""

import os
import sys
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def run_test():
    driver = None
    
    try:
        print("Seleniumテストを開始します...")
        
        # 絶対パスでHTMLファイルのパスを作成
        filepath = Path(project_root) / "data" / "pages" / "bishamon_ebis_ne_jp_20250321_075218.html"
        if not filepath.exists():
            print(f"ファイルが見つかりません: {filepath}")
            return False
            
        print(f"使用するファイル: {filepath}")
        
        # WebDriverのセットアップ
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        
        # HTMLファイルを開く
        file_url = f"file:///{filepath.absolute()}"
        print(f"URLを開きます: {file_url}")
        driver.get(file_url)
        
        # ページが読み込まれたかの確認
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # スクリーンショットを保存
        driver.save_screenshot("simple_test.png")
        print("スクリーンショットを保存しました: simple_test.png")
        
        # body要素のテキストを取得
        body_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"ページの内容: {body_text[:200]}...")
        
        # 「コンバージョン」を含む要素を探す
        try:
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'コンバージョン')]")
            if elements:
                print(f"{len(elements)}個の「コンバージョン」を含む要素が見つかりました")
                for i, elem in enumerate(elements, 1):
                    print(f"要素 {i}: タグ={elem.tag_name}, テキスト={elem.text}")
                    # 要素をハイライト
                    driver.execute_script("arguments[0].style.border='3px solid red'", elem)
                driver.save_screenshot("elements_found.png")
            else:
                print("「コンバージョン」を含む要素は見つかりませんでした")
        except Exception as e:
            print(f"要素検索中にエラーが発生しました: {e}")
        
        # 全てのリンクを表示
        links = driver.find_elements(By.TAG_NAME, "a")
        print(f"\n{len(links)}個のリンクが見つかりました")
        for i, link in enumerate(links[:10], 1):  # 最初の10個だけ表示
            try:
                print(f"リンク {i}: テキスト={link.text}, href={link.get_attribute('href')}")
            except:
                print(f"リンク {i}: 属性取得中にエラーが発生しました")
                
        return True
    except Exception as e:
        print(f"テスト実行中にエラーが発生しました: {e}")
        return False
    finally:
        if driver:
            driver.quit()
            print("ブラウザを終了しました")

if __name__ == "__main__":
    run_test() 