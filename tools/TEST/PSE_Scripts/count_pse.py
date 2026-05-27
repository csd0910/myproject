import pandas as pd
import os

dir_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\20260526"
files = [
    "0512 大分類46と47と48　商品一覧(em310)_PSE付き.csv",
    "0512 大分類9と11と13　商品一覧(em310)_PSE付き.csv"
]

for f in files:
    path = os.path.join(dir_path, f)
    print(f"--- File: {f} ---")
    if os.path.exists(path):
        try:
            # 必要な列だけ読み込むことでメモリを節約
            df = pd.read_csv(path, encoding="cp932", usecols=["PSE判定"])
            total = len(df)
            target = len(df[df["PSE判定"] == "PSE対象"])
            print(f"総件数: {total:,} 件")
            print(f"PSE対象: {target:,} 件")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"File not found.")
