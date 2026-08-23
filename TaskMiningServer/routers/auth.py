"""
routers/auth.py - 認証・アカウント系ルーター
===========================================
役割:
  - ログイン (マスターパスワード対応)
  - パスワード変更
  - 従業員（クライアントPC）自動登録
"""

from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse
import os
import time

from database import get_connection
from utils import ADMIN_TOKEN_SECRET

router = APIRouter(tags=["Auth"])

@router.post("/api/auth/login")
async def login(request: Request):
    """
    管理者ログイン
    DBのadmin_password、または固定マスターパスワードに合致すればTokenを返す
    """
    data = await request.json()
    input_pwd = data.get("password")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'admin_password'")
    row = cursor.fetchone()
    conn.close()
    
    correct_pwd = row[0] if row else "Forest0720TaskMining!"
    
    if input_pwd == correct_pwd or input_pwd == "zaq12wsX=":
        return {"status": "success", "token": ADMIN_TOKEN_SECRET}
    return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid password"})

@router.post("/api/auth/change_password")
async def change_password(request: Request, x_admin_token: str = Header(None, alias="X-Admin-Token")):
    """管理者パスワードの変更"""
    if x_admin_token != f"Bearer {ADMIN_TOKEN_SECRET}":
        return JSONResponse(status_code=401, content={"status": "error", "message": "Unauthorized"})
        
    data = await request.json()
    new_pwd = data.get("new_password")
    if not new_pwd or len(new_pwd) < 6:
        return {"status": "error", "message": "パスワードは6文字以上必要です"}
        
    conn = get_connection()
    cursor = conn.cursor()
    if not os.environ.get("DATABASE_URL"):
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_password', ?)", (new_pwd,))
    else:
        cursor.execute("INSERT INTO settings (key, value) VALUES ('admin_password', %s) ON CONFLICT(key) DO UPDATE SET value = EXCLUDED.value", (new_pwd,))
    
    conn.commit()
    conn.close()
    
    return {"status": "success"}

@router.post("/api/auth/register_employee")
async def register_employee(request: Request):
    """クライアントソフト初回起動時に従業員情報を登録・更新する"""
    try:
        data = await request.json()
        uid = data.get("user_id")
        name = data.get("name", "Unknown")
        dept = data.get("department", "Unknown")
        section = data.get("section", "")
        if not uid:
            return {"status": "error", "message": "user_id is required"}
            
        conn = get_connection()
        cursor = conn.cursor()
        now = time.time()
        
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
        conn.commit()
        conn.close()
        return {"status": "success"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
