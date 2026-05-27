import pandas as pd
import os
import time
import datetime
import unicodedata

# ==========================================
# 設定エリア
# ==========================================
input_csv_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\0512 大分類9と11と13　商品一覧(em310).csv" 
pse_master_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\PSE判定用ルールマスタ.csv"
exclude_master_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\除外マスタ.csv"

# Excelの列インデックス
P_IDX = 15 # P列 (サイト名)
Q_IDX = 16 # Q列 (商品コード)
AK_IDX = 36
AM_IDX = 38
AN_IDX = 39
AO_IDX = 40

# ==========================================
# 処理メイン
# ==========================================

def generate_url(row):
    """P列とQ列に基づき、各サイト専用のURLを生成する。添付の除外サイトは空欄にする。"""
    site_name = str(row.iloc[P_IDX]) if len(row) > P_IDX else ""
    code = str(row.iloc[Q_IDX]).lower() if len(row) > Q_IDX else ""
    
    if not code: return ""

    # --- 除外サイト判定 (画像で指定されたサイト) ---
    exclude_keywords = ["買い物コネクト", "カタログ", "マイストック", "店舗用", "パーソナル"]
    if any(k in site_name for k in exclude_keywords):
        return ""

    # --- 特定サイト判定 (専用URL) ---
    # 1. ココデカウ
    if "ココデカウ（楽天市場）" in site_name:
        return f"https://item.rakuten.co.jp/cocodecow/{code}/"
    elif "ココデカウ（Yahoo!ショッピング）" in site_name:
        return f"https://store.shopping.yahoo.co.jp/cocodecow/{code}.html"
    
    # 2. JetPrice
    elif "ＪｅｔＰｒｉｃｅ　楽天店" in site_name:
        return f"https://item.rakuten.co.jp/jetprice/{code}/"
    elif "ＪｅｔＰｒｉｃｅ　yahoo店" in site_name:
        return f"https://store.shopping.yahoo.co.jp/jetprice/{code}.html"
    
    # 3. BUNGU便
    elif "BUNGU便 楽天市場店" in site_name:
        return f"https://item.rakuten.co.jp/bungubin/{code}/"
    elif "Yahoo!BUNGU便" in site_name:
        return f"https://store.shopping.yahoo.co.jp/bungubin/{code}.html"
    
    # --- 上記以外はForestwayとして生成 ---
    return f"https://www.forest.co.jp/Forestway/gi/{code}/"

