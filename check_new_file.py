import chardet
import pandas as pd

# 入力ファイルのパス
input_file = 'data/AE_SSresult/202503232018_cv_attr.csv'

# ファイルの先頭部分を16進数でダンプ
def hex_dump(data, length=100):
    """データのバイト列を16進数でダンプします"""
    hex_chars = [f'{b:02x}' for b in data[:length]]
    printable = ''.join([chr(b) if 32 <= b < 127 else '.' for b in data[:length]])
    
    print("\nヘックスダンプ:")
    for i in range(0, len(hex_chars), 16):
        line_hex = ' '.join(hex_chars[i:i+16])
        line_printable = printable[i:i+16]
        print(f"{i:04x}: {line_hex.ljust(48)} | {line_printable}")

try:
    # ファイルの内容を読み込む
    with open(input_file, 'rb') as f:
        content = f.read(10000)  # 最初の10000バイトを読み込む
        
    print(f"ファイルサイズ（先頭部分）: {len(content)} バイト")
    
    # ファイルの先頭部分をダンプ
    hex_dump(content)
    
    # chardetによる自動検出
    result = chardet.detect(content)
    print(f"\nchardetによる検出結果: {result['encoding']} (信頼度: {result['confidence']:.2f})")
    
    # UTF-8のBOMチェック
    if content.startswith(b'\xef\xbb\xbf'):
        print("UTF-8 BOMが検出されました")
    else:
        print("UTF-8 BOMは検出されませんでした")
    
    # UTF-8の置換文字をチェック
    utf8_replacement = b'\xef\xbf\xbd'
    utf8_replacement_count = content.count(utf8_replacement)
    if utf8_replacement_count > 0:
        percent = (utf8_replacement_count * 3 / len(content)) * 100
        print(f"UTF-8の置換文字 (�) の数: {utf8_replacement_count} (先頭部分の約 {percent:.1f}%)")
    
    # 一般的な日本語エンコーディングでの読み込みを試す
    encodings = ['utf-8', 'cp932', 'shift_jis', 'euc_jp', 'iso-2022-jp']
    print("\n各エンコーディングでの読み込み試行:")
    
    for encoding in encodings:
        try:
            decoded = content[:200].decode(encoding)
            print(f"✓ {encoding}: 正常にデコードできました")
            print(f"  最初の20文字: {decoded[:20]}")
            
            # pandasでCSVとして読み込めるかテスト
            try:
                with open(input_file, 'rb') as f:
                    test_content = f.read(1000)  # 最初の1000バイトだけ
                
                with open('temp_test.csv', 'wb') as f:
                    f.write(test_content)
                
                df = pd.read_csv('temp_test.csv', encoding=encoding, nrows=1)
                print(f"  CSVとして正常に読み込めました (カラム数: {len(df.columns)})")
                print(f"  最初の5カラム: {df.columns[:5].tolist() if len(df.columns) > 5 else df.columns.tolist()}")
            except Exception as e:
                print(f"  CSVとしての読み込みに失敗: {e}")
            
        except UnicodeDecodeError as e:
            print(f"✗ {encoding}: デコードエラー - {e}")
    
    # 結論
    print("\n結論:")
    if result['encoding'] and result['confidence'] > 0.7:
        print(f"このファイルは {result['encoding']} でエンコードされている可能性が高いです (信頼度: {result['confidence']:.2f})")
    elif utf8_replacement_count > 0 and (utf8_replacement_count * 3 / len(content)) > 0.1:
        print("このファイルは文字化けしているUTF-8ファイルです。元々はcp932/Shift-JISだった可能性があります。")
    else:
        print("このファイルのエンコーディングを確定できませんでした。複数のエンコーディングを試してください。")

except FileNotFoundError:
    print(f"エラー: ファイル '{input_file}' が見つかりません。")
except Exception as e:
    print(f"エラーが発生しました: {e}") 