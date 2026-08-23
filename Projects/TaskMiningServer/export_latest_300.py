import os
from dotenv import load_dotenv
load_dotenv()
import csv
from urllib.parse import urlparse
import psycopg2
import sqlite3

def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        result = urlparse(db_url)
        username = result.username
        from urllib.parse import unquote
        password = unquote(result.password) if result.password else None
        database = result.path[1:]
        hostname = result.hostname
        port = result.port
        return psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
    else:
        return sqlite3.connect("server_central.db")

def export():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.user_id, c.app_name, c.folder_name, c.file_name, c.operation_type,
               c.manual_typing_count, c.manual_typing_time, c.copy_paste_count,
               c.click_count, c.scroll_count, c.mouse_distance, c.context_switch_count,
               c.duration_seconds, c.idle_time_seconds, c.cpu_usage_percent, c.memory_usage_mb,
               datetime(c.received_at, 'unixepoch', 'localtime'), e.name, e.department
        FROM client_logs c
        LEFT JOIN employees e ON c.user_id = e.user_id
        ORDER BY c.received_at DESC
        LIMIT 300
    """)
    rows = cursor.fetchall()
    conn.close()

    headers = [
        "ID", "ユーザーID", "アプリ名", "フォルダ名", "ファイル/画面名", "操作種別",
        "手動キー入力回数", "手動キー入力時間(秒)", "コピペ回数",
        "クリック数", "スクロール数", "マウス移動距離(px)", "画面切替回数",
        "所要時間(秒)", "アイドル時間(秒)", "CPU使用率(%)", "メモリ使用量(MB)",
        "受信日時", "担当者名", "部門"
    ]

    filename = "client_logs_latest300_japanese.csv"
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Exported to {filename}")

if __name__ == "__main__":
    export()
