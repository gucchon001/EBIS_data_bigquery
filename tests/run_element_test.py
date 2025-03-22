# -*- coding: utf-8 -*-
"""
Seleniumでの要素検索テストを実行するスクリプト
"""

import os
import sys
import time
import glob
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.utils.environment import EnvironmentUtils as env
from src.utils.logging_config import get_logger
# 直接Seleniumのドライバーを使うようにします
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

from element_finder_utils import (
    find_element_by_text,
    find_elements_by_text,
    highlight_element,
    click_element_safely,
    wait_for_page_load
)

logger = get_logger(__name__)

def get_latest_html_file(directory="data/pages"):
    """最新のHTMLファイルを取得する"""
    try:
        # ディレクトリの絶対パスを取得
        abs_dir = env.resolve_path(directory)
        html_files = glob.glob(f"{abs_dir}/*.html")
        
        if not html_files:
            logger.error(f"HTMLファイルが見つかりません: {abs_dir}")
            return None
            
        # 最新のファイルを取得
        latest_file = max(html_files, key=os.path.getmtime)
        logger.info(f"最新のHTMLファイル: {latest_file}")
        return latest_file
    except Exception as e:
        logger.error(f"HTMLファイル検索中にエラーが発生しました: {str(e)}")
        return None

def setup_driver(headless=False):
    """Chromeドライバーをセットアップする"""
    try:
        # Chromeオプションの設定
        options = Options()
        if headless:
            options.add_argument("--headless")
        
        # ウィンドウサイズの設定
        options.add_argument("--window-size=1920,1080")
        
        # その他の有用なオプション
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # ChromeDriverのセットアップ
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # タイムアウトの設定
        driver.set_page_load_timeout(30)
        driver.set_script_timeout(30)
        
        logger.info("Chromeドライバーのセットアップが完了しました")
        return driver
    except Exception as e:
        logger.error(f"ドライバーのセットアップ中にエラーが発生しました: {str(e)}")
        return None

