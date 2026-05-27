import pandas as pd
import os

file_path = r'C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\20260526\0512 大分類46と47と48　商品一覧(em310)_PSE付き.csv'

if os.path.exists(file_path):
    print('ファイルを読み込んでいます...')
    df = pd.read_csv(file_path, encoding='cp932', low_memory=False)
    
    cols_to_drop = [c for c in df.columns if 'URL_TEMP' in c]
    if cols_to_drop:
        print(f'不要な列を削除します: {cols_to_drop}')
        df = df.drop(columns=cols_to_drop)
        
        print('上書き保存しています...')
        df.to_csv(file_path, index=False, encoding='cp932')
        print('既存データの修正が完了しました！')
    else:
        print('すでに修正済み、または不要な列は見つかりませんでした。')
else:
    print('ファイルが見つかりません。')
