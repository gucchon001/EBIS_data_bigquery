#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
単体テスト実行スクリプト
"""

import unittest
import sys
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent)
sys.path.append(project_root)

def run_tests():
    """テストを検出して実行"""
    # テストディレクトリからテストを検出
    loader = unittest.TestLoader()
    tests = loader.discover('tests', pattern='test_*.py')
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(tests)
    
    # 結果に基づいて終了コードを設定
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(run_tests()) 