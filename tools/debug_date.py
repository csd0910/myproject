import pandas as pd
import sys

csv_path = r"\\10.85.33.230\01_全社共有\システム統括部\業改室\★大宮システム部\（NAS）伊藤\残業調査\岸川\岸川_ログ検索結果-20260401_20260404.csv"

for enc in ['cp932', 'utf-8', 'utf-8-sig', 'shift_jis']:
    try:
        df = pd.read_csv(csv_path, encoding=enc, engine='python', on_bad_lines='skip')
        print(f"Loaded with {enc}")
        break
    except:
        pass

print("Columns:", df.columns.tolist())
col_datetime = None
for c in df.columns:
    if '日時' in c:
        col_datetime = c
        break

if not col_datetime:
    col_datetime = df.columns[6]

print(f"Datetime col: {col_datetime}")
print(df[col_datetime].head(5))
print(df[col_datetime].tail(5))

df['日時'] = pd.to_datetime(df[col_datetime])
df['日付_log'] = df['日時'].dt.normalize()
print("日付のユニーク値:")
print(df['日付_log'].unique())
