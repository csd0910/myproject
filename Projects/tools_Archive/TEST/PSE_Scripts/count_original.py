import pandas as pd

files = [
    r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\0512 大分類46と47と48　商品一覧(em310).csv",
    r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\0512 大分類9と11と13　商品一覧(em310).csv"
]

print("オリジナルの件数をカウントします...")
for path in files:
    try:
        # 処理速度を上げるため、最初の1列だけを読み込んで行数を取得します
        df = pd.read_csv(path, encoding="cp932", usecols=[0])
        print(f"Original Count: {len(df):,} for {path}")
    except Exception as e:
        print(f"Error on {path}: {e}")
