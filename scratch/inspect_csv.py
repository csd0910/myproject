import pandas as pd
import os

def find_col(df, keywords, fallback_index=None):
    for col in df.columns:
        for kw in keywords:
            if kw in col:
                return col
    if fallback_index is not None and fallback_index < len(df.columns):
        return df.columns[fallback_index]
    return df.columns[0]

def test(path):
    if not os.path.exists(path):
        print(f"Not found: {path}")
        return
    try:
        # Load with cp932 to match script behavior
        df = pd.read_csv(path, encoding='cp932', engine='python', on_bad_lines='skip', nrows=10)
        c_dt = find_col(df, ['日時', '時間', '発生'], 6)
        c_title = find_col(df, ['タイトル', 'ウィンドウ名', '件名'], 14)
        
        print(f"File: {os.path.basename(path)}")
        print(f"  Datetime Col: '{c_dt}' (Index: {df.columns.get_loc(c_dt)})")
        print(f"  Title Col: '{c_title}' (Index: {df.columns.get_loc(c_title)})")
        
        # Check first few non-empty titles
        print(f"  Sample Titles from CSV (Indices 14, 15, 16):")
        for i in range(1, min(len(df), 5)):
            val14 = df.iloc[i, 14]
            val15 = df.iloc[i, 15]
            val16 = df.iloc[i, 16]
            print(f"    Line {i}: [14]=\"{val14}\", [15]=\"{val15}\", [16]=\"{val16}\"")
            
    except Exception as e:
        print(f"Error processing {path}: {e}")

print("--- Start Inspection ---")
test(r'C:\Users\フォーレスト026\Desktop\伊藤作業用\残業調査\成川\成川_ログ検索結果-20260415.csv')
test(r'C:\Users\フォーレスト026\Desktop\伊藤作業用\残業調査\岸川\岸川_ログ検索結果-20260415.csv')
print("--- End Inspection ---")
