#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CSVファイルの内容を確認するユーティリティスクリプト

使用方法:
    python check_csv.py [ファイルパス] [表示行数]
    
    ファイルパスが指定されていない場合は、data/SE_SSresult/test ディレクトリ内の
    最新のCSVファイルを使用します。
    表示行数のデフォルトは5行です。
"""

import os
import csv
import sys
from pathlib import Path
import glob
import datetime
import traceback

def excel_serial_to_datetime(serial_number):
    """Excelシリアル値をdatetimeオブジェクトに変換します"""
    if not serial_number or serial_number.strip() == '':
        return ""
    
    try:
        # Excelの日付の起点は1900年1月1日。ただし、1900年はうるう年ではないのに
        # Excelはそれをうるう年と誤認しているため、1900/2/28より後の日付は1日ずれる
        serial_float = float(serial_number)
        # エクセルのバグに対応: 1900/3/1 (シリアル値 61) 以降は1日引く
        if serial_float > 60:
            serial_float -= 1
            
        days_since_1900 = int(serial_float)
        fraction_of_day = serial_float - days_since_1900
        
        # 1900/1/1 からの日数を加算
        base_date = datetime.datetime(1900, 1, 1)
        date_part = base_date + datetime.timedelta(days=days_since_1900)
        
        # 時間部分を計算（日の小数部分）
        seconds = int(fraction_of_day * 86400)  # 24 * 60 * 60
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        
        # JSTに変換（UTC + 9時間）
        dt = datetime.datetime(
            date_part.year, date_part.month, date_part.day,
            hours, minutes, seconds
        )
        
        # フォーマット: YYYY/MM/DD HH:MM:SS
        return dt.strftime('%Y/%m/%d %H:%M:%S')
    except (ValueError, TypeError) as e:
        print(f"変換エラー: {e} (値: {serial_number})")
        return f"変換エラー: {serial_number}"

def show_csv_content(file_path, max_lines=5):
    """CSVファイルの内容を表示します"""
    print(f"ファイル: {file_path}")
    print("-" * 80)
    
    try:
        if not Path(file_path).exists():
            print(f"エラー: ファイル {file_path} が存在しません")
            return
            
        print(f"ファイルサイズ: {Path(file_path).stat().st_size} バイト")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            if not rows:
                print("CSVファイルが空です")
                return
            
            header = rows[0]
            print(f"ヘッダー行: {', '.join(header[:5])}..." if len(header) > 5 else f"ヘッダー行: {', '.join(header)}")
            print("-" * 80)
            
            # タイムスタンプ列のインデックスを見つける
            timestamp_cols = []
            for i, col in enumerate(header):
                if "時間" in col or "日時" in col or "発生日時" in col or "CV時間" in col:
                    timestamp_cols.append(i)
            
            print(f"タイムスタンプ列のインデックス: {timestamp_cols}")
            
            # データ行を表示
            data_rows = rows[1:max_lines+1] if max_lines else rows[1:]
            display_count = len(data_rows)
            total_count = len(rows) - 1
            
            print(f"データ行数: {total_count}, 表示行数: {display_count}")
            
            for i, row in enumerate(data_rows, 1):
                print(f"行 {i}:")
                
                # タイムスタンプ列の表示
                for ts_idx in timestamp_cols:
                    if ts_idx < len(row):
                        excel_date = row[ts_idx]
                        human_date = excel_serial_to_datetime(excel_date)
                        print(f"  タイムスタンプ列 {ts_idx} ({header[ts_idx]}): {excel_date} → {human_date}")
                
                # 先頭5列を表示
                print(f"  先頭5列: {', '.join(row[:5])}..." if len(row) > 5 else f"  先頭5列: {', '.join(row)}")
                print()
        
        print("-" * 80)
        print("CSV分析完了")
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        traceback.print_exc()

def find_latest_csv_file():
    """最新のCSVファイルを検索して返します"""
    test_dir = Path("data/SE_SSresult/test")
    
    if not test_dir.exists():
        print(f"エラー: ディレクトリ {test_dir} が存在しません")
        # ディレクトリ構造を表示
        print("現在のディレクトリ構造:")
        for path in Path('.').glob('**/'):
            print(f"  {path}")
        return None
        
    print(f"検索ディレクトリ: {test_dir.absolute()}")
    
    csv_files = list(test_dir.glob("test_data_*.csv"))
    print(f"見つかったCSVファイル数: {len(csv_files)}")
    
    if not csv_files:
        print("テストデータCSVファイルが見つかりません。")
        # ディレクトリの内容を表示
        print(f"{test_dir} ディレクトリの内容:")
        for item in test_dir.glob('*'):
            print(f"  {item.name}")
        return None
    
    # 最新のファイルを使用
    return sorted(csv_files, key=lambda p: p.stat().st_mtime, reverse=True)[0]

def main():
    """メイン処理"""
    try:
        # コマンドライン引数の解析
        file_path = None
        max_lines = 5
        
        if len(sys.argv) > 1:
            # ファイルパスが指定されている場合
            file_arg = sys.argv[1]
            if file_arg.lower() == 'all':
                max_lines = None  # すべての行を表示
            else:
                file_path = Path(file_arg)
        
        if len(sys.argv) > 2:
            # 表示行数が指定されている場合
            lines_arg = sys.argv[2]
            if lines_arg.lower() == 'all':
                max_lines = None  # すべての行を表示
            else:
                try:
                    max_lines = int(lines_arg)
                except ValueError:
                    print(f"警告: 無効な行数指定 '{lines_arg}'、デフォルト値の5を使用します")
                    max_lines = 5
        
        # ファイルパスが指定されていない場合は最新のファイルを使用
        if file_path is None:
            file_path = find_latest_csv_file()
            
        if file_path:
            print(f"最新のCSVファイル: {file_path}")
            show_csv_content(file_path, max_lines)
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 