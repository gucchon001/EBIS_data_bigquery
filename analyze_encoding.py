import pandas as pd
import os
import chardet
from pathlib import Path

# 入力ファイルのパス
input_file = 'data/AE_SSresult/202503231824_cv_attr.csv'

# ファイルの先頭部分を16進数でダンプ
def hex_dump(data, length=100):
    """データのバイト列を16進数でダンプします"""
    hex_chars = [f'{b:02x}' for b in data[:length]]
    hex_string = ' '.join(hex_chars)
    printable = ''.join([chr(b) if 32 <= b < 127 else '.' for b in data[:length]])
    
    print("\nヘックスダンプ:")
    for i in range(0, len(hex_chars), 16):
        line_hex = ' '.join(hex_chars[i:i+16])
        line_printable = printable[i:i+16]
        print(f"{i:04x}: {line_hex.ljust(48)} | {line_printable}")

# ファイルの内容を読み込む
with open(input_file, 'rb') as f:
    content = f.read()
    
print(f"ファイルサイズ: {len(content):,} バイト")

# ファイルの先頭部分をダンプ
hex_dump(content)

# chardetによる自動検出
result = chardet.detect(content[:10000])
print(f"\nchardetによる検出結果: {result['encoding']} (信頼度: {result['confidence']:.2f})")

# UTF-8のBOMチェック
if content.startswith(b'\xef\xbb\xbf'):
    print("UTF-8 BOMが検出されました")
else:
    print("UTF-8 BOMは検出されませんでした")

# 一般的なエンコーディングパターンのチェック
patterns = {
    'UTF-8の文字化け': b'\xef\xbf\xbd',
    'SJIS/CP932マーカー': b'\x82\xa0',  # 「あ」の文字コード
    '文字切れ（不正なUTF-8）': b'\xE3\x81'  # 「あ」の最初の2バイト
}

for name, pattern in patterns.items():
    count = content.count(pattern)
    if count > 0:
        print(f"{name}のパターンが {count} 個検出されました")

# 典型的な日本語エンコーディングでバイト「0xef」の統計
if b'\xef' in content:
    ef_count = content.count(b'\xef')
    print(f"\nバイト 0xef (UTF-8の一部) の出現回数: {ef_count}")
    
    # 0xefの後の2バイトのパターンを調査
    ef_patterns = {}
    for i in range(len(content) - 2):
        if content[i] == 0xef:
            pattern = content[i:i+3]
            ef_patterns[pattern] = ef_patterns.get(pattern, 0) + 1
    
    print("最も一般的な 0xef で始まるパターン:")
    for pattern, count in sorted(ef_patterns.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {pattern.hex()} : {count}回")

# 最終的な診断
# UTF-8 の置換文字 (U+FFFD) は \xef\xbf\xbd としてエンコードされる
if content.count(b'\xef\xbf\xbd') > 0:
    utf8_replacement_count = content.count(b'\xef\xbf\xbd')
    percent = (utf8_replacement_count * 3 / len(content)) * 100
    print(f"\nUTF-8の置換文字 (�) の数: {utf8_replacement_count} (ファイルの約 {percent:.1f}%)")
    
    if percent > 10:
        print("診断: このファイルは元々cp932/Shift-JISだったテキストがUTF-8として誤って解釈された可能性が高いです。")
    
# 正しいCSVカラム数の推定（最初の数行からカンマの数をカウント）
print("\nCSV構造の分析:")
lines = content.split(b'\n')[:5]
for i, line in enumerate(lines):
    if i == 0:
        comma_count = line.count(b',')
        expected_columns = comma_count + 1
        print(f"ヘッダー行のカラム数の推定: {expected_columns}")
    if len(line) > 5:  # 空行でない場合
        actual_columns = line.count(b',') + 1
        print(f"行 {i+1} のカラム数: {actual_columns} {'(OK)' if actual_columns == expected_columns else '(不一致)'}")

# utf-8 → cp932 変換で直したファイルを確認
recovered_file = 'data/recovered/recovered_utf-8_to_cp932.csv'
if os.path.exists(recovered_file):
    print(f"\n修復後のファイル ({recovered_file}) の分析:")
    try:
        df = pd.read_csv(recovered_file, encoding='cp932', nrows=1)
        print(f"カラム数: {len(df.columns)}")
        print(f"カラム名（最初の5つ）: {df.columns[:5].tolist()}")
    except Exception as e:
        print(f"修復ファイルの読み込みエラー: {e}")

print("\n結論:")
print("このCSVファイルはShift-JIS/cp932でエンコードされたデータがUTF-8として誤って解釈された可能性が高いです。")
print("解決策: UTF-8としてデコードしてcp932として再エンコードすると、元の文字に近づく可能性があります。") 