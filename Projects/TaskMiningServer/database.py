import os
import json
import time
from dotenv import load_dotenv

# ローカル環境の .env ファイルを読み込む（Cloud Runでは自動設定される）
load_dotenv()

# GCP環境変数として設定されるPostgreSQLのURL
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    import psycopg2
else:
    import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "server_central.db")

def get_connection():
    """環境に合わせてコネクションを返す"""
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    if DATABASE_URL:
        conn.autocommit = True
    try:
        cursor = conn.cursor()
        
        if DATABASE_URL:
            # PostgreSQL用テーブル定義（タスクマイニング完全版）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS client_logs (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    app_name VARCHAR(255),
                    folder_name TEXT,
                    file_name TEXT,
                    operation_type VARCHAR(100),
                    manual_typing_count INTEGER DEFAULT 0,
                    manual_typing_time INTEGER DEFAULT 0,
                    copy_paste_count INTEGER DEFAULT 0,
                    click_count INTEGER DEFAULT 0,
                    scroll_count INTEGER DEFAULT 0,
                    mouse_distance INTEGER DEFAULT 0,
                    duration_seconds INTEGER,
                    idle_time_seconds INTEGER DEFAULT 0,
                    context_switch_count INTEGER DEFAULT 0,
                    cpu_usage_percent DOUBLE PRECISION,
                    memory_usage_mb DOUBLE PRECISION,
                    browser_tab_count INTEGER DEFAULT 0,
                    is_processed INTEGER DEFAULT 0,
                    received_at DOUBLE PRECISION
                )
            ''')
            try:
                cursor.execute("ALTER TABLE client_logs ADD COLUMN click_count INTEGER DEFAULT 0")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE client_logs ADD COLUMN scroll_count INTEGER DEFAULT 0")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE client_logs ADD COLUMN mouse_distance INTEGER DEFAULT 0")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE client_logs ADD COLUMN right_click_count INTEGER DEFAULT 0")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE client_logs ADD COLUMN shortcut_key_count INTEGER DEFAULT 0")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE client_logs ADD COLUMN shortcut_details TEXT")
            except:
                pass
                
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS client_logs_summary (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    app_name VARCHAR(255),
                    operation_type VARCHAR(100),
                    manual_typing_count INTEGER DEFAULT 0,
                    copy_paste_count INTEGER DEFAULT 0,
                    click_count INTEGER DEFAULT 0,
                    scroll_count INTEGER DEFAULT 0,
                    mouse_distance INTEGER DEFAULT 0,
                    right_click_count INTEGER DEFAULT 0,
                    shortcut_key_count INTEGER DEFAULT 0,
                    duration_seconds INTEGER DEFAULT 0,
                    idle_time_seconds INTEGER DEFAULT 0,
                    context_switch_count INTEGER DEFAULT 0,
                    record_date DATE NOT NULL,
                    record_hour INTEGER NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key VARCHAR(255) PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    department VARCHAR(255) NOT NULL,
                    section VARCHAR(255),
                    registered_at DOUBLE PRECISION
                )
            ''')
            try:
                cursor.execute("ALTER TABLE employees ADD COLUMN base_salary INTEGER DEFAULT 0")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE employees ADD COLUMN hourly_wage INTEGER DEFAULT 0")
            except:
                pass
        else:
            # SQLite用テーブル定義（タスクマイニング完全版）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS client_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    app_name TEXT,
                    folder_name TEXT,
                    file_name TEXT,
                    operation_type TEXT,
                    manual_typing_count INTEGER DEFAULT 0,
                    manual_typing_time INTEGER DEFAULT 0,
                    copy_paste_count INTEGER DEFAULT 0,
                    click_count INTEGER DEFAULT 0,
                    scroll_count INTEGER DEFAULT 0,
                    mouse_distance INTEGER DEFAULT 0,
                    duration_seconds INTEGER,
                    idle_time_seconds INTEGER DEFAULT 0,
                    context_switch_count INTEGER DEFAULT 0,
                    cpu_usage_percent REAL,
                    memory_usage_mb REAL,
                    browser_tab_count INTEGER DEFAULT 0,
                    is_processed INTEGER DEFAULT 0,
                    received_at REAL
                )
            ''')
            try:
                cursor.execute("ALTER TABLE client_logs ADD COLUMN click_count INTEGER DEFAULT 0")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE client_logs ADD COLUMN scroll_count INTEGER DEFAULT 0")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE client_logs ADD COLUMN mouse_distance INTEGER DEFAULT 0")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE client_logs ADD COLUMN right_click_count INTEGER DEFAULT 0")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE client_logs ADD COLUMN shortcut_key_count INTEGER DEFAULT 0")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE client_logs ADD COLUMN shortcut_details TEXT")
            except:
                pass
                
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS client_logs_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    app_name TEXT,
                    operation_type TEXT,
                    manual_typing_count INTEGER DEFAULT 0,
                    copy_paste_count INTEGER DEFAULT 0,
                    click_count INTEGER DEFAULT 0,
                    scroll_count INTEGER DEFAULT 0,
                    mouse_distance INTEGER DEFAULT 0,
                    right_click_count INTEGER DEFAULT 0,
                    shortcut_key_count INTEGER DEFAULT 0,
                    duration_seconds INTEGER DEFAULT 0,
                    idle_time_seconds INTEGER DEFAULT 0,
                    context_switch_count INTEGER DEFAULT 0,
                    record_date TEXT NOT NULL,
                    record_hour INTEGER NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    section TEXT,
                    registered_at REAL
                )
            ''')
            try:
                cursor.execute("ALTER TABLE employees ADD COLUMN base_salary INTEGER DEFAULT 0")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE employees ADD COLUMN hourly_wage INTEGER DEFAULT 0")
            except:
                pass
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            
            # 検索の高速化のためのインデックス作成（ダッシュボードの表示フリーズを防止）
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_client_logs_user_id ON client_logs(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_client_logs_received_at ON client_logs(received_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_client_logs_user_date ON client_logs(user_id, received_at)")
            except:
                pass
            
            conn.commit()
    finally:
        conn.close()
    
    mode = "PostgreSQL" if DATABASE_URL else "SQLite"
    print(f"【Server】データベース初期化完了({mode})")

def insert_log(user_id: str, log_type: str, payload: dict):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # オフライン時に溜まったログが送信された場合、発生当時の時間を使う
        log_time = payload.get("timestamp", time.time())
        
        app_name = payload.get("app_name", "")
        folder_name = payload.get("folder_name", "")
        file_name = payload.get("file_name", "")
        operation_type = payload.get("operation_type", log_type)
        manual = payload.get("manual_typing_count", 0)
        manual_time = 0
        copy = payload.get("copy_paste_count", 0)
        click = payload.get("click_count", 0)
        scroll = payload.get("scroll_count", 0)
        m_dist = payload.get("mouse_distance", 0)
        c_switch = payload.get("window_switch_count", 0)
        right_click = payload.get("right_click_count", 0)
        shortcut = payload.get("shortcut_key_count", 0)
        shortcut_details = payload.get("shortcut_details", "{}")
        if isinstance(shortcut_details, dict):
            import json
            shortcut_details = json.dumps(shortcut_details, ensure_ascii=False)
        duration = payload.get("duration_seconds", 0)
        idle = payload.get("idle_time_seconds", 0)
        cpu = payload.get("cpu_usage_percent", 0.0)
        mem = payload.get("memory_usage_mb", 0.0)
        
        query = """
            INSERT INTO client_logs (
                user_id, app_name, folder_name, file_name, operation_type,
                manual_typing_count, manual_typing_time, copy_paste_count,
                click_count, scroll_count, mouse_distance, context_switch_count,
                right_click_count, shortcut_key_count, shortcut_details,
                duration_seconds, idle_time_seconds, cpu_usage_percent, memory_usage_mb,
                received_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s
            )
        """
        if not DATABASE_URL:
            query = query.replace("%s", "?")
            
        cursor.execute(query, (
            user_id, app_name, folder_name, file_name, operation_type,
            manual, manual_time, copy,
            click, scroll, m_dist, c_switch,
            right_click, shortcut, shortcut_details,
            duration, idle, cpu, mem,
            log_time
        ))
            
        conn.commit()
    finally:
        conn.close()
