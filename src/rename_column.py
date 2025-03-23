import pandas as pd

# CSVファイルを読み込む
df = pd.read_csv('./data/AE_SSresult/202503231824_cv_attr.csv', encoding='cp932')

# カラム名を変更
df.rename(columns={'売上金額': '応募ID'}, inplace=True)

# 新しいファイルに保存
df.to_csv('./data/AE_SSresult/202503231824_cv_attr_renamed.csv', index=False, encoding='cp932')
print("カラム名の変更が完了しました。") 