import pandas as pd
import os
import time
import datetime

# ==========================================
# 設定エリア (大分類46,47,48専用)
# ==========================================
input_csv_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\大分類46と47と48\大分類46と47と48_PSE付き.csv" 
pse_master_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\PSE判定用ルールマスタ.csv"
exclude_master_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\除外マスタ.csv"

# このファイル固有の列インデックス
P_IDX = 14 # サイト名
Q_IDX = 15 # 商品コード
AN_IDX = 37 # 電源スペック
AO_IDX = 39 # 備考（除外属性）

# ==========================================
# 処理メイン
# ==========================================

def generate_url(row):
    site_name = str(row.iloc[P_IDX]) if len(row) > P_IDX else ""
    code = str(row.iloc[Q_IDX]).lower() if len(row) > Q_IDX else ""
    if not code: return ""
    
    exclude_keywords = ["買い物コネクト", "カタログ", "マイストック", "店舗用", "パーソナル"]
    if any(k in site_name for k in exclude_keywords): return ""

    if "ココデカウ" in site_name:
        if "Yahoo" in site_name or "yahoo" in site_name:
            return f"https://store.shopping.yahoo.co.jp/cocodecow/{code}.html"
        return f"https://item.rakuten.co.jp/cocodecow/{code}/"
    elif "JetPrice" in site_name or "io" in site_name: # 文字化け考慮
        if "yahoo" in site_name:
            return f"https://store.shopping.yahoo.co.jp/jetprice/{code}.html"
        return f"https://item.rakuten.co.jp/jetprice/{code}/"
    elif "BUNGU" in site_name:
        if "Yahoo" in site_name:
            return f"https://store.shopping.yahoo.co.jp/bungubin/{code}.html"
        return f"https://item.rakuten.co.jp/bungubin/{code}/"
    
    return f"https://www.forest.co.jp/Forestway/gi/{code}/"

