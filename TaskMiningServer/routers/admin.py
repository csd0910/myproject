"""
routers/admin.py - 管理者向けAPIルーター
===========================================
役割:
  - ログクリーニング・集計
  - DB再構築・バックアップ
  - モックデータ生成
  - 夜間レポート生成
"""

from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
import os
import time
import random

from database import get_connection
from utils import ADMIN_TOKEN_SECRET
from services.db_service import rollup_old_logs, rebuild_database, dump_all_data

router = APIRouter(tags=["Admin"])

@router.get("/api/admin/clean_old_logs")
async def clean_old_logs():
    """12時間以上前に受信した古いテストデータをすべて削除"""
    conn = get_connection()
    cursor = conn.cursor()
    cutoff = time.time() - (12 * 3600)
    placeholder = "%s" if os.environ.get("DATABASE_URL") else "?"
    
    try:
        cursor.execute(f"DELETE FROM client_logs WHERE received_at < {placeholder}", (cutoff,))
        deleted = cursor.rowcount
        conn.commit()
        return {"status": "success", "deleted_rows": deleted}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()

@router.get("/api/admin/rollup_data")
async def rollup_data(days_old: int = 30):
    """古い詳細ログを1時間単位に集計(圧縮)してサマリーへ"""
    return rollup_old_logs(days_old)

@router.get("/api/admin/rebuild_db")
async def rebuild_db():
    """DBを初期化（警告：全データ消失）"""
    return rebuild_database()

@router.post("/api/admin/execute_sql")
async def execute_sql(request: Request, x_admin_token: str = Header(None)):
    """(デバッグ用) 直接SQL実行"""
    if x_admin_token != ADMIN_TOKEN_SECRET:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Unauthorized"})
    
    try:
        data = await request.json()
        sql = data.get("sql")
        params = data.get("params", [])
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        rowcount = cursor.rowcount
        conn.commit()
        conn.close()
        return {"status": "success", "rowcount": rowcount}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/api/admin/dump_db_full")
async def dump_db_full(x_admin_token: str = Header(None)):
    """DBの全データを出力（デバッグ用）"""
    if x_admin_token != ADMIN_TOKEN_SECRET:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Unauthorized"})
    
    return dump_all_data()

@router.get("/api/admin/generate_mock_data")
async def generate_mock_data():
    """デモ用のモック従業員とログデータを500件生成"""
    conn = get_connection()
    cursor = conn.cursor()
    now = time.time()
    apps = ["Excel", "Chrome", "PowerPoint", "Word", "Slack", "VSCode"]
    users_data = [
        {"uid": "user-111", "name": "山田 太郎", "dept": "営業部", "sec": "営業課"},
        {"uid": "user-222", "name": "佐藤 花子", "dept": "システム部", "sec": "システム課"},
        {"uid": "user-333", "name": "鈴木 一郎", "dept": "商品部", "sec": "商品課"}
    ]
    
    try:
        # 従業員登録
        for u in users_data:
            if os.environ.get("DATABASE_URL"):
                cursor.execute("""
                    INSERT INTO employees (user_id, name, department, section, registered_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT(user_id) DO UPDATE SET name=EXCLUDED.name, department=EXCLUDED.department, section=EXCLUDED.section
                """, (u["uid"], u["name"], u["dept"], u["sec"], now))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO employees (user_id, name, department, section, registered_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (u["uid"], u["name"], u["dept"], u["sec"], now))
                
        # ログ500件生成
        for _ in range(500):
            t = now - random.randint(0, 24 * 3600)
            u = random.choice(users_data)["uid"]
            a = random.choice(apps)
            
            click = random.randint(10, 100)
            scroll = random.randint(20, 200)
            dist = random.randint(500, 5000)
            csw = random.randint(1, 15)
            duration = random.randint(10, 300)
            idle = random.randint(0, int(duration * 0.3))
            
            if os.environ.get("DATABASE_URL"):
                cursor.execute("""
                    INSERT INTO client_logs (
                        user_id, app_name, folder_name, file_name, operation_type,
                        manual_typing_count, manual_typing_time, copy_paste_count,
                        duration_seconds, idle_time_seconds, cpu_usage_percent, memory_usage_mb,
                        click_count, scroll_count, mouse_distance, context_switch_count,
                        received_at
                    ) VALUES (
                        %s, %s, '', 'TestDoc.xlsx', 'Editing',
                        %s, 0, %s,
                        %s, %s, 10.0, 500.0,
                        %s, %s, %s, %s,
                        %s
                    )
                """, (u, a, random.randint(0, 50), random.randint(0, 5), duration, idle, click, scroll, dist, csw, t))
            else:
                cursor.execute("""
                    INSERT INTO client_logs (
                        user_id, app_name, folder_name, file_name, operation_type,
                        manual_typing_count, manual_typing_time, copy_paste_count,
                        duration_seconds, idle_time_seconds, cpu_usage_percent, memory_usage_mb,
                        click_count, scroll_count, mouse_distance, context_switch_count,
                        received_at
                    ) VALUES (
                        ?, ?, '', 'TestDoc.xlsx', 'Editing',
                        ?, 0, ?,
                        ?, ?, 10.0, 500.0,
                        ?, ?, ?, ?,
                        ?
                    )
                """, (u, a, random.randint(0, 50), random.randint(0, 5), duration, idle, click, scroll, dist, csw, t))
            
        conn.commit()
        return {"status": "success", "message": "500 mock logs and employees registered successfully"}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()

@router.get("/api/admin/generate_report")
async def generate_report(x_admin_token: str = Header(None, alias="X-Admin-Token")):
    """バッチ処理で夜間レポートを生成"""
    try:
        import batch_processor
        filename = batch_processor.run_nightly_batch()
        
        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), filename) if filename else ""
        if filename and os.path.exists(filepath):
            return FileResponse(filepath)
        else:
            return HTMLResponse("データが不足しているか、レポートが生成されませんでした。", 200)
    except Exception as e:
        return HTMLResponse(f"エラーが発生しました: {str(e)}", 500)
