import json
from database import get_connection

try:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, log_type, payload, received_at FROM client_logs ORDER BY id DESC LIMIT 5')
    rows = cursor.fetchall()
    
    if not rows:
        print("DBにまだデータは保存されていません。")
    else:
        print("【直近5件の受信ログ（サーバーDB）】")
        for r in rows:
            try:
                # r[2]が辞書(JSONB)の場合と文字列の場合を考慮
                p = json.loads(r[2]) if isinstance(r[2], str) else r[2]
                print(f"ID: {r[0]} | 時刻: {r[3]} | 種類: {r[1]}")
                print(f"  -> アプリ: {p.get('app', '')}")
                print(f"  -> タイトル: {p.get('title', '')}")
                if "analysis" in p:
                    print(f"  -> AI解析: {p.get('analysis', '')}")
                print("-" * 40)
            except Exception as e:
                print(f"JSON Parse Error: {e}")
    conn.close()
except Exception as e:
    print(f"DB Error: {e}")
