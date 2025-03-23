import os
import pandas as pd
from pathlib import Path

# 入力ファイルのパス
input_file = 'data/AE_SSresult/202503231824_cv_attr.csv'

# ファイルの先頭バイトを16進数で表示
with open(input_file, 'rb') as f:
    header_bytes = f.read(100)
    hex_header = ' '.join(f'{b:02x}' for b in header_bytes)
    print(f"ファイルの最初の100バイト (16進数):")
    print(hex_header)

# UTF-8で保存された破損したShift-JISファイルの可能性を検証
output_dir = Path('data/recovered')
os.makedirs(output_dir, exist_ok=True)

# 元のファイルをバイナリで読み込む
with open(input_file, 'rb') as f:
    content = f.read()

# latin1 (ISO-8859-1) は任意のバイト列を受け入れるため、有効な復元手段
print("\n\n特別な変換: バイナリ → latin1 → cp932")
try:
    # バイナリ → latin1 (どんなバイト値も受け付ける) → cp932
    output_file = output_dir / "recovered_binary_latin1_cp932.csv"
    decoded = content.decode('latin1')  # どんなバイト列も文字として受け入れる
    encoded = decoded.encode('cp932', errors='replace')
    
    with open(output_file, 'wb') as f:
        f.write(encoded)
    
    # cp932として読み込んでみる
    df = pd.read_csv(output_file, encoding='cp932', nrows=3)
    print(f"カラム名 ({len(df.columns)} 列):")
    if len(df.columns) > 5:
        print(f"  {df.columns[:5].tolist()} ... (他 {len(df.columns)-5} 列)")
    else:
        print(f"  {df.columns.tolist()}")
    
    # 最初の行も表示
    print("\n最初の行:")
    if len(df.columns) > 5:
        first_row = df.iloc[0]
        for col in df.columns[:5]:
            print(f"  {col}: {first_row[col]}")
        print(f"  ... (他 {len(df.columns)-5} 列)")
    else:
        print(df.iloc[0])
    
except Exception as e:
    print(f"特別な変換失敗: {e}")

# 他の可能性も試す
print("\n他のエンコーディング変換も試します...")

# よく使われる日本語エンコーディングの組み合わせ
encodings = [
    ('utf-8', 'cp932'),
    ('latin1', 'utf-8'),
    ('cp932', 'utf-8'),
    ('shift_jis', 'utf-8')
]

for src_enc, dst_enc in encodings:
    try:
        # 特殊な組み合わせでファイルを処理
        output_file = output_dir / f"recovered_{src_enc}_to_{dst_enc}.csv"
        
        # latin1経由での変換
        if src_enc != 'latin1':
            with open(input_file, 'rb') as f:
                content = f.read()
                decoded = content.decode(src_enc, errors='replace')
        else:
            decoded = content.decode('latin1')
        
        encoded = decoded.encode(dst_enc, errors='replace')
        
        with open(output_file, 'wb') as f:
            f.write(encoded)
        
        print(f"\n変換: {src_enc} → {dst_enc}")
        print(f"保存先: {output_file}")
        
        # 変換後のファイルをデータフレームとして読み込む
        df = pd.read_csv(output_file, encoding=dst_enc, nrows=2)
        print(f"カラム数: {len(df.columns)}")
        print(f"最初の5つのカラム: {df.columns[:5].tolist() if len(df.columns) > 5 else df.columns.tolist()}")
    
    except Exception as e:
        print(f"変換に失敗: {src_enc} → {dst_enc}: {e}") 