import pandas as pd
import os
import chardet

# 入力ファイルと出力ファイルのパス
input_file = 'data/AE_SSresult/202503231824_cv_attr.csv'
output_file = 'data/AE_SSresult/202503231824_cv_attr_utf8.csv'

# ファイルの最初の数千バイトを読み込んでエンコーディングを検出
with open(input_file, 'rb') as f:
    raw_data = f.read(10000)
    result = chardet.detect(raw_data)
    detected_encoding = result['encoding']
    confidence = result['confidence']

print(f"検出されたエンコーディング: {detected_encoding} (信頼度: {confidence})")

try:
    # バイナリモードでファイルを読み込む
    with open(input_file, 'rb') as f:
        content = f.read()
    
    # UTF-8でファイルを保存
    with open(output_file, 'wb') as f:
        f.write(content.decode(detected_encoding).encode('utf-8'))
    
    print(f"ファイルを {detected_encoding} から UTF-8 に変換し、{output_file} に保存しました")
    
    # 変換後のファイルを読み込んでみる
    df = pd.read_csv(output_file, encoding='utf-8', nrows=3)
    print("\nUTF-8で変換後のファイルを読み込みました")
    print("カラム名:")
    print(df.columns.tolist())
    print("\n最初のデータ:")
    print(df.iloc[0])
    
except Exception as e:
    print(f"エラーが発生しました: {e}")
    
    # エンコーディングリストを試す
    print("\n複数のエンコーディングで試行します...")
    encodings = ['utf-8', 'cp932', 'shift_jis', 'euc_jp', 'iso-2022-jp', 'utf-16']
    
    for encoding in encodings:
        try:
            # バイナリモードでファイルを読み込む
            with open(input_file, 'rb') as f:
                content = f.read()
            
            # デコード試行
            decoded = content.decode(encoding)
            
            # UTF-8でファイルを保存
            output_file_enc = f'data/AE_SSresult/202503231824_cv_attr_{encoding}.csv'
            with open(output_file_enc, 'w', encoding='utf-8') as f:
                f.write(decoded)
            
            print(f"{encoding} で正常にデコードでき、{output_file_enc} に保存しました")
            
            # 変換後のファイルを読み込んでみる
            df = pd.read_csv(output_file_enc, encoding='utf-8', nrows=3)
            print(f"\n{encoding}から変換後のファイルを読み込みました")
            print("カラム名:")
            print(df.columns.tolist())
            print("\n最初のデータ:")
            print(df.iloc[0])
            
        except Exception as e:
            print(f"エラー（{encoding}）: {e}") 