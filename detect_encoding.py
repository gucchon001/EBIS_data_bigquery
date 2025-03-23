import chardet

# 入力ファイルのパス
input_file = 'data/AE_SSresult/202503231824_cv_attr.csv'

# ファイルの最初の部分を読み込んでエンコーディングを検出
with open(input_file, 'rb') as f:
    raw_data = f.read(10000)  # 最初の10000バイトを読み込む
    result = chardet.detect(raw_data)
    detected_encoding = result['encoding']
    confidence = result['confidence']

print(f"検出されたエンコーディング: {detected_encoding}")
print(f"信頼度: {confidence}")

# ファイルの最初のバイトを16進数で表示
with open(input_file, 'rb') as f:
    header_bytes = f.read(30)  # 最初の30バイトを読み込む
    hex_header = ' '.join(f'{b:02x}' for b in header_bytes)
    print(f"\nファイルの最初の30バイト (16進数):")
    print(hex_header)

# 全体のファイルでも確認
with open(input_file, 'rb') as f:
    raw_data = f.read()
    result = chardet.detect(raw_data)
    detected_encoding_full = result['encoding']
    confidence_full = result['confidence']

print(f"\nファイル全体で検出されたエンコーディング: {detected_encoding_full}")
print(f"信頼度: {confidence_full}")

# いくつかの一般的な日本語エンコーディングも試してみる
encodings = ['utf-8', 'cp932', 'shift_jis', 'euc_jp', 'iso-2022-jp', 'utf-16', 'utf-16-le', 'utf-16-be']
print("\n各エンコーディングでの読み込み試行:")

for encoding in encodings:
    try:
        with open(input_file, 'rb') as f:
            content = f.read(200)  # 最初の200バイトだけを試す
            # デコードを試みる
            decoded = content.decode(encoding)
            print(f"✓ {encoding}: 正常にデコードできました")
            print(f"  最初の20文字: {decoded[:20]}")
    except UnicodeDecodeError as e:
        print(f"✗ {encoding}: デコードエラー - {e}") 