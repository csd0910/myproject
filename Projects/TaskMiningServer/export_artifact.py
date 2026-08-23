import sqlite3
import json
import os

db_path = r'C:\Users\フォーレスト026\MyProject\TaskMiningServer\server_central.db'
out_md = r'C:\Users\フォーレスト026\.gemini\antigravity-ide\brain\72534331-0355-4e4a-a173-69fd193a7a89\raw_db_dump.md'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # 直近の20件を取得
    cursor.execute('SELECT id, log_type, payload, received_at FROM client_logs ORDER BY id DESC LIMIT 20')
    rows = cursor.fetchall()
    
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write("# サーバーDB（PostgreSQLモック）の生データダンプ\n\n")
        f.write("以下は、実際にPC側のクライアントアプリ（NEXUS）から送られ、サーバーのデータベースに蓄積された「生のJSONペイロード」です。\n")
        f.write("夜間のバッチ処理（Gemini API）は、この生データをそのまま読み込んで解析を行います。\n\n")
        
        if not rows:
            f.write("現在、データは保存されていません。\n")
        else:
            for r in rows:
                try:
                    payload = json.loads(r[2])
                    # 見やすく整形
                    pretty_json = json.dumps(payload, indent=2, ensure_ascii=False)
                    f.write(f"### ID: {r[0]} | 受信時刻: {r[3]}\n")
                    f.write(f"```json\n{pretty_json}\n```\n\n")
                except Exception:
                    pass
    conn.close()
    print(f"Artifact created at {out_md}")
except Exception as e:
    print(f"Error: {e}")
