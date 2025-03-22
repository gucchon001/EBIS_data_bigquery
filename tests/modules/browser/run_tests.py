#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ログインページテンプレートのユニットテストを実行するスクリプト
"""

import os
import sys
import unittest
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent.parent.parent)
sys.path.append(project_root)

# テスト実行情報を表示
print("=====================================")
print("ログインページテンプレートテストの実行")
print("=====================================")
print(f"テスト対象モジュール: src/modules/browser/login_page_template.py")
print(f"プロジェクトルート: {project_root}")
print("-------------------------------------")

if __name__ == "__main__":
    try:
        # テストディレクトリを現在のディレクトリに設定
        test_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"テストディレクトリ: {test_dir}")
        os.chdir(test_dir)
        
        # test_から始まるすべてのPythonファイルを検索してテスト実行
        test_suite = unittest.defaultTestLoader.discover(
            start_dir=".", 
            pattern="test_*.py",
            top_level_dir=test_dir
        )
        
        # テストの数を表示
        test_count = test_suite.countTestCases()
        print(f"実行テスト数: {test_count}")
        print("-------------------------------------")
        
        # テスト実行
        test_runner = unittest.TextTestRunner(verbosity=2)
        result = test_runner.run(test_suite)
        
        # 結果のサマリーを表示
        print("-------------------------------------")
        print(f"テスト結果サマリー:")
        print(f"実行数: {result.testsRun}")
        print(f"成功数: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"失敗数: {len(result.failures)}")
        print(f"エラー数: {len(result.errors)}")
        
        # 詳細なエラーを表示
        if result.failures:
            print("\n失敗したテスト:")
            for i, (test, err) in enumerate(result.failures):
                print(f"{i+1}. {test}")
                print(f"エラー: {err}")
                print("-" * 40)
        
        if result.errors:
            print("\nエラーが発生したテスト:")
            for i, (test, err) in enumerate(result.errors):
                print(f"{i+1}. {test}")
                print(f"エラー: {err}")
                print("-" * 40)
        
        # 終了コードを設定（テスト失敗時は非ゼロ）
        sys.exit(not result.wasSuccessful())
        
    except Exception as e:
        print(f"テスト実行中に予期しないエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 