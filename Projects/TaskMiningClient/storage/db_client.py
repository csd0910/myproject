import sqlite3
import json
import threading
import time
import os

# DBファイルと設定ファイルの保存先
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "local_cache.db")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")

def init_db():
    """
    初回起動時にローカルキャッシュ用のSQLite DBとテーブルを作成。
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload TEXT,
            status TEXT DEFAULT 'PENDING',
            created_at REAL
        )
    ''')
    conn.commit()
    conn.close()

def get_user_id():
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("uuid", "anonymous_user")
    except:
        pass
    return "anonymous_user"

def enqueue_data(payload):
    """
    トラッカーから呼ばれる関数。
    データを即座にSQLiteへ一時保存（オフライン時もここで安全にキャッシュされる）。
    """
    try:
        payload["user_id"] = get_user_id()
        
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO logs (payload, created_at) VALUES (?, ?)",
            (json.dumps(payload, ensure_ascii=False), time.time())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB Error] {e}")

def _sync_worker():
    """
    バックグラウンドで常駐し、SQLite内の未送信データをクラウドへ同期するスレッド。
    オフライン時は送信をスキップし、オンライン復帰時に一括送信する。
    """
    while True:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            
            # 送信待ちのデータを古い順に取得（最大50件ずつのバッチ処理でメモリを節約）
            cursor.execute("SELECT id, payload FROM logs WHERE status = 'PENDING' ORDER BY id ASC LIMIT 50")
            rows = cursor.fetchall()
            
            if rows:
                payloads = []
                row_ids = []
                for row_id, payload_str in rows:
                    payloads.append(json.loads(payload_str))
                    row_ids.append(row_id)
                    
                import requests
                from google.oauth2 import service_account
                import google.auth.transport.requests
                
                # 本番用
                SERVER_URL = "https://task-mining-server-1097969102143.asia-northeast1.run.app/api/v1/logs/bulk"
                
                KEY_PATH = os.path.join(os.path.dirname(__file__), "..", "client-key.json")
                
                is_sync_success = False
                try:
                    # Token caching to prevent regenerating token 50 times
                    if not hasattr(_sync_worker, "token") or getattr(_sync_worker, "token_expire", 0) < time.time():
                        credentials = service_account.IDTokenCredentials.from_service_account_file(
                            KEY_PATH, target_audience="https://task-mining-server-1097969102143.asia-northeast1.run.app"
                        )
                        auth_req = google.auth.transport.requests.Request()
                        credentials.refresh(auth_req)
                        _sync_worker.token = credentials.token
                        _sync_worker.token_expire = time.time() + 3000 # 50 mins

                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {_sync_worker.token}'
                    }
                    
                    response = requests.post(SERVER_URL, json={"logs": payloads}, headers=headers, timeout=10)
                    if response.status_code == 200:
                        is_sync_success = True
                    else:
                        print(f"[Network] 送信エラー: {response.status_code} - {response.text}")
                except Exception as http_e:
                    print(f"[Network] サーバーに接続できません (オフライン): {http_e}")
                
                if is_sync_success:
                    # クラウドへの一括送信が成功したら、ローカルDBから一括削除
                    placeholders = ','.join('?' * len(row_ids))
                    cursor.execute(f"DELETE FROM logs WHERE id IN ({placeholders})", tuple(row_ids))
                    print(f"[Sync] クラウド一括送信完了＆ローカル削除: {len(row_ids)}件")
                    
                conn.commit()
            
            conn.close()
        except Exception as e:
            print(f"[Sync Error] {e}")
            
        # オフラインからの復帰時など、50件フルで送信できた場合は
        # まだ裏にログが溜まっている可能性が高いため、0.5秒の短い間隔ですぐ次を送る（渋滞解消）
        try:
            if 'rows' in locals() and rows and 'is_sync_success' in locals() and is_sync_success and len(rows) == 50:
                time.sleep(0.5)
            else:
                # 同期ループの通常間隔（PCの通信帯域を専有しないよう10秒間隔でチェック）
                time.sleep(10)
        except Exception:
            time.sleep(10)

# アプリ起動時（モジュールインポート時）にDB初期化と同期スレッドを自動開始
init_db()
threading.Thread(target=_sync_worker, daemon=True).start()
