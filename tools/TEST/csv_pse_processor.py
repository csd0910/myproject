import pandas as pd
import os
import time
import datetime

# ==========================================
# 設定エリア
# ==========================================
input_csv_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\0512 大分類9と11と13　商品一覧(em310).csv" 
pse_master_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\PSE判定用ルールマスタ.csv"
exclude_master_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\除外マスタ.csv"

# ExcelのAN列(40番目), AO列(41番目)のインデックス
AN_IDX = 39
AO_IDX = 40

# ==========================================
# 処理メイン
# ==========================================

def process_pse_csv(input_path, master_path, exclude_path):
    if not os.path.exists(input_path):
        print(f"エラー: 入力ファイルが見つかりません -> {input_path}", flush=True)
        return
    
    # 各種マスタの読み込み
    print(f"INFO: マスタを読み込んでいます...", flush=True)
    master_df = pd.read_csv(master_path, encoding='cp932') if os.path.exists(master_path) else None
    exclude_df = pd.read_csv(exclude_path, encoding='cp932') if os.path.exists(exclude_path) else None
    excludes = exclude_df.to_dict('records') if exclude_df is not None else []
    masters = master_df.to_dict('records') if master_df is not None else []

    # メインCSVの読み込み
    print(f"INFO: メインファイルを読み込んでいます...", flush=True)
    df = pd.read_csv(input_path, encoding='cp932')
    current_encoding = 'cp932'

    jisya_code_col = df.columns[0]
    base_url = "https://www.forest.co.jp/Forestway/gi/"
    df['自社商品URL'] = base_url + df[jisya_code_col].astype(str) + "/"

    # 判定に使用する列の特定
    name_cols = [c for c in df.columns if any(k in c for k in ["商品名", "品目名"])]
    cat_cols = [c for c in df.columns if any(k in c for k in ["分類", "カテゴリ"])]
    desc_cols = [c for c in df.columns if any(k in c for k in ["説明", "情報", "備考"])]
    
    total_rows = len(df)
    print(f"INFO: 新ロジック（AN/AO列活用）で全 {total_rows} 件の判定を開始します...", flush=True)

    start_time = time.time()
    processed_count = 0

    def judge_pse(row):
        nonlocal processed_count
        processed_count += 1
        
        # 進捗表示
        if processed_count % 500 == 0 or processed_count == total_rows:
            elapsed = time.time() - start_time
            speed = processed_count / elapsed if elapsed > 0 else 0
            remaining = (total_rows - processed_count) / speed if speed > 0 else 0
            rem_time = str(datetime.timedelta(seconds=int(remaining)))
            ela_time = str(datetime.timedelta(seconds=int(elapsed)))
            print(f"\r進捗: {processed_count}/{total_rows} ({processed_count/total_rows*100:>.1f}%) | 経過: {ela_time} | 残り予測: {rem_time}", end="", flush=True)

        res_judge, res_type, res_cat, res_item, res_reason, res_kw, res_check = "PSE対象外", "", "", "", "", "", 0

        # テキストの準備
        an_text = str(row.iloc[AN_IDX]).lower() if len(row) > AN_IDX else ""
        ao_text = str(row.iloc[AO_IDX]).lower() if len(row) > AO_IDX else ""
        name_text = " ".join([str(row[c]) for c in name_cols if c in row]).lower()
        cat_text = " ".join([str(row[c]) for c in cat_cols if c in row]).lower()
        desc_text = " ".join([str(row[c]) for c in desc_cols if c in row]).lower()
        full_text = f"{name_text} {cat_text} {desc_text} {an_text} {ao_text}"

        # --- STEP 1: AO列による超優先除外 ---
        ao_exclude_kws = ["医療機器", "管理医療機器", "血圧計", "体温計", "パルスオキシメータ", "自動車用", "車載用", "産業用", "工業用"]
        for kw in ao_exclude_kws:
            if kw in ao_text:
                res_reason = f"AO列優先除外: {kw}"
                res_kw = kw
                return pd.Series([res_judge, res_type, res_cat, res_item, res_reason, res_kw, res_check])

        # --- STEP 2: 除外マスタによる判定 ---
        for ex in excludes:
            kw = str(ex["keyword"]).strip().lower()
            if not kw: continue
            target = full_text
            if ex["keyword_type"] == "name": target = name_text
            elif ex["keyword_type"] == "category": target = cat_text
            
            if kw in target:
                res_reason = f"除外理由: {ex['exclude_reason']} / キーワード: {kw}"
                res_kw = kw
                return pd.Series([res_judge, res_type, res_cat, res_item, res_reason, res_kw, res_check])

        # --- STEP 3: 電源方式の分類 (AN列) ---
        power_mode = "不明"
        if any(k in an_text for k in ["ac100v", "交流100v", "ac電源", "コンセント"]):
            power_mode = "AC駆動"
        elif any(k in an_text for k in ["usb給電", "dc5v", "dc12v", "乾電池"]):
            power_mode = "DC駆動"

        # --- STEP 4: 対象マスタ（457品目）との照合 ---
        for m in masters:
            keywords = [str(m["base_keyword"])] + str(m["extra_keywords"]).split(",")
            for kw in keywords:
                kw = kw.strip().lower()
                if kw and kw in full_text:
                    if power_mode == "DC駆動":
                        res_judge = "PSE対象外"
                        res_reason = f"品目一致「{m['pse_item_name']}」だがDC駆動のため対象外"
                        res_kw = kw
                        res_check = 1 # ACアダプタ同梱の可能性があるため要確認
                    else:
                        res_judge = "PSE対象"
                        res_type, res_cat, res_item = m["pse_type"], m["pse_category"], m["pse_item_name"]
                        res_reason = f"対象品目「{m['pse_item_name']}」に一致 / 電源: {power_mode}"
                        res_kw = kw
                        if m["pse_type"] == "特定" or kw in ["扇風機", "ストーブ", "モバイルバッテリー"]:
                            res_check = 1
                    return pd.Series([res_judge, res_type, res_cat, res_item, res_reason, res_kw, res_check])
        
        # ヒットなしだがAC駆動の場合は要確認
        if power_mode == "AC駆動":
            res_check = 1
            res_reason = "AC100V駆動だが品目未ヒットのため要確認"

        return pd.Series([res_judge, res_type, res_cat, res_item, res_reason, res_kw, res_check])

    # 判定の実行
    judged_cols = df.apply(judge_pse, axis=1)
    judged_cols.columns = ["PSE判定", "PSE種別", "PSE対象区分", "PSE対象品目名", "PSE判定根拠", "PSEキーワード", "PSE要人手確認"]
    df = pd.concat([df, judged_cols], axis=1)
    
    print("\nINFO: 判定完了。保存しています...", flush=True)
    output_path = input_path.replace(".csv", "_PSE付き.csv")
    try:
        df.to_csv(output_path, index=False, encoding=current_encoding)
        print(f"完了しました: {output_path}", flush=True)
    except Exception:
        # ファイルが開いている場合は、タイムスタンプを付けて保存
        now = datetime.datetime.now().strftime("%H%M%S")
        alt_path = output_path.replace(".csv", f"_{now}.csv")
        df.to_csv(alt_path, index=False, encoding=current_encoding)
        print(f"警告: 元のファイルが開かれていたため、別名で保存しました: {alt_path}", flush=True)

if __name__ == "__main__":
    process_pse_csv(input_csv_path, pse_master_path, exclude_master_path)
