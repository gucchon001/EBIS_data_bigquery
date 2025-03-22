#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
スキーマJSONの内容確認用スクリプト
"""

import json
import glob
from pathlib import Path

def main():
    # 最新のスキーマファイルを検索
    schema_files = glob.glob('data/SE_SSresult/test/test_schema_*.json')
    if not schema_files:
        print("スキーマファイルが見つかりません。")
        return
    
    schema_file = sorted(schema_files)[-1]
    print(f"最新のスキーマファイル: {schema_file}")
    
    # スキーマの内容を表示
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    
    print(f"スキーマフィールド数: {len(schema)}")
    
    # 最初の5フィールドを表示
    print("\n最初の5フィールド:")
    for i, field in enumerate(schema[:5]):
        print(f"{i+1}. {field['name']} ({field['type']})")
    
    # テストデータも表示
    data_file = Path(schema_file).parent / Path(schema_file).name.replace('schema', 'data').replace('.json', '.csv')
    if data_file.exists():
        print(f"\nテストデータファイル: {data_file}")
        with open(data_file, 'r', encoding='utf-8') as f:
            header = f.readline().strip()
            first_data = f.readline().strip()
        
        print("\nCSVヘッダー（最初の100文字）:")
        print(header[:100] + "...")
        
        print("\n最初のデータ行（最初の100文字）:")
        print(first_data[:100] + "...")
    
if __name__ == "__main__":
    main() 