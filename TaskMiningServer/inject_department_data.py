import time
import json
import random
from datetime import datetime, timedelta
from database import get_connection

def insert_department_dummy_data():
    conn = get_connection()
    cursor = conn.cursor()
    
    # テーブル再構築のため一度ドロップ（テスト用）
    cursor.execute("DROP TABLE IF EXISTS client_logs")
    conn.commit()
    
    from database import init_db
    init_db()
    
    users = [f"dept_member_{i}" for i in range(1, 7)]
    
    now = datetime.now()
    start_dt = now.replace(hour=9, minute=0, second=0, microsecond=0)
    
    activities = [
        ("explorer.exe", "タスクの切り替え", "会議資料作成のため、共有ドライブと特定のExcelファイルを検索・特定", "検索・確認"),
        ("explorer.exe", r"C:\Users\Desktop\2026年週次\7月 - エクスプローラー", "ネットワーク共有とデスクトップで会議資料や受発注明細ファイルを検索", "検索・確認"),
        ("EXCEL.EXE", "受注明細(er_20)_分類指定20250701-20250801.csv - Excel", "受注明細CSVデータをExcelで開き、売上や顧客情報、商品詳細を確認", "検索・確認"),
        ("EXCEL.EXE", "受注明細(er_20)_分類指定20250701-20250801.csv - Excel", "Excelで受注明細データを期間でフィルター設定中", "関数・機能"),
        ("EXCEL.EXE", "【商品課】週次報告フォーマット（作成日0727）.xlsx - Excel", "データ処理のため、CH列からCV列のデータをコピー＆ペースト", "コピー＆ペースト"),
        ("EXCEL.EXE", "【商品課】週次報告フォーマット（作成日0727）.xlsx - Excel", "商品課の週次報告書フォーマットに、VLOOKUP関数を用いて他ファイルから実績を参照", "関数・機能"),
        ("EXCEL.EXE", "商品課　商品政策書 2026年7月13日.xlsx - Excel", "商品別の売上・粗利実績と計画を比較分析し、好不調要因を手入力", "手入力"),
        ("EXCEL.EXE", "テーブルまたは範囲からのピボットテーブル", "ExcelでCSVデータからピボットテーブルを作成し、フィールドを選択", "関数・機能"),
        ("EXCEL.EXE", "【商品課】週次報告フォーマット（作成日0727）.xlsx - Excel", "【非効率疑い】商品課週次報告フォーマットに共有実績データを手作業でコピー＆ペーストして転記", "コピー＆ペースト"),
        ("EXCEL.EXE", "【商品課】週次報告フォーマット（作成日0727）.xlsx - Excel", "マクロを実行してデータの書式を一括整形", "マクロ"),
        ("EXCEL.EXE", "0727商品一覧(em310).csv - Excel", "C6セルに「品目cd」と手入力し、データを手修正", "手入力"),
        ("chrome.exe", "Google検索 - 競合調査", "ブラウザでの競合他社の価格やスペック調査", "検索・確認"),
        ("Teams.exe", "定例進捗会議 - 会議", "部門のオンライン定例会議に参加", "会議・コミュニケーション"),
        ("Zoom.exe", "ベンダー打ち合わせ - Zoomミーティング", "外部ベンダーとのオンライン打ち合わせ", "会議・コミュニケーション")
    ]
    
    total_logs = 0
    for user in users:
        current_dt = start_dt
        while current_dt.hour < 18:
            duration_sec = random.randint(1800, 3600)
            
            app, title, analysis, op_type = random.choices(
                activities,
                weights=[5, 5, 10, 10, 20, 15, 10, 5, 20, 5, 10, 15, 15, 5],
                k=1
            )[0]
            
            folder_name = "C:\\Users\\Desktop\\2026年週次" if "csv" in title or "xlsx" in title else ""
            file_name = title.split(" - ")[0] if " - " in title else title
            
            copy_paste_count = random.randint(10, 50) if op_type == "コピー＆ペースト" else 0
            manual_typing_count = random.randint(100, 500) if op_type == "手入力" else random.randint(0, 20)
            manual_typing_time = int(manual_typing_count * 0.4)
            
            idle_time = random.randint(0, int(duration_sec * 0.3))
            switch_count = random.randint(0, 5)
            cpu_usage = round(random.uniform(5.0, 45.0), 1)
            memory_usage = round(random.uniform(4000.0, 8000.0), 1)
            
            # Chromeならタブ数をランダムに生成（重い人は20タブとか開いている）
            tab_count = random.randint(1, 25) if app == "chrome.exe" else 0
            
            current_timestamp = current_dt.timestamp()
            
            cursor.execute(
                """
                INSERT INTO client_logs (
                    user_id, app_name, folder_name, file_name, operation_type,
                    manual_typing_count, manual_typing_time, copy_paste_count,
                    duration_seconds, idle_time_seconds, context_switch_count,
                    cpu_usage_percent, memory_usage_mb, browser_tab_count, is_processed, received_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s)
                """,
                (user, app, folder_name, file_name, op_type, 
                 manual_typing_count, manual_typing_time, copy_paste_count,
                 duration_sec, idle_time, switch_count, cpu_usage, memory_usage, tab_count, current_timestamp)
            )
            
            current_dt += timedelta(seconds=duration_sec)
            total_logs += 1

    conn.commit()
    conn.close()
    print(f"6人分のリアルな部署ダミーデータ（計{total_logs}件）の注入が完了しました！")

if __name__ == "__main__":
    insert_department_dummy_data()
