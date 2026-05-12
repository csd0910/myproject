import pandas as pd
import os

def repair_kishikawa_0415():
    good_path = r'C:\Users\フォーレスト026\Desktop\伊藤作業用\残業調査\岸川\岸川_ログ検索結果-20260407_20260411.csv'
    bad_path = r'C:\Users\フォーレスト026\Desktop\伊藤作業用\残業調査\岸川\岸川_ログ検索結果-20260415.csv'
    
    print("Reading GOOD file header...")
    df_good = pd.read_csv(good_path, encoding='cp932', engine='python', nrows=0)
    good_cols = list(df_good.columns)
    
    print("Reading BAD file data...")
    df_bad = pd.read_csv(bad_path, encoding='cp932', engine='python', on_bad_lines='skip')
    
    # バックアップ作成
    backup_path = bad_path + ".bak"
    if not os.path.exists(backup_path):
        os.rename(bad_path, backup_path)
        print(f"Created backup: {backup_path}")
    
    # 並び替えロジック
    # 分析結果: BADの16列目(Index 16)がタイトル、GOODは14列目(Index 14)がタイトル
    # また、BADの12列目はプログラム名で合っている。
    
    # 新しいデータフレームを作成（GOODと同じ列数・列名）
    df_repaired = pd.DataFrame(columns=good_cols)
    
    # 共通する列をコピー（ズレていない前提の列）
    for i in range(min(len(df_bad.columns), len(good_cols))):
        if i == 14: # タイトル列
            # BADの16列目から持ってくる
            if len(df_bad.columns) > 16:
                df_repaired[good_cols[i]] = df_bad.iloc[:, 16].fillna(df_bad.iloc[:, 15])
            else:
                df_repaired[good_cols[i]] = df_bad.iloc[:, i]
        else:
            df_repaired[good_cols[i]] = df_bad.iloc[:, i]
            
    # 保存
    df_repaired.to_csv(bad_path, index=False, encoding='cp932')
    print(f"Successfully repaired {bad_path} to match GOOD format.")

if __name__ == "__main__":
    repair_kishikawa_0415()
