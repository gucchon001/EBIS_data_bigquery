# -*- coding: utf-8 -*-
"""
要素検索ユーティリティ
Seleniumを使用した要素検索を簡単に行うためのユーティリティ関数を提供します。
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

def find_element_by_text(driver, text, tag_names=None, partial_match=True, timeout=10):
    """
    テキスト内容で要素を検索します
    
    Args:
        driver: Seleniumのドライバーインスタンス
        text: 検索するテキスト
        tag_names: 検索対象のタグ名のリスト（例: ['a', 'button', 'div']）
        partial_match: 部分一致を許可するかどうか
        timeout: タイムアウト秒数
    
    Returns:
        見つかった要素、またはNone
    """
    wait = WebDriverWait(driver, timeout)
    
    # タグ名が指定されていない場合はデフォルトのリストを使用
    if tag_names is None:
        tag_names = ['a', 'button', 'div', 'span', 'li', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    
    # 各タグに対して検索を実行
    for tag in tag_names:
        try:
            if partial_match:
                xpath = f"//{tag}[contains(text(), '{text}')]"
            else:
                xpath = f"//{tag}[text()='{text}']"
            
            print(f"XPathで検索中: {xpath}")
            element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            if element:
                return element
        except (TimeoutException, NoSuchElementException):
            continue
    
    # タグの子要素にテキストがある場合の検索
    for tag in tag_names:
        try:
            if partial_match:
                xpath = f"//{tag}[.//*[contains(text(), '{text}')]]"
            else:
                xpath = f"//{tag}[.//*[text()='{text}']]"
            
            print(f"子要素を含めて検索中: {xpath}")
            element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            if element:
                return element
        except (TimeoutException, NoSuchElementException):
            continue
    
    # 日本語の場合、半角スペースで分割して検索
    if any(ord(c) > 127 for c in text) and ' ' in text:
        words = text.split(' ')
        print(f"テキストを分割して検索: {words}")
        
        # 各単語を含む要素を検索
        for tag in tag_names:
            try:
                conditions = []
                for word in words:
                    if word.strip():
                        conditions.append(f"contains(text(), '{word.strip()}')")
                
                if conditions:
                    condition_str = " and ".join(conditions)
                    xpath = f"//{tag}[{condition_str}]"
                    
                    print(f"複合条件で検索中: {xpath}")
                    element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                    if element:
                        return element
            except (TimeoutException, NoSuchElementException):
                continue
    
    # ここまで見つからなかった場合はNoneを返す
    return None

def find_elements_by_text(driver, text, tag_names=None, partial_match=True, timeout=10):
    """
    テキスト内容で複数の要素を検索します
    
    Args:
        driver: Seleniumのドライバーインスタンス
        text: 検索するテキスト
        tag_names: 検索対象のタグ名のリスト（例: ['a', 'button', 'div']）
        partial_match: 部分一致を許可するかどうか
        timeout: タイムアウト秒数
    
    Returns:
        見つかった要素のリスト
    """
    # タグ名が指定されていない場合はデフォルトのリストを使用
    if tag_names is None:
        tag_names = ['a', 'button', 'div', 'span', 'li', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    
    all_elements = []
    
    # 各タグに対して検索を実行
    for tag in tag_names:
        try:
            if partial_match:
                xpath = f"//{tag}[contains(text(), '{text}')]"
            else:
                xpath = f"//{tag}[text()='{text}']"
            
            elements = driver.find_elements(By.XPATH, xpath)
            all_elements.extend(elements)
        except Exception:
            continue
    
    # タグの子要素にテキストがある場合の検索
    for tag in tag_names:
        try:
            if partial_match:
                xpath = f"//{tag}[.//*[contains(text(), '{text}')]]"
            else:
                xpath = f"//{tag}[.//*[text()='{text}']]"
            
            elements = driver.find_elements(By.XPATH, xpath)
            all_elements.extend(elements)
        except Exception:
            continue
    
    # 日本語の場合、半角スペースで分割して検索
    if any(ord(c) > 127 for c in text) and ' ' in text:
        words = text.split(' ')
        
        # 各単語を含む要素を検索
        for tag in tag_names:
            try:
                conditions = []
                for word in words:
                    if word.strip():
                        conditions.append(f"contains(text(), '{word.strip()}')")
                
                if conditions:
                    condition_str = " and ".join(conditions)
                    xpath = f"//{tag}[{condition_str}]"
                    
                    elements = driver.find_elements(By.XPATH, xpath)
                    all_elements.extend(elements)
            except Exception:
                continue
    
    # 重複を削除して返す
    unique_elements = []
    for element in all_elements:
        if element not in unique_elements:
            unique_elements.append(element)
    
    return unique_elements

def wait_for_page_load(driver, timeout=30):
    """
    ページの読み込みが完了するまで待機します
    
    Args:
        driver: Seleniumのドライバーインスタンス
        timeout: タイムアウト秒数
    
    Returns:
        bool: 成功したかどうか
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        # DOMが完全にレンダリングされるための追加待機
        time.sleep(1)
        return True
    except TimeoutException:
        return False

def highlight_element(driver, element, duration=3, color='red', border=3):
    """
    要素をハイライト表示します
    
    Args:
        driver: Seleniumのドライバーインスタンス
        element: ハイライトする要素
        duration: ハイライト表示する秒数
        color: ハイライトの色
        border: ボーダーの太さ
    """
    try:
        original_style = element.get_attribute('style')
        
        # ハイライト用のスタイルを適用
        driver.execute_script(
            f"arguments[0].setAttribute('style', arguments[1] + 'border: {border}px solid {color} !important; background: yellow !important;');",
            element, original_style)
        
        # 指定秒数後に元のスタイルに戻す
        if duration > 0:
            time.sleep(duration)
            driver.execute_script(
                "arguments[0].setAttribute('style', arguments[1]);",
                element, original_style)
    except Exception as e:
        print(f"ハイライト表示中にエラーが発生しました: {str(e)}")

def click_element_safely(driver, element, wait_for_load=True, timeout=30):
    """
    要素を安全にクリックします
    
    Args:
        driver: Seleniumのドライバーインスタンス
        element: クリックする要素
        wait_for_load: クリック後にページ読み込みを待つかどうか
        timeout: タイムアウト秒数
    
    Returns:
        bool: クリックに成功したかどうか
    """
    try:
        # 要素が表示されるまでスクロール
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        time.sleep(0.5)  # スクロールが完了するのを待つ
        
        # ハイライト表示（デバッグ用）
        highlight_element(driver, element, duration=1)
        
        # JavaScriptを使用してクリック
        driver.execute_script("arguments[0].click();", element)
        
        # ページ読み込みを待機
        if wait_for_load:
            wait_for_page_load(driver, timeout)
            
        return True
    except Exception as e:
        print(f"要素のクリック中にエラーが発生しました: {str(e)}")
        
        # 標準のクリックも試す
        try:
            element.click()
            
            # ページ読み込みを待機
            if wait_for_load:
                wait_for_page_load(driver, timeout)
                
            return True
        except Exception as click_e:
            print(f"標準クリックも失敗しました: {str(click_e)}")
            return False 