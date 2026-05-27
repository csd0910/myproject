import pandas as pd
import os
import datetime

def safe_to_csv(df_sub, path, label, raw_len=None):
    try:
        df_sub.to_csv(path, index=False, encoding='cp932')
        if raw_len is not None:
            print(f"SUCCESS: {label} ({raw_len}件 -> 除外後 {len(df_sub)}件) を出力しました -> {path}", flush=True)
        else:
            print(f"SUCCESS: {label} ({len(df_sub)}件) を出力しました -> {path}", flush=True)
    except Exception:
        now = datetime.datetime.now().strftime("%H%M%S")
        alt_path = path.replace(".csv", f"_{now}.csv")
        df_sub.to_csv(alt_path, index=False, encoding='cp932')
        if raw_len is not None:
            print(f"WARNING: ファイルが開かれているため、別名で保存しました: {label} ({raw_len}件 -> 除外後 {len(df_sub)}件) -> {alt_path}", flush=True)
        else:
            print(f"WARNING: ファイルが開かれているため、別名で保存しました: {label} ({len(df_sub)}件) -> {alt_path}", flush=True)

def extract_subclass():
    input_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\0512 大分類9と11と13　商品一覧(em310)_PSE付き.csv"
    output_dir = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\小分類抽出"
    
    if not os.path.exists(input_path):
        print(f"エラー: 入力ファイルが見つかりません -> {input_path}")
        return
    
    # 出力フォルダの作成
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"INFO: 出力フォルダを作成しました -> {output_dir}")
        
    print("INFO: データを読み込んでいます...", flush=True)
    df = pd.read_csv(input_path, encoding='cp932')
    
    # AI列は0始まりで34番目のインデックス（小分類名称）
    subclass_col = df.columns[34]
    ak_col = df.columns[36]
    print(f"INFO: 列名称の確認 -> AI列: '{subclass_col}', AK列: '{ak_col}'", flush=True)
    
    # 1. 掃除機・クリーナー の抽出 & AK列フィルタ（関連品・紙パック除外）
    df_cleaner_raw = df[df[subclass_col] == '掃除機・クリーナー']
    df_cleaner = df_cleaner_raw[~df_cleaner_raw[ak_col].astype(str).str.contains("関連品|紙パック", na=False)]
    path_cleaner = os.path.join(output_dir, "01_掃除機・クリーナー.csv")
    safe_to_csv(df_cleaner, path_cleaner, "掃除機・クリーナー", df_cleaner_raw.shape[0])
    
    # 2. バッテリー・充電器 の抽出 & AK列フィルタ（関連品・紙パック除外）
    df_battery_raw = df[df[subclass_col] == 'バッテリー・充電器']
    df_battery = df_battery_raw[~df_battery_raw[ak_col].astype(str).str.contains("関連品|紙パック", na=False)]
    path_battery = os.path.join(output_dir, "02_バッテリー・充電器.csv")
    safe_to_csv(df_battery, path_battery, "バッテリー・充電器", df_battery_raw.shape[0])
    
    # 3. 両方をまとめた一括ファイル
    df_combined = pd.concat([df_cleaner, df_battery])
    path_combined = os.path.join(output_dir, "03_掃除機とバッテリー_一括抽出.csv")
    safe_to_csv(df_combined, path_combined, "一括抽出ファイル")

if __name__ == "__main__":
    extract_subclass()