def process_pse_csv(input_path, master_path, exclude_path, output_dir=None):
    if not os.path.exists(input_path):
        print(f"エラー: 入力ファイルが見つかりません -> {input_path}", flush=True)
        return
    
    # マスタの読み込み
    master_df = pd.read_csv(master_path, encoding='cp932') if os.path.exists(master_path) else None
    exclude_df = pd.read_csv(exclude_path, encoding='cp932') if os.path.exists(exclude_path) else None
    excludes = exclude_df.to_dict('records') if exclude_df is not None else []
    masters = master_df.to_dict('records') if master_df is not None else []

    # メインCSVの読み込み
    print(f"INFO: ファイルを読み込んでいます...", flush=True)
    df = pd.read_csv(input_path, encoding='cp932')
    current_encoding = 'cp932'

    # 処理前の元々の列名を保存しておく
    original_columns = df.columns.tolist()

    # URLの生成 (新ロジック適用)
    print(f"INFO: サイト名(P列)に応じたURLを生成中...", flush=True)
    df['自社商品URL_TEMP'] = df.apply(generate_url, axis=1)

    # 判定に使用する列の特定
    name_cols = [c for c in df.columns if any(k in c for k in ["商品名", "品目名"])]
    cat_cols = [c for c in df.columns if any(k in c for k in ["分類", "カテゴリ"])]
    desc_cols = [c for c in df.columns if any(k in c for k in ["説明", "情報", "備考"])]
    
    total_rows = len(df)
    print(f"INFO: 全 {total_rows} 件のPSE判定を開始します...", flush=True)

    start_time = time.time()
    processed_count = 0

    def judge_pse(row):
        nonlocal processed_count
        processed_count += 1
        
        if processed_count % 500 == 0 or processed_count == total_rows:
            elapsed = time.time() - start_time
            speed = processed_count / elapsed if elapsed > 0 else 0
            remaining = (total_rows - processed_count) / speed if speed > 0 else 0
            rem_time = str(datetime.timedelta(seconds=int(remaining)))
            ela_time = str(datetime.timedelta(seconds=int(elapsed)))
            print(f"\r進捗: {processed_count}/{total_rows} ({processed_count/total_rows*100:>.1f}%) | 経過: {ela_time} | 残り予測: {rem_time}", end="", flush=True)

        res_judge, res_type, res_cat, res_item, res_reason, res_kw, res_check = "PSE対象外", "", "", "", "", "", 0

        ak_text = unicodedata.normalize('NFKC', str(row.iloc[AK_IDX])).lower() if len(row) > AK_IDX else ""
        am_text = unicodedata.normalize('NFKC', str(row.iloc[AM_IDX])).lower() if len(row) > AM_IDX else ""
        an_text = unicodedata.normalize('NFKC', str(row.iloc[AN_IDX])).lower() if len(row) > AN_IDX else ""
        ao_text = unicodedata.normalize('NFKC', str(row.iloc[AO_IDX])).lower() if len(row) > AO_IDX else ""
        name_text = unicodedata.normalize('NFKC', " ".join([str(row[c]) for c in name_cols if c in row])).lower()
        cat_text = unicodedata.normalize('NFKC', " ".join([str(row[c]) for c in cat_cols if c in row])).lower()
        desc_text = unicodedata.normalize('NFKC', " ".join([str(row[c]) for c in desc_cols if c in row])).lower()
        full_text = f"{name_text} {cat_text} {desc_text} {an_text} {ao_text}"
        am_an_ao_text = f"{am_text} {an_text} {ao_text}"

        # STEP 0: AK列（関連品）の除外
        if "関連品" in ak_text:
            return pd.Series(["PSE対象外", "", "", "", "AK列: 関連品(オプションパーツ等)のため除外", "関連品", 0])

        # 低電圧・通信用ケーブルの除外（ACコード・電源ケーブル、および充電器・タップ本体は除く）
        low_voltage_cable_kws = ["usbケーブル", "usb ケーブル", "スマホケーブル", "リールケーブル", "充電ケーブル", "通信ケーブル", "変換ケーブル", "lanケーブル", "hdmiケーブル", "光ケーブル", "オーディオケーブル", "同軸ケーブル", "アンテナケーブル"]
        for kw in low_voltage_cable_kws:
            if kw in full_text:
                if any(x in full_text for x in ["電源ケーブル", "acケーブル", "電源コード", "acコード"]):
                    continue
                # AC電源用の機器本体やモバイルバッテリーである場合は、ケーブル付属という記述であっても除外しない
                device_kws = ["ac式充電器", "ac充電器", "acアダプタ", "usb充電器", "コンセント充電器", "電源タップ", "oaタップ", "モバイルバッテリー", "リチウムイオン蓄電池"]
                if any(x in cat_text + " " + name_text for x in device_kws):
                    continue
                return pd.Series(["PSE対象外", "", "", "", f"低電圧・通信用ケーブルのため除外: {kw}", kw, 0])

        # STEP 0.5: AM, AN, AO列のPSE明記による即時判定
        pse_exclude_kws = ["pse対象外", "pse 対象外", "認証不要", "認証が必要ない", "pse非対象", "非対象"]
        for kw in pse_exclude_kws:
            if kw in am_an_ao_text:
                return pd.Series(["PSE対象外", "", "", "", f"明記による除外: {kw}", kw, 0])

        # 「PSマークの種類：PSE」や「PSE記述基準適合」「PSE技術基準適合」などの表記揺れに対応
        if ("psマーク" in am_an_ao_text or "pseマーク" in am_an_ao_text) and "pse" in am_an_ao_text:
            return pd.Series(["PSE対象", "明記により確定", "", "", "明記による対象: PSマークの種類：PSE等", "PSマーク_PSE", 0])

        if "pse" in am_an_ao_text and "適合" in am_an_ao_text:
            return pd.Series(["PSE対象", "明記により確定", "", "", "明記による対象: PSE適合関連（記述/技術基準適合等）", "pse_適合", 0])

        pse_include_kws = ["pse対応", "pse認証取得", "pseマーク取得", "pseマーク付", "pse取得", "pse適合", "pseマーク"]
        for kw in pse_include_kws:
            if kw in am_an_ao_text:
                return pd.Series(["PSE対象", "明記により確定", "", "", f"明記による対象: {kw}", kw, 0])

        # STEP 1: AO列優先除外
        ao_exclude_kws = ["医療機器", "管理医療機器", "血圧計", "体温計", "パルスオキシメータ", "自動車用", "車載用", "産業用", "工業用"]
        for kw in ao_exclude_kws:
            if kw in ao_text:
                return pd.Series(["PSE対象外", "", "", "", f"AO列優先除外: {kw}", kw, 0])

        # STEP 2: 除外マスタ
        for ex in excludes:
            kw = str(ex["keyword"]).strip().lower()
            if not kw: continue
            target = full_text
            if ex["keyword_type"] == "name": target = name_text
            elif ex["keyword_type"] == "category": target = cat_text
            if kw in target:
                return pd.Series(["PSE対象外", "", "", "", f"除外理由: {ex['exclude_reason']} / キーワード: {kw}", kw, 0])

        # STEP 3: 電源分類
        power_mode = "不明"
        if any(k in an_text for k in ["ac100v", "交流100v", "ac電源", "コンセント"]): power_mode = "AC駆動"
        elif any(k in an_text for k in ["usb給電", "dc5v", "dc12v", "乾電池"]): power_mode = "DC駆動"

        # STEP 4: 対象マスタ
        for m in masters:
            keywords = [str(m["base_keyword"])] + str(m["extra_keywords"]).split(",")
            for kw in keywords:
                kw = kw.strip().lower()
                if kw and kw in full_text:
                    if power_mode == "DC駆動":
                        # モバイルバッテリーやリチウムイオン蓄電池は電池なのでDC駆動が当然であり、PSE対象になります
                        if any(k in str(m['pse_item_name']) for k in ["リチウムイオン蓄電池", "モバイルバッテリー"]):
                            res_check = 1
                            return pd.Series(["PSE対象", m["pse_type"], m["pse_category"], m["pse_item_name"], f"対象品目「{m['pse_item_name']}」に一致（リチウムイオン蓄電池はDC駆動でも対象）", kw, res_check])
                        return pd.Series(["PSE対象外", "", "", "", f"品目一致「{m['pse_item_name']}」だがDC駆動のため対象外", kw, 1])
                    else:
                        res_check = 1 if (m["pse_type"] == "特定" or kw in ["扇風機", "ストーブ", "モバイルバッテリー"]) else 0
                        return pd.Series(["PSE対象", m["pse_type"], m["pse_category"], m["pse_item_name"], f"対象品目「{m['pse_item_name']}」に一致 / 電源: {power_mode}", kw, res_check])
        
        if power_mode == "AC駆動":
            return pd.Series(["PSE対象外", "", "", "", "AC100V駆動だが品目未ヒットのため要確認", "", 1])

        return pd.Series([res_judge, res_type, res_cat, res_item, res_reason, res_kw, res_check])

    # 判定の実行
    results = df.apply(judge_pse, axis=1)
    results.columns = ["判定", "種別", "区分", "品目名", "根拠", "KW", "確認"]

    # 列の整理（元々の列 + 指定順序の判定列）
    base_df = df[original_columns]
    new_cols = pd.DataFrame({
        "自社商品URL": df["自社商品URL_TEMP"], # AP列 (42)
        "PSE判定": results["判定"],      # AQ列 (43)
        "PSE種別": results["種別"],      # AR列 (44)
        "PSE対象区分": results["区分"],  # AS列 (45)
        "PSE対象品目名": results["品目名"], # AT列 (46)
        "PSEキーワード": results["KW"],   # AU列 (47)
        "PSE要人手確認": results["確認"], # AV列 (48)
        "PSE判定根拠": results["根拠"]    # AW列 (49)
    })

    final_df = pd.concat([base_df, new_cols], axis=1)
    
    print("\nINFO: 判定完了。保存しています...", flush=True)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.basename(input_path).replace(".csv", "_PSE付き.csv")
        output_path = os.path.join(output_dir, base_name)
    else:
        output_path = input_path.replace(".csv", "_PSE付き.csv")
    try:
        final_df.to_csv(output_path, index=False, encoding=current_encoding)
        print(f"完了しました: {output_path}", flush=True)
    except Exception:
        now = datetime.datetime.now().strftime("%H%M%S")
        alt_path = output_path.replace(".csv", f"_{now}.csv")
        final_df.to_csv(alt_path, index=False, encoding=current_encoding)
        print(f"別名で保存しました: {alt_path}", flush=True)

if __name__ == "__main__":
    process_pse_csv(input_csv_path, pse_master_path, exclude_master_path)