def process_pse_csv(input_path, master_path, exclude_path):
    print(f"INFO: {input_path} の判定を開始します...", flush=True)
    master_df = pd.read_csv(master_path, encoding='cp932')
    exclude_df = pd.read_csv(exclude_path, encoding='cp932')
    excludes = exclude_df.to_dict('records')
    masters = master_df.to_dict('records')

    df = pd.read_csv(input_path, encoding='cp932')
    df['自社商品URL_TEMP'] = df.apply(generate_url, axis=1)

    name_cols = [3, 16] # 品目名に関連しそうな列を直接指定
    cat_cols = [33, 35] # 分類に関連しそうな列
    
    total_rows = len(df)
    start_time = time.time()
    processed_count = 0

    def judge_pse(row):
        nonlocal processed_count
        processed_count += 1
        if processed_count % 500 == 0 or processed_count == total_rows:
            elapsed = time.time() - start_time
            speed = processed_count / elapsed if elapsed > 0 else 0
            remaining = (total_rows - processed_count) / speed if speed > 0 else 0
            print(f"\r進捗: {processed_count}/{total_rows} ({processed_count/total_rows*100:>.1f}%) | 残り: {int(remaining)}s", end="", flush=True)

        an_text = str(row.iloc[AN_IDX]).lower()
        ao_text = str(row.iloc[AO_IDX]).lower()
        name_text = " ".join([str(row.iloc[i]) for i in name_cols]).lower()
        cat_text = " ".join([str(row.iloc[i]) for i in cat_cols]).lower()
        full_text = f"{name_text} {cat_text} {an_text} {ao_text}"

        am_an_ao_text = f"{an_text} {ao_text}"

        low_voltage_cable_kws = ["usbケーブル", "usb ケーブル", "スマホケーブル", "リールケーブル", "充電ケーブル", "通信ケーブル", "変換ケーブル", "lanケーブル", "hdmiケーブル", "光ケーブル", "オーディオケーブル", "同軸ケーブル", "アンテナケーブル"]
        for kw in low_voltage_cable_kws:
            if kw in full_text:
                if any(x in full_text for x in ["電源ケーブル", "acケーブル", "電源コード", "acコード"]):
                    continue
                device_kws = ["ac式充電器", "ac充電器", "acアダプタ", "usb充電器", "コンセント充電器", "電源タップ", "oaタップ", "モバイルバッテリー", "リチウムイオン蓄電池"]
                if any(x in cat_text + " " + name_text for x in device_kws):
                    continue
                return pd.Series(["PSE対象外", "", "", "", f"低電圧・通信用ケーブルのため除外: {kw}", kw, 0])

        pse_exclude_kws = ["pse対象外", "pse 対象外", "認証不要", "認証が必要ない", "pse非対象", "非対象"]
        for kw in pse_exclude_kws:
            if kw in am_an_ao_text:
                return pd.Series(["PSE対象外", "", "", "", f"明記による除外: {kw}", kw, 0])

        if ("psマーク" in am_an_ao_text or "pseマーク" in am_an_ao_text) and "pse" in am_an_ao_text:
            return pd.Series(["PSE対象", "明記により確定", "", "", "明記による対象: PSマークの種類：PSE等", "PSマーク_PSE", 0])

        if "pse" in am_an_ao_text and "適合" in am_an_ao_text:
            return pd.Series(["PSE対象", "明記により確定", "", "", "明記による対象: PSE適合関連（記述/技術基準適合等）", "pse_適合", 0])

        pse_include_kws = ["pse対応", "pse認証取得", "pseマーク取得", "pseマーク付", "pse取得", "pse適合", "pseマーク"]
        for kw in pse_include_kws:
            if kw in am_an_ao_text:
                return pd.Series(["PSE対象", "明記により確定", "", "", f"明記による対象: {kw}", kw, 0])

        ao_exclude_kws = ["医療機器", "管理医療機器", "血圧計", "体温計", "パルスオキシメータ", "自動車用", "車載用", "産業用", "工業用"]
        for kw in ao_exclude_kws:
            if kw in ao_text or kw in name_text:
                return pd.Series(["PSE対象外", "", "", "", f"属性除外: {kw}", kw, 0])

        for ex in excludes:
            kw = str(ex["keyword"]).strip().lower()
            if kw and kw in full_text:
                return pd.Series(["PSE対象外", "", "", "", f"除外マスタ: {ex['exclude_reason']}", kw, 0])

        power_mode = "不明"
        if any(k in an_text for k in ["ac100v", "交流100v", "ac電源", "コンセント"]): power_mode = "AC駆動"
        elif any(k in an_text for k in ["usb給電", "dc5v", "dc12v", "乾電池"]): power_mode = "DC駆動"

        for m in masters:
            keywords = [str(m["base_keyword"])] + str(m["extra_keywords"]).split(",")
            for kw in keywords:
                kw = kw.strip().lower()
                if kw and kw in full_text:
                    if power_mode == "DC駆動":
                        return pd.Series(["PSE対象外", "", "", "", f"品目「{m['pse_item_name']}」だがDC駆動", kw, 1])
                    else:
                        check = 1 if (m["pse_type"] == "特定" or kw in ["扇風機", "ストーブ", "モバイルバッテリー"]) else 0
                        return pd.Series(["PSE対象", m["pse_type"], m["pse_category"], m["pse_item_name"], f"品目「{m['pse_item_name']}」に一致", kw, check])
        
        if power_mode == "AC駆動":
            return pd.Series(["PSE対象外", "", "", "", "AC100V駆動だが品目未ヒット", "", 1])

        return pd.Series(["PSE対象外", "", "", "", "", "", 0])

    results = df.apply(judge_pse, axis=1)
    results.columns = ["判定", "種別", "区分", "品目名", "根拠", "KW", "確認"]

    base_df = df.iloc[:, :40]
    new_cols = pd.DataFrame({
        "自社商品URL": df["自社商品URL_TEMP"],
        "PSE判定": results["判定"],
        "PSE種別": results["種別"],
        "PSE対象区分": results["区分"],
        "PSE対象品目名": results["品目名"],
        "PSEキーワード": results["KW"],
        "PSE要人手確認": results["確認"],
        "PSE判定根拠": results["根拠"]
    })

    final_df = pd.concat([base_df, new_cols], axis=1)
    output_path = input_path
    final_df.to_csv(output_path, index=False, encoding='cp932')
    print(f"\n完了: {output_path}")

if __name__ == "__main__":
    process_pse_csv(input_csv_path, pse_master_path, exclude_master_path)
