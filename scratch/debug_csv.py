import pandas as pd

csv_path = r"\\10.85.33.230\01_全社共有\システム統括部\業改室\★大宮システム部\（NAS）伊藤\残業調査\岸川\岸川_ログ検索結果-20260401_20260404.csv"

for enc in ['cp932', 'utf-8']:
    try:
        df = pd.read_csv(csv_path, encoding=enc, engine='python', on_bad_lines='skip')
        break
    except:
        pass

print("Total rows:", len(df))
cols_to_show = [6, 10, 11, 12, 14]
for c in cols_to_show:
    if c < len(df.columns):
        print(f"Col {c}: {df.columns[c]}")

print(df.iloc[:10, [c for c in cols_to_show if c < len(df.columns)]])
