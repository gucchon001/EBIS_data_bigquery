#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HTMLファイル保存の単体テスト
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import traceback
from urllib.parse import urlparse

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent)
sys.path.append(project_root)

# 保存先ディレクトリの設定
pages_dir = os.path.join(project_root, "data", "pages")

def generate_test_filename(url):
    """テスト用のファイル名生成"""
    # URLからドメイン部分を抽出
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace(".", "_")
    
    # タイムスタンプを追加
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # ファイル名作成
    filename = f"{domain}_{timestamp}.html"
    print(f"生成されたファイル名: {filename}")
    return filename

def save_html_to_file(url, html_content):
    """HTMLをファイルに保存するテスト関数"""
    try:
        # ファイル名を生成
        filename = generate_test_filename(url)
        filepath = os.path.join(pages_dir, filename)
        print(f"保存先ファイルパス: {filepath}")
        
        # ディレクトリが存在するか確認
        Path(pages_dir).mkdir(parents=True, exist_ok=True)
        
        # ファイルに書き込み
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTMLファイルを保存しました: {filepath}")
        
        # ファイルが存在するか確認
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            print(f"保存されたファイルサイズ: {file_size} バイト")
        else:
            print(f"エラー: ファイルが存在しません: {filepath}")
            
        return filepath
        
    except Exception as e:
        print(f"HTMLファイル保存中にエラーが発生: {e}")
        print(traceback.format_exc())
        return ""

def main():
    """メイン処理"""
    print("HTMLファイル保存テストを開始します")
    
    # ディレクトリのアクセス権確認
    try:
        if not os.path.exists(pages_dir):
            print(f"ディレクトリが存在しません: {pages_dir}")
            os.makedirs(pages_dir, exist_ok=True)
            print(f"ディレクトリを作成しました: {pages_dir}")
        else:
            print(f"ディレクトリが存在します: {pages_dir}")
            
        # 書き込み権限があるかテスト
        test_file = os.path.join(pages_dir, "test_write_permission.txt")
        with open(test_file, 'w') as f:
            f.write("テスト")
        os.remove(test_file)
        print("ディレクトリへの書き込み権限があります")
    except Exception as e:
        print(f"ディレクトリアクセスエラー: {e}")
        print(traceback.format_exc())
        return

    # テストケース1: シンプルなHTML
    test_url = "https://bishamon.ebis.ne.jp/dashboard"
    test_html = "<html><body>テストHTML</body></html>"
    save_html_to_file(test_url, test_html)
    
    # テストケース2: 本物のHTMLを模したより大きなコンテンツ
    big_html = "<html><body>" + "コンテンツ" * 1000 + "</body></html>"
    save_html_to_file(test_url, big_html)

if __name__ == "__main__":
    main() 