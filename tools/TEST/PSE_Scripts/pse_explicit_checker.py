import pandas as pd
import unicodedata
import os
import glob

def normalize_text(text):
    if pd.isna(text): return ""
    # 半角カナや全角英数を正規化（ＰＳＥ -> pse, ﾏｰｸ -> マーク）
    return unicodedata.normalize('NFKC', str(text)).lower()

def update_explicit_pse(file_path, am_idx, an_idx, ao_idx):
    print(f"INFO: ファイルを読み込んでいます -> {os.path.basename(file_path)}")
    df = pd.read_csv(file_path, encoding='cp932')
    
    if "PSE判定" not in df.columns:
        print("Error: PSE判定列が見つかりません。")
        return df
        
    updated_in = 0
    updated_out = 0
    
    # 対象とするキーワード群
    in_kws = ["pse対応", "pse認証取得", "pseマーク取得", "pseマーク付", "pse適合", "pse取得", "pse付"]
    out_kws = ["pse対象外", "pse非対象", "pse不要", "pse認証不要", "pseマーク不要"]
    
    print("INFO: AM・AN・AO列の明記テキストを精査中...")
    for i in range(len(df)):
        am_val = normalize_text(df.iloc[i, am_idx])
        an_val = normalize_text(df.iloc[i, an_idx])
        ao_val = normalize_text(df.iloc[i, ao_idx])
        
        combined_text = f"{am_val} {an_val} {ao_val}"
        
        if "pse" in combined_text:
            # 対象外の文言が含まれているか
            if any(k in combined_text for k in out_kws):
                if df.at[i, "PSE判定"] != "PSE対象外":
                    df.at[i, "PSE判定"] = "PSE対象外"
                    df.at[i, "PSE判定根拠"] = "明記あり: PSE対象外/不要"
                    df.at[i, "PSEキーワード"] = "PSE対象外"
                    df.at[i, "PSE要人手確認"] = 0
                    updated_out += 1
            # 対象の文言が含まれているか
            elif any(k in combined_text for k in in_kws):
                if df.at[i, "PSE判定"] != "PSE対象":
                    df.at[i, "PSE判定"] = "PSE対象"
                    df.at[i, "PSE判定根拠"] = "明記あり: PSEマーク/認証取得済"
                    df.at[i, "PSEキーワード"] = "PSE取得済"
                    df.at[i, "PSE要人手確認"] = 1
                    updated_in += 1

    print(f"  -> 明記により「PSE対象」に上書き: {updated_in} 件")
    print(f"  -> 明記により「PSE対象外」に上書き: {updated_out} 件")
    
    print("INFO: 上書き保存しています...")
    df.to_csv(file_path, index=False, encoding='cp932')
    return df

def resplit_files(df, target_dir, base_name, supplier_col_idx):
    print(f"INFO: 既存の分割ファイルをクリアしています...")
    old_files = glob.glob(os.path.join(target_dir, "*.csv"))
    for f in old_files:
        if os.path.basename(f) != base_name:
            try:
                os.remove(f)
            except Exception:
                pass
            
    print(f"INFO: 仕入先ごとに再分割しています...")
    supplier_col = df.columns[supplier_col_idx]
    suppliers = df[supplier_col].unique()
    
    pure_base_name = base_name.replace(".csv", "")
    
    for supplier in suppliers:
        if pd.isna(supplier) or str(supplier).strip() == "":
            supplier_name = "仕入先不明"
        else:
            supplier_name = str(supplier).replace("/", "／").replace("\\", "＼").replace(":", "：").replace("*", "＊").strip()
            
        new_file_name = f"{pure_base_name}_{supplier_name}.csv"
        save_path = os.path.join(target_dir, new_file_name)
        
        supplier_df = df[df[supplier_col] == supplier]
        try:
            supplier_df.to_csv(save_path, index=False, encoding='cp932')
        except Exception:
            print(f"  -> Warning: {new_file_name} が開かれているため上書きをスキップしました。")

if __name__ == "__main__":
    # --- 大分類 9, 11, 13 ---
    dir_9 = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\大分類9と11と13"
    file_9 = os.path.join(dir_9, "0512 大分類9と11と13　商品一覧(em310)_PSE付き.csv")
    if os.path.exists(file_9):
        # AM=38, AN=39, AO=40, 仕入先=10
        df_9 = update_explicit_pse(file_9, 38, 39, 40)
        resplit_files(df_9, dir_9, "0512 大分類9と11と13　商品一覧(em310)_PSE付き.csv", 10)
        print("大分類 9, 11, 13 の再精査・分割完了\n")

    # --- 大分類 46, 47, 48 ---
    dir_46 = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\大分類46と47と48"
    file_46 = os.path.join(dir_46, "大分類46と47と48_PSE付き.csv")
    if os.path.exists(file_46):
        # AM=37, AN=38, AO=39, 仕入先=9
        df_46 = update_explicit_pse(file_46, 37, 38, 39)
        resplit_files(df_46, dir_46, "大分類46と47と48_PSE付き.csv", 9)
        print("大分類 46, 47, 48 の再精査・分割完了\n")
        
    print("すべての追加処理が完了しました。")
