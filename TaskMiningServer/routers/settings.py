"""
routers/settings.py - 設定・システム情報ルーター
===================================================
役割:
  - 従業員CSVのアップロード/ダウンロード
  - 部門一覧の取得
  - システムステータス（ダッシュボード・サーバー状態）の取得
  - 最新のログの取得
"""

from fastapi import APIRouter, Request, Header, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
import os
import time
import io
import csv
from datetime import datetime

from database import get_connection
from utils import ADMIN_TOKEN_SECRET

router = APIRouter(tags=["Settings"])

@router.get("/api/debug/db")
async def debug_db():
    """全従業員の情報を取得(デバッグ用)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees")
    rows = cursor.fetchall()
    conn.close()
    return {"employees": rows}

@router.post("/api/settings/upload_csv")
async def upload_csv(file: UploadFile = File(...), x_admin_token: str = Header(None, alias="X-Admin-Token")):
    """従業員マスターCSVのアップロードとDB更新"""
    if x_admin_token != f"Bearer {ADMIN_TOKEN_SECRET}":
        return JSONResponse(status_code=401, content={"status": "error", "message": "Unauthorized"})
    
    contents = await file.read()
    decoded = contents.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))
    
    conn = get_connection()
    cursor = conn.cursor()
    now = time.time()
    
    try:
        count = 0
        for row in reader:
            uid = row.get("user_id") or row.get("ID")
            name = row.get("name") or row.get("名前") or row.get("氏名")
            dept = row.get("department") or row.get("部署") or row.get("部門")
            section = row.get("section") or row.get("課") or ""
            
            if uid and name and dept:
                if os.environ.get("DATABASE_URL"):
                    cursor.execute(
                        "INSERT INTO employees (user_id, name, department, section, registered_at) VALUES (%s, %s, %s, %s, %s) ON CONFLICT(user_id) DO UPDATE SET name=EXCLUDED.name, department=EXCLUDED.department, section=EXCLUDED.section",
                        (uid, name, dept, section, now)
                    )
                else:
                    cursor.execute(
                        "INSERT OR REPLACE INTO employees (user_id, name, department, section, registered_at) VALUES (?, ?, ?, ?, ?)",
                        (uid, name, dept, section, now)
                    )
                count += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()
        
    return {"status": "success", "count": count}

@router.get("/api/settings/departments")
async def get_departments(x_admin_token: str = Header(None, alias="X-Admin-Token")):
    """部門一覧と所属人数を返す"""
    if x_admin_token != f"Bearer {ADMIN_TOKEN_SECRET}":
        return JSONResponse(status_code=401, content={"status": "error", "message": "Unauthorized"})
        
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT department, COUNT(*) as emp_count FROM employees GROUP BY department")
    rows = cursor.fetchall()
    conn.close()
    
    departments = [{"name": row[0], "count": row[1]} for row in rows]
    return {"departments": departments}

@router.get("/api/settings/system_status")
async def get_system_status(x_admin_token: str = Header(None, alias="X-Admin-Token")):
    """システムステータス（ログ数、DBサイズ、直近の稼働状況）を返す"""
    if x_admin_token != f"Bearer {ADMIN_TOKEN_SECRET}":
        return JSONResponse(status_code=401, content={"status": "error", "message": "Unauthorized"})
        
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM client_logs")
    total_logs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM client_logs")
    total_users = cursor.fetchone()[0]
    
    active_limit = time.time() - 3600
    placeholder = "%s" if os.environ.get("DATABASE_URL") else "?"
    cursor.execute(f"SELECT COUNT(DISTINCT user_id) FROM client_logs WHERE received_at > {placeholder}", (active_limit,))
    active_clients = cursor.fetchone()[0]
    
    db_size_mb = 0
    if os.environ.get("DATABASE_URL"):
        try:
            cursor.execute("SELECT pg_database_size(current_database())")
            db_size_mb = round(cursor.fetchone()[0] / (1024 * 1024), 2)
        except:
            pass
    else:
        try:
            db_size_mb = round(os.path.getsize("server_central.db") / (1024 * 1024), 2)
        except:
            pass
    
    time_limit_24h = time.time() - (24 * 3600)
    cursor.execute(f"SELECT received_at FROM client_logs WHERE received_at > {placeholder}", (time_limit_24h,))
    recent_logs = cursor.fetchall()
    conn.close()
    
    import datetime as dt_mod
    from collections import Counter
    hours_count = Counter()
    for row in recent_logs:
        dt = dt_mod.datetime.fromtimestamp(row[0])
        hour_str = dt.strftime('%H:00')
        hours_count[hour_str] += 1
        
    chart_labels = []
    chart_data = []
    current_hour = dt_mod.datetime.fromtimestamp(time.time()).replace(minute=0, second=0, microsecond=0)
    for i in range(23, -1, -1):
        h = current_hour - dt_mod.timedelta(hours=i)
        h_str = h.strftime('%H:00')
        chart_labels.append(h_str)
        chart_data.append(hours_count.get(h_str, 0))
    
    gemini_key = os.environ.get("GEMINI_API_KEY")
    api_status = "正常稼働中 (API Key設定済)" if gemini_key else "未設定 (API Keyなし)"
    db_type = "PostgreSQL" if os.environ.get("DATABASE_URL") else "SQLite (Local)"
    
    return {
        "status": "success",
        "total_logs": total_logs,
        "active_clients": active_clients,
        "total_users": total_users,
        "db_size_mb": db_size_mb,
        "api_status": api_status,
        "db_type": db_type,
        "chart_labels": chart_labels,
        "chart_data": chart_data
    }

@router.get("/api/settings/latest_logs")
async def get_latest_logs(x_admin_token: str = Header(None, alias="X-Admin-Token")):
    """最新のログを50件返す"""
    if x_admin_token != f"Bearer {ADMIN_TOKEN_SECRET}":
        return JSONResponse(status_code=401, content={"status": "error", "message": "Unauthorized"})
        
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.user_id, c.app_name, c.operation_type, c.file_name, c.received_at, e.name 
        FROM client_logs c
        LEFT JOIN employees e ON c.user_id = e.user_id
        ORDER BY c.received_at DESC LIMIT 50
    """)
    rows = cursor.fetchall()
    conn.close()
    
    logs = []
    for r in rows:
        uid, app, op, fname, recv, ename = r
        dt_str = datetime.fromtimestamp(recv).strftime('%m/%d %H:%M:%S')
        logs.append({
            "time": dt_str,
            "user": ename if ename else uid[:8],
            "app": app,
            "op": op,
            "file": fname or ""
        })
        
    return {"status": "success", "logs": logs}
    
@router.get("/api/settings/export_employees_csv")
async def export_employees_csv(x_admin_token: str = Header(None, alias="X-Admin-Token")):
    """従業員マスターのCSVエクスポート"""
    if x_admin_token != f"Bearer {ADMIN_TOKEN_SECRET}":
        return JSONResponse(status_code=401, content={"status": "error", "message": "Unauthorized"})
        
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, name, department, section FROM employees ORDER BY department, section, name")
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["user_id", "name", "department", "section"])
    for row in rows:
        writer.writerow([row[0], row[1], row[2], row[3] if row[3] else ""])
        
    encoded_csv = "\ufeff" + output.getvalue()
    return StreamingResponse(
        iter([encoded_csv]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=employees_master.csv"}
    )
