import pandas as pd

# 試すエンコーディングのリスト
encodings = ['utf-8', 'cp932', 'shift_jis', 'euc_jp', 'iso-2022-jp', 'utf-16']

for encoding in encodings:
    try:
        print(f"\n{encoding}エンコーディングで試行中...")
        # CSVファイルを読み込む
        df = pd.read_csv('data/AE_SSresult/202503231824_cv_attr.csv', encoding=encoding, nrows=3)
        
        # カラム名を表示
        print("カラム名:")
        print(df.columns.tolist())
        
        # 最初の行を表示
        print("\n最初のデータ:")
        print(df.iloc[0])
        
        print(f"\n{encoding}エンコーディングで正常に読み込みました！")
        break
        
    except Exception as e:
        print(f"エラー（{encoding}）: {e}")

else:
    print("\nすべてのエンコーディングで失敗しました。") 