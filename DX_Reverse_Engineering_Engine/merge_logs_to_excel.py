import pandas as pd
import os
import glob
import datetime

def merge_logs_to_excel(date_str=None, base_dir=r"C:\AutoAnalysisLogs"):
    if not date_str:
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        
    system_ai_csv = os.path.join(base_dir, f"system_log_ai_evaluated_{date_str}.csv")
    activity_csv = os.path.join(base_dir, f"activity_log_{date_str}.csv")
    
    # AI解析済みが無い場合は、通常のSystemLogを探す
    if not os.path.exists(system_ai_csv):
        system_ai_csv = os.path.join(base_dir, f"system_log_{date_str}.csv")
        
    if not os.path.exists(system_ai_csv) or not os.path.exists(activity_csv):
        print(f"[エラー] {date_str} のログが見つかりません。パス: {base_dir}")
        return

    try:
        df_sys = pd.read_csv(system_ai_csv, encoding="utf-8-sig")
    except Exception as e:
        print(f"SystemLog読込エラー: {e}")
        return
        
    try:
        df_act = pd.read_csv(activity_csv, encoding="utf-8-sig")
    except Exception as e:
        print(f"ActivityLog読込エラー: {e}")
        return

    out_file = os.path.join(base_dir, f"Integrated_Log_{date_str}.xlsx")
    with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
        df_sys.to_excel(writer, sheet_name="SystemLog", index=False)
        df_act.to_excel(writer, sheet_name="ActivityLog", index=False)
        
    print(f"[完了] Excel統合完了: {out_file}")

if __name__ == "__main__":
    import sys
    d_str = sys.argv[1] if len(sys.argv) > 1 else "20260812"
    d_dir = sys.argv[2] if len(sys.argv) > 2 else r"C:\AutoAnalysisLogs"
    merge_logs_to_excel(d_str, d_dir)
