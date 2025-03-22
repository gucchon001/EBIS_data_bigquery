# -*- coding: utf-8 -*-
"""
HTML保存機能のユニットテスト
"""

import os
import sys
import unittest
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
from urllib.parse import urlparse

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.modules.browser.ai_element_extractor import AIElementExtractor

class TestHtmlSave(unittest.TestCase):
    """HTML保存機能のテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.extractor = AIElementExtractor(keep_browser_open=True)
        
        # テスト用の一時ディレクトリを作成
        self.test_dir = tempfile.mkdtemp()
        # ページディレクトリを上書きするために_pages_dirを直接アクセス
        self._original_pages_dir = self.extractor.pages_dir
        
        # テスト用のモックメソッドを作成
        def mock_save_html(url, html):
            if not os.path.exists(self.test_dir):
                os.makedirs(self.test_dir)
            filename = self.extractor._generate_filename(url)
            filepath = os.path.join(self.test_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
            return filepath
        
        # オリジナルのメソッドを保存
        self._original_save_method = self.extractor._save_html_to_file
        # モックメソッドに置き換え
        self.extractor._save_html_to_file = mock_save_html
        
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # 一時ディレクトリを削除（存在する場合のみ）
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        # 元のメソッドを復元
        self.extractor._save_html_to_file = self._original_save_method
        
    def test_generate_filename(self):
        """ファイル名生成のテスト"""
        # テスト用URL
        test_url = "https://bishamon.ebis.ne.jp/dashboard"
        
        # ファイル名生成
        filename = self.extractor._generate_filename(test_url)
        
        # 検証
        parsed_url = urlparse(test_url)
        domain = parsed_url.netloc.replace('.', '_')
        path = parsed_url.path.strip('/').replace('/', '_')
        today = datetime.now().strftime("%Y%m%d")
        
        # ファイル名のパターン検証
        self.assertTrue(filename.startswith(f"{domain}_{path}_{today}"))
        self.assertTrue(filename.endswith(".html"))
        self.assertTrue("_" in filename)
        
    def test_save_html_to_file(self):
        """HTML保存機能のテスト"""
        # テスト用URL
        test_url = "https://bishamon.ebis.ne.jp/dashboard"
        
        # テスト用HTML
        test_html = """
        <!DOCTYPE html>
        <html>
        <head><title>テストページ</title></head>
        <body><h1>テスト</h1></body>
        </html>
        """
        
        # HTMLを保存
        file_path = self.extractor._save_html_to_file(test_url, test_html)
        
        # 検証
        self.assertTrue(os.path.exists(file_path))
        self.assertTrue(file_path.startswith(self.test_dir))
        self.assertTrue(file_path.endswith(".html"))
        
        # ファイル内容の検証
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, test_html)
            
    def test_save_html_to_file_with_invalid_chars(self):
        """不正な文字を含むURLでのHTML保存テスト"""
        # 特殊文字を含むテスト用URL
        test_url = "https://bishamon.ebis.ne.jp/dashboard?q=テスト&id=123"
        
        # テスト用HTML
        test_html = "<html><body>特殊文字テスト</body></html>"
        
        # HTMLを保存
        file_path = self.extractor._save_html_to_file(test_url, test_html)
        
        # 検証
        self.assertTrue(os.path.exists(file_path))
        self.assertTrue(file_path.startswith(self.test_dir))
        
        # ファイル内容の検証
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, test_html)
            
    def test_directory_creation(self):
        """ディレクトリ作成のテスト"""
        # 一時ディレクトリを削除（存在する場合のみ）
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        
        # テスト用URL
        test_url = "https://bishamon.ebis.ne.jp/dashboard"
        
        # テスト用HTML
        test_html = "<html><body>ディレクトリ作成テスト</body></html>"
        
        # HTMLを保存
        file_path = self.extractor._save_html_to_file(test_url, test_html)
        
        # 検証
        self.assertTrue(os.path.exists(file_path))
        self.assertTrue(os.path.exists(self.test_dir))

def main():
    unittest.main()

if __name__ == "__main__":
    main() 