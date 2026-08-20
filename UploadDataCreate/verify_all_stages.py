import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
import os
import sys

def get_ojima_col_idx(df, col_name, fallback_idx):
    if col_name in df.columns:
        return df.columns.get_loc(col_name)
    for i, c in enumerate(df.columns):
        if col_name in str(c):
            return i
    return fallback_idx

def verify_stage_rows(stage_name, temp_file, ojima_file):
    print(f"\n--- {stage_name} の検証を開始 ---")
    if not os.path.exists(temp_file):
        print(f"エラー: {temp_file} が見つかりません。")
        return False
    if not os.path.exists(ojima_file):
        print(f"エラー: {ojima_file} が見つかりません。")
        return False

    df_temp = pd.read_excel(temp_file)
    df_ojima = pd.read_excel(ojima_file)
    
    t_chumon = get_ojima_col_idx(df_temp, "注文番号", 3)
    o_chumon = get_ojima_col_idx(df_ojima, "注文番号", 3)
    
    temp_orders = set(df_temp.iloc[:, t_chumon].dropna().astype(str).str.strip())
    ojima_orders = set(df_ojima.iloc[:, o_chumon].dropna().astype(str).str.strip())
    
    match_count = len(temp_orders & ojima_orders)
    extra_count = len(temp_orders - ojima_orders)
    missing_count = len(ojima_orders - temp_orders)
    
    print(f"・正解（一致）: {match_count}件")
    print(f"・Python側の消し漏れ (余分): {extra_count}件")
    if extra_count > 0:
        print(f"  例: {list(temp_orders - ojima_orders)[:5]}")
    print(f"・Python側の誤削除 (不足): {missing_count}件")
    if missing_count > 0:
        print(f"  例: {list(ojima_orders - temp_orders)[:5]}")
    
    if extra_count == 0 and missing_count == 0:
        print(f"[OK] {stage_name} は完全に一致しています！")
        return True
    else:
        print(f"[NG] {stage_name} に差異があります。ここで検証をストップします。")
        return False

def verify_stage_content(stage_name, temp_file, ojima_file, check_col_name="足し算"):
    print(f"\n--- {stage_name} の検証を開始 ---")
    if not os.path.exists(temp_file):
        print(f"エラー: {temp_file} が見つかりません。")
        return False
    if not os.path.exists(ojima_file):
        print(f"エラー: {ojima_file} が見つかりません。")
        return False

    df_temp = pd.read_excel(temp_file)
    df_ojima = pd.read_excel(ojima_file)
    
    t_chumon = get_ojima_col_idx(df_temp, "注文番号", 3)
    o_chumon = get_ojima_col_idx(df_ojima, "注文番号", 3)
    
    t_val = get_ojima_col_idx(df_temp, check_col_name, 15)
    o_val = get_ojima_col_idx(df_ojima, check_col_name, 15)
    
    # 注文番号をキーにして比較
    temp_dict = dict(zip(df_temp.iloc[:, t_chumon].dropna().astype(str).str.strip(), df_temp.iloc[:, t_val].fillna("").astype(str)))
    ojima_dict = dict(zip(df_ojima.iloc[:, o_chumon].dropna().astype(str).str.strip(), df_ojima.iloc[:, o_val].fillna("").astype(str)))
    
    common_orders = set(temp_dict.keys()) & set(ojima_dict.keys())
    mismatch_count = 0
    
    for order in common_orders:
        if temp_dict[order] != ojima_dict[order]:
            if mismatch_count == 0:
                print("【差異の例】")
                print(f"注文番号: {order}")
                print(f"Python : {temp_dict[order]}")
                print(f"尾島様 : {ojima_dict[order]}")
            mismatch_count += 1
            
    if mismatch_count == 0:
        print(f"[OK] {stage_name} の「{check_col_name}」は完全に一致しています！")
        return True
    else:
        print(f"[NG] {stage_name} に差異が {mismatch_count} 件あります。ここで検証をストップします。")
        return False

def main():
    base_dir = r"C:\Users\フォーレスト026\MyProject\UploadDataCreate"
    out_dir = os.path.join(base_dir, "output")
    ojima_dir = os.path.join(base_dir, "【テスト用】商品名作成 尾島手作業")
    
    stages = [
        ("Stage1 (除外)", "temp_stage1.xlsx", "【手順1】result_260819_154419.xlsx", "rows"),
        ("Stage2 (取り寄せ除外)", "temp_stage2.xlsx", "【手順5】result_260819_154419.xlsx", "rows"),
        ("Stage3 (医薬品除外)", "temp_stage3.xlsx", "【手順6】result_260819_154419.xlsx", "rows"),
        ("Stage4 (文字列削除)", "temp_stage4.xlsx", "【手順7】result_260819_154419.xlsx", "content"),
        ("Stage5 (送料無料付与)", "temp_stage5.xlsx", "【手順8】result_260819_154419.xlsx", "content")
    ]
    
    stages_advanced = [
        ("Stage6 (シート分割_その他)", "temp_stage6.xlsx", "【手順9】シート分け＆キーワード付与まで.xlsx", "advanced"),
        ("Stage7 (文字数調整_その他)", "temp_stage7.xlsx", "【手順10-1】文字数調整直後.xlsx", "advanced")
    ]
    
    for stage_name, temp_name, ojima_name, check_type in stages:
        temp_file = os.path.join(out_dir, temp_name)
        ojima_file = os.path.join(ojima_dir, ojima_name)
        
        if check_type == "rows":
            if not verify_stage_rows(stage_name, temp_file, ojima_file):
                break
        else:
            if not verify_stage_content(stage_name, temp_file, ojima_file):
                break
                
    # Stage 6, 7, 8 verification (custom logic)
    print("\n--- Stage6〜8 の検証 ---")
    
    # Stage 8
    try:
        df_temp8 = pd.read_excel(os.path.join(out_dir, "normal-item_rcその他.xlsx"))
        df_oj8 = pd.read_excel(os.path.join(ojima_dir, "【手順10-3 ツールにかける前】normal-item_rcその他.xlsx"))
        
        t_chumon_col = '商品管理番号'
        o_chumon_col = '商品管理番号（商品URL）'
        
        temp_dict = dict(zip(df_temp8[t_chumon_col].dropna().astype(str).str.strip(), df_temp8['商品名'].fillna('').astype(str)))
        ojima_dict = dict(zip(df_oj8[o_chumon_col].dropna().astype(str).str.strip(), df_oj8['商品名'].fillna('').astype(str)))
        
        diff_count = sum(1 for order in set(temp_dict) & set(ojima_dict) if temp_dict[order] != ojima_dict[order])
        
        if diff_count == 0:
            print("[OK] Stage6〜8 (最終フォーマット出力) は完全に一致しています！")
        else:
            print(f"[NG] Stage6〜8 に差異が {diff_count} 件あります。")
            
    except Exception as e:
        print(f"[NG] Stage6〜8 検証エラー: {e}")

if __name__ == "__main__":
    main()
