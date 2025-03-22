# -*- coding: utf-8 -*-
"""
コンバージョン属性要素をクリックするテスト
特定のHTMLファイルを開き、コンバージョン属性要素を見つけてクリック操作をテストします
"""

import os
import sys
import time
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

def run_click_test():
    driver = None
    
    try:
        print("コンバージョン属性要素のクリックテストを開始します...")
        
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
        driver.save_screenshot("before_click.png")
        print("スクリーンショット（クリック前）を保存しました")
        
        # 正確なXPathを使用してコンバージョン属性要素を探す
        xpath = "//span[text()='コンバージョン属性']"
        print(f"XPathで要素を検索: {xpath}")
        
        try:
            # 要素が見つかるまで待機
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            
            # 要素の情報を表示
            print(f"要素が見つかりました: タグ={element.tag_name}, テキスト={element.text}")
            print(f"要素の親要素: {element.find_element(By.XPATH, '..').tag_name}")
            
            # 要素の親リンクを検索
            parent_link = element.find_element(By.XPATH, "./ancestor::a")
            print(f"親リンク: href={parent_link.get_attribute('href')}")
            
            # 要素をハイライト
            driver.execute_script("arguments[0].style.border='3px solid red'", element)
            driver.save_screenshot("element_highlighted.png")
            print("要素をハイライトしました")
            
            # 親リンクの要素情報を表示
            print(f"親リンクのクラス: {parent_link.get_attribute('class')}")
            print(f"親リンクのID: {parent_link.get_attribute('id')}")
            
            # 要素までスクロール
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(1)  # スクロール完了を待つ
            
            # 要素をクリック
            print("要素をクリックします...")
            
            # JavaScriptによるクリック
            driver.execute_script("arguments[0].click();", parent_link)
            
            # クリック後のURLを取得
            time.sleep(2)  # ページ遷移を待つ
            new_url = driver.current_url
            print(f"クリック後のURL: {new_url}")
            
            # クリック後のスクリーンショット
            driver.save_screenshot("after_click.png")
            print("スクリーンショット（クリック後）を保存しました")
            
            return True
        except Exception as e:
            print(f"要素検索・クリック中にエラーが発生しました: {e}")
            
            # バックアップ方法：linkタグ内で「コンバージョン属性」を含むものを探す
            try:
                print("\nバックアップ方法で検索を実行...")
                links = driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    if "コンバージョン属性" in link.text:
                        print(f"リンクが見つかりました: {link.text}")
                        driver.execute_script("arguments[0].style.border='3px solid blue'", link)
                        driver.save_screenshot("link_found.png")
                        
                        # リンクをクリック
                        print("リンクをクリックします...")
                        driver.execute_script("arguments[0].click();", link)
                        
                        time.sleep(2)  # ページ遷移を待つ
                        driver.save_screenshot("after_backup_click.png")
                        print("バックアップ方法でクリックに成功しました")
                        return True
                
                print("「コンバージョン属性」を含むリンクが見つかりませんでした")
            except Exception as backup_e:
                print(f"バックアップ検索中にエラーが発生しました: {backup_e}")
            
            return False
            
    except Exception as e:
        print(f"テスト実行中にエラーが発生しました: {e}")
        return False
    finally:
        if driver:
            driver.quit()
            print("ブラウザを終了しました")

if __name__ == "__main__":
    run_click_test() 