def test_find_element(html_file=None, element_text="コンバージョン属性", headless=False):
    """要素検索のテストを実行する"""
    driver = None
    
    try:
        # HTMLファイルが指定されていない場合は最新のファイルを使用
        if not html_file:
            html_file = get_latest_html_file()
            if not html_file:
                print("テスト用のHTMLファイルが見つかりません。")
                return False
        
        print(f"テスト開始: 「{element_text}」要素の検索")
        print(f"使用するHTMLファイル: {html_file}")
        
        # ドライバーをセットアップ
        driver = setup_driver(headless)
        if not driver:
            print("ドライバーのセットアップに失敗しました。")
            return False
        
        # HTMLファイルを開く (file:// プロトコルを使用)
        file_url = f"file:///{html_file}"
        print(f"ファイルを開いています: {file_url}")
        
        try:
            driver.get(file_url)
            
            # ページの読み込みを待機
            wait_for_page_load(driver)
            
            # スクリーンショットを保存
            driver.save_screenshot("page_loaded.png")
            print("スクリーンショットを保存しました: page_loaded.png")
            
        except Exception as e:
            print(f"HTMLファイルの読み込み中にエラーが発生しました: {str(e)}")
            return False
        
        # 要素の検索を試行
        print(f"\n--- 「{element_text}」の検索を開始します ---")
        
        # 1. テキスト完全一致で検索
        print("\n1. テキスト完全一致で検索:")
        element = find_element_by_text(driver, element_text, partial_match=False)
        
        if element:
            print("✅ 完全一致で要素が見つかりました！")
            print(f"- タグ: {element.tag_name}")
            print(f"- テキスト: {element.text}")
            highlight_element(driver, element, duration=3)
            driver.save_screenshot("exact_match_found.png")
            
            # クリックテスト
            print("\nクリックテスト...")
            click_result = click_element_safely(driver, element)
            if click_result:
                print("✅ クリック成功")
                driver.save_screenshot("after_click.png")
            else:
                print("❌ クリック失敗")
            
            return True
        
        # 2. テキスト部分一致で検索
        print("\n2. テキスト部分一致で検索:")
        element = find_element_by_text(driver, element_text, partial_match=True)
        
        if element:
            print("✅ 部分一致で要素が見つかりました！")
            print(f"- タグ: {element.tag_name}")
            print(f"- テキスト: {element.text}")
            highlight_element(driver, element, duration=3)
            driver.save_screenshot("partial_match_found.png")
            
            # クリックテスト
            print("\nクリックテスト...")
            click_result = click_element_safely(driver, element)
            if click_result:
                print("✅ クリック成功")
                driver.save_screenshot("after_click.png")
            else:
                print("❌ クリック失敗")
            
            return True
        
        # 3. テキスト分割検索（日本語の場合）
        if ' ' in element_text:
            words = element_text.split(' ')
            first_word = words[0]
            
            print(f"\n3. 最初の単語「{first_word}」で検索:")
            element = find_element_by_text(driver, first_word)
            
            if element:
                print(f"✅ 「{first_word}」で要素が見つかりました！")
                print(f"- タグ: {element.tag_name}")
                print(f"- テキスト: {element.text}")
                highlight_element(driver, element, duration=3)
                driver.save_screenshot("word_match_found.png")
                
                # クリックテスト
                print("\nクリックテスト...")
                click_result = click_element_safely(driver, element)
                if click_result:
                    print("✅ クリック成功")
                    driver.save_screenshot("after_click.png")
                else:
                    print("❌ クリック失敗")
                
                return True
        
        # 4. 複数要素の検索
        print("\n4. 類似テキストの要素を探して一覧表示:")
        if ' ' in element_text:
            search_term = element_text.split(' ')[0]  # 最初の単語で検索
        else:
            search_term = element_text[:min(len(element_text), 3)]  # 先頭3文字で検索
            
        elements = find_elements_by_text(driver, search_term)
        
        if elements:
            print(f"✅ 「{search_term}」に関連する要素が {len(elements)} 個見つかりました！")
            
            # 見つかった要素の一覧を表示
            for i, el in enumerate(elements, 1):
                try:
                    print(f"\n要素 {i}:")
                    print(f"- タグ: {el.tag_name}")
                    print(f"- テキスト: {el.text}")
                    print(f"- クラス: {el.get_attribute('class')}")
                    print(f"- ID: {el.get_attribute('id')}")
                    
                    # 要素をハイライト表示してスクリーンショット
                    highlight_element(driver, el, duration=1)
                    driver.save_screenshot(f"element_{i}.png")
                    
                    # 「コンバージョン」を含む要素が見つかった場合、クリックテスト
                    if "コンバージョン" in el.text:
                        print(f"\n「コンバージョン」を含む要素 {i} をクリックします...")
                        click_result = click_element_safely(driver, el)
                        if click_result:
                            print("✅ クリック成功")
                            driver.save_screenshot(f"after_click_element_{i}.png")
                            return True
                        else:
                            print("❌ クリック失敗")
                except Exception as e:
                    print(f"要素 {i} の情報取得中にエラーが発生しました: {str(e)}")
        
        print("\n❌ 指定した要素が見つかりませんでした。")
        return False
        
    except Exception as e:
        print(f"テスト実行中にエラーが発生しました: {str(e)}")
        return False
        
    finally:
        if driver:
            driver.quit()
            print("ブラウザを終了しました。")

if __name__ == "__main__":
    # コマンドライン引数からHTMLファイルパスと要素テキストを取得
    html_file = None
    element_text = "コンバージョン属性"
    headless = False
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("使用方法: python run_element_test.py [HTMLファイルパス] [検索テキスト] [--headless]")
            print("  HTMLファイルパス: テスト対象のHTMLファイルパス（指定しない場合は最新のファイルを使用）")
            print("  検索テキスト: 検索する要素のテキスト（デフォルト: コンバージョン属性）")
            print("  --headless: ヘッドレスモードで実行（ブラウザを表示しない）")
            sys.exit(0)
            
        if sys.argv[1] == "--headless":
            headless = True
        else:
            html_file = sys.argv[1]
    
    if len(sys.argv) > 2:
        if sys.argv[2] == "--headless":
            headless = True
        else:
            element_text = sys.argv[2]
            
    if len(sys.argv) > 3 and sys.argv[3] == "--headless":
        headless = True
    
    # 環境変数を読み込む
    env.load_env()
    
    # テストを実行
    success = test_find_element(html_file, element_text, headless)
    sys.exit(0 if success else 1) 